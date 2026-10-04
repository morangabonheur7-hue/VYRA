from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Integration:
    id: int | None = None

    company_id: int | None = None

    provider: str = ""
    integration_type: str = ""

    name: str = ""
    description: str | None = None

    status: str = "inactive"

    credentials: dict[str, Any] = field(default_factory=dict)
    configuration: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    webhook_url: str | None = None
    webhook_secret: str | None = None

    external_account_id: str | None = None
    external_business_id: str | None = None
    external_phone_id: str | None = None

    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None

    last_connected_at: datetime | None = None
    last_used_at: datetime | None = None
    last_error_at: datetime | None = None

    error_code: str | None = None
    error_message: str | None = None

    messages_sent: int = 0
    messages_received: int = 0
    failed_operations: int = 0

    active: bool = True

    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @classmethod
    def from_row(cls, row: Any) -> "Integration":
        data = dict(row)

        known = {
            "id",
            "company_id",
            "provider",
            "integration_type",
            "name",
            "description",
            "status",
            "credentials",
            "configuration",
            "metadata",
            "webhook_url",
            "webhook_secret",
            "external_account_id",
            "external_business_id",
            "external_phone_id",
            "access_token",
            "refresh_token",
            "token_expires_at",
            "last_connected_at",
            "last_used_at",
            "last_error_at",
            "error_code",
            "error_message",
            "messages_sent",
            "messages_received",
            "failed_operations",
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
            "provider": self.provider,
            "integration_type": self.integration_type,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "credentials": self.credentials,
            "configuration": self.configuration,
            "metadata": self.metadata,
            "webhook_url": self.webhook_url,
            "webhook_secret": self.webhook_secret,
            "external_account_id": self.external_account_id,
            "external_business_id": self.external_business_id,
            "external_phone_id": self.external_phone_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expires_at": self.token_expires_at,
            "last_connected_at": self.last_connected_at,
            "last_used_at": self.last_used_at,
            "last_error_at": self.last_error_at,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "failed_operations": self.failed_operations,
            "active": self.active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def is_connected(self) -> bool:
        return self.active and self.status == "connected"

    def is_available(self) -> bool:
        return (
            self.active
            and self.status in {"connected", "ready"}
        )

    def connect(self) -> "Integration":
        self.status = "connected"
        self.last_connected_at = _now()
        self.error_code = None
        self.error_message = None
        self.updated_at = _now()
        return self

    def activate(self) -> "Integration":
        self.active = True

        if self.status == "inactive":
            self.status = "ready"

        self.updated_at = _now()
        return self

    def deactivate(
        self,
        reason: str | None = None,
    ) -> "Integration":
        self.active = False
        self.status = "inactive"

        if reason:
            self.metadata["deactivation_reason"] = reason

        self.updated_at = _now()
        return self

    def disconnect(
        self,
        reason: str | None = None,
    ) -> "Integration":
        self.status = "disconnected"

        if reason:
            self.metadata["disconnect_reason"] = reason

        self.updated_at = _now()
        return self

    def mark_error(
        self,
        error_message: str,
        *,
        error_code: str | None = None,
    ) -> "Integration":
        self.status = "error"
        self.error_message = error_message
        self.error_code = error_code
        self.last_error_at = _now()
        self.failed_operations += 1
        self.updated_at = _now()
        return self

    def mark_message_sent(self) -> "Integration":
        self.messages_sent += 1
        self.last_used_at = _now()
        self.updated_at = _now()
        return self

    def mark_message_received(self) -> "Integration":
        self.messages_received += 1
        self.last_used_at = _now()
        self.updated_at = _now()
        return self

    def set_external_identity(
        self,
        *,
        account_id: str | None = None,
        business_id: str | None = None,
        phone_id: str | None = None,
    ) -> "Integration":
        if account_id is not None:
            self.external_account_id = account_id

        if business_id is not None:
            self.external_business_id = business_id

        if phone_id is not None:
            self.external_phone_id = phone_id

        self.updated_at = _now()
        return self

    def set_configuration(
        self,
        key: str,
        value: Any,
    ) -> "Integration":
        self.configuration[key] = value
        self.updated_at = _now()
        return self

    def set_metadata(
        self,
        key: str,
        value: Any,
    ) -> "Integration":
        self.metadata[key] = value
        self.updated_at = _now()
        return self

    def set_credential(
        self,
        key: str,
        value: Any,
    ) -> "Integration":
        self.credentials[key] = value
        self.updated_at = _now()
        return self

    def token_is_expired(
        self,
        now: datetime | None = None,
    ) -> bool:
        if self.token_expires_at is None:
            return False

        current = now or _now()
        return self.token_expires_at <= current

    def ai_context(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "integration_type": self.integration_type,
            "name": self.name,
            "status": self.status,
            "active": self.active,
            "external_account_id": self.external_account_id,
            "external_business_id": self.external_business_id,
            "external_phone_id": self.external_phone_id,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
        }

    def touch(self) -> "Integration":
        self.updated_at = _now()
        return self