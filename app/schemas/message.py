from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.message import (
    MessageRole,
    MessageSender,
    MessageStatus,
)


class MessageBase(BaseModel):
    """
    Données communes d'un message.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Le contenu du message ne peut pas être vide."
            )

        return value


class MessageCreate(MessageBase):
    """
    Création d'un message envoyé par l'utilisateur.
    """

    conversation_id: int = Field(
        ...,
        gt=0,
    )
    external_message_id: str | None = Field(
        default=None,
        max_length=255,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class IncomingMessageCreate(MessageBase):
    """
    Message entrant provenant du contact.

    Utilisé plus tard par les intégrations de messagerie.
    """

    conversation_id: int = Field(
        ...,
        gt=0,
    )
    external_message_id: str | None = Field(
        default=None,
        max_length=255,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class AIDraftCreate(MessageBase):
    """
    Création d'une proposition de réponse générée par l'IA.
    """

    conversation_id: int = Field(
        ...,
        gt=0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class MessageUpdate(BaseModel):
    """
    Modification d'un message avant son envoi.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    content: str | None = Field(
        default=None,
        min_length=1,
        max_length=10000,
    )
    metadata: dict[str, Any] | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError(
                "Le contenu du message ne peut pas être vide."
            )

        return value


class MessageApproval(BaseModel):
    """
    Validation ou rejet d'une proposition générée par l'IA.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    approved: bool


class MessageStatusUpdate(BaseModel):
    """
    Modification explicite du statut d'un message.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    status: MessageStatus


class MessageResponse(BaseModel):
    """
    Représentation publique d'un message.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: int
    conversation_id: int
    sender: MessageSender
    role: MessageRole
    content: str
    status: MessageStatus
    is_ai_generated: bool
    requires_approval: bool
    approved_by_user: bool
    external_message_id: str | None
    metadata: dict[str, Any]
    is_incoming: bool
    is_outgoing: bool
    is_pending: bool
    is_sent: bool
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None


class MessageListResponse(BaseModel):
    """
    Réponse utilisée lorsqu'une liste de messages est renvoyée.
    """

    items: list[MessageResponse]
    total: int
    page: int = Field(
        default=1,
        ge=1,
    )
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
    )


class AIDraftResponse(BaseModel):
    """
    Réponse spécialisée pour une proposition IA.

    Elle permet au frontend de savoir clairement
    qu'une validation humaine est nécessaire.
    """

    message: MessageResponse
    requires_approval: bool = True