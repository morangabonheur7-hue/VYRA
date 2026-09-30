import json
import urllib.error
import urllib.request
from typing import Any

from app.ai.gateway import AIRequest, AIResponse
from app.core.config import settings
from app.core.errors import (
    AIConfigurationError,
    AIProviderError,
    AIProviderTimeoutError,
)


class GeminiProvider:
    """
    Provider Gemini pour VYRA.

    Cette classe communique directement avec l'API REST Gemini.
    Le reste de VYRA ne dépend pas directement de Gemini :
    il passe par l'AI Gateway.
    """

    name = "gemini"

    def __init__(self) -> None:
        self.api_key = settings.ai_api_key
        self.base_url = settings.ai_base_url.rstrip("/")
        self.default_model = settings.ai_model

    # ==========================================================
    # PUBLIC API
    # ==========================================================

    def generate(self, request: AIRequest) -> AIResponse:
        """
        Génère une réponse avec Gemini.
        """

        self._validate_configuration()

        model = request.model or self.default_model

        url = (
            f"{self.base_url}/models/"
            f"{model}:generateContent"
        )

        payload = self._build_payload(request)

        http_request = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                http_request,
                timeout=request.timeout_seconds,
            ) as response:
                raw_response = response.read().decode("utf-8")

        except TimeoutError as exc:
            raise AIProviderTimeoutError(
                message="Gemini API request timed out.",
                details={
                    "provider": self.name,
                    "timeout_seconds": request.timeout_seconds,
                },
            ) from exc

        except urllib.error.HTTPError as exc:
            body = self._read_http_error(exc)

            raise AIProviderError(
                message="Gemini API returned an HTTP error.",
                details={
                    "provider": self.name,
                    "status_code": exc.code,
                    "response": body,
                },
            ) from exc

        except urllib.error.URLError as exc:
            raise AIProviderError(
                message="Unable to connect to Gemini API.",
                details={
                    "provider": self.name,
                    "reason": str(exc.reason),
                },
            ) from exc

        except OSError as exc:
            raise AIProviderError(
                message="Network error while contacting Gemini API.",
                details={
                    "provider": self.name,
                    "error": str(exc),
                },
            ) from exc

        return self._parse_response(raw_response, model)

    # ==========================================================
    # CONFIGURATION
    # ==========================================================

    def _validate_configuration(self) -> None:
        """
        Vérifie que Gemini possède les informations nécessaires.
        """

        if not self.api_key:
            raise AIConfigurationError(
                message="Gemini API key is not configured.",
                details={
                    "provider": self.name,
                    "expected_environment_variables": [
                        "GEMINI_API_KEY",
                        "AI_API_KEY",
                        "GOOGLE_API_KEY",
                    ],
                },
            )

        if not self.base_url:
            raise AIConfigurationError(
                message="Gemini API base URL is not configured.",
                details={
                    "provider": self.name,
                },
            )

    # ==========================================================
    # REQUEST BUILDING
    # ==========================================================

    def _build_payload(
        self,
        request: AIRequest,
    ) -> dict[str, Any]:
        """
        Transforme une AIRequest VYRA en payload Gemini.
        """

        contents: list[dict[str, Any]] = []

        for message in request.messages:
            role = self._map_role(
                message.get("role", "user")
            )

            content = str(
                message.get("content", "")
            ).strip()

            if not content:
                continue

            contents.append(
                {
                    "role": role,
                    "parts": [
                        {
                            "text": content,
                        }
                    ],
                }
            )

        if not contents:
            raise AIProviderError(
                message="Gemini request contains no usable messages.",
                details={
                    "provider": self.name,
                },
            )

        generation_config: dict[str, Any] = {
            "temperature": (
                request.temperature
                if request.temperature is not None
                else settings.ai_temperature
            ),
            "maxOutputTokens": (
                request.max_tokens
                if request.max_tokens is not None
                else settings.ai_max_tokens
            ),
        }

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }

        if request.system_prompt:
            payload["systemInstruction"] = {
                "parts": [
                    {
                        "text": request.system_prompt,
                    }
                ]
            }

        return payload

    # ==========================================================
    # ROLE MAPPING
    # ==========================================================

    @staticmethod
    def _map_role(role: str) -> str:
        """
        Convertit les rôles VYRA vers les rôles Gemini.
        """

        normalized = role.strip().lower()

        if normalized in {
            "assistant",
            "model",
        }:
            return "model"

        return "user"

    # ==========================================================
    # RESPONSE PARSING
    # ==========================================================

    def _parse_response(
        self,
        raw_response: str,
        model: str,
    ) -> AIResponse:
        """
        Transforme la réponse Gemini en AIResponse VYRA.
        """

        try:
            data = json.loads(raw_response)

        except json.JSONDecodeError as exc:
            raise AIProviderError(
                message="Gemini returned invalid JSON.",
                details={
                    "provider": self.name,
                },
            ) from exc

        text = self._extract_text(data)

        if not text:
            raise AIProviderError(
                message="Gemini returned no text content.",
                details={
                    "provider": self.name,
                    "response": data,
                },
            )

        usage = self._extract_usage(data)

        return AIResponse(
            text=text,
            provider=self.name,
            model=model,
            usage=usage,
            raw_response=data,
        )

    @staticmethod
    def _extract_text(
        data: dict[str, Any],
    ) -> str:
        """
        Extrait le texte depuis le premier candidat Gemini.
        """

        candidates = data.get("candidates", [])

        if not candidates:
            return ""

        candidate = candidates[0]

        content = candidate.get("content", {})

        parts = content.get("parts", [])

        text_parts: list[str] = []

        for part in parts:
            part_text = part.get("text")

            if isinstance(part_text, str):
                text_parts.append(part_text)

        return "\n".join(
            text_parts
        ).strip()

    @staticmethod
    def _extract_usage(
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extrait les informations de consommation disponibles.
        """

        usage_metadata = data.get(
            "usageMetadata",
            {},
        )

        if not isinstance(
            usage_metadata,
            dict,
        ):
            return {}

        return {
            "prompt_tokens": usage_metadata.get(
                "promptTokenCount"
            ),
            "output_tokens": usage_metadata.get(
                "candidatesTokenCount"
            ),
            "total_tokens": usage_metadata.get(
                "totalTokenCount"
            ),
        }

    # ==========================================================
    # ERROR HANDLING
    # ==========================================================

    @staticmethod
    def _read_http_error(
        error: urllib.error.HTTPError,
    ) -> str:
        """
        Lit proprement le corps d'une erreur HTTP.
        """

        try:
            body = error.read().decode(
                "utf-8",
                errors="replace",
            )

            if body:
                return body

        except Exception:
            pass

        return str(error)


class MockAIProvider:
    """
    Provider local de test.

    Il permet de tester VYRA sans appeler une API externe.
    """

    name = "mock"

    def generate(
        self,
        request: AIRequest,
    ) -> AIResponse:
        """
        Retourne une réponse déterministe de test.
        """

        return AIResponse(
            text=(
                "Réponse de test générée par le "
                "MockAIProvider de VYRA."
            ),
            provider=self.name,
            model=request.model or "mock-model",
            usage={
                "prompt_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
            raw_response={
                "mock": True,
            },
        )


# ==============================================================
# PROVIDER FACTORY
# ==============================================================

def create_ai_provider():
    """
    Crée le provider correspondant à la configuration VYRA.
    """

    provider_name = settings.ai_provider.strip().lower()

    if provider_name == "gemini":
        return GeminiProvider()

    if provider_name == "mock":
        return MockAIProvider()

    raise AIConfigurationError(
        message=(
            f"Unsupported AI provider: "
            f"{settings.ai_provider}"
        ),
        details={
            "supported_providers": [
                "gemini",
                "mock",
            ],
        },
    )