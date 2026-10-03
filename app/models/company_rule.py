from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CompanyRule:
    """
    Règle commerciale appartenant à une entreprise VYRA.

    V2 :
    - règles commerciales
    - comportement de l'assistant
    - réponses autorisées/interdites
    - prix et remises
    - horaires
    - paiement
    - livraison
    - escalade humaine
    - limites commerciales

    V3 :
    - qualification des prospects
    - signaux d'achat
    - scoring
    - intentions
    - conditions de décision
    - follow-up
    - actions commerciales
    """

    id: int | None = None
    company_id: int | None = None

    # ------------------------------------------------------------------
    # IDENTITÉ
    # ------------------------------------------------------------------

    name: str = ""
    description: str | None = None
    category: str = "general"
    priority: int = 0
    active: bool = True

    # ------------------------------------------------------------------
    # TYPE DE RÈGLE
    # ------------------------------------------------------------------

    rule_type: str = "instruction"

    # Exemples :
    # instruction
    # pricing
    # discount
    # payment
    # delivery
    # availability
    # communication
    # qualification
    # escalation
    # follow_up
    # prohibited
    # approval
    # custom

    trigger_conditions: dict[str, Any] = field(
        default_factory=dict
    )

    conditions: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # COMPORTEMENT COMMERCIAL
    # ------------------------------------------------------------------

    instruction: str | None = None

    action: str = "respond"

    # Actions possibles :
    # respond
    # ask
    # wait
    # follow_up
    # human
    # stop
    # reject
    # recommend
    # qualify
    # score

    response_template: str | None = None

    response_style: str | None = None

    required_context: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # RÉPONSES AUTORISÉES / INTERDITES
    # ------------------------------------------------------------------

    allowed_responses: list[str] = field(
        default_factory=list
    )

    forbidden_responses: list[str] = field(
        default_factory=list
    )

    forbidden_topics: list[str] = field(
        default_factory=list
    )

    forbidden_claims: list[str] = field(
        default_factory=list
    )

    required_disclaimers: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # PRIX / REMISES
    # ------------------------------------------------------------------

    price_rules: dict[str, Any] = field(
        default_factory=dict
    )

    minimum_price: float | None = None

    maximum_discount_percentage: float = 0.0

    discount_requires_approval: bool = True

    discount_approval_role: str | None = None

    negotiation_allowed: bool = False

    negotiation_instruction: str | None = None

    # ------------------------------------------------------------------
    # PAIEMENT
    # ------------------------------------------------------------------

    payment_methods: list[str] = field(
        default_factory=list
    )

    payment_rules: list[str] = field(
        default_factory=list
    )

    payment_before_service: bool = False

    payment_confirmation_required: bool = False

    payment_information_allowed: bool = True

    # ------------------------------------------------------------------
    # LIVRAISON / SERVICE
    # ------------------------------------------------------------------

    delivery_rules: list[str] = field(
        default_factory=list
    )

    service_area_rules: list[str] = field(
        default_factory=list
    )

    delivery_fee_rules: dict[str, Any] = field(
        default_factory=dict
    )

    delivery_time_rules: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # HORAIRES
    # ------------------------------------------------------------------

    business_hours: dict[str, Any] = field(
        default_factory=dict
    )

    outside_hours_action: str = "wait"

    outside_hours_message: str | None = None

    # ------------------------------------------------------------------
    # QUALIFICATION V3
    # ------------------------------------------------------------------

    qualification_enabled: bool = False

    qualification_stage: str = "initial"

    qualification_questions: list[str] = field(
        default_factory=list
    )

    required_information: list[str] = field(
        default_factory=list
    )

    optional_information: list[str] = field(
        default_factory=list
    )

    qualification_conditions: dict[str, Any] = field(
        default_factory=dict
    )

    qualification_score_threshold: float = 0.0

    # ------------------------------------------------------------------
    # INTENTIONS V3
    # ------------------------------------------------------------------

    relevant_intents: list[str] = field(
        default_factory=list
    )

    excluded_intents: list[str] = field(
        default_factory=list
    )

    intent_conditions: dict[str, Any] = field(
        default_factory=dict
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
    # SCORING V3
    # ------------------------------------------------------------------

    scoring_enabled: bool = False

    score_weight: float = 1.0

    score_bonus: float = 0.0

    score_penalty: float = 0.0

    minimum_score: float = 0.0

    hot_score_threshold: float = 80.0

    warm_score_threshold: float = 50.0

    cold_score_threshold: float = 20.0

    scoring_factors: dict[str, float] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # DÉCISION COMMERCIALE V3
    # ------------------------------------------------------------------

    decision_enabled: bool = True

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

    default_action: str = "respond"

    human_required_conditions: list[str] = field(
        default_factory=list
    )

    stop_conditions: list[str] = field(
        default_factory=list
    )

    escalation_conditions: list[str] = field(
        default_factory=list
    )

    approval_required: bool = False

    # ------------------------------------------------------------------
    # FOLLOW-UP V3
    # ------------------------------------------------------------------

    follow_up_enabled: bool = False

    follow_up_delay_minutes: int | None = None

    follow_up_max_attempts: int = 0

    follow_up_message: str | None = None

    follow_up_conditions: dict[str, Any] = field(
        default_factory=dict
    )

    follow_up_stop_conditions: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # ESCALADE HUMAINE
    # ------------------------------------------------------------------

    human_escalation_enabled: bool = True

    escalation_message: str | None = None

    escalation_reason_required: bool = True

    escalation_contact: str | None = None

    escalation_priority: str = "normal"

    # ------------------------------------------------------------------
    # LIMITES DE L'IA
    # ------------------------------------------------------------------

    ai_can_negotiate: bool = False

    ai_can_offer_discount: bool = False

    ai_can_confirm_order: bool = False

    ai_can_confirm_payment: bool = False

    ai_can_schedule: bool = False

    ai_can_cancel: bool = False

    ai_can_refund: bool = False

    ai_can_make_commitment: bool = False

    ai_can_contact_human: bool = True

    # ------------------------------------------------------------------
    # SÉCURITÉ COMMERCIALE
    # ------------------------------------------------------------------

    sensitive_information: list[str] = field(
        default_factory=list
    )

    information_never_disclose: list[str] = field(
        default_factory=list
    )

    competitor_rules: list[str] = field(
        default_factory=list
    )

    legal_rules: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # CONTEXTE IA
    # ------------------------------------------------------------------

    ai_instruction: str | None = None

    ai_context: dict[str, Any] = field(
        default_factory=dict
    )

    examples: list[dict[str, str]] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # MÉTADONNÉES
    # ------------------------------------------------------------------

    created_at: datetime = field(
        default_factory=_utcnow
    )

    updated_at: datetime = field(
        default_factory=_utcnow
    )

    # ==================================================================
    # CONVERSION DATABASE → MODEL
    # ==================================================================

    @classmethod
    def from_row(cls, row: Any) -> "CompanyRule":
        if row is None:
            raise ValueError(
                "Impossible de créer CompanyRule "
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
    # VALIDATION
    # ==================================================================

    def is_valid_action(self, action: str) -> bool:
        normalized = action.strip().lower()

        return normalized in {
            item.strip().lower()
            for item in self.allowed_actions
        }

    def can_execute_action(self, action: str) -> bool:
        if not self.active:
            return False

        if not self.decision_enabled:
            return False

        return self.is_valid_action(action)

    # ==================================================================
    # INTENTIONS
    # ==================================================================

    def matches_intent(self, intent: str) -> bool:
        normalized = intent.strip().lower()

        relevant = {
            item.strip().lower()
            for item in self.relevant_intents
        }

        excluded = {
            item.strip().lower()
            for item in self.excluded_intents
        }

        if normalized in excluded:
            return False

        if not relevant:
            return True

        return normalized in relevant

    # ==================================================================
    # SIGNAUX D'ACHAT
    # ==================================================================

    def has_buying_signal(self, signal: str) -> bool:
        normalized = signal.strip().lower()

        signals = {
            item.strip().lower()
            for item in self.buying_signals
        }

        return normalized in signals

    def has_strong_buying_signal(
        self,
        signal: str,
    ) -> bool:
        normalized = signal.strip().lower()

        signals = {
            item.strip().lower()
            for item in self.strong_buying_signals
        }

        return normalized in signals

    def has_negative_signal(
        self,
        signal: str,
    ) -> bool:
        normalized = signal.strip().lower()

        signals = {
            item.strip().lower()
            for item in self.negative_signals
        }

        return normalized in signals

    def is_disqualifying_signal(
        self,
        signal: str,
    ) -> bool:
        normalized = signal.strip().lower()

        signals = {
            item.strip().lower()
            for item in self.disqualifying_signals
        }

        return normalized in signals

    # ==================================================================
    # SCORING
    # ==================================================================

    def calculate_score_adjustment(
        self,
        *,
        buying_signal: bool = False,
        strong_buying_signal: bool = False,
        negative_signal: bool = False,
        disqualifying_signal: bool = False,
    ) -> float:
        if not self.scoring_enabled:
            return 0.0

        score = 0.0

        if buying_signal:
            score += self.score_bonus

        if strong_buying_signal:
            score += self.score_bonus * 2

        if negative_signal:
            score -= self.score_penalty

        if disqualifying_signal:
            score -= self.score_penalty * 2

        return score * self.score_weight

    def classify_score(self, score: float) -> str:
        if score >= self.hot_score_threshold:
            return "hot"

        if score >= self.warm_score_threshold:
            return "warm"

        if score >= self.cold_score_threshold:
            return "cold"

        return "very_cold"

    # ==================================================================
    # QUALIFICATION
    # ==================================================================

    def needs_qualification(self) -> bool:
        return (
            self.active
            and self.qualification_enabled
        )

    def get_missing_information(
        self,
        customer_information: dict[str, Any],
    ) -> list[str]:
        missing: list[str] = []

        for field_name in self.required_information:
            value = customer_information.get(field_name)

            if value is None:
                missing.append(field_name)
                continue

            if isinstance(value, str) and not value.strip():
                missing.append(field_name)

        return missing

    def is_qualified(
        self,
        customer_information: dict[str, Any],
        score: float | None = None,
    ) -> bool:
        if not self.qualification_enabled:
            return True

        missing = self.get_missing_information(
            customer_information
        )

        if missing:
            return False

        if score is not None:
            if score < self.qualification_score_threshold:
                return False

        return True

    # ==================================================================
    # REMISE / NÉGOCIATION
    # ==================================================================

    def can_negotiate(self) -> bool:
        return (
            self.active
            and self.negotiation_allowed
            and self.ai_can_negotiate
        )

    def can_offer_discount(
        self,
        discount_percentage: float,
    ) -> bool:
        if not self.active:
            return False

        if not self.ai_can_offer_discount:
            return False

        if self.discount_requires_approval:
            return False

        return (
            discount_percentage
            <= self.maximum_discount_percentage
        )

    # ==================================================================
    # ACTIONS SENSIBLES
    # ==================================================================

    def requires_human_for(
        self,
        action: str,
    ) -> bool:
        if not self.human_escalation_enabled:
            return False

        if action.strip().lower() == "human":
            return True

        return action.strip().lower() in {
            item.strip().lower()
            for item in self.human_required_conditions
        }

    def must_stop(self, reason: str) -> bool:
        normalized = reason.strip().lower()

        return normalized in {
            item.strip().lower()
            for item in self.stop_conditions
        }

    # ==================================================================
    # CONTEXTE POUR LE CERVEAU IA
    # ==================================================================
    
    def get_ai_context(self) -> dict[str, Any]:
        return {
            "rule": {
                "name": self.name,
                "description": self.description,
                "category": self.category,
                "type": self.rule_type,
                "priority": self.priority,
                "active": self.active,
            },
            "behavior": {
                "instruction": self.instruction,
                "action": self.action,
                "response_template": self.response_template,
                "response_style": self.response_style,
                "required_context": self.required_context,
            },
            "communication": {
                "allowed_responses": self.allowed_responses,
                "forbidden_responses": self.forbidden_responses,
                "forbidden_topics": self.forbidden_topics,
                "forbidden_claims": self.forbidden_claims,
                "required_disclaimers": self.required_disclaimers,
            },
            "commercial": {
                "price_rules": self.price_rules,
                "minimum_price": self.minimum_price,
                "maximum_discount_percentage": (
                    self.maximum_discount_percentage
                ),
                "discount_requires_approval": (
                    self.discount_requires_approval
                ),
                "negotiation_allowed": (
                    self.negotiation_allowed
                ),
                "payment_methods": self.payment_methods,
                "payment_rules": self.payment_rules,
                "delivery_rules": self.delivery_rules,
                "service_area_rules": self.service_area_rules,
            },
            "qualification": {
                "enabled": self.qualification_enabled,
                "stage": self.qualification_stage,
                "questions": self.qualification_questions,
                "required_information": (
                    self.required_information
                ),
                "optional_information": (
                    self.optional_information
                ),
                "conditions": self.qualification_conditions,
                "score_threshold": (
                    self.qualification_score_threshold
                ),
            },
            "intent": {
                "relevant": self.relevant_intents,
                "excluded": self.excluded_intents,
                "conditions": self.intent_conditions,
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
            "scoring": {
                "enabled": self.scoring_enabled,
                "weight": self.score_weight,
                "bonus": self.score_bonus,
                "penalty": self.score_penalty,
                "minimum": self.minimum_score,
                "hot": self.hot_score_threshold,
                "warm": self.warm_score_threshold,
                "cold": self.cold_score_threshold,
                "factors": self.scoring_factors,
            },
            "decision": {
                "enabled": self.decision_enabled,
                "allowed_actions": self.allowed_actions,
                "default_action": self.default_action,
                "human_required": (
                    self.human_required_conditions
                ),
                "stop_conditions": self.stop_conditions,
                "escalation_conditions": (
                    self.escalation_conditions
                ),
                "approval_required": self.approval_required,
            },
            "follow_up": {
                "enabled": self.follow_up_enabled,
                "delay_minutes": (
                    self.follow_up_delay_minutes
                ),
                "max_attempts": (
                    self.follow_up_max_attempts
                ),
                "message": self.follow_up_message,
                "conditions": self.follow_up_conditions,
                "stop_conditions": (
                    self.follow_up_stop_conditions
                ),
            },
            "human": {
                "enabled": self.human_escalation_enabled,
                "message": self.escalation_message,
                "reason_required": (
                    self.escalation_reason_required
                ),
                "contact": self.escalation_contact,
                "priority": self.escalation_priority,
            },
            "ai_limits": {
                "can_negotiate": self.ai_can_negotiate,
                "can_offer_discount": (
                    self.ai_can_offer_discount
                ),
                "can_confirm_order": (
                    self.ai_can_confirm_order
                ),
                "can_confirm_payment": (
                    self.ai_can_confirm_payment
                ),
                "can_schedule": self.ai_can_schedule,
                "can_cancel": self.ai_can_cancel,
                "can_refund": self.ai_can_refund,
                "can_make_commitment": (
                    self.ai_can_make_commitment
                ),
                "can_contact_human": (
                    self.ai_can_contact_human
                ),
            },
            "security": {
                "sensitive_information": (
                    self.sensitive_information
                ),
                "never_disclose": (
                    self.information_never_disclose
                ),
                "competitor_rules": (
                    self.competitor_rules
                ),
                "legal_rules": self.legal_rules,
            },
            "ai": {
                "instruction": self.ai_instruction,
                "context": self.ai_context,
                "examples": self.examples,
            },
        }

    # ==================================================================
    # PRIORITÉ
    # ==================================================================

    def get_priority(self) -> int:
        return max(0, min(100, self.priority))

    # ==================================================================
    # ACTIVATION
    # ==================================================================

    def activate(self) -> None:
        self.active = True
        self.touch()

    def deactivate(self) -> None:
        self.active = False
        self.touch()

    # ==================================================================
    # MISE À JOUR
    # ==================================================================

    def get_ai_context(self) -> dict[str, Any]:
        return {
            "rule": {
                "name": self.name,
                "description": self.description,
                "category": self.category,
                "type": self.rule_type,
                "priority": self.priority,
                "active": self.active,
            },
            "behavior": {
                "instruction": self.instruction,
                "action": self.action,
                "response_template": self.response_template,
                "response_style": self.response_style,
                "required_context": self.required_context,
            },
            "communication": {
                "allowed_responses": self.allowed_responses,
                "forbidden_responses": self.forbidden_responses,
                "forbidden_topics": self.forbidden_topics,
                "forbidden_claims": self.forbidden_claims,
                "required_disclaimers": self.required_disclaimers,
            },
            "commercial": {
                "price_rules": self.price_rules,
                "minimum_price": self.minimum_price,
                "maximum_discount_percentage": (
                    self.maximum_discount_percentage
                ),
                "discount_requires_approval": (
                    self.discount_requires_approval
                ),
                "negotiation_allowed": (
                    self.negotiation_allowed
                ),
                "payment_methods": self.payment_methods,
                "payment_rules": self.payment_rules,
                "delivery_rules": self.delivery_rules,
                "service_area_rules": self.service_area_rules,
            },
            "qualification": {
                "enabled": self.qualification_enabled,
                "stage": self.qualification_stage,
                "questions": self.qualification_questions,
                "required_information": (
                    self.required_information
                ),
                "optional_information": (
                    self.optional_information
                ),
                "conditions": self.qualification_conditions,
                "score_threshold": (
                    self.qualification_score_threshold
                ),
            },
            "intent": {
                "relevant": self.relevant_intents,
                "excluded": self.excluded_intents,
                "conditions": self.intent_conditions,
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
            "scoring": {
                "enabled": self.scoring_enabled,
                "weight": self.score_weight,
                "bonus": self.score_bonus,
                "penalty": self.score_penalty,
                "minimum": self.minimum_score,
                "hot": self.hot_score_threshold,
                "warm": self.warm_score_threshold,
                "cold": self.cold_score_threshold,
                "factors": self.scoring_factors,
            },
            "decision": {
                "enabled": self.decision_enabled,
                "allowed_actions": self.allowed_actions,
                "default_action": self.default_action,
                "human_required": (
                    self.human_required_conditions
                ),
                "stop_conditions": self.stop_conditions,
                "escalation_conditions": (
                    self.escalation_conditions
                ),
                "approval_required": self.approval_required,
            },
            "follow_up": {
                "enabled": self.follow_up_enabled,
                "delay_minutes": (
                    self.follow_up_delay_minutes
                ),
                "max_attempts": (
                    self.follow_up_max_attempts
                ),
                "message": self.follow_up_message,
                "conditions": self.follow_up_conditions,
                "stop_conditions": (
                    self.follow_up_stop_conditions
                ),
            },
            "human": {
                "enabled": self.human_escalation_enabled,
                "message": self.escalation_message,
                "reason_required": (
                    self.escalation_reason_required
                ),
                "contact": self.escalation_contact,
                "priority": self.escalation_priority,
            },
            "ai_limits": {
                "can_negotiate": self.ai_can_negotiate,
                "can_offer_discount": (
                    self.ai_can_offer_discount
                ),
                "can_confirm_order": (
                    self.ai_can_confirm_order
                ),
                "can_confirm_payment": (
                    self.ai_can_confirm_payment
                ),
                "can_schedule": self.ai_can_schedule,
                "can_cancel": self.ai_can_cancel,
                "can_refund": self.ai_can_refund,
                "can_make_commitment": (
                    self.ai_can_make_commitment
                ),
                "can_contact_human": (
                    self.ai_can_contact_human
                ),
            },
            "security": {
                "sensitive_information": (
                    self.sensitive_information
                ),
                "never_disclose": (
                    self.information_never_disclose
                ),
                "competitor_rules": (
                    self.competitor_rules
                ),
                "legal_rules": self.legal_rules,
            },
            "ai": {
                "instruction": self.ai_instruction,
                "context": self.ai_context,
                "examples": self.examples,
            },
        }

    # ==================================================================
    # PRIORITÉ
    # ==================================================================

    def get_priority(self) -> int:
        return max(0, min(100, self.priority))

    # ==================================================================
    # ACTIVATION
    # ==================================================================

    def activate(self) -> None:
        self.active = True
        self.touch()

    def deactivate(self) -> None:
        self.active = False
        self.touch()

    # ==================================================================
    # MISE À JOUR
    # ==================================================================
    
     def touch(self) -> None:
        self.updated_at = _utcnow() 