from typing import Any


class VYRAError(Exception):
    """
    Classe de base pour toutes les erreurs métier de VYRA.

    Toutes les erreurs spécifiques de VYRA héritent de cette classe.

    Attributs :
        message:
            Message lisible destiné à expliquer l'erreur.

        code:
            Identifiant interne stable de l'erreur.
            Il pourra être utilisé par l'API, le frontend
            ou les logs.

        status_code:
            Code HTTP correspondant lorsque l'erreur est exposée
            par l'API.

        details:
            Informations supplémentaires facultatives.
    """

    default_code = "vyra_error"
    default_status_code = 500

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code or self.default_code
        self.status_code = (
            status_code
            if status_code is not None
            else self.default_status_code
        )
        self.details = details or {}

        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """
        Transforme l'erreur en dictionnaire.

        Cette méthode sera utile plus tard pour construire
        les réponses JSON de l'API.
        """

        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        """
        Représentation lisible de l'erreur.
        """

        return self.message


# ==========================================================
# CONFIGURATION
# ==========================================================


class ConfigurationError(VYRAError):
    """
    Erreur générale de configuration de VYRA.
    """

    default_code = "configuration_error"
    default_status_code = 500


# ==========================================================
# VALIDATION
# ==========================================================


class ValidationError(VYRAError):
    """
    Données fournies invalides ou incohérentes.
    """

    default_code = "validation_error"
    default_status_code = 422


# ==========================================================
# AUTHENTIFICATION / AUTORISATION
# ==========================================================


class AuthenticationError(VYRAError):
    """
    L'utilisateur ne peut pas être authentifié.
    """

    default_code = "authentication_error"
    default_status_code = 401


class AuthorizationError(VYRAError):
    """
    L'utilisateur est authentifié mais n'a pas
    les permissions nécessaires.
    """

    default_code = "authorization_error"
    default_status_code = 403


# ==========================================================
# RESSOURCES INTROUVABLES
# ==========================================================


class UserNotFoundError(VYRAError):
    """
    Utilisateur demandé introuvable.
    """

    default_code = "user_not_found"
    default_status_code = 404


class ContactNotFoundError(VYRAError):
    """
    Contact demandé introuvable.
    """

    default_code = "contact_not_found"
    default_status_code = 404


class ConversationNotFoundError(VYRAError):
    """
    Conversation demandée introuvable.
    """

    default_code = "conversation_not_found"
    default_status_code = 404


class MessageNotFoundError(VYRAError):
    """
    Message demandé introuvable.
    """

    default_code = "message_not_found"
    default_status_code = 404


class TaskNotFoundError(VYRAError):
    """
    Tâche demandée introuvable.
    """

    default_code = "task_not_found"
    default_status_code = 404


class MemoryNotFoundError(VYRAError):
    """
    Élément de mémoire demandé introuvable.
    """

    default_code = "memory_not_found"
    default_status_code = 404


# ==========================================================
# CONFLITS
# ==========================================================


class ConflictError(VYRAError):
    """
    L'opération demandée entre en conflit avec
    l'état actuel des données.
    """

    default_code = "conflict"
    default_status_code = 409


# ==========================================================
# BASE DE DONNÉES
# ==========================================================


class DatabaseError(VYRAError):
    """
    Erreur générale liée à la base de données.
    """

    default_code = "database_error"
    default_status_code = 500


# ==========================================================
# INTELLIGENCE ARTIFICIELLE
# ==========================================================


class AIProviderError(VYRAError):
    """
    Le fournisseur IA n'a pas pu traiter correctement
    la requête.
    """

    default_code = "ai_provider_error"
    default_status_code = 502


class AIConfigurationError(VYRAError):
    """
    La configuration du système IA est incorrecte
    ou incomplète.
    """

    default_code = "ai_configuration_error"
    default_status_code = 500


class AIProviderTimeoutError(AIProviderError):
    """
    Le fournisseur IA n'a pas répondu dans le délai prévu.
    """

    default_code = "ai_provider_timeout"
    default_status_code = 504


class AIRateLimitError(AIProviderError):
    """
    Le fournisseur IA a refusé la requête parce qu'une
    limite de requêtes a été atteinte.
    """

    default_code = "ai_rate_limit"
    default_status_code = 429


# ==========================================================
# SERVICES EXTERNES
# ==========================================================


class ExternalServiceError(VYRAError):
    """
    Erreur provenant d'un service externe utilisé par VYRA.
    """

    default_code = "external_service_error"
    default_status_code = 502