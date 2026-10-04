from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class WebhookEvent:
    id: int | None = None

    company_id: int | None = None
    integration_id: int | None = None

    provider: str = ""
    event_type: str = ""
    external_event_id: str | None = None

    source: str | None = None
    channel: str | None = None

    status: str = "received"

    payload: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    received_at: datetime = field(default_factory=_now)
    processing_started_at: datetime | None = None
    processed_at: datetime | None = None

    attempts: int = 0
    max_attempts: int = 5

    error_code: str | None = None
    error_message: str | None = None
    last_error_at: datetime | None = None

    retry_at: datetime | None = None

    related_contact_id: int | None = None
    related_conversation_id: int | None = None
    related_message_id: int | None = None
    related_action_id: int | None = None

    duplicate_of: int | None = None
    idempotency_key: str | None = None

    active: bool = True
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @classmethod
    def from_row(cls, row: Any) -> "WebhookEvent":
        data = dict(row)

        known = {
            "id",
            "company_id",
            "integration_id",
            "provider",
            "event_type",
            "external_event_id",
            "source",
            "channel",
            "status",
            "payload",
            "headers",
            "metadata",
            "received_at",
            "processing_started_at",
            "processed_at",
            "attempts",
            "max_attempts",
            "error_code",
            "error_message",
            "last_error_at",
            "retry_at",
            "related_contact_id",
            "related_conversation_id",
            "related_message_id",
            "related_action_id",
            "duplicate_of",
            "idempotency_key",
            "active",
            "created_at",
            "updated_at",
        }

        return cls(
            **{
                key: data[key]
                for key in known
                if key in data
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "integration_id": self.integration_id,
            "provider": self.provider,
            "event_type": self.event_type,
            "external_event_id": self.external_event_id,
            "source": self.source,
            "channel": self.channel,
            "status": self.status,
            "payload": self.payload,
            "headers": self.headers,
            "metadata": self.metadata,
            "received_at": self.received_at,
            "processing_started_at": self.processing_started_at,
            "processed_at": self.processed_at,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "last_error_at": self.last_error_at,
            "retry_at": self.retry_at,
            "related_contact_id": self.related_contact_id,
            "related_conversation_id": self.related_conversation_id,
            "related_message_id": self.related_message_id,
            "related_action_id": self.related_action_id,
            "duplicate_of": self.duplicate_of,
            "idempotency_key": self.idempotency_key,
            "active": self.active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def is_pending(self) -> bool:
        return self.status in {"received", "pending", "retry"}

    def is_processing(self) -> bool:
        return self.status == "processing"

    def is_completed(self) -> bool:
        return self.status == "processed"

    def is_failed(self) -> bool:
        return self.status == "failed"

    def is_duplicate(self) -> bool:
        return self.status == "duplicate"

    def can_retry(self) -> bool:
        return (
            self.active
            and self.attempts < self.max_attempts
            and self.status in {"failed", "retry"}
        )

    def mark_processing(self) -> "WebhookEvent":
        self.status = "processing"
        self.processing_started_at = _now()
        self.attempts += 1
        self.updated_at = _now()
        return self

    def mark_processed(
        self,
        *,
        contact_id: int | None = None,
        conversation_id: int | None = None,
        message_id: int | None = None,
        action_id: int | None = None,
    ) -> "WebhookEvent":
        self.status = "processed"
        self.processed_at = _now()

        if contact_id is not None:
            self.related_contact_id = contact_id

        if conversation_id is not None:
            self.related_conversation_id = conversation_id

        if message_id is not None:
            self.related_message_id = message_id

        if action_id is not None:
            self.related_action_id = action_id

        self.updated_at = _now()
        return self

    def mark_failed(
        self,
        error_message: str,
        *,
        error_code: str | None = None,
        retry: bool = True,
        retry_at: datetime | None = None,
    ) -> "WebhookEvent":
        self.error_message = error_message
        self.error_code = error_code
        self.last_error_at = _now()

        if retry and self.attempts < self.max_attempts:
            self.status = "retry"
            self.retry_at = retry_at
        else:
            self.status = "failed"

        self.updated_at = _now()
        return self

    def mark_duplicate(
        self,
        duplicate_of: int | None = None,
    ) -> "WebhookEvent":
        self.status = "duplicate"
        self.duplicate_of = duplicate_of
        self.updated_at = _now()
        return self

    def schedule_retry(
        self,
        retry_at: datetime,
    ) -> "WebhookEvent":
        self.status = "retry"
        self.retry_at = retry_at
        self.updated_at = _now()
        return self

    def set_relation(
        self,
        *,
        contact_id: int | None = None,
        conversation_id: int | None = None,
        message_id: int | None = None,
        action_id: int | None = None,
    ) -> "WebhookEvent":
        if contact_id is not None:
            self.related_contact_id = contact_id

        if conversation_id is not None:
            self.related_conversation_id = conversation_id

        if message_id is not None:
            self.related_message_id = message_id

        if action_id is not None:
            self.related_action_id = action_id

        self.updated_at = _now()
        return self

    def set_idempotency_key(
        self,
        key: str,
    ) -> "WebhookEvent":
        self.idempotency_key = key
        self.updated_at = _now()
        return self

    def set_metadata(
        self,
        key: str,
        value: Any,
    ) -> "WebhookEvent":
        self.metadata[key] = value
        self.updated_at = _now()
        return self

    def ai_context(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "event_type": self.event_type,
            "source": self.source,
            "channel": self.channel,
            "status": self.status,
            "attempts": self.attempts,
            "metadata": self.metadata,
        }

    def touch(self) -> "WebhookEvent":
        self.updated_at = _now()
        return self