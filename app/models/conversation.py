from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    """
    Retourne la date et l'heure actuelles en UTC.
    """

    return datetime.now(timezone.utc)


class ConversationStatus(str, Enum):
    """
    Statut actuel d'une conversation.
    """

    ACTIVE = "active"
    WAITING = "waiting"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ConversationChannel(str, Enum):
    """
    Canal utilisé pour la conversation.

    VYRA V1 commence avec une architecture qui peut accueillir
    plusieurs canaux, même si WhatsApp est notre priorité.
    """

    WHATSAPP = "whatsapp"
    EMAIL = "email"
    PHONE = "phone"
    SMS = "sms"
    INSTAGRAM = "instagram"
    TELEGRAM = "telegram"
    OTHER = "other"


class Conversation:
    """
    Modèle représentant une conversation VYRA.

    Une conversation appartient à un utilisateur et est associée
    à un contact.

    Les messages individuels seront gérés séparément par
    le modèle Message.
    """

    TABLE_NAME = "conversations"

    def __init__(
        self,
        *,
        conversation_id: int | None = None,
        user_id: int,
        contact_id: int,
        channel: ConversationChannel | str = ConversationChannel.WHATSAPP,
        status: ConversationStatus | str = ConversationStatus.ACTIVE,
        subject: str | None = None,
        summary: str | None = None,
        ai_enabled: bool = True,
        is_archived: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        last_message_at: datetime | None = None,
        closed_at: datetime | None = None,
    ) -> None:
        self.id = conversation_id

        self.user_id = user_id
        self.contact_id = contact_id

        self.channel = self._normalize_channel(channel)
        self.status = self._normalize_status(status)

        self.subject = (
            subject.strip()
            if subject
            else None
        )

        self.summary = (
            summary.strip()
            if summary
            else None
        )

        self.ai_enabled = bool(ai_enabled)
        self.is_archived = bool(is_archived)

        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or self.created_at

        self.last_message_at = last_message_at
        self.closed_at = closed_at

    # ==========================================================
    # NORMALISATION
    # ==========================================================

    @staticmethod
    def _normalize_channel(
        channel: ConversationChannel | str,
    ) -> ConversationChannel:
        """
        Convertit une valeur en ConversationChannel.
        """

        if isinstance(channel, ConversationChannel):
            return channel

        try:
            return ConversationChannel(
                channel.strip().lower()
            )
        except ValueError as exc:
            raise ValueError(
                f"Canal de conversation invalide : {channel!r}"
            ) from exc

    @staticmethod
    def _normalize_status(
        status: ConversationStatus | str,
    ) -> ConversationStatus:
        """
        Convertit une valeur en ConversationStatus.
        """

        if isinstance(status, ConversationStatus):
            return status

        try:
            return ConversationStatus(
                status.strip().lower()
            )
        except ValueError as exc:
            raise ValueError(
                f"Statut de conversation invalide : {status!r}"
            ) from exc

    # ==========================================================
    # PROPRIÉTÉS
    # ==========================================================

    @property
    def is_active(self) -> bool:
        """
        Indique si la conversation est actuellement active.
        """

        return (
            self.status == ConversationStatus.ACTIVE
            and not self.is_archived
        )

    @property
    def is_closed(self) -> bool:
        """
        Indique si la conversation est fermée.
        """

        return self.status == ConversationStatus.CLOSED

    @property
    def can_use_ai(self) -> bool:
        """
        Indique si l'assistant IA peut intervenir
        sur cette conversation.
        """

        return (
            self.ai_enabled
            and not self.is_archived
            and self.status != ConversationStatus.CLOSED
        )

    # ==========================================================
    # STATUT
    # ==========================================================

    def activate(self) -> None:
        """
        Active ou réactive la conversation.
        """

        self.status = ConversationStatus.ACTIVE
        self.closed_at = None
        self.is_archived = False
        self.touch()

    def mark_as_waiting(self) -> None:
        """
        Place la conversation en attente.

        Exemple :
        VYRA a proposé une réponse et attend une action
        de l'utilisateur ou du contact.
        """

        self.status = ConversationStatus.WAITING
        self.touch()

    def close(self) -> None:
        """
        Ferme la conversation.
        """

        self.status = ConversationStatus.CLOSED
        self.closed_at = utc_now()
        self.touch()

    def archive(self) -> None:
        """
        Archive la conversation.
        """

        self.is_archived = True
        self.status = ConversationStatus.ARCHIVED
        self.touch()

    def unarchive(self) -> None:
        """
        Désarchive la conversation.
        """

        self.is_archived = False

        if self.status == ConversationStatus.ARCHIVED:
            self.status = ConversationStatus.ACTIVE

        self.touch()

    # ==========================================================
    # IA
    # ==========================================================

    def enable_ai(self) -> None:
        """
        Active l'assistance IA pour cette conversation.
        """

        self.ai_enabled = True
        self.touch()

    def disable_ai(self) -> None:
        """
        Désactive l'assistance IA pour cette conversation.

        La conversation continue d'exister normalement.
        Seule l'intervention de l'IA est désactivée.
        """

        self.ai_enabled = False
        self.touch()

    # ==========================================================
    # MESSAGES
    # ==========================================================

    def register_message(
        self,
        message_time: datetime | None = None,
    ) -> None:
        """
        Enregistre l'arrivée ou l'envoi d'un nouveau message.

        Cette méthode ne crée pas le message.
        Elle met simplement à jour l'état de la conversation.
        """

        self.last_message_at = (
            message_time or utc_now()
        )

        if self.status in {
            ConversationStatus.CLOSED,
            ConversationStatus.ARCHIVED,
        }:
            self.status = ConversationStatus.ACTIVE
            self.is_archived = False
            self.closed_at = None

        self.touch()

    # ==========================================================
    # SUJET ET RÉSUMÉ
    # ==========================================================

    def set_subject(self, subject: str | None) -> None:
        """
        Définit ou modifie le sujet de la conversation.
        """

        self.subject = (
            subject.strip()
            if subject
            else None
        )

        self.touch()

    def update_summary(self, summary: str | None) -> None:
        """
        Met à jour le résumé de la conversation.

        Le résumé pourra être généré ou actualisé par VYRA
        après plusieurs échanges.
        """

        self.summary = (
            summary.strip()
            if summary
            else None
        )

        self.touch()

    # ==========================================================
    # MISE À JOUR
    # ==========================================================

    def update(
        self,
        *,
        channel: ConversationChannel | str | None = None,
        status: ConversationStatus | str | None = None,
        subject: str | None = None,
        summary: str | None = None,
        ai_enabled: bool | None = None,
    ) -> None:
        """
        Met à jour les informations modifiables
        de la conversation.

        Seuls les champs fournis sont modifiés.
        """

        if channel is not None:
            self.channel = self._normalize_channel(
                channel
            )

        if status is not None:
            self.status = self._normalize_status(
                status
            )

            if self.status == ConversationStatus.CLOSED:
                self.closed_at = utc_now()

        if subject is not None:
            self.subject = (
                subject.strip()
                or None
            )

        if summary is not None:
            self.summary = (
                summary.strip()
                or None
            )

        if ai_enabled is not None:
            self.ai_enabled = bool(ai_enabled)

        self.touch()

    def touch(self) -> None:
        """
        Met à jour la date de modification.
        """

        self.updated_at = utc_now()

    # ==========================================================
    # VALIDATION MÉTIER
    # ==========================================================

    def can_receive_message(self) -> bool:
        """
        Indique si la conversation peut recevoir un nouveau message.
        """

        return not self.is_archived

    def belongs_to_user(
        self,
        user_id: int,
    ) -> bool:
        """
        Vérifie que la conversation appartient
        à l'utilisateur indiqué.
        """

        return self.user_id == user_id

    # ==========================================================
    # CONVERSION
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convertit la conversation en dictionnaire.
        """

        return {
            "id": self.id,
            "user_id": self.user_id,
            "contact_id": self.contact_id,
            "channel": self.channel.value,
            "status": self.status.value,
            "subject": self.subject,
            "summary": self.summary,
            "ai_enabled": self.ai_enabled,
            "is_archived": self.is_archived,
            "is_active": self.is_active,
            "is_closed": self.is_closed,
            "can_use_ai": self.can_use_ai,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_message_at": (
                self.last_message_at.isoformat()
                if self.last_message_at
                else None
            ),
            "closed_at": (
                self.closed_at.isoformat()
                if self.closed_at
                else None
            ),
        }

    def to_database_dict(self) -> dict[str, Any]:
        """
        Prépare les données pour SQLite.
        """

        return {
            "id": self.id,
            "user_id": self.user_id,
            "contact_id": self.contact_id,
            "channel": self.channel.value,
            "status": self.status.value,
            "subject": self.subject,
            "summary": self.summary,
            "ai_enabled": int(self.ai_enabled),
            "is_archived": int(self.is_archived),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_message_at": (
                self.last_message_at.isoformat()
                if self.last_message_at
                else None
            ),
            "closed_at": (
                self.closed_at.isoformat()
                if self.closed_at
                else None
            ),
        }

    # ==========================================================
    # DATABASE
    # ==========================================================

    @classmethod
    def from_row(cls, row: Any) -> "Conversation":
        """
        Construit une Conversation à partir d'une ligne SQLite.
        """

        def parse_datetime(
            value: Any,
        ) -> datetime | None:
            if value is None:
                return None

            if isinstance(value, datetime):
                return value

            return datetime.fromisoformat(str(value))

        return cls(
            conversation_id=row["id"],
            user_id=row["user_id"],
            contact_id=row["contact_id"],
            channel=row["channel"],
            status=row["status"],
            subject=row["subject"],
            summary=row["summary"],
            ai_enabled=bool(row["ai_enabled"]),
            is_archived=bool(row["is_archived"]),
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
            last_message_at=parse_datetime(
                row["last_message_at"]
            ),
            closed_at=parse_datetime(
                row["closed_at"]
            ),
        )

    # ==========================================================
    # REPRÉSENTATION
    # ==========================================================

    def __repr__(self) -> str:
        """
        Représentation utile pendant le développement.
        """

        return (
            f"Conversation("
            f"id={self.id!r}, "
            f"user_id={self.user_id!r}, "
            f"contact_id={self.contact_id!r}, "
            f"channel={self.channel.value!r}, "
            f"status={self.status.value!r}, "
            f"ai_enabled={self.ai_enabled!r}"
            f")"
        )