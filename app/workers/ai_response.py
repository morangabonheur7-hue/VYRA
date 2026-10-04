from __future__ import annotations

from typing import Any

from psycopg import Connection

from app.services.ai_processor import AIProcessor
from app.services.whatsapp_cloud import WhatsAppCloudService


class AIResponseWorker:

    def __init__(self, connection: Connection):
        self.connection = connection
        self.ai = AIProcessor(connection)
        self.whatsapp = WhatsAppCloudService(connection)

    def execute(
        self,
        action: dict[str, Any],
    ) -> dict[str, Any]:

        payload = action.get("payload") or {}

        conversation_id = payload.get(
            "conversation_id"
        )
        company_id = payload.get(
            "company_id"
        )
        recipient = payload.get(
            "recipient"
        )
        user_message = payload.get(
            "message_text"
        ) or payload.get("message")

        if not conversation_id:
            raise ValueError(
                "conversation_id manquant."
            )

        if not company_id:
            raise ValueError(
                "company_id manquant."
            )

        if not recipient:
            raise ValueError(
                "recipient manquant."
            )

        if not user_message:
            raise ValueError(
                "message utilisateur manquant."
            )

        result = self.ai.process(
            conversation_id=int(conversation_id),
            user_message=str(user_message),
        )

        sent = self.whatsapp.send_text(
            company_id=int(company_id),
            recipient=str(recipient),
            text=result["text"],
        )

        if not sent.success:
            raise RuntimeError(
                sent.error
                or "Impossible d'envoyer la réponse WhatsApp."
            )

        return {
            "success": True,
            "conversation_id": conversation_id,
            "message_id": sent.message_id,
            "text": result["text"],
        }