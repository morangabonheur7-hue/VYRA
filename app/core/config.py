from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration centrale de VYRA V1.

    Les valeurs par défaut permettent de démarrer le projet
    en développement.

    Les informations sensibles doivent être placées dans
    les variables d'environnement ou dans le fichier .env.
    """

    # ==========================================================
    # APPLICATION
    # ==========================================================

    app_name: str = "VYRA"
    app_version: str = "1.0.0"

    environment: Literal[
        "development",
        "testing",
        "production",
    ] = "development"

    debug: bool = True

    # ==========================================================
    # API
    # ==========================================================

    api_prefix: str = "/api"

    api_title: str = "VYRA API"

    api_description: str = (
        "Backend API for VYRA V1, an AI-powered commercial assistant."
    )

    host: str = "0.0.0.0"

    port: int = 8000

    # ==========================================================
    # DATABASE
    # ==========================================================

    database_url: str = "sqlite:///./vyra.db"

    # ==========================================================
    # SECURITY
    # ==========================================================

    secret_key: str = Field(
        default="CHANGE_THIS_SECRET_KEY_IN_PRODUCTION",
        min_length=16,
    )

    algorithm: str = "HS256"

    access_token_expire_minutes: int = Field(
        default=60,
        ge=1,
    )

    refresh_token_expire_days: int = Field(
        default=30,
        ge=1,
    )

    # ==========================================================
    # CORS
    # ==========================================================

    cors_origins: str = (
        "http://localhost:3000,"
        "http://localhost:8000"
    )

    # ==========================================================
    # AI GATEWAY
    # ==========================================================

    # Provider actuellement utilisé par VYRA.
    # Le Gateway permet de changer de provider plus tard.
    ai_provider: Literal[
        "gemini",
        "mock",
    ] = "gemini"

    # Modèle Gemini actuel utilisé par VYRA.
    ai_model: str = "gemini-3.6-flash"

    # La clé peut être fournie avec :
    # AI_API_KEY
    # GEMINI_API_KEY
    # GOOGLE_API_KEY
    ai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AI_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
        ),
    )

    # Endpoint REST Gemini.
    ai_base_url: str = (
        "https://generativelanguage.googleapis.com/v1beta"
    )

    ai_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
    )

    ai_max_tokens: int = Field(
        default=1000,
        ge=1,
    )

    ai_timeout_seconds: int = Field(
        default=60,
        ge=1,
    )

    # ==========================================================
    # AI ASSISTANT
    # ==========================================================

    assistant_name: str = "VYRA"

    assistant_language: str = "fr"

    assistant_default_tone: str = "professional"

    # ==========================================================
    # MEMORY
    # ==========================================================

    memory_enabled: bool = True

    memory_max_items_per_contact: int = Field(
        default=100,
        ge=1,
    )

    memory_max_context_messages: int = Field(
        default=20,
        ge=1,
    )

    # ==========================================================
    # TASKS
    # ==========================================================

    task_reminders_enabled: bool = True

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        """
        Garantit que le préfixe API commence par '/'.
        """

        if not value.startswith("/"):
            value = f"/{value}"

        return value.rstrip("/") or "/"

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        """
        Nettoie la liste des origines CORS.
        """

        origins = [
            origin.strip()
            for origin in value.split(",")
            if origin.strip()
        ]

        return ",".join(origins)

    @field_validator("assistant_language")
    @classmethod
    def validate_assistant_language(
        cls,
        value: str,
    ) -> str:
        """
        Normalise la langue de l'assistant.
        """

        return value.strip().lower()

    @field_validator("assistant_default_tone")
    @classmethod
    def validate_assistant_tone(
        cls,
        value: str,
    ) -> str:
        """
        Normalise le ton par défaut de l'assistant.
        """

        return value.strip().lower()

    # ==========================================================
    # PYDANTIC SETTINGS
    # ==========================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Retourne l'instance unique de configuration.

    Le cache évite de recréer la configuration à chaque appel.
    """

    return Settings()


settings = get_settings()