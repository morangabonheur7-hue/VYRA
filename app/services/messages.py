import json
import sqlite3
from typing import Any

from app.core.errors import (
    DatabaseError,
)
from app.models.message import (
    Message,
    MessageRole,
    MessageSender,
    MessageStatus,
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

    Ce service constitue la base du contexte conversationnel
    utilisé plus tard par VYRA et Gemini.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        self.connection = connection

    # ==========================================================
    # CREATE
    # ==========================================================

    def create_message(
        self,
        message: Message,
    ) -> Message:
        """
        Enregistre un message dans la base de données.
        """

        query = """
            INSERT INTO messages (
                conversation_id,
                sender,
                role,
                content,
                status,
                is_ai_generated,
                requires_approval,
                approved_by_user,
                external_message_id,
                metadata,
                created_at,
                updated_at,
                sent_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        metadata = json.dumps(
            message.metadata,
            ensure_ascii=False,
        )

        values = (
            message.conversation_id,
            message.sender.value,
            message.role.value,
            message.content,
            message.status.value,
            int(message.is_ai_generated),
            int(message.requires_approval),
            int(message.approved_by_user),
            message.external_message_id,
            metadata,
            message.created_at.isoformat(),
            message.updated_at.isoformat(),
            (
                message.sent_at.isoformat()
                if message.sent_at
                else None
            ),
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

    # ==========================================================
    # READ
    # ==========================================================

    def get_message(
        self,
        *,
        message_id: int,
    ) -> Message | None:
        """
        Récupère un message par son identifiant.
        """

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

    # ==========================================================
    # CONVERSATION HISTORY
    # ==========================================================

    def get_conversation_messages(
        self,
        *,
        conversation_id: int,
        limit: int = 50,
    ) -> list[Message]:
        """
        Récupère les messages d'une conversation.

        Les messages sont retournés dans l'ordre chronologique,
        du plus ancien au plus récent.
        """

        limit = min(
            max(limit, 1),
            200,
        )

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
                (
                    conversation_id,
                    limit,
                ),
            ).fetchall()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer l'historique "
                "de la conversation."
            ) from exc

        messages = [
            Message.from_row(row)
            for row in rows
        ]

        messages.reverse()

        return messages

    # ==========================================================
    # AI CONTEXT
    # ==========================================================

    def get_ai_context(
        self,
        *,
        conversation_id: int,
        limit: int = 20,
    ) -> list[dict[str, str]]:
        """
        Prépare l'historique d'une conversation dans un format
        directement exploitable par le système IA.

        Exemple :

        [
            {
                "role": "user",
                "content": "Bonjour"
            },
            {
                "role": "assistant",
                "content": "Bonjour ! Comment puis-je vous aider ?"
            }
        ]
        """

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
        """
        Convertit le rôle VYRA en rôle compatible avec Gemini.
        """

        if message.role == MessageRole.ASSISTANT:
            return "assistant"

        if message.role == MessageRole.SYSTEM:
            return "system"

        return "user"

    # ==========================================================
    # INCOMING MESSAGE
    # ==========================================================

    def create_incoming_message(
        self,
        *,
        conversation_id: int,
        content: str,
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """
        Crée et enregistre un message reçu d'un contact.
        """

        message = Message.incoming(
            conversation_id=conversation_id,
            content=content,
            external_message_id=external_message_id,
            metadata=metadata,
        )

        return self.create_message(message)

    # ==========================================================
    # USER MESSAGE
    # ==========================================================

    def create_user_message(
        self,
        *,
        conversation_id: int,
        content: str,
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """
        Crée et enregistre un message écrit par l'utilisateur.
        """

        message = Message.user_message(
            conversation_id=conversation_id,
            content=content,
            external_message_id=external_message_id,
            metadata=metadata,
        )

        return self.create_message(message)

    # ==========================================================
    # AI MESSAGE
    # ==========================================================

    def create_ai_draft(
        self,
        *,
        conversation_id: int,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """
        Crée et enregistre une réponse proposée par VYRA.

        La réponse reste en attente de validation humaine.
        """

        message = Message.ai_draft(
            conversation_id=conversation_id,
            content=content,
            metadata=metadata,
        )

        return self.create_message(message)

    # ==========================================================
    # EXTERNAL MESSAGE SEARCH
    # ==========================================================

    def get_by_external_id(
        self,
        *,
        external_message_id: str,
    ) -> Message | None:
        """
        Recherche un message provenant d'un service externe,
        par exemple WhatsApp.
        """

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
                "Impossible de rechercher le message externe."
            ) from exc

        if row is None:
            return None

        return Message.from_row(row)

    # ==========================================================
    # UPDATE STATUS
    # ==========================================================

    def update_message(
        self,
        message: Message,
    ) -> Message:
        """
        Sauvegarde l'état actuel d'un message.
        """

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
                requires_approval = ?,
                approved_by_user = ?,
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

        values = (
            message.content,
            message.role.value,
            message.status.value,
            int(message.is_ai_generated),
            int(message.requires_approval),
            int(message.approved_by_user),
            message.external_message_id,
            metadata,
            message.updated_at.isoformat(),
            (
                message.sent_at.isoformat()
                if message.sent_at
                else None
            ),
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

    # ==========================================================
    # APPROVAL
    # ==========================================================

    def approve_message(
        self,
        *,
        message_id: int,
    ) -> Message:
        """
        Approuve une réponse IA.
        """

        message = self.get_message(
            message_id=message_id,
        )

        if message is None:
            raise DatabaseError(
                "Message introuvable."
            )

        message.approve()

        return self.update_message(message)

    # ==========================================================
    # REJECT
    # ==========================================================

    def reject_message(
        self,
        *,
        message_id: int,
    ) -> Message:
        """
        Rejette une réponse IA.
        """

        message = self.get_message(
            message_id=message_id,
        )

        if message is None:
            raise DatabaseError(
                "Message introuvable."
            )

        message.reject()

        return self.update_message(message)

    # ==========================================================
    # SENT
    # ==========================================================

    def mark_as_sent(
        self,
        *,
        message_id: int,
    ) -> Message:
        """
        Marque un message comme envoyé.
        """

        message = self.get_message(
            message_id=message_id,
        )

        if message is None:
            raise DatabaseError(
                "Message introuvable."
            )

        message.mark_as_sent()

        return self.update_message(message)

    # ==========================================================
    # DELETE
    # ==========================================================

    def delete_message(
        self,
        *,
        message_id: int,
    ) -> None:
        """
        Supprime définitivement un message.
        """

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