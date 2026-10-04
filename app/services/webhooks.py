from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from psycopg import Connection

from app.core.errors import VYRAError


class WebhookService:
    """
    Service de gestion des événements webhook.

    Responsabilités :
    - enregistrer les événements entrants ;
    - empêcher les doublons ;
    - retrouver un événement ;
    - marquer un événement comme traité ;
    - marquer un événement en erreur ;
    - permettre la reprise après un redémarrage.
    """

    def __init__(self, connection: Connection):
        self.connection = connection

    # ------------------------------------------------------------------
    # ID EMPREINTE
    # ------------------------------------------------------------------

    @staticmethod
    def build_event_id(
        provider: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> str:
        """
        Construit un identifiant déterministe à partir du webhook.

        Si Meta renvoie exactement le même événement plusieurs fois,
        la même empreinte sera produite.
        """

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

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

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
        Enregistre un événement webhook.

        Retourne :
        {
            "event": {...},
            "created": True/False,
            "duplicate": True/False
        }
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

        query = """
            INSERT INTO webhook_events (
                event_id,
                provider,
                event_type,
                company_id,
                integration_id,
                payload,
                status,
                attempts,
                received_at,
                updated_at
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s::jsonb,
                'pending',
                0,
                %s,
                %s
            )
            ON CONFLICT (event_id)
            DO NOTHING
            RETURNING *
        """

        now = datetime.now(timezone.utc)

        cursor = self.connection.execute(
            query,
            (
                event_id,
                provider,
                event_type,
                company_id,
                integration_id,
                payload_json,
                now,
                now,
            ),
        )

        row = cursor.fetchone()

        if row is not None:
            columns = [desc.name for desc in cursor.description]
            event = dict(zip(columns, row))

            self.connection.commit()

            return {
                "event": event,
                "created": True,
                "duplicate": False,
            }

        self.connection.rollback()

        existing = self.get_by_event_id(event_id)

        if existing is None:
            raise VYRAError(
                "WEBHOOK_CREATE_FAILED",
                "Impossible d'enregistrer l'événement webhook.",
            )

        return {
            "event": existing,
            "created": False,
            "duplicate": True,
        }

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def get_by_event_id(
        self,
        event_id: str,
    ) -> Optional[dict[str, Any]]:
        cursor = self.connection.execute(
            """
            SELECT *
            FROM webhook_events
            WHERE event_id = %s
            LIMIT 1
            """,
            (event_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        columns = [desc.name for desc in cursor.description]

        return dict(zip(columns, row))

    # ------------------------------------------------------------------
    # CLAIM
    # ------------------------------------------------------------------

    def claim(
        self,
        event_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Réserve un événement pour traitement.

        Grâce à FOR UPDATE SKIP LOCKED, deux workers ne devraient
        pas traiter simultanément le même événement.
        """

        now = datetime.now(timezone.utc)

        cursor = self.connection.execute(
            """
            SELECT *
            FROM webhook_events
            WHERE event_id = %s
              AND status = 'pending'
            FOR UPDATE SKIP LOCKED
            """,
            (event_id,),
        )

        row = cursor.fetchone()

        if row is None:
            self.connection.commit()
            return None

        columns = [desc.name for desc in cursor.description]
        event = dict(zip(columns, row))

        update_cursor = self.connection.execute(
            """
            UPDATE webhook_events
            SET
                status = 'processing',
                attempts = COALESCE(attempts, 0) + 1,
                processed_at = NULL,
                updated_at = %s
            WHERE event_id = %s
            RETURNING *
            """,
            (now, event_id),
        )

        updated_row = update_cursor.fetchone()

        if updated_row is None:
            self.connection.rollback()
            return None

        updated_columns = [
            desc.name for desc in update_cursor.description
        ]

        updated_event = dict(
            zip(updated_columns, updated_row)
        )

        self.connection.commit()

        return updated_event

    # ------------------------------------------------------------------
    # COMPLETE
    # ------------------------------------------------------------------

    def mark_processed(
        self,
        event_id: str,
    ) -> Optional[dict[str, Any]]:
        now = datetime.now(timezone.utc)

        cursor = self.connection.execute(
            """
            UPDATE webhook_events
            SET
                status = 'processed',
                processed_at = %s,
                updated_at = %s,
                error_message = NULL
            WHERE event_id = %s
            RETURNING *
            """,
            (
                now,
                now,
                event_id,
            ),
        )

        row = cursor.fetchone()

        if row is None:
            self.connection.rollback()
            return None

        columns = [desc.name for desc in cursor.description]
        event = dict(zip(columns, row))

        self.connection.commit()

        return event

    # ------------------------------------------------------------------
    # ERROR
    # ------------------------------------------------------------------

    def mark_failed(
        self,
        event_id: str,
        error_message: str,
    ) -> Optional[dict[str, Any]]:
        now = datetime.now(timezone.utc)

        cursor = self.connection.execute(
            """
            UPDATE webhook_events
            SET
                status = 'failed',
                error_message = %s,
                updated_at = %s
            WHERE event_id = %s
            RETURNING *
            """,
            (
                error_message[:4000],
                now,
                event_id,
            ),
        )

        row = cursor.fetchone()

        if row is None:
            self.connection.rollback()
            return None

        columns = [desc.name for desc in cursor.description]
        event = dict(zip(columns, row))

        self.connection.commit()

        return event

    # ------------------------------------------------------------------
    # RETRY
    # ------------------------------------------------------------------

    def retry(
        self,
        event_id: str,
    ) -> Optional[dict[str, Any]]:
        now = datetime.now(timezone.utc)

        cursor = self.connection.execute(
            """
            UPDATE webhook_events
            SET
                status = 'pending',
                error_message = NULL,
                updated_at = %s
            WHERE event_id = %s
              AND status IN ('failed', 'processing')
            RETURNING *
            """,
            (
                now,
                event_id,
            ),
        )

        row = cursor.fetchone()

        if row is None:
            self.connection.rollback()
            return None

        columns = [desc.name for desc in cursor.description]
        event = dict(zip(columns, row))

        self.connection.commit()

        return event

    # ------------------------------------------------------------------
    # PENDING EVENTS
    # ------------------------------------------------------------------

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
            ORDER BY received_at ASC
            LIMIT %s
            """,
            (limit,),
        )

        rows = cursor.fetchall()

        columns = [desc.name for desc in cursor.description]

        return [
            dict(zip(columns, row))
            for row in rows
        ]

    # ------------------------------------------------------------------
    # FAILED EVENTS
    # ------------------------------------------------------------------

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

        columns = [desc.name for desc in cursor.description]

        return [
            dict(zip(columns, row))
            for row in rows
        ]