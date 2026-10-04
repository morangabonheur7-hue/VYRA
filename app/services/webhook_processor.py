from __future__ import annotations

from typing import Any

from psycopg import Connection

from app.services.webhooks import WebhookService
from app.services.whatsapp_cloud import WhatsAppCloudService
from app.services.contacts import ContactService
from app.services.conversations import ConversationService
from app.services.messages import MessageService


class WebhookProcessor:

    def __init__(self, connection: Connection):
        self.connection = connection
        self.webhooks = WebhookService(connection)
        self.whatsapp = WhatsAppCloudService(connection)
        self.contacts = ContactService(connection)
        self.conversations = ConversationService(connection)
        self.messages = MessageService(connection)

    def process(self, event_id: str) -> dict[str, Any]:
        event = self.webhooks.claim(event_id)

        if event is None:
            return {
                "success": True,
                "processed": False,
                "reason": "already_processing_or_processed",
            }

        try:
            payload = event["payload"]

            if isinstance(payload, str):
                import json
                payload = json.loads(payload)

            result = self._process_payload(
                payload,
                event,
            )

            self.webhooks.mark_processed(event_id)

            return {
                "success": True,
                "processed": True,
                "result": result,
            }

        except Exception as exc:
            self.webhooks.mark_failed(
                event_id,
                str(exc),
            )
            raise

    def _process_payload(
        self,
        payload: dict[str, Any],
        event: dict[str, Any],
    ) -> dict[str, Any]:

        messages_found = 0
        statuses_found = 0

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                for message in value.get("messages", []):
                    self._process_message(
                        message=message,
                        value=value,
                        event=event,
                    )
                    messages_found += 1

                statuses_found += len(
                    value.get("statuses", [])
                )

        return {
            "messages": messages_found,
            "statuses": statuses_found,
        }

    def _process_message(
        self,
        message: dict[str, Any],
        value: dict[str, Any],
        event: dict[str, Any],
    ) -> None:

        phone = message.get("from")

        if not phone:
            return

        company_id = event.get("company_id")

        if not company_id:
            phone_number_id = (
                value.get("metadata", {})
                .get("phone_number_id")
            )

            integration = (
                self.whatsapp
                ._get_integration_by_phone_number_id(
                    phone_number_id
                )
            ) if phone_number_id else None

            if integration:
                company_id = integration["company_id"]

        if not company_id:
            return

        text = self._extract_text(message)

        if not text:
            return

        contact = self.contacts.get_or_create(
            user_id=company_id,
            phone=phone,
        )

        conversation = (
            self.conversations.get_or_create_active(
                user_id=company_id,
                contact_id=contact["id"],
                channel="whatsapp",
            )
        )

        self.messages.create(
            conversation_id=conversation["id"],
            role="user",
            content=text,
            external_message_id=message.get("id"),
            metadata={
                "whatsapp_message": message,
            },
        )

    @staticmethod
    def _extract_text(
        message: dict[str, Any],
    ) -> str | None:

        message_type = message.get("type")

        if message_type == "text":
            return (
                message.get("text", {})
                .get("body")
            )

        return None