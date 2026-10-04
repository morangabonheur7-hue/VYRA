from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import psycopg

from app.core.config import settings


@dataclass
class QueueItem:
    """
    Représente une action persistante à traiter par un worker.
    """

    id: int
    company_id: Optional[int]
    action_type: str
    channel: Optional[str]
    status: str
    payload: dict[str, Any]
    scheduled_at: Optional[datetime]
    attempts: int
    max_attempts: int
    idempotency_key: Optional[str]
    recipient: Optional[str]
    message_text: Optional[str]

    @classmethod
    def from_row(cls, row: Any) -> "QueueItem":
        data = dict(row)

        return cls(
            id=data["id"],
            company_id=data.get("company_id"),
            action_type=data.get("action_type", ""),
            channel=data.get("channel"),
            status=data.get("status", "pending"),
            payload=data.get("payload") or {},
            scheduled_at=data.get("scheduled_at"),
            attempts=data.get("attempts") or 0,
            max_attempts=data.get("max_attempts") or 3,
            idempotency_key=data.get("idempotency_key"),
            recipient=data.get("recipient"),
            message_text=data.get("message_text"),
        )


class JobQueue:
    """
    File d'attente persistante basée sur PostgreSQL.

    Le worker peut redémarrer sans perdre les actions :
    les jobs sont stockés dans ai_actions.

    FOR UPDATE SKIP LOCKED permet à plusieurs workers
    de travailler en parallèle sans prendre le même job.
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.database_url

    def connection(self):
        return psycopg.connect(
            self.database_url,
            row_factory=psycopg.rows.dict_row,
        )

    # ---------------------------------------------------------------
    # RÉCUPÉRER ET RÉSERVER UN JOB
    # ---------------------------------------------------------------

    def claim(
        self,
        worker_id: str,
        limit: int = 10,
    ) -> list[QueueItem]:

        query = """
            WITH candidates AS (
                SELECT id
                FROM ai_actions
                WHERE status = 'pending'
                  AND (
                      scheduled_at IS NULL
                      OR scheduled_at <= NOW()
                  )
                  AND (
                      attempts < max_attempts
                      OR max_attempts IS NULL
                  )
                ORDER BY
                    priority DESC,
                    COALESCE(scheduled_at, created_at) ASC,
                    id ASC
                FOR UPDATE SKIP LOCKED
                LIMIT %s
            )
            UPDATE ai_actions
            SET
                status = 'processing',
                started_at = NOW(),
                attempts = COALESCE(attempts, 0) + 1,
                metadata = COALESCE(metadata, '{}'::jsonb)
                    || jsonb_build_object(
                        'worker_id', %s
                    ),
                updated_at = NOW()
            WHERE id IN (SELECT id FROM candidates)
            RETURNING *
        """

        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (limit, worker_id))
                rows = cursor.fetchall()

        return [QueueItem.from_row(row) for row in rows]

    # ---------------------------------------------------------------
    # TERMINER
    # ---------------------------------------------------------------

    def complete(
        self,
        action_id: int,
        result: Optional[dict[str, Any]] = None,
    ) -> bool:

        query = """
            UPDATE ai_actions
            SET
                status = 'completed',
                completed_at = NOW(),
                result = %s,
                updated_at = NOW()
            WHERE id = %s
              AND status = 'processing'
        """

        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        result or {},
                        action_id,
                    ),
                )
                return cursor.rowcount == 1

    # ---------------------------------------------------------------
    # ÉCHEC
    # ---------------------------------------------------------------

    def fail(
        self,
        action_id: int,
        error: str,
        retry: bool = True,
    ) -> bool:

        if retry:
            status = "pending"
        else:
            status = "failed"

        query = """
            UPDATE ai_actions
            SET
                status = %s,
                error_message = %s,
                updated_at = NOW()
            WHERE id = %s
              AND status = 'processing'
        """

        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        status,
                        error[:4000],
                        action_id,
                    ),
                )
                return cursor.rowcount == 1

    # ---------------------------------------------------------------
    # ANNULER
    # ---------------------------------------------------------------

    def cancel(self, action_id: int) -> bool:

        query = """
            UPDATE ai_actions
            SET
                status = 'cancelled',
                updated_at = NOW()
            WHERE id = %s
              AND status IN ('pending', 'processing')
        """

        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (action_id,))
                return cursor.rowcount == 1

    # ---------------------------------------------------------------
    # COMPTER
    # ---------------------------------------------------------------

    def count_pending(self) -> int:

        query = """
            SELECT COUNT(*)
            FROM ai_actions
            WHERE status = 'pending'
              AND (
                  scheduled_at IS NULL
                  OR scheduled_at <= NOW()
              )
        """

        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()

        return int(row["count"])