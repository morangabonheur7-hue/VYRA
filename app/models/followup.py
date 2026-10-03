from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class FollowUp:
    """
    Suivi commercial automatique VYRA.

    V2 :
    - rappel
    - message de suivi
    - date d'exécution
    - statut
    - nombre de tentatives

    V3 :
    - suivi déclenché par intention
    - score du prospect
    - règles commerciales
    - arrêt intelligent
    - personnalisation
    - priorités
    - décision automatique
    """

    id: int | None = None
    company_id: int | None = None
    contact_id: int | None = None
    prospect_profile_id: int | None = None
    conversation_id: int | None = None
    intent_id: int | None = None
    score_id: int | None = None

    # ------------------------------------------------------------------
    # IDENTITÉ
    # ------------------------------------------------------------------

    name: str = ""

    description: str | None = None

    follow_up_type: str = "commercial"

    # commercial
    # reminder
    # abandoned_conversation
    # interested_prospect
    # quote
    # proposal
    # payment
    # booking
    # reactivation
    # custom

    # ------------------------------------------------------------------
    # DÉCLENCHEMENT
    # ------------------------------------------------------------------

    trigger_type: str = "manual"

    # manual
    # automatic
    # score
    # intent
    # inactivity
    # event
    # rule

    trigger_reason: str | None = None

    trigger_conditions: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # MESSAGE
    # ------------------------------------------------------------------

    message_template: str | None = None

    generated_message: str | None = None

    language: str = "fr"

    tone: str = "professional"

    personalization_context: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # PLANIFICATION
    # ------------------------------------------------------------------

    scheduled_at: datetime | None = None

    delay_minutes: int | None = None

    timezone: str = "UTC"

    # ------------------------------------------------------------------
    # EXÉCUTION
    # ------------------------------------------------------------------

    status: str = "pending"

    # pending
    # scheduled
    # processing
    # sent
    # failed
    # cancelled
    # skipped
    # stopped

    attempts: int = 0

    max_attempts: int = 3

    last_attempt_at: datetime | None = None

    sent_at: datetime | None = None

    failed_at: datetime | None = None

    failure_reason: str | None = None

    # ------------------------------------------------------------------
    # CONDITIONS D'ARRÊT V3
    # ------------------------------------------------------------------

    stop_if_customer_replies: bool = True

    stop_if_customer_buys: bool = True

    stop_if_customer_requests_human: bool = True

    stop_if_conversation_closed: bool = True

    stop_if_contact_blocked: bool = True

    stop_if_score_drops: bool = False

    minimum_score: float | None = None

    stop_conditions: list[str] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # V3 : INTELLIGENCE COMMERCIALE
    # ------------------------------------------------------------------

    required_intents: list[str] = field(
        default_factory=list
    )

    excluded_intents: list[str] = field(
        default_factory=list
    )

    required_signals: list[str] = field(
        default_factory=list
    )

    minimum_prospect_score: float | None = None

    minimum_purchase_intent: float | None = None

    # ------------------------------------------------------------------
    # PRIORITÉ
    # ------------------------------------------------------------------

    priority: int = 50

    urgency: str = "normal"

    # low
    # normal
    # high
    # urgent

    # ------------------------------------------------------------------
    # AUTOMATISATION
    # ------------------------------------------------------------------

    automatic: bool = True

    ai_generated: bool = True

    requires_human_validation: bool = False

    human_validated: bool = False

    # ------------------------------------------------------------------
    # CANAL
    # ------------------------------------------------------------------

    channel: str = "whatsapp"

    channel_metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # RÉPONSE / RÉSULTAT
    # ------------------------------------------------------------------

    customer_replied: bool = False

    reply_message_id: int | None = None

    result: str | None = None

    result_data: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # RELANCES
    # ------------------------------------------------------------------

    follow_up_sequence: int = 1

    max_sequence: int = 3

    next_follow_up_id: int | None = None

    previous_follow_up_id: int | None = None

    # ------------------------------------------------------------------
    # ÉTAT
    # ------------------------------------------------------------------

    active: bool = True

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
    def from_row(cls, row: Any) -> "FollowUp":
        if row is None:
            raise ValueError(
                "Impossible de créer FollowUp "
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
    # PLANIFICATION
    # ==================================================================

    def is_due(
        self,
        now: datetime | None = None,
    ) -> bool:
        if not self.active:
            return False

        if self.status not in {
            "pending",
            "scheduled",
        }:
            return False

        if self.scheduled_at is None:
            return False

        current_time = now or _utcnow()

        if self.scheduled_at.tzinfo is None:
            current_time = current_time.replace(
                tzinfo=None
            )

        return self.scheduled_at <= current_time

    def schedule(
        self,
        scheduled_at: datetime,
    ) -> None:
        self.scheduled_at = scheduled_at
        self.status = "scheduled"
        self.active = True

        self.touch()

    # ==================================================================
    # CONDITIONS D'EXÉCUTION
    # ==================================================================

    def can_execute(
        self,
        *,
        prospect_score: float | None = None,
        purchase_intent: float | None = None,
        intent: str | None = None,
        signals: list[str] | None = None,
        customer_replied: bool = False,
        customer_bought: bool = False,
        human_requested: bool = False,
        conversation_closed: bool = False,
        contact_blocked: bool = False,
    ) -> bool:
        if not self.active:
            return False

        if self.status not in {
            "pending",
            "scheduled",
        }:
            return False

        if self.attempts >= self.max_attempts:
            return False

        if (
            self.stop_if_customer_replies
            and (
                customer_replied
                or self.customer_replied
            )
        ):
            return False

        if (
            self.stop_if_customer_buys
            and customer_bought
        ):
            return False

        if (
            self.stop_if_customer_requests_human
            and human_requested
        ):
            return False

        if (
            self.stop_if_conversation_closed
            and conversation_closed
        ):
            return False

        if (
            self.stop_if_contact_blocked
            and contact_blocked
        ):
            return False

        if (
            self.minimum_score is not None
            and prospect_score is not None
            and prospect_score < self.minimum_score
        ):
            return False

        if (
            self.minimum_prospect_score is not None
            and prospect_score is not None
            and prospect_score
            < self.minimum_prospect_score
        ):
            return False

        if (
            self.minimum_purchase_intent is not None
            and purchase_intent is not None
            and purchase_intent
            < self.minimum_purchase_intent
        ):
            return False

        if intent is not None:
            if not self.matches_intent(intent):
                return False

        if signals is not None:
            if not self.matches_signals(signals):
                return False

        return True

    # ==================================================================
    # INTENTIONS
    # ==================================================================

    def matches_intent(
        self,
        intent: str,
    ) -> bool:
        normalized = intent.strip().lower()

        excluded = {
            item.strip().lower()
            for item in self.excluded_intents
        }

        if normalized in excluded:
            return False

        if not self.required_intents:
            return True

        required = {
            item.strip().lower()
            for item in self.required_intents
        }

        return normalized in required

    # ==================================================================
    # SIGNAUX
    # ==================================================================

    def matches_signals(
        self,
        signals: list[str],
    ) -> bool:
        if not self.required_signals:
            return True

        normalized_signals = {
            item.strip().lower()
            for item in signals
        }

        required = {
            item.strip().lower()
            for item in self.required_signals
        }

        return required.issubset(
            normalized_signals
        )

    # ==================================================================
    # EXÉCUTION
    # ==================================================================

    def start_processing(self) -> None:
        if not self.active:
            raise ValueError(
                "Ce follow-up est inactif."
            )

        if self.attempts >= self.max_attempts:
            raise ValueError(
                "Nombre maximal de tentatives atteint."
            )

        self.status = "processing"
        self.attempts += 1
        self.last_attempt_at = _utcnow()

        self.touch()

    def mark_sent(
        self,
        result: str | None = None,
        result_data: dict[str, Any] | None = None,
    ) -> None:
        self.status = "sent"
        self.sent_at = _utcnow()
        self.result = result

        if result_data is not None:
            self.result_data = result_data

        self.touch()

    def mark_failed(
        self,
        reason: str,
    ) -> None:
        self.status = "failed"
        self.failed_at = _utcnow()
        self.failure_reason = reason

        if self.attempts >= self.max_attempts:
            self.active = False

        self.touch()

    # ==================================================================
    # ARRÊT
    # ==================================================================

    def cancel(
        self,
        reason: str | None = None,
    ) -> None:
        self.status = "cancelled"
        self.active = False

        if reason:
            self.result = reason

        self.touch()

    def stop(
        self,
        reason: str | None = None,
    ) -> None:
        self.status = "stopped"
        self.active = False

        if reason:
            self.result = reason

        self.touch()

    def skip(
        self,
        reason: str | None = None,
    ) -> None:
        self.status = "skipped"
        self.active = False

        if reason:
            self.result = reason

        self.touch()

    # ==================================================================
    # RÉPONSE DU CLIENT
    # ==================================================================

    def register_customer_reply(
        self,
        message_id: int | None = None,
    ) -> None:
        self.customer_replied = True

        if message_id is not None:
            self.reply_message_id = message_id

        if self.stop_if_customer_replies:
            self.status = "stopped"
            self.active = False

        self.touch()

    # ==================================================================
    # VALIDATION HUMAINE
    # ==================================================================

    def validate_by_human(self) -> None:
        self.human_validated = True
        self.requires_human_validation = False

        self.touch()

    # ==================================================================
    # CONTEXTE IA
    # ==================================================================

    def get_ai_context(self) -> dict[str, Any]:
        return {
            "follow_up": {
                "name": self.name,
                "type": self.follow_up_type,
                "reason": self.trigger_reason,
                "status": self.status,
                "sequence": self.follow_up_sequence,
                "max_sequence": self.max_sequence,
            },
            "message": {
                "template": self.message_template,
                "generated": self.generated_message,
                "language": self.language,
                "tone": self.tone,
                "personalization": (
                    self.personalization_context
                ),
            },
            "commercial": {
                "required_intents": (
                    self.required_intents
                ),
                "excluded_intents": (
                    self.excluded_intents
                ),
                "required_signals": (
                    self.required_signals
                ),
                "minimum_score": (
                    self.minimum_prospect_score
                ),
                "minimum_purchase_intent": (
                    self.minimum_purchase_intent
                ),
            },
            "stopping": {
                "customer_reply": (
                    self.stop_if_customer_replies
                ),
                "customer_bought": (
                    self.stop_if_customer_buys
                ),
                "human_requested": (
                    self.stop_if_customer_requests_human
                ),
                "conversation_closed": (
                    self.stop_if_conversation_closed
                ),
                "contact_blocked": (
                    self.stop_if_contact_blocked
                ),
                "conditions": self.stop_conditions,
            },
            "execution": {
                "automatic": self.automatic,
                "ai_generated": self.ai_generated,
                "human_validation": (
                    self.requires_human_validation
                ),
                "channel": self.channel,
            },
        }

    # ==================================================================
    # TIMESTAMP
    # ==================================================================

    def touch(self) -> None:
        self.updated_at = _utcnow()