from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.contact import ContactSource, ContactStatus


class ContactBase(BaseModel):
    """
    Données communes d'un contact.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    last_name: str = Field(
        default="",
        max_length=100,
    )
    company_name: str | None = Field(
        default=None,
        max_length=200,
    )
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        max_length=30,
    )
    position: str | None = Field(
        default=None,
        max_length=150,
    )
    status: ContactStatus = ContactStatus.NEW
    source: ContactSource = ContactSource.MANUAL
    notes: str | None = Field(
        default=None,
        max_length=5000,
    )

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Le prénom du contact ne peut pas être vide."
            )

        return value

    @field_validator(
        "last_name",
        "company_name",
        "phone",
        "position",
        "notes",
    )
    @classmethod
    def normalize_optional_strings(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class ContactCreate(ContactBase):
    """
    Données nécessaires pour créer un contact.
    """

    pass


class ContactUpdate(BaseModel):
    """
    Données modifiables après création d'un contact.

    Tous les champs sont optionnels.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    last_name: str | None = Field(
        default=None,
        max_length=100,
    )
    company_name: str | None = Field(
        default=None,
        max_length=200,
    )
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None,
        max_length=30,
    )
    position: str | None = Field(
        default=None,
        max_length=150,
    )
    status: ContactStatus | None = None
    source: ContactSource | None = None
    notes: str | None = Field(
        default=None,
        max_length=5000,
    )

    @field_validator(
        "first_name",
        "last_name",
        "company_name",
        "phone",
        "position",
        "notes",
    )
    @classmethod
    def normalize_optional_strings(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class ContactResponse(BaseModel):
    """
    Représentation publique d'un contact.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: int
    user_id: int
    first_name: str
    last_name: str
    full_name: str
    display_name: str
    company_name: str | None
    email: EmailStr | None
    phone: str | None
    position: str | None
    status: ContactStatus
    source: ContactSource
    notes: str | None
    is_archived: bool
    has_email: bool
    has_phone: bool
    created_at: datetime
    updated_at: datetime
    last_contacted_at: datetime | None


class ContactListResponse(BaseModel):
    """
    Réponse utilisée lorsqu'une liste de contacts est renvoyée.
    """

    items: list[ContactResponse]
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ContactStatusUpdate(BaseModel):
    """
    Permet de modifier uniquement le statut d'un contact.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    status: ContactStatus


class ContactArchiveUpdate(BaseModel):
    """
    Permet d'archiver ou de désarchiver un contact.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    is_archived: bool