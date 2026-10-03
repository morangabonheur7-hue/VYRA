from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ProspectIntent:
    """
    Intention commerciale détectée par VYRA.

    V2 :
    - intention détectée
    - confiance
    - source
    - contexte

    V3 :
    - classification commerciale
    - signaux associés
    - produits/services concernés
    - étape du parcours
    - impact sur le scoring
    - action recommandée
    """

    id: int | None = None
    company_id: int | None = None
    contact_id: int | None = None
    prospect_profile_id: int | None = None
    conversation_id: int | None = None
    message_id: int | None = None

    # ------------------------------------------------------------------
    # INTENTION
    # ------------------------------------------------------------------

    intent: str = ""
    intent_type: str = "unknown"

    # Exemples :
    # information
    # pricing
    # product_interest
    # service_interest
    # purchase
    # booking
    # negotiation
    # complaint
    # support
    # cancellation
    # refund
    # comparison
    # hesitation
    # human_request
    # follow_up
    # unknown

    sub_intent: str | None = None

    confidence: float = 0.0

    # ------------------------------------------------------------------
    # CLASSIFICATION COMMERCIALE
    # ------------------------------------------------------------------

    commercial_intent: str = "low"

    # low
    # medium
    # high
    # very_high

    purchase_intent_score: float = 0.0

    urgency_score: float = 0.0

    engagement_score: float = 0.0

    # ------------------------------------------------------------------
    # PRODUITS / SERVICES CONCERNÉS
    # ------------------------------------------------------------------

    product_ids: list[int] = field(
        default_factory=list
    )

    service_ids: list[int] = field(
        default_factory=list
    )

    product_names: list[str] = field(
        default_factory=list
    )

    service_names: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # SIGNAUX
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
    # BUDGET / TIMING
    # ------------------------------------------------------------------

    budget_detected: float | None = None
    budget_currency: str | None = None

    price_sensitivity: str | None = None

    purchase_timeline: str | None = None

    urgency: str = "unknown"

    # ------------------------------------------------------------------
    # OBJECTIONS
    # ------------------------------------------------------------------

    objections: list[str] = field(
        default_factory=list
    )

    objection_type: str | None = None

    # ------------------------------------------------------------------
    # CONTEXTE
    # ------------------------------------------------------------------

    extracted_entities: dict[str, Any] = field(
        default_factory=dict
    )

    extracted_requirements: list[str] = field(
        default_factory=list
    )

    context_summary: str | None = None

    evidence: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # QUALIFICATION
    # ------------------------------------------------------------------

    qualification_relevant: bool = False

    qualification_stage: str | None = None

    qualification_fields: dict[str, Any] = field(
        default_factory=dict
    )

    missing_information: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # SCORING V3
    # ------------------------------------------------------------------

    score_impact: float = 0.0

    score_reason: str | None = None

    score_components: dict[str, float] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # DÉCISION V3
    # ------------------------------------------------------------------

    recommended_action: str = "respond"

    allowed_actions: list[str] = field(
        default_factory=lambda: [
            "respond",
            "ask",
            "wait",
            "follow_up",
            "human",
            "stop",
        ]
    )

    decision_reason: str | None = None

    human_required: bool = False

    human_reason: str | None = None

    # ------------------------------------------------------------------
    # FOLLOW-UP V3
    # ------------------------------------------------------------------

    follow_up_recommended: bool = False

    follow_up_delay_minutes: int | None = None

    follow_up_reason: str | None = None

    # ------------------------------------------------------------------
    # DÉTECTION
    # ------------------------------------------------------------------

    detection_source: str = "ai"

    detection_model: str | None = None

    detection_version: str | None = None

    raw_ai_output: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    validated: bool = False

    validated_by_human: bool = False

    validation_reason: str | None = None

    # ------------------------------------------------------------------
    # ÉTAT
    # ------------------------------------------------------------------

    active: bool = True

    superseded: bool = False

    superseded_by_id: int | None = None

    # ------------------------------------------------------------------
    # DATES
    # ------------------------------------------------------------------

    detected_at: datetime = field(
        default_factory=_utcnow
    )

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
    def from_row(cls, row: Any) -> "ProspectIntent":
        if row is None:
            raise ValueError(
                "Impossible de créer ProspectIntent "
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
    # CONFIDENCE
    # ==================================================================

    def set_confidence(
        self,
        confidence: float,
    ) -> None:
        self.confidence = max(
            0.0,
            min(1.0, confidence),
        )

        self.touch()

    def is_confident(
        self,
        threshold: float = 0.70,
    ) -> bool:
        return self.confidence >= threshold

    # ==================================================================
    # INTENTION COMMERCIALE
    # ==================================================================

    def update_commercial_intent(
        self,
        purchase_score: float,
    ) -> None:
        self.purchase_intent_score = max(
            0.0,
            min(100.0, purchase_score),
        )

        if self.purchase_intent_score >= 80:
            self.commercial_intent = "very_high"
        elif self.purchase_intent_score >= 60:
            self.commercial_intent = "high"
        elif self.purchase_intent_score >= 30:
            self.commercial_intent = "medium"
        else:
            self.commercial_intent = "low"

        self.touch()

    def is_high_intent(self) -> bool:
        return self.commercial_intent in {
            "high",
            "very_high",
        }

    def is_purchase_intent(self) -> bool:
        return self.intent_type in {
            "purchase",
            "product_interest",
            "service_interest",
            "booking",
        }

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
    # PRODUITS / SERVICES
    # ==================================================================

    def add_product(
        self,
        product_id: int,
        name: str | None = None,
    ) -> None:
        if product_id not in self.product_ids:
            self.product_ids.append(product_id)

        if name and name not in self.product_names:
            self.product_names.append(name)

        self.touch()

    def add_service(
        self,
        service_id: int,
        name: str | None = None,
    ) -> None:
        if service_id not in self.service_ids:
            self.service_ids.append(service_id)

        if name and name not in self.service_names:
            self.service_names.append(name)

        self.touch()

    # ==================================================================
    # QUALIFICATION
    # ==================================================================

    def requires_qualification(self) -> bool:
        return (
            self.qualification_relevant
            and bool(self.missing_information)
        )

    def add_missing_information(
        self,
        field_name: str,
    ) -> None:
        normalized = field_name.strip()

        if (
            normalized
            and normalized not in self.missing_information
        ):
            self.missing_information.append(normalized)

        self.touch()

    # ==================================================================
    # DÉCISION
    # ==================================================================

    def set_recommended_action(
        self,
        action: str,
        reason: str | None = None,
    ) -> None:
        self.recommended_action = action.strip().lower()
        self.decision_reason = reason

        self.touch()

    def requires_human(self) -> bool:
        return self.human_required

    def request_human(
        self,
        reason: str,
    ) -> None:
        self.human_required = True
        self.human_reason = reason

        self.recommended_action = "human"

        self.touch()

    # ==================================================================
    # FOLLOW-UP
    # ==================================================================

    def recommend_follow_up(
        self,
        delay_minutes: int | None = None,
        reason: str | None = None,
    ) -> None:
        self.follow_up_recommended = True
        self.follow_up_delay_minutes = delay_minutes
        self.follow_up_reason = reason

        if self.recommended_action == "respond":
            self.recommended_action = "follow_up"

        self.touch()

    # ==================================================================
    # VALIDATION
    # ==================================================================

    def validate(
        self,
        reason: str | None = None,
    ) -> None:
        self.validated = True
        self.validated_by_human = True
        self.validation_reason = reason

        self.touch()

    # ==================================================================
    # SUPERSESSION
    # ==================================================================

    def supersede(
        self,
        new_intent_id: int,
    ) -> None:
        self.superseded = True
        self.superseded_by_id = new_intent_id
        self.active = False

        self.touch()

    # ==================================================================
    # CONTEXTE IA
    # ==================================================================

    def get_ai_context(self) -> dict[str, Any]:
        return {
            "intent": {
                "name": self.intent,
                "type": self.intent_type,
                "sub_intent": self.sub_intent,
                "confidence": self.confidence,
                "commercial_intent": self.commercial_intent,
            },
            "purchase": {
                "score": self.purchase_intent_score,
                "timeline": self.purchase_timeline,
                "urgency": self.urgency,
                "budget": self.budget_detected,
                "currency": self.budget_currency,
                "price_sensitivity": self.price_sensitivity,
            },
            "products": {
                "ids": self.product_ids,
                "names": self.product_names,
            },
            "services": {
                "ids": self.service_ids,
                "names": self.service_names,
            },
            "signals": {
                "buying": self.buying_signals,
                "strong_buying": (
                    self.strong_buying_signals
                ),
                "negative": self.negative_signals,
                "disqualifying": (
                    self.disqualifying_signals
                ),
            },
            "objections": {
                "items": self.objections,
                "type": self.objection_type,
            },
            "qualification": {
                "relevant": self.qualification_relevant,
                "stage": self.qualification_stage,
                "fields": self.qualification_fields,
                "missing": self.missing_information,
            },
            "scoring": {
                "impact": self.score_impact,
                "reason": self.score_reason,
                "components": self.score_components,
            },
            "decision": {
                "action": self.recommended_action,
                "reason": self.decision_reason,
                "human_required": self.human_required,
            },
            "follow_up": {
                "recommended": self.follow_up_recommended,
                "delay_minutes": (
                    self.follow_up_delay_minutes
                ),
                "reason": self.follow_up_reason,
            },
            "context": {
                "entities": self.extracted_entities,
                "requirements": self.extracted_requirements,
                "summary": self.context_summary,
                "evidence": self.evidence,
            },
        }

    # ==================================================================
    # TIMESTAMP
    # ==================================================================

    def touch(self) -> None:
        self.updated_at = _utcnow()