from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AIDecision:
    """
    Décision commerciale prise par VYRA.

    V2 :
    - décision de réponse
    - action
    - confiance
    - contexte
    - validation humaine

    V3 :
    - intention
    - qualification
    - score prospect
    - règles commerciales
    - follow-up
    - escalade
    - décision autonome
    """

    id: int | None = None

    company_id: int | None = None
    contact_id: int | None = None
    conversation_id: int | None = None
    message_id: int | None = None
    prospect_profile_id: int | None = None
    prospect_intent_id: int | None = None
    prospect_score_id: int | None = None

    # ------------------------------------------------------------------
    # DÉCISION
    # ------------------------------------------------------------------

    action: str = "respond"

    # respond
    # ask
    # wait
    # follow_up
    # human
    # stop
    # qualify
    # recommend
    # reject

    decision: str = "respond"

    confidence: float = 0.0

    priority: int = 50

    # ------------------------------------------------------------------
    # JUSTIFICATION
    # ------------------------------------------------------------------

    reason: str | None = None

    reasoning_summary: str | None = None

    decision_factors: list[str] = field(
        default_factory=list
    )

    supporting_evidence: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # CONTEXTE COMMERCIAL
    # ------------------------------------------------------------------

    detected_intent: str | None = None

    intent_confidence: float = 0.0

    prospect_score: float = 0.0

    prospect_temperature: str = "very_cold"

    purchase_intent: float = 0.0

    qualification_status: str = "unqualified"

    sales_stage: str = "new"

    # ------------------------------------------------------------------
    # PRODUITS / SERVICES
    # ------------------------------------------------------------------

    recommended_product_ids: list[int] = field(
        default_factory=list
    )

    recommended_service_ids: list[int] = field(
        default_factory=list
    )

    recommendation_reason: str | None = None

    # ------------------------------------------------------------------
    # RÉPONSE
    # ------------------------------------------------------------------

    response_required: bool = True

    response_text: str | None = None

    response_language: str = "fr"

    response_tone: str = "professional"

    response_max_length: int | None = None

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    human_validation_required: bool = False

    human_validated: bool = False

    validation_reason: str | None = None

    validated_by: str | None = None

    validated_at: datetime | None = None

    # ------------------------------------------------------------------
    # ESCALADE
    # ------------------------------------------------------------------

    escalation_required: bool = False

    escalation_reason: str | None = None

    escalation_priority: str = "normal"

    # ------------------------------------------------------------------
    # FOLLOW-UP
    # ------------------------------------------------------------------

    follow_up_required: bool = False

    follow_up_delay_minutes: int | None = None

    follow_up_reason: str | None = None

    follow_up_rule_id: int | None = None

    # ------------------------------------------------------------------
    # RÈGLES UTILISÉES
    # ------------------------------------------------------------------

    applied_rule_ids: list[int] = field(
        default_factory=list
    )

    blocked_rule_ids: list[int] = field(
        default_factory=list
    )

    rule_conflicts: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # LIMITES / SÉCURITÉ
    # ------------------------------------------------------------------

    blocked_actions: list[str] = field(
        default_factory=list
    )

    sensitive_action: bool = False

    safety_intervention: bool = False

    safety_reason: str | None = None

    # ------------------------------------------------------------------
    # IA
    # ------------------------------------------------------------------

    provider: str | None = None

    model: str | None = None

    prompt_version: str | None = None

    raw_ai_output: dict[str, Any] = field(
        default_factory=dict
    )

    ai_metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # EXÉCUTION
    # ------------------------------------------------------------------

    executed: bool = False

    execution_successful: bool = False

    execution_error: str | None = None

    executed_at: datetime | None = None

    # ------------------------------------------------------------------
    # ÉTAT
    # ------------------------------------------------------------------

    active: bool = True

    superseded: bool = False

    superseded_by_id: int | None = None

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
    def from_row(cls, row: Any) -> "AIDecision":
        if row is None:
            raise ValueError(
                "Impossible de créer AIDecision "
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    # ==================================================================
    # ACTION
    # ==================================================================

    def set_action(
        self,
        action: str,
        reason: str | None = None,
    ) -> None:
        self.action = action.strip().lower()
        self.decision = self.action

        if reason:
            self.reason = reason

        self.touch()

    def is_action_allowed(
        self,
        allowed_actions: list[str],
    ) -> bool:
        normalized = self.action.strip().lower()

        return normalized in {
            item.strip().lower()
            for item in allowed_actions
        }

    # ==================================================================
    # CONFIANCE
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

    def requires_review(
        self,
        threshold: float = 0.70,
    ) -> bool:
        return (
            self.confidence < threshold
            or self.human_validation_required
        )

    # ==================================================================
    # INTENTION
    # ==================================================================

    def set_intent(
        self,
        intent: str,
        confidence: float = 0.0,
    ) -> None:
        self.detected_intent = intent.strip()

        self.intent_confidence = max(
            0.0,
            min(1.0, confidence),
        )

        self.touch()

    # ==================================================================
    # SCORE
    # ==================================================================

    def set_prospect_score(
        self,
        score: float,
        temperature: str | None = None,
    ) -> None:
        self.prospect_score = max(
            0.0,
            min(100.0, score),
        )

        if temperature:
            self.prospect_temperature = (
                temperature.strip().lower()
            )
        elif self.prospect_score >= 80:
            self.prospect_temperature = "hot"
        elif self.prospect_score >= 50:
            self.prospect_temperature = "warm"
        elif self.prospect_score >= 20:
            self.prospect_temperature = "cold"
        else:
            self.prospect_temperature = "very_cold"

        self.touch()

    # ==================================================================
    # QUALIFICATION
    # ==================================================================

    def set_qualification(
        self,
        status: str,
    ) -> None:
        self.qualification_status = (
            status.strip().lower()
        )

        self.touch()

    # ==================================================================
    # RÈGLES
    # ==================================================================

    def apply_rule(
        self,
        rule_id: int,
    ) -> None:
        if rule_id not in self.applied_rule_ids:
            self.applied_rule_ids.append(rule_id)

        self.touch()

    def block_action(
        self,
        action: str,
    ) -> None:
        normalized = action.strip().lower()

        if normalized not in self.blocked_actions:
            self.blocked_actions.append(normalized)

        if normalized == self.action:
            self.human_validation_required = True

        self.touch()

    def add_rule_conflict(
        self,
        conflict: str,
    ) -> None:
        normalized = conflict.strip()

        if (
            normalized
            and normalized not in self.rule_conflicts
        ):
            self.rule_conflicts.append(normalized)

        self.human_validation_required = True

        self.touch()

    # ==================================================================
    # RÉPONSE
    # ==================================================================

    def set_response(
        self,
        response_text: str,
        language: str | None = None,
        tone: str | None = None,
    ) -> None:
        self.response_text = response_text

        if language:
            self.response_language = language

        if tone:
            self.response_tone = tone

        self.response_required = True

        self.touch()

    def suppress_response(
        self,
        reason: str | None = None,
    ) -> None:
        self.response_required = False

        if reason:
            self.reason = reason

        self.touch()

    # ==================================================================
    # FOLLOW-UP
    # ==================================================================

    def schedule_follow_up(
        self,
        delay_minutes: int | None = None,
        reason: str | None = None,
        rule_id: int | None = None,
    ) -> None:
        self.follow_up_required = True
        self.follow_up_delay_minutes = delay_minutes
        self.follow_up_reason = reason
        self.follow_up_rule_id = rule_id

        self.touch()

    # ==================================================================
    # ESCALADE
    # ==================================================================

    def require_human(
        self,
        reason: str,
        priority: str = "normal",
    ) -> None:
        self.human_validation_required = True
        self.escalation_required = True
        self.escalation_reason = reason
        self.escalation_priority = priority

        self.action = "human"
        self.decision = "human"

        self.touch()

    # ==================================================================
    # VALIDATION
    # ==================================================================

    def validate_by_human(
        self,
        validator: str | None = None,
        reason: str | None = None,
    ) -> None:
        self.human_validated = True
        self.human_validation_required = False

        self.validated_by = validator
        self.validation_reason = reason
        self.validated_at = _utcnow()

        self.touch()

    # ==================================================================
    # EXÉCUTION
    # ==================================================================

    def mark_executed(
        self,
        successful: bool = True,
        error: str | None = None,
    ) -> None:
        self.executed = True
        self.execution_successful = successful
        self.execution_error = error
        self.executed_at = _utcnow()

        self.touch()

    # ==================================================================
    # SUPERSESSION
    # ==================================================================

    def supersede(
        self,
        new_decision_id: int,
    ) -> None:
        self.superseded = True
        self.superseded_by_id = new_decision_id
        self.active = False

        self.touch()

    # ==================================================================
    # CONTEXTE IA
    # ==================================================================

    def get_ai_context(self) -> dict[str, Any]:
        return {
            "decision": {
                "action": self.action,
                "decision": self.decision,
                "confidence": self.confidence,
                "priority": self.priority,
                "reason": self.reason,
                "factors": self.decision_factors,
                "evidence": self.supporting_evidence,
            },
            "prospect": {
                "score": self.prospect_score,
                "temperature": (
                    self.prospect_temperature
                ),
                "purchase_intent": (
                    self.purchase_intent
                ),
                "qualification": (
                    self.qualification_status
                ),
                "sales_stage": self.sales_stage,
            },
            "intent": {
                "name": self.detected_intent,
                "confidence": self.intent_confidence,
            },
            "recommendations": {
                "products": (
                    self.recommended_product_ids
                ),
                "services": (
                    self.recommended_service_ids
                ),
                "reason": (
                    self.recommendation_reason
                ),
            },
            "response": {
                "required": self.response_required,
                "text": self.response_text,
                "language": self.response_language,
                "tone": self.response_tone,
                "max_length": self.response_max_length,
            },
            "follow_up": {
                "required": self.follow_up_required,
                "delay_minutes": (
                    self.follow_up_delay_minutes
                ),
                "reason": self.follow_up_reason,
            },
            "human": {
                "required": self.escalation_required,
                "reason": self.escalation_reason,
                "priority": self.escalation_priority,
            },
            "rules": {
                "applied": self.applied_rule_ids,
                "blocked": self.blocked_rule_ids,
                "conflicts": self.rule_conflicts,
            },
            "security": {
                "blocked_actions": self.blocked_actions,
                "sensitive_action": self.sensitive_action,
                "safety_intervention": (
                    self.safety_intervention
                ),
                "safety_reason": self.safety_reason,
            },
        }

    # ==================================================================
    # TIMESTAMP
    # ==================================================================

    def touch(self) -> None:
        self.updated_at = _utcnow()