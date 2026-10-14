from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from psycopg import Connection

from app.ai.gateway import AIRequest, ai_gateway
from app.core.database import get_db
from app.services.webhooks import WebhookService
from app.services.whatsapp_cloud import WhatsAppCloudService

router = APIRouter(
    prefix="/whatsapp/cloud",
    tags=["WhatsApp Cloud"],
)

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _business_context(integration: dict[str, Any]) -> str:
    """Récupère uniquement les informations commerciales autorisées."""

    configuration = integration.get("configuration", {})

    if isinstance(configuration, str):
        try:
            configuration = json.loads(configuration)
        except (json.JSONDecodeError, TypeError):
            configuration = {}

    if not isinstance(configuration, dict):
        configuration = {}

    allowed_keys = {
        "business_profile",
        "profile",
        "business_name",
        "company_name",
        "business_description",
        "description",
        "products",
        "services",
        "prices",
        "stock",
        "currency",
        "opening_hours",
        "address",
        "language",
        "instructions",
        "faq",
        "tone",
    }

    context = {
        key: configuration[key]
        for key in allowed_keys
        if key in configuration
    }

    if not context:
        return (
            "Aucune fiche commerciale détaillée n'est disponible. "
            "Réponds poliment et naturellement. Ne devine jamais "
            "les prix, le stock, les horaires ou les caractéristiques "
            "des produits. Si une information manque, demande une "
            "précision ou indique qu'elle doit être confirmée."
        )

    return (
        "Informations commerciales de cette entreprise :\n"
        + json.dumps(context, ensure_ascii=False, default=str)
        + "\nUtilise uniquement les informations disponibles. "
        "Ne fabrique jamais de prix, de stock ou de promesse."
    )


def _save_event(
    db: Connection,
    *,
    company_id: int,
    external_message_id: str,
    payload: dict[str, Any],
) -> bool:
    """Enregistre un message une seule fois pour cette entreprise."""

    now = _now()

    row = db.execute(
        """
        INSERT INTO webhook_events (
            company_id,
            provider,
            external_event_id,
            event_type,
            payload,
            status,
            attempts,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (
            company_id,
            provider,
            external_event_id
        ) DO NOTHING
        RETURNING id
        """,
        (
            company_id,
            "whatsapp",
            external_message_id,
            "incoming_message",
            json.dumps(payload, ensure_ascii=False),
            "received",
            0,
            now,
            now,
        ),
    ).fetchone()

    db.commit()
    return row is not None


def _update_event_status(
    db: Connection,
    *,
    company_id: int,
    external_message_id: str,
    status: str,
    error: str | None = None,
) -> None:
    db.execute(
        """
        UPDATE webhook_events
        SET status = %s,
            error = %s,
            updated_at = %s,
            processed_at = %s
        WHERE company_id = %s
          AND provider = %s
          AND external_event_id = %s
        """,
        (
            status,
            error,
            _now(),
            _now() if status == "processed" else None,
            company_id,
            "whatsapp",
            external_message_id,
        ),
    )
    db.commit()


@router.get("/webhook")
def verify_webhook(
    request: Request,
    db: Connection = Depends(get_db),
):
    """Vérification initiale du webhook Meta."""

    params = request.query_params

    result = WhatsAppCloudService(db).verify_webhook(
        mode=params.get("hub.mode"),
        token=params.get("hub.verify_token"),
        challenge=params.get("hub.challenge"),
    )

    if result is None:
        raise HTTPException(
            status_code=403,
            detail="Webhook verification failed",
        )

    return PlainTextResponse(content=result, status_code=200)


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(
        default=None,
        alias="X-Hub-Signature-256",
    ),
    db: Connection = Depends(get_db),
):
    """Reçoit les événements WhatsApp et traite les messages texte."""

    raw_body = await request.body()
    whatsapp = WhatsAppCloudService(db)

    if not whatsapp.verify_signature(
        raw_body,
        x_hub_signature_256,
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook signature",
        )

    try:
        payload: dict[str, Any] = json.loads(
            raw_body.decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    webhook_service = WebhookService(db)
    processed = 0

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            field = change.get("field", "unknown")
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")

            integration = None

            if phone_number_id:
                integration = (
                    whatsapp._get_integration_by_phone_number_id(
                        str(phone_number_id)
                    )
                )

            company_id = (
                integration.get("company_id")
                if integration
                else None
            )

            # Conserve également les événements de statut Meta.
            if field != "messages":
                webhook_service.create(
                    provider="whatsapp",
                    event_type=field,
                    payload={"entry": entry, "change": change},
                    company_id=company_id,
                    integration_id=(
                        integration.get("id") if integration else None
                    ),
                )
                continue

            # Sans intégration active reconnue, aucune réponse n'est envoyée.
            if not integration or company_id is None:
                continue

            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue

                sender = message.get("from")
                text_body = (
                    message.get("text", {}).get("body", "").strip()
                )
                message_id = message.get("id")

                if not sender or not text_body or not message_id:
                    continue

                # Évite de traiter deux fois le même message Meta.
                try:
                    is_new = _save_event(
                        db,
                        company_id=int(company_id),
                        external_message_id=str(message_id),
                        payload=message,
                    )
                except Exception:
                    db.rollback()
                    logger.exception("Impossible d'enregistrer le message.")
                    raise

                if not is_new:
                    continue

                try:
                    system_prompt = (
                        "Tu es l'assistant commercial WhatsApp de "
                        "l'entreprise configurée dans VYRA. "
                        "Réponds dans la langue du client, avec un ton "
                        "naturel, clair et professionnel. Sois concis. "
                        "Ne prétends jamais qu'une commande est confirmée "
                        "si tu ne peux pas le vérifier. Ne demande pas "
                        "de mots de passe ni de données de paiement. "
                        "Informations de l'entreprise :\n"
                        + _business_context(integration)
                    )

                    ai_response = ai_gateway.generate(
                        AIRequest(
                            messages=[
                                {
                                    "role": "user",
                                    "content": text_body,
                                }
                            ],
                            system_prompt=system_prompt,
                            temperature=0.4,
                            max_tokens=400,
                            timeout_seconds=25,
                            metadata={
                                "company_id": int(company_id),
                                "channel": "whatsapp",
                            },
                        )
                    )

                    reply = ai_response.text.strip()

                    if not reply:
                        raise RuntimeError(
                            "Le fournisseur IA a retourné une réponse vide."
                        )

                    result = whatsapp.send_text(
                        company_id=int(company_id),
                        recipient=str(sender),
                        text=reply,
                        reply_to_message_id=str(message_id),
                    )

                    if not result.success:
                        raise RuntimeError(
                            result.error or "Échec de l'envoi WhatsApp."
                        )

                    _update_event_status(
                        db,
                        company_id=int(company_id),
                        external_message_id=str(message_id),
                        status="processed",
                    )
                    processed += 1

                except Exception as exc:
                    db.rollback()

                    logger.exception(
                        "Échec du traitement d'un message WhatsApp."
                    )

                    try:
                        _update_event_status(
                            db,
                            company_id=int(company_id),
                            external_message_id=str(message_id),
                            status="failed",
                            error=str(exc)[:1000],
                        )
                    except Exception:
                        db.rollback()
                        logger.exception(
                            "Impossible de sauvegarder l'échec du message."
                        )

    return {
        "success": True,
        "processed": processed,
}
