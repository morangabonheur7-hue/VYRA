from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from psycopg import Connection

from app.core.errors import VYRAError


class IntegrationService:
    """Gestion des intégrations externes d'une entreprise."""

    def __init__(self, connection: Connection):
        self.connection = connection

    def create(
        self,
        company_id: int,
        provider: str,
        integration_type: str,
        *,
        external_account_id: Optional[str] = None,
        external_phone_number_id: Optional[str] = None,
        access_token: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:

        now = datetime.now(timezone.utc)

        cursor = self.connection.execute(
            """
            INSERT INTO integrations (
                company_id,
                provider,
                integration_type,
                external_account_id,
                external_phone_number_id,
                access_token,
                metadata,
                active,
                created_at,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s::jsonb,
                TRUE,
                %s,
                %s
            )
            RETURNING *
            """,
            (
                company_id,
                provider,
                integration_type,
                external_account_id,
                external_phone_number_id,
                access_token,
                __import__("json").dumps(metadata or {}),
                now,
                now,
            ),
        )

        row = cursor.fetchone()

        if row is None:
            self.connection.rollback()
            raise VYRAError(
                "INTEGRATION_CREATE_FAILED",
                "Impossible de créer l'intégration.",
            )

        columns = [desc.name for desc in cursor.description]
        result = dict(zip(columns, row))

        self.connection.commit()

        return result

    def get(
        self,
        integration_id: int,
    ) -> Optional[dict[str, Any]]:

        cursor = self.connection.execute(
            """
            SELECT *
            FROM integrations
            WHERE id = %s
            LIMIT 1
            """,
            (integration_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        columns = [desc.name for desc in cursor.description]
        return dict(zip(columns, row))

    def get_company_integration(
        self,
        company_id: int,
        provider: str,
        integration_type: str,
    ) -> Optional[dict[str, Any]]:

        cursor = self.connection.execute(
            """
            SELECT *
            FROM integrations
            WHERE company_id = %s
              AND provider = %s
              AND integration_type = %s
              AND active = TRUE
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                company_id,
                provider,
                integration_type,
            ),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        columns = [desc.name for desc in cursor.description]
        return dict(zip(columns, row))

    def get_by_phone_number_id(
        self,
        phone_number_id: str,
    ) -> Optional[dict[str, Any]]:

        cursor = self.connection.execute(
            """
            SELECT *
            FROM integrations
            WHERE provider = 'whatsapp'
              AND integration_type = 'cloud_api'
              AND external_phone_number_id = %s
              AND active = TRUE
            LIMIT 1
            """,
            (phone_number_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        columns = [desc.name for desc in cursor.description]
        return dict(zip(columns, row))

    def activate(
        self,
        integration_id: int,
    ) -> Optional[dict[str, Any]]:

        now = datetime.now(timezone.utc)

        cursor = self.connection.execute(
            """
            UPDATE integrations
            SET
                active = TRUE,
                updated_at = %s
            WHERE id = %s
            RETURNING *
            """,
            (now, integration_id),
        )

        row = cursor.fetchone()

        if row is None:
            self.connection.rollback()
            return None

        columns = [desc.name for desc in cursor.description]
        result = dict(zip(columns, row))

        self.connection.commit()

        return result

    def deactivate(
        self,
        integration_id: int,
    ) -> Optional[dict[str, Any]]:

        now = datetime.now(timezone.utc)

        cursor = self.connection.execute(
            """
            UPDATE integrations
            SET
                active = FALSE,
                updated_at = %s
            WHERE id = %s
            RETURNING *
            """,
            (now, integration_id),
        )

        row = cursor.fetchone()

        if row is None:
            self.connection.rollback()
            return None

        columns = [desc.name for desc in cursor.description]
        result = dict(zip(columns, row))

        self.connection.commit()

        return result

    def record_sent(
        self,
        integration_id: int,
    ) -> None:

        now = datetime.now(timezone.utc)

        self.connection.execute(
            """
            UPDATE integrations
            SET
                messages_sent = COALESCE(messages_sent, 0) + 1,
                last_used_at = %s,
                last_error = NULL,
                last_error_at = NULL,
                updated_at = %s
            WHERE id = %s
            """,
            (
                now,
                now,
                integration_id,
            ),
        )

        self.connection.commit()

    def record_received(
        self,
        integration_id: int,
    ) -> None:

        now = datetime.now(timezone.utc)

        self.connection.execute(
            """
            UPDATE integrations
            SET
                messages_received =
                    COALESCE(messages_received, 0) + 1,
                last_used_at = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (
                now,
                now,
                integration_id,
            ),
        )

        self.connection.commit()

    def record_error(
        self,
        integration_id: int,
        error_message: str,
    ) -> None:

        now = datetime.now(timezone.utc)

        self.connection.execute(
            """
            UPDATE integrations
            SET
                last_error = %s,
                last_error_at = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (
                error_message[:4000],
                now,
                now,
                integration_id,
            ),
        )

        self.connection.commit()