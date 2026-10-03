from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ProspectScore:
    """
    Score commercial d'un prospect.

    V2 :
    - score global
    - température
    - raisons du score
    - historique

    V3 :
    - scoring multi-facteurs
    - intention d'achat
    - urgence
    - budget
    - engagement
    - signaux d'achat
    - qualification
    - valeur potentielle
    - recommandation commerciale
    """

    id: int | None = None
    company_id: int | None = None
    contact_id: int | None = None
    prospect_profile_id: int | None = None
    conversation_id: int | None = None
    intent_id: int | None = None

    # ------------------------------------------------------------------
    # SCORE GLOBAL
    # ------------------------------------------------------------------

    score: float = 0.0

    previous_score: float = 0.0

    temperature: str = "very_cold"

    # hot / warm / cold / very_cold

    confidence: float = 0.0

    # ------------------------------------------------------------------
    # COMPOSANTS DU SCORE V3
    # ------------------------------------------------------------------

    intent_score: float = 0.0
    purchase_intent_score: float = 0.0
    engagement_score: float = 0.0
    qualification_score: float = 0.0
    budget_score: float = 0.0
    urgency_score: float = 0.0
    fit_score: float = 0.0
    interaction_score: float = 0.0
    recency_score: float = 0.0

    buying_signal_score: float = 0.0
    negative_signal_score: float = 0.0
    disqualification_score: float = 0.0

    # ------------------------------------------------------------------
    # VALEUR COMMERCIALE
    # ------------------------------------------------------------------

    estimated_value: float | None = None
    currency: str = "XAF"

    conversion_probability: float = 0.0

    expected_revenue: float | None = None

    # ------------------------------------------------------------------
    # SIGNIFICATION DU SCORE
    # ------------------------------------------------------------------

    reasons: list[str] = field(
        default_factory=list
    )

    positive_factors: list[str] = field(
        default_factory=list
    )

    negative_factors: list[str] = field(
        default_factory=list
    )

    buying_signals: list[str] = field(
        default_factory=list
    )

    disqualifying_signals: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # SCORING CONFIGURATION
    # ------------------------------------------------------------------

    scoring_version: str = "1.0"

    scoring_method: str = "weighted"

    weights: dict[str, float] = field(
        default_factory=dict
    )

    thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "hot": 80.0,
            "warm": 50.0,
            "cold": 20.0,
        }
    )

    # ------------------------------------------------------------------
    # DÉCISION COMMERCIALE
    # ------------------------------------------------------------------

    recommended_action: str = "respond"

    action_priority: int = 0

    action_reason: str | None = None

    human_attention_required: bool = False

    follow_up_recommended: bool = False

    # ------------------------------------------------------------------
    # ÉTAT
    # ------------------------------------------------------------------

    active: bool = True

    manually_overridden: bool = False

    override_score: float | None = None

    override_reason: str | None = None

    # ------------------------------------------------------------------
    # HISTORIQUE
    # ------------------------------------------------------------------

    score_history: list[dict[str, Any]] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # DATES
    # ------------------------------------------------------------------

    calculated_at: datetime = field(
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
    def from_row(cls, row: Any) -> "ProspectScore":
        if row is None:
            raise ValueError(
                "Impossible de créer ProspectScore "
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
    # SCORE EFFECTIF
    # ==================================================================

    def get_effective_score(self) -> float:
        if self.manually_overridden and self.override_score is not None:
            return max(
                0.0,
                min(100.0, self.override_score),
            )

        return max(
            0.0,
            min(100.0, self.score),
        )

    # ==================================================================
    # CLASSIFICATION
    # ==================================================================

    def classify(
        self,
        score: float | None = None,
    ) -> str:
        value = (
            self.get_effective_score()
            if score is None
            else max(0.0, min(100.0, score))
        )

        hot = self.thresholds.get(
            "hot",
            80.0,
        )

        warm = self.thresholds.get(
            "warm",
            50.0,
        )

        cold = self.thresholds.get(
            "cold",
            20.0,
        )

        if value >= hot:
            return "hot"

        if value >= warm:
            return "warm"

        if value >= cold:
            return "cold"

        return "very_cold"

    def update_temperature(self) -> None:
        self.temperature = self.classify()
        self.touch()

    def is_hot(self) -> bool:
        return self.temperature == "hot"

    def is_warm(self) -> bool:
        return self.temperature == "warm"

    def is_cold(self) -> bool:
        return self.temperature == "cold"

    # ==================================================================
    # CALCUL DU SCORE
    # ==================================================================

    def calculate_weighted_score(self) -> float:
        components = {
            "intent": self.intent_score,
            "purchase_intent": self.purchase_intent_score,
            "engagement": self.engagement_score,
            "qualification": self.qualification_score,
            "budget": self.budget_score,
            "urgency": self.urgency_score,
            "fit": self.fit_score,
            "interaction": self.interaction_score,
            "recency": self.recency_score,
            "buying_signals": self.buying_signal_score,
        }

        if not self.weights:
            weights = {
                key: 1.0
                for key in components
            }
        else:
            weights = self.weights

        total_weight = 0.0
        weighted_total = 0.0

        for key, value in components.items():
            weight = max(
                0.0,
                weights.get(key, 0.0),
            )

            weighted_total += (
                max(0.0, min(100.0, value))
                * weight
            )

            total_weight += weight

        if total_weight == 0:
            return 0.0

        positive_score = (
            weighted_total / total_weight
        )

        penalty = (
            self.negative_signal_score
            + self.disqualification_score
        )

        return max(
            0.0,
            min(
                100.0,
                positive_score - penalty,
            ),
        )

    def recalculate(self) -> float:
        self.previous_score = self.score

        self.score = self.calculate_weighted_score()

        self.temperature = self.classify(
            self.score
        )

        self.score_history.append(
            {
                "previous_score": self.previous_score,
                "score": self.score,
                "temperature": self.temperature,
                "timestamp": _utcnow(),
            }
        )

        self.calculated_at = _utcnow()
        self.touch()

        return self.score

    # ==================================================================
    # FACTEURS
    # ==================================================================

    def add_positive_factor(
        self,
        factor: str,
    ) -> None:
        normalized = factor.strip()

        if (
            normalized
            and normalized not in self.positive_factors
        ):
            self.positive_factors.append(normalized)

        self.touch()

    def add_negative_factor(
        self,
        factor: str,
    ) -> None:
        normalized = factor.strip()

        if (
            normalized
            and normalized not in self.negative_factors
        ):
            self.negative_factors.append(normalized)

        self.touch()

    def add_reason(
        self,
        reason: str,
    ) -> None:
        normalized = reason.strip()

        if (
            normalized
            and normalized not in self.reasons
        ):
            self.reasons.append(normalized)

        self.touch()

    # ==================================================================
    # SIGNaux COMMERCIAUX
    # ==================================================================

    def add_buying_signal(
        self,
        signal: str,
    ) -> None:
        normalized = signal.strip()

        if (
            normalized
            and normalized not in self.buying_signals
        ):
            self.buying_signals.append(normalized)

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
    # CONVERSION
    # ==================================================================

    def update_conversion_probability(
        self,
        probability: float,
    ) -> None:
        self.conversion_probability = max(
            0.0,
            min(1.0, probability),
        )

        if self.estimated_value is not None:
            self.expected_revenue = (
                self.estimated_value
                * self.conversion_probability
            )

        self.touch()

    # ==================================================================
    # DÉCISION
    # ==================================================================

    def set_recommended_action(
        self,
        action: str,
        reason: str | None = None,
        priority: int = 0,
    ) -> None:
        self.recommended_action = (
            action.strip().lower()
        )

        self.action_reason = reason

        self.action_priority = max(
            0,
            min(100, priority),
        )

        self.touch()

    def require_human_attention(
        self,
        reason: str | None = None,
    ) -> None:
        self.human_attention_required = True

        if reason:
            self.action_reason = reason

        self.recommended_action = "human"

        self.touch()

    def recommend_follow_up(
        self,
        reason: str | None = None,
    ) -> None:
        self.follow_up_recommended = True

        if reason:
            self.action_reason = reason

        self.touch()

    # ==================================================================
    # OVERRIDE HUMAIN
    # ==================================================================

    def override(
        self,
        score: float,
        reason: str,
    ) -> None:
        self.manually_overridden = True

        self.override_score = max(
            0.0,
            min(100.0, score),
        )

        self.override_reason = reason

        self.temperature = self.classify(
            self.override_score
        )

        self.touch()

    def clear_override(self) -> None:
        self.manually_overridden = False
        self.override_score = None
        self.override_reason = None

        self.update_temperature()

    # ==================================================================
    # CONTEXTE IA
    # ==================================================================

    def get_ai_context(self) -> dict[str, Any]:
        return {
            "score": {
                "value": self.get_effective_score(),
                "temperature": self.temperature,
                "confidence": self.confidence,
            },
            "components": {
                "intent": self.intent_score,
                "purchase_intent": self.purchase_intent_score,
                "engagement": self.engagement_score,
                "qualification": self.qualification_score,
                "budget": self.budget_score,
                "urgency": self.urgency_score,
                "fit": self.fit_score,
                "interaction": self.interaction_score,
                "recency": self.recency_score,
                "buying_signals": self.buying_signal_score,
            },
            "commercial": {
                "conversion_probability": (
                    self.conversion_probability
                ),
                "estimated_value": self.estimated_value,
                "expected_revenue": self.expected_revenue,
            },
            "signals": {
                "buying": self.buying_signals,
                "disqualifying": (
                    self.disqualifying_signals
                ),
            },
            "reasons": self.reasons,
            "positive_factors": self.positive_factors,
            "negative_factors": self.negative_factors,
            "decision": {
                "action": self.recommended_action,
                "priority": self.action_priority,
                "reason": self.action_reason,
                "human_required": (
                    self.human_attention_required
                ),
                "follow_up": (
                    self.follow_up_recommended
                ),
            },
        }

    # ==================================================================
    # TIMESTAMP
    # ==================================================================

    def touch(self) -> None:
        self.updated_at = _utcnow()