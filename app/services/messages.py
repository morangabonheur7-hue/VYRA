import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.core.errors import DatabaseError
from app.models.message import (
    Message,
    MessageRole,
    MessageSender,
)


class MessageService:
    """
    Service métier responsable des messages VYRA.

    Il gère :
        - la création des messages ;
        - la récupération des messages ;
        - l'historique d'une conversation ;
        - les messages entrants ;
        - les réponses IA ;
        - les statuts des messages.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        self.connection = connection

    def create_message(self, message: Message) -> Message:
        query = """
            INSERT INTO messages (
                conversation_id,
                sender,
                role,
                content,
                status,
                is_ai_generated,
                requires_human_validation,
                is_approved,
                approved_at,
                external_message_id,
                metadata,
                created_at,
                updated_at,
                sent_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        metadata = json.dumps(
            message.metadata,
            ensure_ascii=False,
        )

        approved_at = None

        if message.approved_by_user:
            approved_at = datetime.now(
                timezone.utc
            ).isoformat()

        values = (
            message.conversation_id,
            message.sender.value,
            message.role.value,
            message.content,
            message.status.value,
            int(message.is_ai_generated),
            int(message.requires_approval),
            int(message.approved_by_user),
            approved_at,
            message.external_message_id,
            metadata,
            message.created_at.isoformat(),
            message.updated_at.isoformat(),
            message.sent_at.isoformat()
            if message.sent_at
            else None,
        )

        try:
            cursor = self.connection.execute(
                query,
                values,
            )
            self.connection.commit()

            message.id = cursor.lastrowid

            return message

        except sqlite3.IntegrityError as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible d'enregistrer le message.",
                details={
                    "database_error": str(exc),
                },
            ) from exc

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Une erreur est survenue lors de "
                "l'enregistrement du message."
            ) from exc

    def get_message(
        self,
        *,
        message_id: int,
    ) -> Message | None:

        query = """
            SELECT *
            FROM messages
            WHERE id = ?
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                (message_id,),
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer le message."
            ) from exc

        if row is None:
            return None

        return Message.from_row(row)

    def get_conversation_messages(
        self,
        *,
        conversation_id: int,
        limit: int = 50,
    ) -> list[Message]:

        limit = min(max(limit, 1), 200)

        query = """
            SELECT *
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """

        try:
            rows = self.connection.execute(
                query,
                (conversation_id, limit),
            ).fetchall()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer "
                "l'historique de la conversation."
            ) from exc

        messages = [
            Message.from_row(row)
            for row in rows
        ]

        messages.reverse()

        return messages

    def get_ai_context(
        self,
        *,
        conversation_id: int,
        limit: int = 20,
    ) -> list[dict[str, str]]:

        messages = self.get_conversation_messages(
            conversation_id=conversation_id,
            limit=limit,
        )

        context: list[dict[str, str]] = []

        for message in messages:
            role = self._ai_role(message)

            context.append(
                {
                    "role": role,
                    "content": message.content,
                }
            )

        return context

    @staticmethod
    def _ai_role(
        message: Message,
    ) -> str:

        if message.role == MessageRole.ASSISTANT:
            return "assistant"

        if message.role == MessageRole.SYSTEM:
            return "system"

        return "user"

    def create_incoming_message(
        self,
        *,
        conversation_id: int,
        content: str,
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:

        message = Message.incoming(
            conversation_id=conversation_id,
            content=content,
            external_message_id=external_message_id,
            metadata=metadata,
        )

        return self.create_message(message)

    def create_user_message(
        self,
        *,
        conversation_id: int,
        content: str,
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:

        message = Message.user_message(
            conversation_id=conversation_id,
            content=content,
            external_message_id=external_message_id,
            metadata=metadata,
        )

        return self.create_message(message)

    def create_ai_draft(
        self,
        *,
        conversation_id: int,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:

        message = Message.ai_draft(
            conversation_id=conversation_id,
            content=content,
            metadata=metadata,
        )

        return self.create_message(message)

    def get_by_external_id(
        self,
        *,
        external_message_id: str,
    ) -> Message | None:

        query = """
            SELECT *
            FROM messages
            WHERE external_message_id = ?
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                (external_message_id,),
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de rechercher "
                "le message externe."
            ) from exc

        if row is None:
            return None

        return Message.from_row(row)

    def update_message(
        self,
        message: Message,
    ) -> Message:

        if message.id is None:
            raise DatabaseError(
                "Impossible de modifier un message "
                "qui n'est pas encore enregistré."
            )

        query = """
            UPDATE messages
            SET
                content = ?,
                role = ?,
                status = ?,
                is_ai_generated = ?,
                requires_human_validation = ?,
                is_approved = ?,
                approved_at = ?,
                external_message_id = ?,
                metadata = ?,
                updated_at = ?,
                sent_at = ?
            WHERE id = ?
        """

        metadata = json.dumps(
            message.metadata,
            ensure_ascii=False,
        )

        approved_at = None

        if message.approved_by_user:
            approved_at = datetime.now(
                timezone.utc
            ).isoformat()

        values = (
            message.content,
            message.role.value,
            message.status.value,
            int(message.is_ai_generated),
            int(message.requires_approval),
            int(message.approved_by_user),
            approved_at,
            message.external_message_id,
            metadata,
            message.updated_at.isoformat(),
            message.sent_at.isoformat()
            if message.sent_at
            else None,
            message.id,
        )

        try:
            self.connection.execute(
                query,
                values,
            )

            self.connection.commit()

            return message

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de modifier le message."
            ) from exc

    def approve_message(
        self,
        *,
        message_id: int,
    ) -> Message:

        message = self.get_message(
            message_id=message_id
        )

        if message is None:
            raise DatabaseError(
                "Message introuvable."
            )

        message.approve()

        return self.update_message(message)

    def reject_message(
        self,
        *,
        message_id: int,
    ) -> Message:

        message = self.get_message(
            message_id=message_id
        )

        if message is None:
            raise DatabaseError(
                "Message introuvable."
            )

        message.reject()

        return self.update_message(message)

    def mark_as_sent(
        self,
        *,
        message_id: int,
    ) -> Message:

        message = self.get_message(
            message_id=message_id
        )

        if message is None:
            raise DatabaseError(
                "Message introuvable."
            )

        message.mark_as_sent()

        return self.update_message(message)

    def delete_message(
        self,
        *,
        message_id: int,
    ) -> None:

        query = """
            DELETE FROM messages
            WHERE id = ?
        """

        try:
            cursor = self.connection.execute(
                query,
                (message_id,),
            )

            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()

            raise DatabaseError(
                "Impossible de supprimer le message."
            ) from exc

        if cursor.rowcount == 0:
            raise DatabaseError(
                "Message introuvable."
    )
