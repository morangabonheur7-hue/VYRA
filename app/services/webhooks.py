from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from psycopg import Connection

from app.core.errors import VYRAError


class WebhookService:
    """Gestion des événements webhook de VYRA."""

    def __init__(self, connection: Connection):
        self.connection = connection

    @staticmethod
    def build_event_id(
        provider: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> str:
        normalized = json.dumps(
            {
                "provider": provider,
                "event_type": event_type,
                "payload": payload,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _row_to_dict(cursor: Any, row: Any) -> dict[str, Any]:
        columns = [column.name for column in cursor.description]
        return dict(zip(columns, row))

    def create(
        self,
        provider: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        external_event_id: Optional[str] = None,
        company_id: Optional[int] = None,
        integration_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Enregistre un événement dans webhook_events.

        integration_id est conservé pour la compatibilité avec les
        appels existants, mais n'est pas enregistré car la colonne
        correspondante n'existe pas dans cette table.
        """

        event_id = external_event_id or self.build_event_id(
            provider=provider,
            event_type=event_type,
            payload=payload,
        )

        payload_json = json.dumps(
            payload,
            ensure_ascii=False,
        )

        now = datetime.now(timezone.utc).isoformat()

        try:
            cursor = self.connection.execute(
                """
                INSERT INTO webhook_events (
                    company_id,
                    provider,
                    external_event_id,
                    event_type,
                    payload,
                    status,
                    attempts,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, 'pending', 0, %s, %s
                )
                ON CONFLICT (
                    company_id,
                    provider,
                    external_event_id
                )
                DO NOTHING
                RETURNING *
                """,
                (
                    company_id,
                    provider,
                    event_id,
                    event_type,
                    payload_json,
                    now,
                    now,
                ),
            )

            row = cursor.fetchone()

            if row is not None:
                event = self._row_to_dict(cursor, row)
                self.connection.commit()

                return {
                    "event": event,
                    "created": True,
                    "duplicate": False,
                }

            self.connection.commit()

        except Exception:
            self.connection.rollback()
            raise

        existing = self.get_by_event_id(event_id)

        if existing is None:
            raise VYRAError(
                "WEBHOOK_CREATE_FAILED",
                "Impossible de retrouver l'événement webhook enregistré.",
            )

        return {
            "event": existing,
            "created": False,
            "duplicate": True,
        }

    def get_by_event_id(
        self,
        event_id: str,
    ) -> Optional[dict[str, Any]]:
        cursor = self.connection.execute(
            """
            SELECT *
            FROM webhook_events
            WHERE external_event_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (event_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_dict(cursor, row)

    def claim(
        self,
        event_id: str,
    ) -> Optional[dict[str, Any]]:
        """Réserve un événement en attente pour son traitement."""

        now = datetime.now(timezone.utc).isoformat()

        try:
            cursor = self.connection.execute(
                """
                SELECT *
                FROM webhook_events
                WHERE external_event_id = %s
                  AND status = 'pending'
                FOR UPDATE SKIP LOCKED
                """,
                (event_id,),
            )

            row = cursor.fetchone()

            if row is None:
                self.connection.commit()
                return None

            cursor = self.connection.execute(
                """
                UPDATE webhook_events
                SET
                    status = 'processing',
                    attempts = COALESCE(attempts, 0) + 1,
                    processed_at = NULL,
                    updated_at = %s
                WHERE external_event_id = %s
                RETURNING *
                """,
                (now, event_id),
            )

            updated_row = cursor.fetchone()

            if updated_row is None:
                self.connection.rollback()
                return None

            event = self._row_to_dict(cursor, updated_row)
            self.connection.commit()
            return event

        except Exception:
            self.connection.rollback()
            raise

    def mark_processed(
        self,
        event_id: str,
    ) -> Optional[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()

        try:
            cursor = self.connection.execute(
                """
                UPDATE webhook_events
                SET
                    status = 'processed',
                    processed_at = %s,
                    updated_at = %s,
                    error = NULL
                WHERE external_event_id = %s
                RETURNING *
                """,
                (now, now, event_id),
            )

            row = cursor.fetchone()

            if row is None:
                self.connection.rollback()
                return None

            event = self._row_to_dict(cursor, row)
            self.connection.commit()
            return event

        except Exception:
            self.connection.rollback()
            raise

    def mark_failed(
        self,
        event_id: str,
        error_message: str,
    ) -> Optional[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()

        try:
            cursor = self.connection.execute(
                """
                UPDATE webhook_events
                SET
                    status = 'failed',
                    error = %s,
                    updated_at = %s
                WHERE external_event_id = %s
                RETURNING *
                """,
                (error_message[:4000], now, event_id),
            )

            row = cursor.fetchone()

            if row is None:
                self.connection.rollback()
                return None

            event = self._row_to_dict(cursor, row)
            self.connection.commit()
            return event

        except Exception:
            self.connection.rollback()
            raise

    def retry(
        self,
        event_id: str,
    ) -> Optional[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()

        try:
            cursor = self.connection.execute(
                """
                UPDATE webhook_events
                SET
                    status = 'pending',
                    error = NULL,
                    updated_at = %s
                WHERE external_event_id = %s
                  AND status IN ('failed', 'processing')
                RETURNING *
                """,
                (now, event_id),
            )

            row = cursor.fetchone()

            if row is None:
                self.connection.rollback()
                return None

            event = self._row_to_dict(cursor, row)
            self.connection.commit()
            return event

        except Exception:
            self.connection.rollback()
            raise

    def get_pending(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))

        cursor = self.connection.execute(
            """
            SELECT *
            FROM webhook_events
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT %s
            """,
            (limit,),
        )

        rows = cursor.fetchall()

        return [
            self._row_to_dict(cursor, row)
            for row in rows
        ]

    def get_failed(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))

        cursor = self.connection.execute(
            """
            SELECT *
            FROM webhook_events
            WHERE status = 'failed'
            ORDER BY updated_at ASC
            LIMIT %s
            """,
            (limit,),
        )

        rows = cursor.fetchall()

        return [
            self._row_to_dict(cursor, row)
            for row in rows
]
