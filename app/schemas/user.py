from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """
    Données communes utilisées par les schémas utilisateur.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    email: EmailStr
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    last_name: str = Field(
        default="",
        max_length=100,
    )
    phone: str | None = Field(
        default=None,
        max_length=30,
    )
    business_name: str | None = Field(
        default=None,
        max_length=200,
    )
    business_description: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, value: str) -> str:
        value = value.strip()

        if not value and cls.model_fields.get("first_name"):
            return value

        return value

    @field_validator(
        "phone",
        "business_name",
        "business_description",
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


class UserCreate(UserBase):
    """
    Données nécessaires pour créer un compte VYRA.
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Le mot de passe ne peut pas être vide.")

        return value


class UserLogin(BaseModel):
    """
    Données nécessaires pour se connecter.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    email: EmailStr
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
    )


class UserUpdate(BaseModel):
    """
    Données modifiables après création du compte.
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
    phone: str | None = Field(
        default=None,
        max_length=30,
    )
    business_name: str | None = Field(
        default=None,
        max_length=200,
    )
    business_description: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator(
        "first_name",
        "last_name",
        "phone",
        "business_name",
        "business_description",
    )
    @classmethod
    def normalize_strings(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class PasswordChange(BaseModel):
    """
    Données nécessaires pour modifier le mot de passe.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    current_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "Le nouveau mot de passe ne peut pas être vide."
            )

        return value


class UserResponse(BaseModel):
    """
    Représentation publique d'un utilisateur.

    Le password_hash n'est volontairement jamais exposé.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    full_name: str
    phone: str | None
    business_name: str | None
    business_description: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


class TokenResponse(BaseModel):
    """
    Réponse renvoyée après authentification.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserLoginResponse(BaseModel):
    """
    Réponse complète après connexion.
    """

    user: UserResponse
    tokens: TokenResponse