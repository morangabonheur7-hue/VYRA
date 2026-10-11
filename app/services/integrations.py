from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from psycopg import Connection

from app.core.errors import VYRAError


class IntegrationService:
    """Gestion des intégrations externes d'une entreprise."""

    def __init__(self, connection: Connection):
        self.connection = connection

    @staticmethod
    def _json_dict(value: Any) -> dict[str, Any]:
        """Convertit un champ JSON texte en dictionnaire."""
        if isinstance(value, dict):
            return value

        if not value:
            return {}

        try:
            result = json.loads(value)
        except (TypeError, ValueError):
            return {}

        return result if isinstance(result, dict) else {}

    @classmethod
    def _internal_row(cls, row: Any) -> Optional[dict[str, Any]]:
        """Expose une représentation compatible avec les services internes."""
        if row is None:
            return None

        result = dict(row)
        credentials = cls._json_dict(result.get("credentials"))
        configuration = cls._json_dict(result.get("configuration"))

        result["integration_type"] = result.get("type")
        result["external_account_id"] = configuration.get(
            "external_account_id"
        )
        result["external_phone_number_id"] = configuration.get(
            "external_phone_number_id"
        )
        result["access_token"] = credentials.get("access_token")
        result["metadata"] = configuration.get("metadata", {})
        result["active"] = result.get("is_active", False)

        return result

    @staticmethod
    def _public_row(
        row: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Retire les secrets avant de renvoyer une intégration à l'API."""
        if row is None:
            return None

        return {
            "id": row.get("id"),
            "company_id": row.get("company_id"),
            "provider": row.get("provider"),
            "integration_type": row.get("integration_type"),
            "external_account_id": row.get("external_account_id"),
            "external_phone_number_id": row.get(
                "external_phone_number_id"
            ),
            "metadata": row.get("metadata", {}),
            "active": row.get("active", False),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

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
        now = datetime.now(timezone.utc).isoformat()

        credentials = {
            "access_token": access_token,
        }

        configuration = {
            "external_account_id": external_account_id,
            "external_phone_number_id": external_phone_number_id,
            "metadata": metadata or {},
        }

        try:
            cursor = self.connection.execute(
                """
                INSERT INTO integrations (
                    company_id,
                    provider,
                    type,
                    credentials,
                    configuration,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s)
                RETURNING *
                """,
                (
                    company_id,
                    provider,
                    integration_type,
                    json.dumps(credentials),
                    json.dumps(configuration),
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

            self.connection.commit()
            result = self._internal_row(row)

            return self._public_row(result) or {}

        except Exception:
            self.connection.rollback()
            raise

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

        return self._public_row(
            self._internal_row(cursor.fetchone())
        )

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
              AND type = %s
              AND is_active = TRUE
            ORDER BY id DESC
            LIMIT 1
            """,
            (company_id, provider, integration_type),
        )

        return self._public_row(
            self._internal_row(cursor.fetchone())
        )

    def get_by_phone_number_id(
        self,
        phone_number_id: str,
    ) -> Optional[dict[str, Any]]:
        cursor = self.connection.execute(
            """
            SELECT *
            FROM integrations
            WHERE provider = 'whatsapp'
              AND type = 'cloud_api'
              AND is_active = TRUE
              AND configuration IS NOT NULL
              AND configuration::jsonb ->>
                  'external_phone_number_id' = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (phone_number_id,),
        )

        return self._internal_row(cursor.fetchone())

    def activate(
        self,
        integration_id: int,
    ) -> Optional[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()

        try:
            cursor = self.connection.execute(
                """
                UPDATE integrations
                SET is_active = TRUE, updated_at = %s
                WHERE id = %s
                RETURNING *
                """,
                (now, integration_id),
            )

            row = cursor.fetchone()
            self.connection.commit()

            return self._public_row(self._internal_row(row))

        except Exception:
            self.connection.rollback()
            raise

    def deactivate(
        self,
        integration_id: int,
    ) -> Optional[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()

        try:
            cursor = self.connection.execute(
                """
                UPDATE integrations
                SET is_active = FALSE, updated_at = %s
                WHERE id = %s
                RETURNING *
                """,
                (now, integration_id),
            )

            row = cursor.fetchone()
            self.connection.commit()

            return self._public_row(self._internal_row(row))

        except Exception:
            self.connection.rollback()
            raise

    def record_sent(self, integration_id: int) -> None:
        """Enregistre une activité sans dépendre de colonnes absentes."""
        now = datetime.now(timezone.utc).isoformat()

        self.connection.execute(
            """
            UPDATE integrations
            SET updated_at = %s
            WHERE id = %s
            """,
            (now, integration_id),
        )
        self.connection.commit()

    def record_received(self, integration_id: int) -> None:
        self.record_sent(integration_id)

    def record_error(
        self,
        integration_id: int,
        error_message: str,
    ) -> None:
        """Enregistre une erreur dans la configuration JSON."""
        now = datetime.now(timezone.utc).isoformat()

        try:
            self.connection.execute(
                """
                UPDATE integrations
                SET configuration = jsonb_set(
                    COALESCE(
                        NULLIF(configuration, '')::jsonb,
                        '{}'::jsonb
                    ),
                    '{last_error}',
                    to_jsonb(%s::text),
                    TRUE
                )::text,
                updated_at = %s
                WHERE id = %s
                """,
                (error_message[:4000], now, integration_id),
            )
            self.connection.commit()

        except Exception:
            self.connection.rollback()
            raise
