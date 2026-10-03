from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Company:
    """
    Modèle principal d'une entreprise dans VYRA.

    V2 :
    - identité de l'entreprise
    - profil commercial
    - produits / services
    - horaires
    - zones
    - langues
    - ton de communication
    - règles commerciales
    - escalade humaine
    - limites de l'assistant

    V3 :
    - qualification automatique
    - scoring des prospects
    - détection d'intention
    - stratégie de suivi
    - règles de follow-up
    - décisions commerciales
    - paramètres de conversion
    """

    id: int | None = None

    # ============================================================
    # IDENTITÉ
    # ============================================================

    name: str = ""
    legal_name: str | None = None
    description: str | None = None

    email: str | None = None
    phone: str | None = None
    whatsapp_number: str | None = None
    website: str | None = None

    country: str | None = None
    city: str | None = None
    address: str | None = None
    timezone: str = "Africa/Brazzaville"

    # ============================================================
    # PROFIL COMMERCIAL — V2
    # ============================================================

    industry: str | None = None
    business_type: str | None = None

    target_customers: str | None = None
    target_market: str | None = None

    services_description: str | None = None
    products_description: str | None = None

    value_proposition: str | None = None
    selling_points: list[str] = field(default_factory=list)

    # ============================================================
    # COMMUNICATION — V2
    # ============================================================

    default_language: str = "fr"

    supported_languages: list[str] = field(
        default_factory=lambda: ["fr"]
    )

    assistant_name: str = "VYRA"

    tone: str = "professional"

    communication_style: str | None = None

    greeting_message: str | None = None

    forbidden_topics: list[str] = field(
        default_factory=list
    )

    forbidden_claims: list[str] = field(
        default_factory=list
    )

    # ============================================================
    # HORAIRES / DISPONIBILITÉ — V2
    # ============================================================

    business_hours: dict[str, Any] = field(
        default_factory=dict
    )

    accepts_messages_outside_hours: bool = True

    outside_hours_message: str | None = None

    # ============================================================
    # ZONES COMMERCIALES — V2
    # ============================================================

    service_areas: list[str] = field(
        default_factory=list
    )

    delivery_areas: list[str] = field(
        default_factory=list
    )

    remote_service: bool = True

    # ============================================================
    # RÈGLES COMMERCIALES — V2
    # ============================================================

    commercial_rules: list[str] = field(
        default_factory=list
    )

    pricing_rules: list[str] = field(
        default_factory=list
    )

    discount_rules: list[str] = field(
        default_factory=list
    )

    payment_methods: list[str] = field(
        default_factory=list
    )

    return_policy: str | None = None

    refund_policy: str | None = None

    shipping_policy: str | None = None

    # ============================================================
    # COMPORTEMENT IA — V2
    # ============================================================

    ai_enabled: bool = True

    ai_auto_reply_enabled: bool = False

    ai_suggestions_enabled: bool = True

    human_validation_required: bool = True

    max_response_length: int = 1000

    ai_instructions: str | None = None

    knowledge_base: str | None = None

    # ============================================================
    # ESCALADE HUMAINE — V2
    # ============================================================

    human_escalation_enabled: bool = True

    escalation_keywords: list[str] = field(
        default_factory=list
    )

    escalation_message: str | None = None

    human_contact_name: str | None = None

    human_contact_phone: str | None = None

    human_contact_email: str | None = None

    # ============================================================
    # LIMITES DE L'ASSISTANT — V2
    # ============================================================

    daily_message_limit: int | None = None

    monthly_message_limit: int | None = None

    max_concurrent_conversations: int | None = None

    # ============================================================
    # QUALIFICATION — V3
    # ============================================================

    qualification_enabled: bool = True

    qualification_questions: list[str] = field(
        default_factory=list
    )

    required_qualification_fields: list[str] = field(
        default_factory=list
    )

    qualification_criteria: dict[str, Any] = field(
        default_factory=dict
    )

    # ============================================================
    # INTENTION — V3
    # ============================================================

    intent_detection_enabled: bool = True

    tracked_intents: list[str] = field(
        default_factory=list
    )

    # ============================================================
    # SCORING PROSPECT — V3
    # ============================================================

    prospect_scoring_enabled: bool = True

    scoring_criteria: dict[str, Any] = field(
        default_factory=dict
    )

    hot_score_threshold: int = 80
    warm_score_threshold: int = 50
    cold_score_threshold: int = 20

    # ============================================================
    # FOLLOW-UP INTELLIGENT — V3
    # ============================================================

    followup_enabled: bool = True

    automatic_followup_enabled: bool = False

    followup_max_attempts: int = 3

    followup_default_delay_hours: int = 24

    followup_rules: list[dict[str, Any]] = field(
        default_factory=list
    )

    # ============================================================
    # MOTEUR DE DÉCISION — V3
    # ============================================================

    decision_engine_enabled: bool = True

    allowed_ai_actions: list[str] = field(
        default_factory=lambda: [
            "respond",
            "wait",
            "ask",
            "follow_up",
            "human",
            "stop",
        ]
    )

    auto_stop_on_negative_intent: bool = True

    auto_escalate_high_value_prospect: bool = True

    high_value_prospect_threshold: int = 80

    # ============================================================
    # CONVERSION — V3
    # ============================================================

    conversion_tracking_enabled: bool = True

    track_interested_prospects: bool = True

    track_sales: bool = True

    track_revenue: bool = True

    currency: str = "XAF"

    # ============================================================
    # STATUT
    # ============================================================

    is_active: bool = True

    is_verified: bool = False

    onboarding_completed: bool = False

    # ============================================================
    # DATES
    # ============================================================

    created_at: datetime = field(
        default_factory=_utcnow
    )

    updated_at: datetime = field(
        default_factory=_utcnow
    )

    # ============================================================
    # CONVERSION
    # ============================================================

    @classmethod
    def from_row(
        cls,
        row: Any,
    ) -> "Company":
        """
        Construit une Company à partir d'une ligne PostgreSQL.

        Accepte :
        - dictionnaire
        - mapping
        - tuple + colonnes
        """

        if row is None:
            raise ValueError(
                "Impossible de créer Company à partir d'une ligne vide."
            )

        if hasattr(row, "keys"):
            data = dict(row)
        elif hasattr(row, "_asdict"):
            data = row._asdict()
        else:
            raise TypeError(
                "La ligne PostgreSQL doit être un mapping "
                "ou fournir _asdict()."
            )

        valid_fields = {
            field_name
            for field_name in cls.__dataclass_fields__
        }

        cleaned: dict[str, Any] = {
            key: value
            for key, value in data.items()
            if key in valid_fields
        }

        return cls(**cleaned)

    # ============================================================
    # SERIALISATION
    # ============================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Retourne le modèle sous forme de dictionnaire.
        """

        return asdict(self)

    # ============================================================
    # PROFIL IA
    # ============================================================

    def get_ai_profile(self) -> dict[str, Any]:
        """
        Retourne uniquement les informations utiles
        au moteur IA.
        """

        return {
            "company": {
                "name": self.name,
                "description": self.description,
                "industry": self.industry,
                "business_type": self.business_type,
                "target_customers": self.target_customers,
                "target_market": self.target_market,
                "value_proposition": self.value_proposition,
                "selling_points": self.selling_points,
            },
            "communication": {
                "language": self.default_language,
                "supported_languages": self.supported_languages,
                "tone": self.tone,
                "style": self.communication_style,
                "greeting": self.greeting_message,
            },
            "commercial": {
                "services": self.services_description,
                "products": self.products_description,
                "rules": self.commercial_rules,
                "pricing_rules": self.pricing_rules,
                "discount_rules": self.discount_rules,
                "payment_methods": self.payment_methods,
                "return_policy": self.return_policy,
                "refund_policy": self.refund_policy,
                "shipping_policy": self.shipping_policy,
            },
            "locations": {
                "country": self.country,
                "city": self.city,
                "service_areas": self.service_areas,
                "delivery_areas": self.delivery_areas,
                "remote_service": self.remote_service,
            },
            "instructions": self.ai_instructions,
            "knowledge_base": self.knowledge_base,
            "forbidden_topics": self.forbidden_topics,
            "forbidden_claims": self.forbidden_claims,
        }

    # ============================================================
    # QUALIFICATION V3
    # ============================================================

    def get_qualification_config(self) -> dict[str, Any]:
        return {
            "enabled": self.qualification_enabled,
            "questions": self.qualification_questions,
            "required_fields": self.required_qualification_fields,
            "criteria": self.qualification_criteria,
        }

    # ============================================================
    # SCORING V3
    # ============================================================

    def get_scoring_config(self) -> dict[str, Any]:
        return {
            "enabled": self.prospect_scoring_enabled,
            "criteria": self.scoring_criteria,
            "thresholds": {
                "hot": self.hot_score_threshold,
                "warm": self.warm_score_threshold,
                "cold": self.cold_score_threshold,
            },
        }

    # ============================================================
    # FOLLOW-UP V3
    # ============================================================

    def get_followup_config(self) -> dict[str, Any]:
        return {
            "enabled": self.followup_enabled,
            "automatic": self.automatic_followup_enabled,
            "max_attempts": self.followup_max_attempts,
            "default_delay_hours": self.followup_default_delay_hours,
            "rules": self.followup_rules,
        }

    # ============================================================
    # DECISION ENGINE V3
    # ============================================================

    def get_decision_config(self) -> dict[str, Any]:
        return {
            "enabled": self.decision_engine_enabled,
            "allowed_actions": self.allowed_ai_actions,
            "stop_on_negative_intent": (
                self.auto_stop_on_negative_intent
            ),
            "escalate_high_value": (
                self.auto_escalate_high_value_prospect
            ),
            "high_value_threshold": (
                self.high_value_prospect_threshold
            ),
        }

    # ============================================================
    # VALIDATION MÉTIER
    # ============================================================

    def can_use_ai(self) -> bool:
        return self.is_active and self.ai_enabled

    def can_auto_reply(self) -> bool:
        return (
            self.is_active
            and self.ai_enabled
            and self.ai_auto_reply_enabled
        )

    def requires_human_validation(self) -> bool:
        return self.human_validation_required

    def can_qualify(self) -> bool:
        return (
            self.is_active
            and self.qualification_enabled
        )

    def can_score_prospect(self) -> bool:
        return (
            self.is_active
            and self.prospect_scoring_enabled
        )

    def can_followup(self) -> bool:
        return (
            self.is_active
            and self.followup_enabled
        )

    def can_use_decision_engine(self) -> bool:
        return (
            self.is_active
            and self.decision_engine_enabled
        )

    def can_escalate(self) -> bool:
        return (
            self.is_active
            and self.human_escalation_enabled
        )

    # ============================================================
    # ACTIONS IA AUTORISÉES
    # ============================================================

    def is_action_allowed(self, action: str) -> bool:
        return action in self.allowed_ai_actions

    # ============================================================
    # SCORE
    # ============================================================

    def classify_score(self, score: int) -> str:
        """
        Transforme un score numérique en catégorie commerciale.
        """

        score = max(0, min(100, score))

        if score >= self.hot_score_threshold:
            return "hot"

        if score >= self.warm_score_threshold:
            return "warm"

        if score >= self.cold_score_threshold:
            return "cold"

        return "very_cold"

    # ============================================================
    # MISE À JOUR
    # ============================================================

    def touch(self) -> None:
        self.updated_at = _utcnow()

    # ============================================================
    # ACTIVATION / DÉSACTIVATION
    # ============================================================

    def activate(self) -> None:
        self.is_active = True
        self.touch()

    def deactivate(self) -> None:
        self.is_active = False
        self.touch()

    # ============================================================
    # ONBOARDING
    # ============================================================

    def complete_onboarding(self) -> None:
        self.onboarding_completed = True
        self.touch()

    # ============================================================
    # VÉRIFICATION
    # ============================================================

    def verify(self) -> None:
        self.is_verified = True
        self.touch()