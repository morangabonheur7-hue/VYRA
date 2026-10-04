from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from psycopg import Connection

from app.core.database import get_db
from app.services.webhooks import WebhookService
from app.services.whatsapp_cloud import WhatsAppCloudService


router = APIRouter(
    prefix="/whatsapp/cloud",
    tags=["WhatsApp Cloud"],
)


@router.get("/webhook")
def verify_webhook(
    request: Request,
    db: Connection = Depends(get_db),
):
    """
    Vérification initiale du webhook Meta.
    """

    params = request.query_params

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    service = WhatsAppCloudService(db)

    result = service.verify_webhook(
        mode=mode,
        token=token,
        challenge=challenge,
    )

    if result is None:
        raise HTTPException(
            status_code=403,
            detail="Webhook verification failed",
        )

    return PlainTextResponse(
        content=result,
        status_code=200,
    )


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(
        default=None,
        alias="X-Hub-Signature-256",
    ),
    db: Connection = Depends(get_db),
):
    """
    Réception des événements WhatsApp Cloud.

    Le webhook :
    1. vérifie la signature ;
    2. parse le JSON ;
    3. enregistre l'événement ;
    4. répond immédiatement à Meta.
    """

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

    entries = payload.get("entry", [])

    for entry in entries:
        changes = entry.get("changes", [])

        for change in changes:
            value = change.get("value", {})
            field = change.get("field", "unknown")

            metadata = value.get("metadata", {})

            phone_number_id = metadata.get(
                "phone_number_id"
            )

            integration = None

            if phone_number_id:
                integration = (
                    whatsapp._get_integration_by_phone_number_id(
                        phone_number_id
                    )
                )

            company_id = None
            integration_id = None

            if integration:
                company_id = integration["company_id"]
                integration_id = integration["id"]

            webhook_service.create(
                provider="whatsapp",
                event_type=field,
                payload={
                    "entry": entry,
                    "change": change,
                },
                company_id=company_id,
                integration_id=integration_id,
            )

    return {
        "success": True,
    }