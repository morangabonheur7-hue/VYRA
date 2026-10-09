from __future__ import annotations

from typing import Any

from psycopg import Connection

from app.ai.gateway import AIGateway, AIRequest
from app.services.conversations import ConversationService
from app.services.messages import MessageService


class AIProcessor:
    """Transforme un message entrant en réponse IA."""

    def __init__(self, connection: Connection):
        self.connection = connection
        self.conversations = ConversationService(connection)
        self.messages = MessageService(connection)
        self.ai = AIGateway()

    def process(
        self,
        conversation_id: int,
        user_message: str,
    ) -> dict[str, Any]:

        history = self.messages.list_by_conversation(
            conversation_id=conversation_id,
            limit=20,
        )

        messages: list[dict[str, str]] = []

        for item in history:
            role = item.get("role", "user")
            content = item.get("content", "")

            if content:
                messages.append(
                    {
                        "role": role,
                        "content": content,
                    }
                )

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        request = AIRequest(
            messages=messages,
        )

        response = self.ai.generate(request)

        text = response.text.strip()

        if not text:
            raise RuntimeError(
                "Le fournisseur IA n'a retourné aucune réponse."
            )

        saved = self.messages.create(
            conversation_id=conversation_id,
            role="assistant",
            content=text,
            metadata={
                "source": "ai",
                "provider": response.provider,
                "model": response.model,
            },
        )

        return {
            "text": text,
            "message": saved,
        }
