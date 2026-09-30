from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.conversation import (
    ConversationChannel,
    ConversationStatus,
)


class ConversationBase(BaseModel):
    """
    Données communes d'une conversation.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    contact_id: int = Field(
        ...,
        gt=0,
    )
    channel: ConversationChannel = ConversationChannel.WHATSAPP
    subject: str | None = Field(
        default=None,
        max_length=300,
    )
    summary: str | None = Field(
        default=None,
        max_length=5000,
    )
    ai_enabled: bool = True

    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class ConversationCreate(ConversationBase):
    """
    Données nécessaires pour créer une conversation.
    """

    pass


class ConversationUpdate(BaseModel):
    """
    Données modifiables après création d'une conversation.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    channel: ConversationChannel | None = None
    status: ConversationStatus | None = None
    subject: str | None = Field(
        default=None,
        max_length=300,
    )
    summary: str | None = Field(
        default=None,
        max_length=5000,
    )
    ai_enabled: bool | None = None

    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class ConversationResponse(BaseModel):
    """
    Représentation publique d'une conversation.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: int
    user_id: int
    contact_id: int
    channel: ConversationChannel
    status: ConversationStatus
    subject: str | None
    summary: str | None
    ai_enabled: bool
    is_archived: bool
    is_active: bool
    is_closed: bool
    can_use_ai: bool
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    closed_at: datetime | None


class ConversationListResponse(BaseModel):
    """
    Réponse utilisée lorsqu'une liste de conversations est renvoyée.
    """

    items: list[ConversationResponse]
    total: int
    page: int = Field(
        default=1,
        ge=1,
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )


class ConversationStatusUpdate(BaseModel):
    """
    Modification dédiée du statut.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    status: ConversationStatus


class ConversationAIUpdate(BaseModel):
    """
    Activation ou désactivation de l'assistant IA
    pour une conversation.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    ai_enabled: bool


class ConversationArchiveUpdate(BaseModel):
    """
    Archivage ou désarchivage d'une conversation.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    is_archived: bool