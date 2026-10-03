from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Escalation:
    id: int | None = None

    company_id: int | None = None
    contact_id: int | None = None
    conversation_id: int | None = None
    message_id: int | None = None
    ai_decision_id: int | None = None
    ai_action_id: int | None = None

    escalation_type: str = "human"
    reason: str = ""

    status: str = "pending"
    priority: int = 0
    urgency: str = "normal"

    summary: str | None = None
    customer_message: str | None = None

    detected_intent: str | None = None
    prospect_temperature: str | None = None
    prospect_score: float | None = None

    qualification_status: str | None = None
    sales_stage: str | None = None

    recommended_action: str | None = None
    recommended_response: str | None = None

    assigned_to: int | None = None
    assigned_team: str | None = None

    notification_channel: str | None = None
    notification_sent: bool = False
    notification_sent_at: datetime | None = None

    response_required: bool = True
    deadline_at: datetime | None = None

    resolved_by: int | None = None
    resolved_at: datetime | None = None
    resolution: str | None = None
    resolution_notes: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    active: bool = True
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @classmethod
    def from_row(cls, row: Any) -> "Escalation":
        data = dict(row)

        known = {
            "id",
            "company_id",
            "contact_id",
            "conversation_id",
            "message_id",
            "ai_decision_id",
            "ai_action_id",
            "escalation_type",
            "reason",
            "status",
            "priority",
            "urgency",
            "summary",
            "customer_message",
            "detected_intent",
            "prospect_temperature",
            "prospect_score",
            "qualification_status",
            "sales_stage",
            "recommended_action",
            "recommended_response",
            "assigned_to",
            "assigned_team",
            "notification_channel",
            "notification_sent",
            "notification_sent_at",
            "response_required",
            "deadline_at",
            "resolved_by",
            "resolved_at",
            "resolution",
            "resolution_notes",
            "metadata",
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
            "ai_action_id": self.ai_action_id,
            "escalation_type": self.escalation_type,
            "reason": self.reason,
            "status": self.status,
            "priority": self.priority,
            "urgency": self.urgency,
            "summary": self.summary,
            "customer_message": self.customer_message,
            "detected_intent": self.detected_intent,
            "prospect_temperature": self.prospect_temperature,
            "prospect_score": self.prospect_score,
            "qualification_status": self.qualification_status,
            "sales_stage": self.sales_stage,
            "recommended_action": self.recommended_action,
            "recommended_response": self.recommended_response,
            "assigned_to": self.assigned_to,
            "assigned_team": self.assigned_team,
            "notification_channel": self.notification_channel,
            "notification_sent": self.notification_sent,
            "notification_sent_at": self.notification_sent_at,
            "response_required": self.response_required,
            "deadline_at": self.deadline_at,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
            "resolution": self.resolution,
            "resolution_notes": self.resolution_notes,
            "metadata": self.metadata,
            "active": self.active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def is_pending(self) -> bool:
        return self.active and self.status == "pending"

    def requires_immediate_attention(self) -> bool:
        return (
            self.status == "pending"
            and self.active
            and self.urgency in {"high", "critical"}
        )

    def assign(
        self,
        user_id: int | None = None,
        team: str | None = None,
    ) -> "Escalation":
        self.assigned_to = user_id
        self.assigned_team = team
        self.status = "assigned"
        self.updated_at = _now()
        return self

    def mark_notification_sent(self) -> "Escalation":
        self.notification_sent = True
        self.notification_sent_at = _now()
        self.updated_at = _now()
        return self

    def resolve(
        self,
        *,
        user_id: int | None = None,
        resolution: str | None = None,
        notes: str | None = None,
    ) -> "Escalation":
        self.status = "resolved"
        self.resolved_by = user_id
        self.resolved_at = _now()
        self.resolution = resolution
        self.resolution_notes = notes
        self.updated_at = _now()
        return self

    def cancel(
        self,
        reason: str | None = None,
    ) -> "Escalation":
        self.status = "cancelled"
        self.active = False

        if reason:
            self.metadata["cancel_reason"] = reason

        self.updated_at = _now()
        return self

    def reopen(self) -> "Escalation":
        self.status = "pending"
        self.active = True
        self.resolved_at = None
        self.resolved_by = None
        self.updated_at = _now()
        return self

    def set_priority(
        self,
        priority: int,
        urgency: str | None = None,
    ) -> "Escalation":
        self.priority = priority

        if urgency is not None:
            self.urgency = urgency

        self.updated_at = _now()
        return self

    def set_recommendation(
        self,
        action: str,
        response: str | None = None,
    ) -> "Escalation":
        self.recommended_action = action
        self.recommended_response = response
        self.updated_at = _now()
        return self

    def is_overdue(
        self,
        now: datetime | None = None,
    ) -> bool:
        if not self.deadline_at:
            return False

        if self.status in {"resolved", "cancelled"}:
            return False

        current = now or _now()
        return current > self.deadline_at

    def set_metadata(
        self,
        key: str,
        value: Any,
    ) -> "Escalation":
        self.metadata[key] = value
        self.updated_at = _now()
        return self

    def ai_context(self) -> dict[str, Any]:
        return {
            "escalation_type": self.escalation_type,
            "reason": self.reason,
            "status": self.status,
            "priority": self.priority,
            "urgency": self.urgency,
            "summary": self.summary,
            "customer_message": self.customer_message,
            "detected_intent": self.detected_intent,
            "prospect_temperature": self.prospect_temperature,
            "prospect_score": self.prospect_score,
            "qualification_status": self.qualification_status,
            "sales_stage": self.sales_stage,
            "recommended_action": self.recommended_action,
            "response_required": self.response_required,
            "assigned_to": self.assigned_to,
            "assigned_team": self.assigned_team,
        }

    def touch(self) -> "Escalation":
        self.updated_at = _now()
        return self