from __future__ import annotations

from typing import Any

from psycopg import Connection

from app.core.errors import VYRAError
from app.services.whatsapp_cloud import WhatsAppCloudService


class WhatsAppWorker:
    """
    Exécute les actions WhatsApp persistées dans ai_actions.
    """

    def __init__(self, connection: Connection):
        self.connection = connection
        self.whatsapp = WhatsAppCloudService(connection)

    def send_text(
        self,
        company_id: int,
        recipient: str,
        message: str,
        *,
        reply_to_message_id: str | None = None,
    ) -> dict[str, Any]:

        if not company_id:
            raise VYRAError(
                "WHATSAPP_COMPANY_REQUIRED",
                "company_id est obligatoire.",
            )

        if not recipient:
            raise VYRAError(
                "WHATSAPP_RECIPIENT_REQUIRED",
                "Le destinataire WhatsApp est obligatoire.",
            )

        if not message:
            raise VYRAError(
                "WHATSAPP_MESSAGE_REQUIRED",
                "Le message WhatsApp est vide.",
            )

        result = self.whatsapp.send_text(
            company_id=company_id,
            recipient=recipient,
            text=message,
            reply_to_message_id=reply_to_message_id,
        )

        if not result.success:
            raise VYRAError(
                "WHATSAPP_SEND_FAILED",
                result.error or "Échec de l'envoi WhatsApp.",
            )

        return {
            "success": True,
            "message_id": result.message_id,
            "response": result.raw_response,
        }

    def execute_action(
        self,
        action: dict[str, Any],
    ) -> dict[str, Any]:

        payload = action.get("payload") or {}

        company_id = payload.get("company_id")
        recipient = (
            payload.get("recipient")
            or payload.get("phone_number")
            or payload.get("to")
        )
        message = (
            payload.get("message")
            or payload.get("message_text")
            or ""
        )

        reply_to_message_id = payload.get(
            "reply_to_message_id"
        )

        return self.send_text(
            company_id=int(company_id),
            recipient=str(recipient),
            message=str(message),
            reply_to_message_id=reply_to_message_id,
        )