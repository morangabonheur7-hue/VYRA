from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    """
    Retourne la date et l'heure actuelles en UTC.
    """

    return datetime.now(timezone.utc)


class MessageSender(str, Enum):
    """
    Identifie l'origine du message.
    """

    CONTACT = "contact"
    USER = "user"
    ASSISTANT = "assistant"


class MessageRole(str, Enum):
    """
    Rôle du message dans le contexte conversationnel.

    Ces rôles seront particulièrement utiles pour l'IA.
    """

    USER = "user"
    ASSISTANT = "assistant"
    CONTACT = "contact"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    """
    État du message.
    """

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
    """
    Modèle représentant un message dans une conversation VYRA.

    Un message peut provenir :
        - du contact ;
        - de l'utilisateur ;
        - de l'assistant IA.

    VYRA V1 garde l'humain dans la boucle :
    une réponse générée par l'IA peut rester en attente
    de validation avant d'être envoyée.
    """

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

    # ==========================================================
    # NORMALISATION
    # ==========================================================

    @staticmethod
    def _normalize_sender(
        sender: MessageSender | str,
    ) -> MessageSender:
        """
        Convertit une valeur en MessageSender.
        """

        if isinstance(sender, MessageSender):
            return sender

        try:
            return MessageSender(
                sender.strip().lower()
            )
        except ValueError as exc:
            raise ValueError(
                f"Expéditeur invalide : {sender!r}"
            ) from exc

    @staticmethod
    def _normalize_role(
        role: MessageRole | str,
    ) -> MessageRole:
        """
        Convertit une valeur en MessageRole.
        """

        if isinstance(role, MessageRole):
            return role

        try:
            return MessageRole(
                role.strip().lower()
            )
        except ValueError as exc:
            raise ValueError(
                f"Rôle de message invalide : {role!r}"
            ) from exc

    @staticmethod
    def _normalize_status(
        status: MessageStatus | str,
    ) -> MessageStatus:
        """
        Convertit une valeur en MessageStatus.
        """

        if isinstance(status, MessageStatus):
            return status

        try:
            return MessageStatus(
                status.strip().lower()
            )
        except ValueError as exc:
            raise ValueError(
                f"Statut de message invalide : {status!r}"
            ) from exc

    @staticmethod
    def _normalize_content(content: str) -> str:
        """
        Nettoie et valide le contenu du message.
        """

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
        """
        Détermine automatiquement le rôle IA correspondant
        à l'expéditeur.
        """

        mapping = {
            MessageSender.CONTACT: MessageRole.CONTACT,
            MessageSender.USER: MessageRole.USER,
            MessageSender.ASSISTANT: MessageRole.ASSISTANT,
        }

        return mapping[sender]

    # ==========================================================
    # PROPRIÉTÉS
    # ==========================================================

    @property
    def is_incoming(self) -> bool:
        """
        Indique si le message vient du contact.
        """

        return self.sender == MessageSender.CONTACT

    @property
    def is_outgoing(self) -> bool:
        """
        Indique si le message est envoyé vers le contact.
        """

        return self.sender in {
            MessageSender.USER,
            MessageSender.ASSISTANT,
        }

    @property
    def is_pending(self) -> bool:
        """
        Indique si le message attend encore une action.
        """

        return self.status in {
            MessageStatus.DRAFT,
            MessageStatus.PENDING_APPROVAL,
        }

    @property
    def is_sent(self) -> bool:
        """
        Indique si le message a été envoyé.
        """

        return self.status in {
            MessageStatus.SENT,
            MessageStatus.DELIVERED,
            MessageStatus.READ,
        }

    @property
    def is_successfully_delivered(self) -> bool:
        """
        Indique si le message a été envoyé et livré.
        """

        return self.status in {
            MessageStatus.DELIVERED,
            MessageStatus.READ,
        }

    # ==========================================================
    # CRÉATION DE MESSAGES
    # ==========================================================

    @classmethod
    def incoming(
        cls,
        *,
        conversation_id: int,
        content: str,
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Message":
        """
        Crée un message reçu d'un contact.
        """

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
        """
        Crée un message écrit par l'utilisateur.
        """

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
        """
        Crée une réponse proposée par VYRA.

        La réponse n'est pas encore envoyée.
        Elle attend éventuellement la validation humaine.
        """

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

    # ==========================================================
    # VALIDATION HUMAINE
    # ==========================================================

    def approve(self) -> None:
        """
        Valide une réponse proposée par VYRA.

        La validation ne signifie pas encore que le message
        a été envoyé.
        """

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
        """
        Annule une proposition IA avant son envoi.
        """

        if not self.is_ai_generated:
            raise ValueError(
                "Seul un message généré par l'IA "
                "peut être rejeté comme proposition IA."
            )

        self.requires_approval = False
        self.approved_by_user = False
        self.status = MessageStatus.CANCELLED

        self.touch()

    # ==========================================================
    # ENVOI
    # ==========================================================

    def mark_as_sent(
        self,
        sent_at: datetime | None = None,
    ) -> None:
        """
        Marque le message comme envoyé.

        Un message IA doit avoir été approuvé avant de pouvoir
        être marqué comme envoyé.
        """

        if self.is_ai_generated and not self.approved_by_user:
            raise ValueError(
                "Une réponse IA doit être approuvée "
                "avant son envoi."
            )

        self.status = MessageStatus.SENT
        self.sent_at = sent_at or utc_now()

        self.touch()

    def mark_as_delivered(self) -> None:
        """
        Marque le message comme livré.
        """

        if not self.is_sent:
            raise ValueError(
                "Un message doit être envoyé avant d'être livré."
            )

        self.status = MessageStatus.DELIVERED
        self.touch()

    def mark_as_read(self) -> None:
        """
        Marque le message comme lu.
        """

        if not self.is_successfully_delivered:
            raise ValueError(
                "Un message doit être livré avant d'être lu."
            )

        self.status = MessageStatus.READ
        self.touch()

    def mark_as_failed(self) -> None:
        """
        Marque l'envoi comme échoué.
        """

        self.status = MessageStatus.FAILED
        self.touch()

    def cancel(self) -> None:
        """
        Annule un message qui n'a pas encore été envoyé.
        """

        if self.is_sent:
            raise ValueError(
                "Un message déjà envoyé ne peut pas être annulé "
                "comme un brouillon."
            )

        self.status = MessageStatus.CANCELLED
        self.touch()

    # ==========================================================
    # MÉTADONNÉES
    # ==========================================================

    def set_metadata(
        self,
        key: str,
        value: Any,
    ) -> None:
        """
        Ajoute ou modifie une métadonnée.
        """

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
        """
        Récupère une métadonnée.
        """

        return self.metadata.get(key, default)

    # ==========================================================
    # MISE À JOUR
    # ==========================================================

    def update_content(
        self,
        content: str,
    ) -> None:
        """
        Modifie le contenu d'un message qui n'a pas encore
        été envoyé.
        """

        if self.is_sent:
            raise ValueError(
                "Le contenu d'un message déjà envoyé "
                "ne peut pas être modifié."
            )

        self.content = self._normalize_content(content)
        self.touch()

    def touch(self) -> None:
        """
        Met à jour la date de modification.
        """

        self.updated_at = utc_now()

    # ==========================================================
    # VALIDATION MÉTIER
    # ==========================================================

    def belongs_to_conversation(
        self,
        conversation_id: int,
    ) -> bool:
        """
        Vérifie l'appartenance à une conversation.
        """

        return self.conversation_id == conversation_id

    def can_be_sent(self) -> bool:
        """
        Vérifie si le message peut être envoyé.
        """

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

    # ==========================================================
    # CONVERSION
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convertit le message en dictionnaire.
        """

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
        """
        Prépare les données pour SQLite.

        Les métadonnées seront sérialisées par la couche
        de persistance lorsqu'elle sera implémentée.
        """

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

    # ==========================================================
    # DATABASE
    # ==========================================================

    @classmethod
    def from_row(cls, row: Any) -> "Message":
        """
        Construit un Message à partir d'une ligne SQLite.
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

            metadata = json.loads(metadata)

        return cls(
            message_id=row["id"],
            conversation_id=row["conversation_id"],
            sender=row["sender"],
            role=row["role"],
            content=row["content"],
            status=row["status"],
            is_ai_generated=bool(row["is_ai_generated"]),
            requires_approval=bool(row["requires_approval"]),
            approved_by_user=bool(row["approved_by_user"]),
            external_message_id=row["external_message_id"],
            metadata=metadata or {},
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
            sent_at=parse_datetime(row["sent_at"]),
        )

    # ==========================================================
    # REPRÉSENTATION
    # ==========================================================

    def __repr__(self) -> str:
        """
        Représentation utile pendant le développement.

        Le contenu complet du message n'est volontairement
        pas affiché afin d'éviter de polluer les logs.
        """

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