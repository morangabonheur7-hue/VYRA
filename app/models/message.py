from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MessageSender(str, Enum):
    CONTACT = "contact"
    USER = "user"
    ASSISTANT = "assistant"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    CONTACT = "contact"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    RECEIVED = "received"
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Message:
    TABLE_NAME = "messages"

    def __init__(
        self,
        *,
        message_id: int | None = None,
        conversation_id: int,
        sender: MessageSender | str,
        content: str,
        role: MessageRole | str | None = None,
        status: MessageStatus | str = MessageStatus.RECEIVED,
        is_ai_generated: bool = False,
        requires_approval: bool = False,
        approved_by_user: bool = False,
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        sent_at: datetime | None = None,
    ) -> None:
        self.id = message_id
        self.conversation_id = conversation_id
        self.sender = self._normalize_sender(sender)
        self.content = self._normalize_content(content)

        self.role = self._normalize_role(
            role or self._default_role_for_sender(self.sender)
        )

        self.status = self._normalize_status(status)
        self.is_ai_generated = bool(is_ai_generated)
        self.requires_approval = bool(requires_approval)
        self.approved_by_user = bool(approved_by_user)

        self.external_message_id = (
            external_message_id.strip()
            if external_message_id
            else None
        )

        self.metadata = dict(metadata or {})
        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or self.created_at
        self.sent_at = sent_at

    @staticmethod
    def _normalize_sender(
        sender: MessageSender | str,
    ) -> MessageSender:
        if isinstance(sender, MessageSender):
            return sender

        try:
            return MessageSender(sender.strip().lower())
        except ValueError as exc:
            raise ValueError(
                f"Expéditeur invalide : {sender!r}"
            ) from exc

    @staticmethod
    def _normalize_role(
        role: MessageRole | str,
    ) -> MessageRole:
        if isinstance(role, MessageRole):
            return role

        try:
            return MessageRole(role.strip().lower())
        except ValueError as exc:
            raise ValueError(
                f"Rôle de message invalide : {role!r}"
            ) from exc

    @staticmethod
    def _normalize_status(
        status: MessageStatus | str,
    ) -> MessageStatus:
        if isinstance(status, MessageStatus):
            return status

        try:
            return MessageStatus(status.strip().lower())
        except ValueError as exc:
            raise ValueError(
                f"Statut de message invalide : {status!r}"
            ) from exc

    @staticmethod
    def _normalize_content(content: str) -> str:
        if not isinstance(content, str):
            raise TypeError(
                "Le contenu du message doit être une chaîne de caractères."
            )

        normalized = content.strip()

        if not normalized:
            raise ValueError(
                "Le contenu du message ne peut pas être vide."
            )

        return normalized

    @staticmethod
    def _default_role_for_sender(
        sender: MessageSender,
    ) -> MessageRole:
        mapping = {
            MessageSender.CONTACT: MessageRole.CONTACT,
            MessageSender.USER: MessageRole.USER,
            MessageSender.ASSISTANT: MessageRole.ASSISTANT,
        }

        return mapping[sender]

    @property
    def is_incoming(self) -> bool:
        return self.sender == MessageSender.CONTACT

    @property
    def is_outgoing(self) -> bool:
        return self.sender in {
            MessageSender.USER,
            MessageSender.ASSISTANT,
        }

    @property
    def is_pending(self) -> bool:
        return self.status in {
            MessageStatus.DRAFT,
            MessageStatus.PENDING_APPROVAL,
        }

    @property
    def is_sent(self) -> bool:
        return self.status in {
            MessageStatus.SENT,
            MessageStatus.DELIVERED,
            MessageStatus.READ,
        }

    @property
    def is_successfully_delivered(self) -> bool:
        return self.status in {
            MessageStatus.DELIVERED,
            MessageStatus.READ,
        }

    @classmethod
    def incoming(
        cls,
        *,
        conversation_id: int,
        content: str,
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Message":
        return cls(
            conversation_id=conversation_id,
            sender=MessageSender.CONTACT,
            role=MessageRole.CONTACT,
            content=content,
            status=MessageStatus.RECEIVED,
            is_ai_generated=False,
            requires_approval=False,
            approved_by_user=False,
            external_message_id=external_message_id,
            metadata=metadata,
        )

    @classmethod
    def user_message(
        cls,
        *,
        conversation_id: int,
        content: str,
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Message":
        return cls(
            conversation_id=conversation_id,
            sender=MessageSender.USER,
            role=MessageRole.USER,
            content=content,
            status=MessageStatus.SENT,
            is_ai_generated=False,
            requires_approval=False,
            approved_by_user=True,
            external_message_id=external_message_id,
            metadata=metadata,
        )

    @classmethod
    def ai_draft(
        cls,
        *,
        conversation_id: int,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> "Message":
        return cls(
            conversation_id=conversation_id,
            sender=MessageSender.ASSISTANT,
            role=MessageRole.ASSISTANT,
            content=content,
            status=MessageStatus.PENDING_APPROVAL,
            is_ai_generated=True,
            requires_approval=True,
            approved_by_user=False,
            metadata=metadata,
        )

    def approve(self) -> None:
        if not self.is_ai_generated:
            raise ValueError(
                "Seul un message généré par l'IA "
                "peut nécessiter une validation."
            )

        self.approved_by_user = True
        self.requires_approval = False
        self.status = MessageStatus.APPROVED
        self.touch()

    def reject(self) -> None:
        if not self.is_ai_generated:
            raise ValueError(
                "Seul un message généré par l'IA "
                "peut être rejeté comme proposition IA."
            )

        self.requires_approval = False
        self.approved_by_user = False
        self.status = MessageStatus.CANCELLED
        self.touch()

    def mark_as_sent(
        self,
        sent_at: datetime | None = None,
    ) -> None:
        if self.is_ai_generated and not self.approved_by_user:
            raise ValueError(
                "Une réponse IA doit être approuvée "
                "avant son envoi."
            )

        self.status = MessageStatus.SENT
        self.sent_at = sent_at or utc_now()
        self.touch()

    def mark_as_delivered(self) -> None:
        if not self.is_sent:
            raise ValueError(
                "Un message doit être envoyé avant d'être livré."
            )

        self.status = MessageStatus.DELIVERED
        self.touch()

    def mark_as_read(self) -> None:
        if not self.is_successfully_delivered:
            raise ValueError(
                "Un message doit être livré avant d'être lu."
            )

        self.status = MessageStatus.READ
        self.touch()

    def mark_as_failed(self) -> None:
        self.status = MessageStatus.FAILED
        self.touch()

    def cancel(self) -> None:
        if self.is_sent:
            raise ValueError(
                "Un message déjà envoyé ne peut pas être annulé "
                "comme un brouillon."
            )

        self.status = MessageStatus.CANCELLED
        self.touch()

    def set_metadata(
        self,
        key: str,
        value: Any,
    ) -> None:
        key = key.strip()

        if not key:
            raise ValueError(
                "La clé de métadonnée ne peut pas être vide."
            )

        self.metadata[key] = value
        self.touch()

    def get_metadata(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        return self.metadata.get(key, default)

    def update_content(
        self,
        content: str,
    ) -> None:
        if self.is_sent:
            raise ValueError(
                "Le contenu d'un message déjà envoyé "
                "ne peut pas être modifié."
            )

        self.content = self._normalize_content(content)
        self.touch()

    def touch(self) -> None:
        self.updated_at = utc_now()

    def belongs_to_conversation(
        self,
        conversation_id: int,
    ) -> bool:
        return self.conversation_id == conversation_id

    def can_be_sent(self) -> bool:
        if self.status in {
            MessageStatus.CANCELLED,
            MessageStatus.FAILED,
            MessageStatus.SENT,
            MessageStatus.DELIVERED,
            MessageStatus.READ,
        }:
            return False

        if self.is_ai_generated and not self.approved_by_user:
            return False

        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender": self.sender.value,
            "role": self.role.value,
            "content": self.content,
            "status": self.status.value,
            "is_ai_generated": self.is_ai_generated,
            "requires_approval": self.requires_approval,
            "approved_by_user": self.approved_by_user,
            "external_message_id": self.external_message_id,
            "metadata": self.metadata,
            "is_incoming": self.is_incoming,
            "is_outgoing": self.is_outgoing,
            "is_pending": self.is_pending,
            "is_sent": self.is_sent,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "sent_at": (
                self.sent_at.isoformat()
                if self.sent_at
                else None
            ),
        }

    def to_database_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender": self.sender.value,
            "role": self.role.value,
            "content": self.content,
            "status": self.status.value,
            "is_ai_generated": int(self.is_ai_generated),
            "requires_approval": int(self.requires_approval),
            "approved_by_user": int(self.approved_by_user),
            "external_message_id": self.external_message_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "sent_at": (
                self.sent_at.isoformat()
                if self.sent_at
                else None
            ),
        }

    @classmethod
    def from_row(cls, row: Any) -> "Message":
        """
        Reconstruit un Message depuis SQLite.

        IMPORTANT :
        Les noms Python restent :
            requires_approval
            approved_by_user

        tandis que SQLite utilise :
            requires_human_validation
            is_approved
        """

        def parse_datetime(
            value: Any,
        ) -> datetime | None:
            if value is None:
                return None

            if isinstance(value, datetime):
                return value

            return datetime.fromisoformat(str(value))

        metadata = row["metadata"]

        if isinstance(metadata, str):
            import json

            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        return cls(
            message_id=row["id"],
            conversation_id=row["conversation_id"],
            sender=row["sender"],
            role=row["role"],
            content=row["content"],
            status=row["status"],
            is_ai_generated=bool(row["is_ai_generated"]),

            # Correspondance exacte avec database.py
            requires_approval=bool(
                row["requires_human_validation"]
            ),
            approved_by_user=bool(
                row["is_approved"]
            ),

            external_message_id=row["external_message_id"],
            metadata=metadata or {},
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
            sent_at=parse_datetime(row["sent_at"]),
        )

    def __repr__(self) -> str:
        return (
            f"Message("
            f"id={self.id!r}, "
            f"conversation_id={self.conversation_id!r}, "
            f"sender={self.sender.value!r}, "
            f"role={self.role.value!r}, "
            f"status={self.status.value!r}, "
            f"is_ai_generated={self.is_ai_generated!r}"
            f")"
)
