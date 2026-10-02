import sqlite3
from typing import Any

from fastapi import APIRouter

from app.ai.gateway import AIRequest, ai_gateway
from app.core.database import create_connection
from app.core.errors import VYRAError
from app.services.messages import MessageService


router = APIRouter(
    prefix="/whatsapp",
    tags=["WhatsApp"],
)


SYSTEM_PROMPT = """
Tu es VYRA, un assistant IA commercial et personnel.

Tu réponds naturellement, clairement et brièvement
aux messages reçus sur WhatsApp.

Tu aides l'utilisateur dans ses échanges avec ses clients
et prospects.

Utilise l'historique de la conversation pour comprendre
le contexte et éviter de répéter inutilement les mêmes
questions.

Réponds dans la langue utilisée par ton interlocuteur.

Ne prétends jamais avoir effectué une action que tu n'as
pas réellement effectuée.

Si une information manque, pose simplement la question
nécessaire.
""".strip()


def _get_active_user_id(
    connection: sqlite3.Connection,
) -> int:
    """
    Pour le webhook WhatsApp V1, récupère le premier
    utilisateur actif de VYRA.

    VYRA V1 fonctionne actuellement avec notre compte
    principal. Le routage multi-utilisateur pourra être
    ajouté plus tard.
    """

    query = """
        SELECT id
        FROM users
        WHERE is_active = 1
        ORDER BY id ASC
        LIMIT 1
    """

    row = connection.execute(query).fetchone()

    if row is None:
        raise VYRAError(
            message="Aucun utilisateur VYRA actif n'est disponible.",
        )

    return int(row["id"])


def _get_or_create_contact(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    sender: str,
) -> int:
    """
    Recherche le contact WhatsApp grâce à son numéro.

    S'il n'existe pas encore, VYRA crée automatiquement
    un contact minimal.
    """

    query = """
        SELECT id
        FROM contacts
        WHERE user_id = ?
          AND phone = ?
          AND is_archived = 0
        LIMIT 1
    """

    row = connection.execute(
        query,
        (user_id, sender),
    ).fetchone()

    if row is not None:
        return int(row["id"])

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    insert_query = """
        INSERT INTO contacts (
            user_id,
            first_name,
            last_name,
            phone,
            status,
            source,
            is_archived,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
    """

    cursor = connection.execute(
        insert_query,
        (
            user_id,
            sender,
            "",
            sender,
            "new",
            "whatsapp",
            now,
            now,
        ),
    )

    connection.commit()

    if cursor.lastrowid is None:
        raise VYRAError(
            message="Impossible de créer le contact WhatsApp.",
        )

    return int(cursor.lastrowid)


def _get_or_create_conversation(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    contact_id: int,
) -> int:
    """
    Recherche la conversation WhatsApp active du contact.

    Une seule conversation active est réutilisée afin que
    Gemini puisse conserver le contexte.
    """

    query = """
        SELECT id
        FROM conversations
        WHERE user_id = ?
          AND contact_id = ?
          AND channel = 'whatsapp'
          AND status = 'active'
          AND is_archived = 0
        ORDER BY id DESC
        LIMIT 1
    """

    row = connection.execute(
        query,
        (user_id, contact_id),
    ).fetchone()

    if row is not None:
        return int(row["id"])

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    insert_query = """
        INSERT INTO conversations (
            user_id,
            contact_id,
            channel,
            status,
            ai_enabled,
            is_archived,
            created_at,
            updated_at
        )
        VALUES (?, ?, 'whatsapp', 'active', 1, 0, ?, ?)
    """

    cursor = connection.execute(
        insert_query,
        (
            user_id,
            contact_id,
            now,
            now,
        ),
    )

    connection.commit()

    if cursor.lastrowid is None:
        raise VYRAError(
            message="Impossible de créer la conversation WhatsApp.",
        )

    return int(cursor.lastrowid)


@router.post("/webhook")
async def whatsapp_webhook(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Reçoit un message WhatsApp via AutoResponder,
    conserve l'historique et génère une réponse avec Gemini.
    """

    query = payload.get("query", {})

    if not isinstance(query, dict):
        query = {}

    message = str(
        query.get("message", "")
    ).strip()

    if not message:
        return {
            "replies": []
        }

    # AutoResponder fournit normalement l'expéditeur
    # dans query.sender.
    sender = str(
        query.get("sender")
        or query.get("phone")
        or "whatsapp_unknown"
    ).strip()

    external_message_id = query.get(
        "message_id"
    )

    connection = create_connection()

    try:
        user_id = _get_active_user_id(
            connection
        )

        contact_id = _get_or_create_contact(
            connection,
            user_id=user_id,
            sender=sender,
        )

        conversation_id = _get_or_create_conversation(
            connection,
            user_id=user_id,
            contact_id=contact_id,
        )

        message_service = MessageService(
            connection
        )

        # 1. Enregistrer le message reçu.
        message_service.create_incoming_message(
            conversation_id=conversation_id,
            content=message,
            external_message_id=(
                str(external_message_id)
                if external_message_id
                else None
            ),
            metadata={
                "channel": "whatsapp",
                "sender": sender,
            },
        )

        # 2. Récupérer l'historique.
        history = message_service.get_ai_context(
            conversation_id=conversation_id,
            limit=20,
        )

        # 3. Envoyer tout le contexte à Gemini.
        response = ai_gateway.generate(
            AIRequest(
                messages=history,
                system_prompt=SYSTEM_PROMPT,
            )
        )

        reply = response.text.strip()

        if not reply:
            reply = (
                "Je suis VYRA. "
                "Comment puis-je vous aider ?"
            )

        # 4. Enregistrer la réponse de VYRA.
        message_service.create_ai_draft(
            conversation_id=conversation_id,
            content=reply,
            metadata={
                "channel": "whatsapp",
                "provider": response.provider,
                "model": response.model,
            },
        )

        # 5. Retour AutoResponder.
        return {
            "replies": [
                {
                    "message": reply,
                }
            ]
        }

    except VYRAError:
        raise

    except Exception as exc:
        raise VYRAError(
            message="VYRA WhatsApp webhook failed.",
            details={
                "error": str(exc),
            },
        ) from exc

    finally:
        connection.close()
