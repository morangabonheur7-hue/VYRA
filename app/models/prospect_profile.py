from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ProspectProfile:
    """
    Profil commercial d'un prospect VYRA.

    V2 :
    - identité et coordonnées
    - localisation
    - entreprise
    - besoins
    - préférences
    - historique commercial

    V3 :
    - profil client idéal
    - qualification
    - signaux d'achat
    - objections
    - budget
    - urgence
    - intention
    - score
    - température commerciale
    - étape du parcours
    """

    id: int | None = None
    company_id: int | None = None
    contact_id: int | None = None

    # ------------------------------------------------------------------
    # IDENTITÉ
    # ------------------------------------------------------------------

    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    preferred_name: str | None = None

    email: str | None = None
    phone: str | None = None
    whatsapp_number: str | None = None

    # ------------------------------------------------------------------
    # PROFIL PROFESSIONNEL
    # ------------------------------------------------------------------

    company_name: str | None = None
    job_title: str | None = None
    industry: str | None = None
    business_type: str | None = None
    company_size: str | None = None

    website: str | None = None
    social_profiles: dict[str, str] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # LOCALISATION
    # ------------------------------------------------------------------

    country: str | None = None
    city: str | None = None
    region: str | None = None
    address: str | None = None
    timezone: str | None = None

    # ------------------------------------------------------------------
    # BESOINS COMMERCIAUX
    # ------------------------------------------------------------------

    needs: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    objectives: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)

    requested_products: list[int] = field(
        default_factory=list
    )

    requested_services: list[int] = field(
        default_factory=list
    )

    preferred_products: list[str] = field(
        default_factory=list
    )

    preferred_services: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # BUDGET / ACHAT
    # ------------------------------------------------------------------

    budget: float | None = None
    minimum_budget: float | None = None
    maximum_budget: float | None = None
    budget_currency: str = "XAF"

    budget_confirmed: bool = False

    purchasing_power: str | None = None

    purchase_timeline: str | None = None
    urgency: str = "unknown"

    decision_timeframe: str | None = None

    # ------------------------------------------------------------------
    # PRÉFÉRENCES
    # ------------------------------------------------------------------

    preferred_language: str | None = None
    preferred_contact_channel: str = "whatsapp"

    communication_preferences: dict[str, Any] = field(
        default_factory=dict
    )

    preferred_contact_times: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # QUALIFICATION V3
    # ------------------------------------------------------------------

    qualification_status: str = "unqualified"

    qualification_stage: str = "initial"

    qualification_data: dict[str, Any] = field(
        default_factory=dict
    )

    required_information: list[str] = field(
        default_factory=list
    )

    missing_information: list[str] = field(
        default_factory=list
    )

    qualification_score: float = 0.0

    qualification_complete: bool = False

    # ------------------------------------------------------------------
    # INTENTION V3
    # ------------------------------------------------------------------

    primary_intent: str | None = None

    secondary_intents: list[str] = field(
        default_factory=list
    )

    intent_confidence: float = 0.0

    intent_history: list[dict[str, Any]] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # SIGNAUX COMMERCIAUX V3
    # ------------------------------------------------------------------

    buying_signals: list[str] = field(
        default_factory=list
    )

    strong_buying_signals: list[str] = field(
        default_factory=list
    )

    negative_signals: list[str] = field(
        default_factory=list
    )

    disqualifying_signals: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # OBJECTIONS
    # ------------------------------------------------------------------

    objections: list[str] = field(
        default_factory=list
    )

    unresolved_objections: list[str] = field(
        default_factory=list
    )

    resolved_objections: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # SCORING V3
    # ------------------------------------------------------------------

    score: float = 0.0

    score_components: dict[str, float] = field(
        default_factory=dict
    )

    score_history: list[dict[str, Any]] = field(
        default_factory=list
    )

    temperature: str = "very_cold"

    # ------------------------------------------------------------------
    # PARCOURS COMMERCIAL V3
    # ------------------------------------------------------------------

    lifecycle_stage: str = "new"

    funnel_stage: str = "awareness"

    sales_stage: str = "new"

    # Exemples :
    # new
    # contacted
    # interested
    # qualified
    # proposal
    # negotiation
    # ready_to_buy
    # customer
    # lost
    # inactive

    # ------------------------------------------------------------------
    # CONVERSION
    # ------------------------------------------------------------------

    purchase_intent: float = 0.0

    conversion_probability: float = 0.0

    estimated_value: float | None = None

    estimated_value_currency: str = "XAF"

    last_purchase_amount: float | None = None

    total_purchase_amount: float = 0.0

    # ------------------------------------------------------------------
    # RELATION COMMERCIALE
    # ------------------------------------------------------------------

    customer_status: str = "prospect"

    is_returning_customer: bool = False

    previous_customer: bool = False

    loyalty_level: str | None = None

    # ------------------------------------------------------------------
    # ACTIVITÉ
    # ------------------------------------------------------------------

    first_contact_at: datetime | None = None
    last_contact_at: datetime | None = None
    last_interaction_at: datetime | None = None

    total_conversations: int = 0
    total_messages: int = 0

    unanswered_messages: int = 0

    # ------------------------------------------------------------------
    # FOLLOW-UP V3
    # ------------------------------------------------------------------

    follow_up_required: bool = False
    follow_up_reason: str | None = None
    next_follow_up_at: datetime | None = None
    follow_up_attempts: int = 0

    # ------------------------------------------------------------------
    # ESCALADE HUMAINE
    # ------------------------------------------------------------------

    human_attention_required: bool = False
    human_attention_reason: str | None = None

    assigned_to: str | None = None

    # ------------------------------------------------------------------
    # CONSENTEMENT / COMMUNICATION
    # ------------------------------------------------------------------

    marketing_consent: bool = False
    communication_allowed: bool = True
    blocked: bool = False
    blocked_reason: str | None = None

    # ------------------------------------------------------------------
    # MÉTADONNÉES IA
    # ------------------------------------------------------------------

    ai_summary: str | None = None

    ai_notes: list[str] = field(
        default_factory=list
    )

    extracted_facts: dict[str, Any] = field(
        default_factory=dict
    )

    custom_attributes: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # DATES
    # ------------------------------------------------------------------

    created_at: datetime = field(
        default_factory=_utcnow
    )

    updated_at: datetime = field(
        default_factory=_utcnow
    )

    # ==================================================================
    # DATABASE → MODEL
    # ==================================================================

    @classmethod
    def from_row(cls, row: Any) -> "ProspectProfile":
        if row is None:
            raise ValueError(
                "Impossible de créer ProspectProfile "
                "à partir d'une ligne vide."
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

        cleaned = {
            key: value
            for key, value in data.items()
            if key in valid_fields
        }

        return cls(**cleaned)

    # ==================================================================
    # MODEL → DICT
    # ==================================================================

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    # ==================================================================
    # IDENTITÉ
    # ==================================================================

    def get_display_name(self) -> str:
        if self.preferred_name:
            return self.preferred_name

        if self.full_name:
            return self.full_name

        full_name = " ".join(
            part
            for part in [
                self.first_name,
                self.last_name,
            ]
            if part
        )

        return full_name or "Prospect"

    # ==================================================================
    # QUALIFICATION
    # ==================================================================

    def is_qualified(self) -> bool:
        return (
            self.qualification_complete
            and self.qualification_status == "qualified"
        )

    def has_missing_information(self) -> bool:
        return bool(self.missing_information)

    def add_missing_information(
        self,
        information: str,
    ) -> None:
        normalized = information.strip()

        if (
            normalized
            and normalized not in self.missing_information
        ):
            self.missing_information.append(normalized)

        self.touch()

    def provide_information(
        self,
        information: str,
    ) -> None:
        normalized = information.strip()

        self.missing_information = [
            item
            for item in self.missing_information
            if item.lower() != normalized.lower()
        ]

        self.touch()

    def complete_qualification(
        self,
        score: float | None = None,
    ) -> None:
        self.qualification_complete = True
        self.qualification_status = "qualified"

        if score is not None:
            self.qualification_score = max(
                0.0,
                min(100.0, score),
            )

        self.touch()

    # ==================================================================
    # INTENTION
    # ==================================================================

    def set_primary_intent(
        self,
        intent: str,
        confidence: float = 0.0,
    ) -> None:
        normalized = intent.strip()

        if not normalized:
            return

        self.primary_intent = normalized
        self.intent_confidence = max(
            0.0,
            min(1.0, confidence),
        )

        self.intent_history.append(
            {
                "intent": normalized,
                "confidence": self.intent_confidence,
                "timestamp": _utcnow(),
            }
        )

        self.touch()

    def add_secondary_intent(
        self,
        intent: str,
    ) -> None:
        normalized = intent.strip()

        if (
            normalized
            and normalized not in self.secondary_intents
        ):
            self.secondary_intents.append(normalized)

        self.touch()

    # ==================================================================
    # SIGNAUX
    # ==================================================================

    def add_buying_signal(
        self,
        signal: str,
        strong: bool = False,
    ) -> None:
        normalized = signal.strip()

        if not normalized:
            return

        target = (
            self.strong_buying_signals
            if strong
            else self.buying_signals
        )

        if normalized not in target:
            target.append(normalized)

        self.touch()

    def add_negative_signal(
        self,
        signal: str,
    ) -> None:
        normalized = signal.strip()

        if (
            normalized
            and normalized not in self.negative_signals
        ):
            self.negative_signals.append(normalized)

        self.touch()

    def add_disqualifying_signal(
        self,
        signal: str,
    ) -> None:
        normalized = signal.strip()

        if (
            normalized
            and normalized not in self.disqualifying_signals
        ):
            self.disqualifying_signals.append(normalized)

        self.touch()

    # ==================================================================
    # SCORE
    # ==================================================================

    def update_score(
        self,
        score: float,
        components: dict[str, float] | None = None,
    ) -> None:
        previous_score = self.score

        self.score = max(
            0.0,
            min(100.0, score),
        )

        self.score_components = (
            components or {}
        )

        self.score_history.append(
            {
                "previous_score": previous_score,
                "score": self.score,
                "components": self.score_components,
                "timestamp": _utcnow(),
            }
        )

        self.update_temperature()

        self.touch()

    def update_temperature(self) -> None:
        if self.score >= 80:
            self.temperature = "hot"
        elif self.score >= 50:
            self.temperature = "warm"
        elif self.score >= 20:
            self.temperature = "cold"
        else:
            self.temperature = "very_cold"

    def is_hot(self) -> bool:
        return self.temperature == "hot"

    def is_warm(self) -> bool:
        return self.temperature == "warm"

    # ==================================================================
    # ACHAT
    # ==================================================================

    def update_conversion_probability(
        self,
        probability: float,
    ) -> None:
        self.conversion_probability = max(
            0.0,
            min(1.0, probability),
        )

        self.touch()

    def update_purchase_intent(
        self,
        intent_score: float,
    ) -> None:
        self.purchase_intent = max(
            0.0,
            min(1.0, intent_score),
        )

        self.touch()

    # ==================================================================
    # FOLLOW-UP
    # ==================================================================

    def require_follow_up(
        self,
        reason: str | None = None,
        next_follow_up_at: datetime | None = None,
    ) -> None:
        self.follow_up_required = True
        self.follow_up_reason = reason
        self.next_follow_up_at = next_follow_up_at

        self.touch()

    def clear_follow_up(self) -> None:
        self.follow_up_required = False
        self.follow_up_reason = None
        self.next_follow_up_at = None

        self.touch()

    # ==================================================================
    # ESCALADE
    # ==================================================================

    def require_human_attention(
        self,
        reason: str,
    ) -> None:
        self.human_attention_required = True
        self.human_attention_reason = reason

        self.touch()

    def clear_human_attention(self) -> None:
        self.human_attention_required = False
        self.human_attention_reason = None

        self.touch()

    # ==================================================================
    # BLOCAGE
    # ==================================================================

    def block(self, reason: str | None = None) -> None:
        self.blocked = True
        self.communication_allowed = False
        self.blocked_reason = reason

        self.touch()

    def unblock(self) -> None:
        self.blocked = False
        self.communication_allowed = True
        self.blocked_reason = None

        self.touch()

    # ==================================================================
    # CONTEXTE IA
    # ==================================================================

   def get_ai_context(self) -> dict[str, Any]:
        return {
            "identity": {
                "name": self.get_display_name(),
                "first_name": self.first_name,
                "last_name": self.last_name,
                "company": self.company_name,
                "job_title": self.job_title,
                "industry": self.industry,
            },
            "location": {
                "country": self.country,
                "city": self.city,
                "region": self.region,
                "timezone": self.timezone,
            },
            "needs": {
                "needs": self.needs,
                "problems": self.problems,
                "objectives": self.objectives,
                "interests": self.interests,
                "products": self.requested_products,
                "services": self.requested_services,
            },
            "commercial": {
                "budget": self.budget,
                "currency": self.budget_currency,
                "budget_confirmed": self.budget_confirmed,
                "purchasing_power": self.purchasing_power,
                "timeline": self.purchase_timeline,
                "urgency": self.urgency,
            },
            "qualification": {
                "status": self.qualification_status,
                "stage": self.qualification_stage,
                "score": self.qualification_score,
                "complete": self.qualification_complete,
                "missing": self.missing_information,
            },
            "intent": {
                "primary": self.primary_intent,
                "secondary": self.secondary_intents,
                "confidence": self.intent_confidence,
            },
            "signals": {
                "buying": self.buying_signals,
                "strong_buying": self.strong_buying_signals,
                "negative": self.negative_signals,
                "disqualifying": self.disqualifying_signals,
            },
            "objections": {
                "active": self.unresolved_objections,
                "resolved": self.resolved_objections,
            },
            "scoring": {
                "score": self.score,
                "temperature": self.temperature,
                "components": self.score_components,
                "conversion_probability": (
                    self.conversion_probability
                ),
                "purchase_intent": self.purchase_intent,
            },
            "sales": {
                "lifecycle_stage": self.lifecycle_stage,
                "funnel_stage": self.funnel_stage,
                "sales_stage": self.sales_stage,
                "customer_status": self.customer_status,
            },
            "follow_up": {
                "required": self.follow_up_required,
                "reason": self.follow_up_reason,
                "next_at": self.next_follow_up_at,
                "attempts": self.follow_up_attempts,
            },
            "human": {
                "required": self.human_attention_required,
                "reason": self.human_attention_reason,
            },
            "ai": {
                "summary": self.ai_summary,
                "notes": self.ai_notes,
                "facts": self.extracted_facts,
            },
        }

    # ==================================================================
    # ACTIVITÉ
    # ==================================================================

    def register_message(self) -> None:
        self.total_messages += 1
        self.last_interaction_at = _utcnow()

        if self.first_contact_at is None:
            self.first_contact_at = self.last_interaction_at

        self.touch()

    def register_conversation(self) -> None:
        self.total_conversations += 1
        self.last_contact_at = _utcnow()
        self.last_interaction_at = self.last_contact_at

        if self.first_contact_at is None:
            self.first_contact_at = self.last_contact_at

        self.touch()

    # ==================================================================
    # TIMESTAMP
    # ==================================================================

    def touch(self) -> None:
        self.updated_at = _utcnow()