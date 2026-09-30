from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.config import settings
from app.core.errors import AIConfigurationError


@dataclass
class AIRequest:
    """
    Requête standardisée envoyée à l'AI Gateway.
    """

    messages: list[dict[str, str]]

    model: str | None = None

    system_prompt: str | None = None

    temperature: float | None = None

    max_tokens: int | None = None

    timeout_seconds: int | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class AIResponse:
    """
    Réponse standardisée retournée par un provider IA.
    """

    text: str

    provider: str

    model: str

    usage: dict[str, Any] = field(
        default_factory=dict
    )

    raw_response: Any = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class AIProviderProtocol(Protocol):
    """
    Contrat minimal que chaque provider IA doit respecter.
    """

    name: str

    def generate(
        self,
        request: AIRequest,
    ) -> AIResponse:
        ...


class AIGateway:
    """
    Point d'entrée unique de VYRA vers les providers IA.

    Le reste de l'application ne parle jamais directement
    à Gemini ou à un autre fournisseur.
    """

    def __init__(
        self,
        provider: AIProviderProtocol | None = None,
    ) -> None:
        self.provider = (
            provider
            if provider is not None
            else self._create_provider()
        )

    # ==========================================================
    # PROVIDER
    # ==========================================================

    @staticmethod
    def _create_provider() -> AIProviderProtocol:
        """
        Crée le provider configuré.
        """

        from app.ai.providers import create_ai_provider

        provider = create_ai_provider()

        if not hasattr(provider, "generate"):
            raise AIConfigurationError(
                message=(
                    "Configured AI provider does not "
                    "implement generate()."
                ),
                details={
                    "provider": settings.ai_provider,
                },
            )

        return provider

    # ==========================================================
    # GENERATION
    # ==========================================================

    def generate(
        self,
        request: AIRequest,
    ) -> AIResponse:
        """
        Envoie une requête au provider configuré.
        """

        self._validate_request(request)

        normalized_request = self._normalize_request(
            request
        )

        response = self.provider.generate(
            normalized_request
        )

        self._validate_response(response)

        return response

    # ==========================================================
    # SIMPLE TEXT API
    # ==========================================================

    def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: int | None = None,
    ) -> AIResponse:
        """
        Raccourci pour une requête contenant un seul message.
        """

        request = AIRequest(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )

        return self.generate(request)

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @staticmethod
    def _validate_request(
        request: AIRequest,
    ) -> None:
        """
        Vérifie qu'une requête est exploitable.
        """

        if not isinstance(request.messages, list):
            raise AIConfigurationError(
                message="AI request messages must be a list."
            )

        if not request.messages:
            raise AIConfigurationError(
                message="AI request must contain at least one message."
            )

        for message in request.messages:
            if not isinstance(message, dict):
                raise AIConfigurationError(
                    message="Each AI message must be a dictionary."
                )

            if "role" not in message:
                raise AIConfigurationError(
                    message="Each AI message must contain a role."
                )

            if "content" not in message:
                raise AIConfigurationError(
                    message="Each AI message must contain content."
                )

    @staticmethod
    def _validate_response(
        response: AIResponse,
    ) -> None:
        """
        Vérifie qu'un provider retourne bien une AIResponse.
        """

        if not isinstance(response, AIResponse):
            raise AIConfigurationError(
                message=(
                    "AI provider returned an invalid "
                    "response object."
                )
            )

        if not isinstance(response.text, str):
            raise AIConfigurationError(
                message="AI provider response text must be a string."
            )

        if not response.provider:
            raise AIConfigurationError(
                message="AI provider response is missing provider name."
            )

        if not response.model:
            raise AIConfigurationError(
                message="AI provider response is missing model name."
            )

    # ==========================================================
    # NORMALIZATION
    # ==========================================================

    @staticmethod
    def _normalize_request(
        request: AIRequest,
    ) -> AIRequest:
        """
        Applique les valeurs par défaut de VYRA.
        """

        return AIRequest(
            messages=request.messages,
            model=request.model or settings.ai_model,
            system_prompt=request.system_prompt,
            temperature=(
                request.temperature
                if request.temperature is not None
                else settings.ai_temperature
            ),
            max_tokens=(
                request.max_tokens
                if request.max_tokens is not None
                else settings.ai_max_tokens
            ),
            timeout_seconds=(
                request.timeout_seconds
                if request.timeout_seconds is not None
                else settings.ai_timeout_seconds
            ),
            metadata=request.metadata,
        )


# ==============================================================
# GLOBAL GATEWAY
# ==============================================================

ai_gateway = AIGateway()