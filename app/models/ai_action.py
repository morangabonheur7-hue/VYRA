from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AIAction:
    id: int | None = None

    company_id: int | None = None
    contact_id: int | None = None
    conversation_id: int | None = None
    message_id: int | None = None
    ai_decision_id: int | None = None
    followup_id: int | None = None
    escalation_id: int | None = None

    action_type: str = "respond"
    channel: str = "whatsapp"

    status: str = "pending"
    priority: int = 0

    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    message_text: str | None = None
    recipient: str | None = None

    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    attempts: int = 0
    max_attempts: int = 3

    error_code: str | None = None
    error_message: str | None = None
    last_error_at: datetime | None = None

    provider: str | None = None
    provider_message_id: str | None = None

    requires_human: bool = False
    human_approved: bool = False
    human_approved_by: int | None = None
    human_approved_at: datetime | None = None

    idempotency_key: str | None = None

    result: dict[str, Any] = field(default_factory=dict)

    active: bool = True
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @classmethod
    def from_row(cls, row: Any) -> "AIAction":
        data = dict(row)

        known = {
            "id",
            "company_id",
            "contact_id",
            "conversation_id",
            "message_id",
            "ai_decision_id",
            "followup_id",
            "escalation_id",
            "action_type",
            "channel",
            "status",
            "priority",
            "payload",
            "metadata",
            "message_text",
            "recipient",
            "scheduled_at",
            "started_at",
            "completed_at",
            "attempts",
            "max_attempts",
            "error_code",
            "error_message",
            "last_error_at",
            "provider",
            "provider_message_id",
            "requires_human",
            "human_approved",
            "human_approved_by",
            "human_approved_at",
            "idempotency_key",
            "result",
            "active",
            "created_at",
            "updated_at",
        }

        values = {
            key: data[key]
            for key in known
            if key in data
        }

        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contact_id": self.contact_id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "ai_decision_id": self.ai_decision_id,
            "followup_id": self.followup_id,
            "escalation_id": self.escalation_id,
            "action_type": self.action_type,
            "channel": self.channel,
            "status": self.status,
            "priority": self.priority,
            "payload": self.payload,
            "metadata": self.metadata,
            "message_text": self.message_text,
            "recipient": self.recipient,
            "scheduled_at": self.scheduled_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "last_error_at": self.last_error_at,
            "provider": self.provider,
            "provider_message_id": self.provider_message_id,
            "requires_human": self.requires_human,
            "human_approved": self.human_approved,
            "human_approved_by": self.human_approved_by,
            "human_approved_at": self.human_approved_at,
            "idempotency_key": self.idempotency_key,
            "result": self.result,
            "active": self.active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def is_pending(self) -> bool:
        return self.status == "pending" and self.active

    def is_terminal(self) -> bool:
        return self.status in {
            "completed",
            "failed",
            "cancelled",
            "blocked",
        }

    def can_execute(self) -> bool:
        if not self.active:
            return False

        if self.status != "pending":
            return False

        if self.requires_human and not self.human_approved:
            return False

        if self.attempts >= self.max_attempts:
            return False

        return True

    def mark_processing(self) -> "AIAction":
        self.status = "processing"
        self.started_at = _now()
        self.updated_at = _now()
        return self

    def mark_completed(
        self,
        *,
        result: dict[str, Any] | None = None,
        provider_message_id: str | None = None,
    ) -> "AIAction":
        self.status = "completed"
        self.completed_at = _now()

        if result is not None:
            self.result = result

        if provider_message_id is not None:
            self.provider_message_id = provider_message_id

        self.updated_at = _now()
        return self

    def mark_failed(
        self,
        error_message: str,
        *,
        error_code: str | None = None,
        retryable: bool = True,
    ) -> "AIAction":
        self.attempts += 1
        self.error_message = error_message
        self.error_code = error_code
        self.last_error_at = _now()

        if retryable and self.attempts < self.max_attempts:
            self.status = "pending"
        else:
            self.status = "failed"

        self.updated_at = _now()
        return self

    def cancel(self, reason: str | None = None) -> "AIAction":
        self.status = "cancelled"

        if reason:
            self.metadata["cancel_reason"] = reason

        self.updated_at = _now()
        return self

    def block(self, reason: str | None = None) -> "AIAction":
        self.status = "blocked"

        if reason:
            self.metadata["block_reason"] = reason

        self.updated_at = _now()
        return self

    def require_human(
        self,
        reason: str | None = None,
    ) -> "AIAction":
        self.requires_human = True
        self.human_approved = False

        if reason:
            self.metadata["human_validation_reason"] = reason

        self.updated_at = _now()
        return self

    def approve(
        self,
        user_id: int,
    ) -> "AIAction":
        self.human_approved = True
        self.human_approved_by = user_id
        self.human_approved_at = _now()
        self.updated_at = _now()
        return self

    def reject(
        self,
        reason: str | None = None,
    ) -> "AIAction":
        self.human_approved = False
        self.status = "blocked"

        if reason:
            self.metadata["rejection_reason"] = reason

        self.updated_at = _now()
        return self

    def is_due(
        self,
        now: datetime | None = None,
    ) -> bool:
        if not self.can_execute():
            return False

        if self.scheduled_at is None:
            return True

        current = now or _now()
        return self.scheduled_at <= current

    def set_payload(
        self,
        key: str,
        value: Any,
    ) -> "AIAction":
        self.payload[key] = value
        self.updated_at = _now()
        return self

    def set_metadata(
        self,
        key: str,
        value: Any,
    ) -> "AIAction":
        self.metadata[key] = value
        self.updated_at = _now()
        return self

    def set_result(
        self,
        key: str,
        value: Any,
    ) -> "AIAction":
        self.result[key] = value
        self.updated_at = _now()
        return self

    def schedule(
        self,
        scheduled_at: datetime,
    ) -> "AIAction":
        self.scheduled_at = scheduled_at
        self.status = "pending"
        self.updated_at = _now()
        return self

    def set_idempotency_key(
        self,
        key: str,
    ) -> "AIAction":
        self.idempotency_key = key
        self.updated_at = _now()
        return self

    def is_same_action(
        self,
        *,
        action_type: str,
        recipient: str | None = None,
        idempotency_key: str | None = None,
    ) -> bool:
        if self.action_type != action_type:
            return False

        if recipient is not None and self.recipient != recipient:
            return False

        if idempotency_key is not None:
            return self.idempotency_key == idempotency_key

        return True

    def ai_context(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "channel": self.channel,
            "status": self.status,
            "priority": self.priority,
            "message_text": self.message_text,
            "recipient": self.recipient,
            "scheduled_at": self.scheduled_at,
            "requires_human": self.requires_human,
            "human_approved": self.human_approved,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "provider": self.provider,
            "metadata": self.metadata,
        }

    def touch(self) -> "AIAction":
        self.updated_at = _now()
        return self