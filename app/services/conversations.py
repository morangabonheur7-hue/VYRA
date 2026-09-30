import sqlite3
from typing import Any

from app.core.errors import (
    ConflictError,
    ConversationNotFoundError,
    DatabaseError,
)
from app.models.conversation import (
    Conversation,
    ConversationChannel,
    ConversationStatus,
)
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
)


class ConversationService:
    """
    Service métier responsable des conversations VYRA.

    Il gère la création, la récupération, la modification,
    l'archivage et les états des conversations.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        self.connection = connection

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_conversation(
        self,
        *,
        user_id: int,
        data: ConversationCreate,
    ) -> Conversation:
        """
        Crée une conversation pour un contact appartenant
        à l'utilisateur.
        """

        self._ensure_contact_exists(
            user_id=user_id,
            contact_id=data.contact_id,
        )

        if self._conversation_exists(
            user_id=user_id,
            contact_id=data.contact_id,
            channel=data.channel,
        ):
            raise ConflictError(
                "Une conversation active existe déjà "
                "pour ce contact et ce canal."
            )

        conversation = Conversation(
            user_id=user_id,
            contact_id=data.contact_id,
            channel=data.channel,
            status=ConversationStatus.ACTIVE,
            subject=data.subject,
            summary=data.summary,
            ai_enabled=data.ai_enabled,
        )

        query = """
            INSERT INTO conversations (
                user_id,
                contact_id,
                channel,
                status,
                subject,
                summary,
                ai_enabled,
                is_archived,
                created_at,
                updated_at,
                last_message_at,
                closed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        values = (
            conversation.user_id,
            conversation.contact_id,
            conversation.channel.value,
            conversation.status.value,
            conversation.subject,
            conversation.summary,
            int(conversation.ai_enabled),
            int(conversation.is_archived),
            conversation.created_at.isoformat(),
            conversation.updated_at.isoformat(),
            None,
            None,
        )

        try:
            cursor = self.connection.execute(
                query,
                values,
            )
            self.connection.commit()
            conversation.id = cursor.lastrowid
            return conversation

        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ConflictError(
                "Impossible de créer cette conversation.",
                details={"database_error": str(exc)},
            ) from exc

        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError(
                "Une erreur est survenue lors de la création "
                "de la conversation."
            ) from exc

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> Conversation:
        """
        Récupère une conversation appartenant à l'utilisateur.
        """

        query = """
            SELECT *
            FROM conversations
            WHERE id = ?
              AND user_id = ?
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                (
                    conversation_id,
                    user_id,
                ),
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer la conversation."
            ) from exc

        if row is None:
            raise ConversationNotFoundError(
                f"La conversation {conversation_id} "
                "est introuvable."
            )

        return Conversation.from_row(row)

    def list_conversations(
        self,
        *,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        include_archived: bool = False,
        status: ConversationStatus | None = None,
        channel: ConversationChannel | None = None,
        contact_id: int | None = None,
        search: str | None = None,
    ) -> tuple[list[Conversation], int]:
        """
        Retourne les conversations d'un utilisateur
        avec pagination et filtres.
        """

        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size

        conditions = ["user_id = ?"]
        parameters: list[Any] = [user_id]

        if not include_archived:
            conditions.append("is_archived = 0")

        if status is not None:
            conditions.append("status = ?")
            parameters.append(status.value)

        if channel is not None:
            conditions.append("channel = ?")
            parameters.append(channel.value)

        if contact_id is not None:
            conditions.append("contact_id = ?")
            parameters.append(contact_id)

        if search:
            search_value = f"%{search.strip()}%"

            conditions.append(
                """
                (
                    subject LIKE ?
                    OR summary LIKE ?
                )
                """
            )

            parameters.extend(
                [
                    search_value,
                    search_value,
                ]
            )

        where_clause = " AND ".join(conditions)

        count_query = f"""
            SELECT COUNT(*)
            FROM conversations
            WHERE {where_clause}
        """

        data_query = f"""
            SELECT *
            FROM conversations
            WHERE {where_clause}
            ORDER BY
                COALESCE(last_message_at, created_at) DESC
            LIMIT ? OFFSET ?
        """

        try:
            total = int(
                self.connection.execute(
                    count_query,
                    parameters,
                ).fetchone()[0]
            )

            rows = self.connection.execute(
                data_query,
                [
                    *parameters,
                    page_size,
                    offset,
                ],
            ).fetchall()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer les conversations."
            ) from exc

        conversations = [
            Conversation.from_row(row)
            for row in rows
        ]

        return conversations, total

    def get_contact_conversations(
        self,
        *,
        user_id: int,
        contact_id: int,
        include_archived: bool = False,
    ) -> list[Conversation]:
        """
        Retourne toutes les conversations d'un contact.
        """

        conditions = [
            "user_id = ?",
            "contact_id = ?",
        ]

        parameters: list[Any] = [
            user_id,
            contact_id,
        ]

        if not include_archived:
            conditions.append("is_archived = 0")

        query = f"""
            SELECT *
            FROM conversations
            WHERE {" AND ".join(conditions)}
            ORDER BY
                COALESCE(last_message_at, created_at) DESC
        """

        try:
            rows = self.connection.execute(
                query,
                parameters,
            ).fetchall()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de récupérer les conversations "
                "du contact."
            ) from exc

        return [
            Conversation.from_row(row)
            for row in rows
        ]

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
        data: ConversationUpdate,
    ) -> Conversation:
        """
        Modifie une conversation.
        """

        conversation = self.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        update_data = data.model_dump(
            exclude_unset=True,
        )

        if not update_data:
            return conversation

        conversation.update(
            channel=update_data.get("channel"),
            status=update_data.get("status"),
            subject=update_data.get("subject"),
            summary=update_data.get("summary"),
            ai_enabled=update_data.get("ai_enabled"),
        )

        query = """
            UPDATE conversations
            SET
                channel = ?,
                status = ?,
                subject = ?,
                summary = ?,
                ai_enabled = ?,
                is_archived = ?,
                updated_at = ?,
                closed_at = ?
            WHERE id = ?
              AND user_id = ?
        """

        values = (
            conversation.channel.value,
            conversation.status.value,
            conversation.subject,
            conversation.summary,
            int(conversation.ai_enabled),
            int(conversation.is_archived),
            conversation.updated_at.isoformat(),
            (
                conversation.closed_at.isoformat()
                if conversation.closed_at
                else None
            ),
            conversation.id,
            user_id,
        )

        try:
            self.connection.execute(
                query,
                values,
            )
            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError(
                "Impossible de modifier la conversation."
            ) from exc

        return conversation

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------

    def activate_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> Conversation:
        conversation = self.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        conversation.activate()

        self._save_conversation_state(conversation)

        return conversation

    def mark_as_waiting(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> Conversation:
        conversation = self.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        conversation.mark_as_waiting()

        self._save_conversation_state(conversation)

        return conversation

    def close_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> Conversation:
        conversation = self.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        conversation.close()

        self._save_conversation_state(conversation)

        return conversation

    # ------------------------------------------------------------------
    # AI
    # ------------------------------------------------------------------

    def enable_ai(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> Conversation:
        """
        Active l'assistant IA pour une conversation.
        """

        conversation = self.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        conversation.enable_ai()

        self._save_conversation_state(conversation)

        return conversation

    def disable_ai(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> Conversation:
        """
        Désactive l'assistant IA pour une conversation.
        """

        conversation = self.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        conversation.disable_ai()

        self._save_conversation_state(conversation)

        return conversation

    # ------------------------------------------------------------------
    # MESSAGES / ACTIVITY
    # ------------------------------------------------------------------

    def register_message(
        self,
        *,
        user_id: int,
        conversation_id: int,
        message_time=None,
    ) -> Conversation:
        """
        Met à jour la conversation lorsqu'un nouveau message
        est enregistré.
        """

        conversation = self.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        conversation.register_message(
            message_time=message_time,
        )

        self._save_conversation_state(conversation)

        return conversation

    def update_summary(
        self,
        *,
        user_id: int,
        conversation_id: int,
        summary: str | None,
    ) -> Conversation:
        """
        Met à jour le résumé d'une conversation.

        Le résumé pourra plus tard être généré par l'IA.
        """

        conversation = self.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        conversation.update_summary(summary)

        self._save_conversation_state(conversation)

        return conversation

    # ------------------------------------------------------------------
    # ARCHIVE
    # ------------------------------------------------------------------

    def archive_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> Conversation:
        conversation = self.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        conversation.archive()

        self._save_conversation_state(conversation)

        return conversation

    def unarchive_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> Conversation:
        conversation = self.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        conversation.unarchive()

        self._save_conversation_state(conversation)

        return conversation

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> None:
        """
        Supprime définitivement une conversation.

        Cette opération sera utilisée avec prudence car les messages
        associés devront également être traités correctement.
        """

        self.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        query = """
            DELETE FROM conversations
            WHERE id = ?
              AND user_id = ?
        """

        try:
            cursor = self.connection.execute(
                query,
                (
                    conversation_id,
                    user_id,
                ),
            )
            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError(
                "Impossible de supprimer la conversation."
            ) from exc

        if cursor.rowcount == 0:
            raise ConversationNotFoundError(
                f"La conversation {conversation_id} "
                "est introuvable."
            )

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _ensure_contact_exists(
        self,
        *,
        user_id: int,
        contact_id: int,
    ) -> None:
        query = """
            SELECT id
            FROM contacts
            WHERE id = ?
              AND user_id = ?
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                (
                    contact_id,
                    user_id,
                ),
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de vérifier le contact."
            ) from exc

        if row is None:
            raise ConversationNotFoundError(
                "Le contact associé à cette conversation "
                "n'existe pas."
            )

    def _conversation_exists(
        self,
        *,
        user_id: int,
        contact_id: int,
        channel: ConversationChannel,
    ) -> bool:
        query = """
            SELECT 1
            FROM conversations
            WHERE user_id = ?
              AND contact_id = ?
              AND channel = ?
              AND is_archived = 0
              AND status != ?
            LIMIT 1
        """

        try:
            row = self.connection.execute(
                query,
                (
                    user_id,
                    contact_id,
                    channel.value,
                    ConversationStatus.CLOSED.value,
                ),
            ).fetchone()

        except sqlite3.Error as exc:
            raise DatabaseError(
                "Impossible de vérifier la conversation existante."
            ) from exc

        return row is not None

    def _save_conversation_state(
        self,
        conversation: Conversation,
    ) -> None:
        query = """
            UPDATE conversations
            SET
                status = ?,
                ai_enabled = ?,
                is_archived = ?,
                updated_at = ?,
                last_message_at = ?,
                closed_at = ?
            WHERE id = ?
              AND user_id = ?
        """

        try:
            self.connection.execute(
                query,
                (
                    conversation.status.value,
                    int(conversation.ai_enabled),
                    int(conversation.is_archived),
                    conversation.updated_at.isoformat(),
                    (
                        conversation.last_message_at.isoformat()
                        if conversation.last_message_at
                        else None
                    ),
                    (
                        conversation.closed_at.isoformat()
                        if conversation.closed_at
                        else None
                    ),
                    conversation.id,
                    conversation.user_id,
                ),
            )
            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()
            raise DatabaseError(
                "Impossible de sauvegarder l'état "
                "de la conversation."
            ) from exc