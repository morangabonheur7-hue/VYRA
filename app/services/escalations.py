from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from psycopg import Connection

from app.core.errors import VYRAError
from app.models.escalation import Escalation


class EscalationService:
    """
    Service de gestion des escalades humaines VYRA.

    Lorsqu'une conversation nécessite un humain :
    - VYRA crée une escalade
    - elle peut être assignée
    - une notification peut être enregistrée
    - elle peut être résolue ou annulée
    - les escalades urgentes peuvent être récupérées par le worker
    """

    def __init__(self, connection: Connection):
        self.connection = connection

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(
        self,
        company_id: int,
        contact_id: int,
        conversation_id: Optional[int] = None,
        message_id: Optional[int] = None,
        ai_decision_id: Optional[int] = None,
        ai_action_id: Optional[int] = None,
        escalation_type: str = "human_review",
        reason: Optional[str] = None,
        priority: str = "normal",
        urgency: str = "normal",
        summary: Optional[str] = None,
        customer_message: Optional[str] = None,
        recommended_action: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Escalation:

        if not company_id:
            raise VYRAError("company_id est obligatoire.")

        if not contact_id:
            raise VYRAError("contact_id est obligatoire.")

        query = """
            INSERT INTO escalations (
                company_id,
                contact_id,
                conversation_id,
                message_id,
                ai_decision_id,
                ai_action_id,
                escalation_type,
                reason,
                status,
                priority,
                urgency,
                summary,
                customer_message,
                recommended_action,
                metadata,
                created_at,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, 'pending', %s, %s,
                %s, %s, %s, %s,
                NOW(), NOW()
            )
            RETURNING *
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        company_id,
                        contact_id,
                        conversation_id,
                        message_id,
                        ai_decision_id,
                        ai_action_id,
                        escalation_type,
                        reason,
                        priority,
                        urgency,
                        summary,
                        customer_message,
                        recommended_action,
                        metadata or {},
                    ),
                )
                row = cursor.fetchone()

            self.connection.commit()

            if not row:
                raise VYRAError("Impossible de créer l'escalade.")

            return Escalation.from_row(dict(row))

        except Exception as exc:
            self.connection.rollback()
            if isinstance(exc, VYRAError):
                raise
            raise VYRAError(f"Erreur création escalade: {exc}") from exc

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def get(
        self,
        escalation_id: int,
        company_id: int,
    ) -> Optional[Escalation]:

        query = """
            SELECT *
            FROM escalations
            WHERE id = %s
              AND company_id = %s
            LIMIT 1
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, (escalation_id, company_id))
            row = cursor.fetchone()

        if not row:
            return None

        return Escalation.from_row(dict(row))

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    def list(
        self,
        company_id: int,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        urgency: Optional[str] = None,
        contact_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[Escalation]:

        conditions = ["company_id = %s"]
        params: list[Any] = [company_id]

        if status is not None:
            conditions.append("status = %s")
            params.append(status)

        if priority is not None:
            conditions.append("priority = %s")
            params.append(priority)

        if urgency is not None:
            conditions.append("urgency = %s")
            params.append(urgency)

        if contact_id is not None:
            conditions.append("contact_id = %s")
            params.append(contact_id)

        params.append(limit)

        query = f"""
            SELECT *
            FROM escalations
            WHERE {" AND ".join(conditions)}
            ORDER BY
                CASE priority
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'normal' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END,
                created_at ASC
            LIMIT %s
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [Escalation.from_row(dict(row)) for row in rows]

    # ------------------------------------------------------------------
    # URGENT / PENDING
    # ------------------------------------------------------------------

    def get_pending(
        self,
        company_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[Escalation]:

        conditions = ["status = 'pending'"]
        params: list[Any] = []

        if company_id is not None:
            conditions.append("company_id = %s")
            params.append(company_id)

        params.append(limit)

        query = f"""
            SELECT *
            FROM escalations
            WHERE {" AND ".join(conditions)}
            ORDER BY
                CASE urgency
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'normal' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END,
                created_at ASC
            LIMIT %s
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [Escalation.from_row(dict(row)) for row in rows]

    # ------------------------------------------------------------------
    # ASSIGN
    # ------------------------------------------------------------------

    def assign(
        self,
        escalation_id: int,
        company_id: int,
        assigned_to: str,
        team: Optional[str] = None,
    ) -> Optional[Escalation]:

        query = """
            UPDATE escalations
            SET
                assigned_to = %s,
                team = %s,
                status = 'assigned',
                updated_at = NOW()
            WHERE id = %s
              AND company_id = %s
              AND status NOT IN ('resolved', 'cancelled')
            RETURNING *
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    assigned_to,
                    team,
                    escalation_id,
                    company_id,
                ),
            )
            row = cursor.fetchone()

        self.connection.commit()

        if not row:
            return None

        return Escalation.from_row(dict(row))

    # ------------------------------------------------------------------
    # NOTIFICATION
    # ------------------------------------------------------------------

    def mark_notification_sent(
        self,
        escalation_id: int,
        company_id: int,
        channel: str,
    ) -> Optional[Escalation]:

        query = """
            UPDATE escalations
            SET
                notification_channel = %s,
                notification_sent = TRUE,
                notification_sent_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
              AND company_id = %s
            RETURNING *
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    channel,
                    escalation_id,
                    company_id,
                ),
            )
            row = cursor.fetchone()

        self.connection.commit()

        if not row:
            return None

        return Escalation.from_row(dict(row))

    # ------------------------------------------------------------------
    # RESOLVE
    # ------------------------------------------------------------------

    def resolve(
        self,
        escalation_id: int,
        company_id: int,
        resolved_by: str,
        resolution: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[Escalation]:

        query = """
            UPDATE escalations
            SET
                status = 'resolved',
                resolved_by = %s,
                resolved_at = NOW(),
                resolution = %s,
                notes = %s,
                updated_at = NOW()
            WHERE id = %s
              AND company_id = %s
              AND status != 'cancelled'
            RETURNING *
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    resolved_by,
                    resolution,
                    notes,
                    escalation_id,
                    company_id,
                ),
            )
            row = cursor.fetchone()

        self.connection.commit()

        if not row:
            return None

        return Escalation.from_row(dict(row))

    # ------------------------------------------------------------------
    # CANCEL
    # ------------------------------------------------------------------

    def cancel(
        self,
        escalation_id: int,
        company_id: int,
        reason: Optional[str] = None,
    ) -> Optional[Escalation]:

        query = """
            UPDATE escalations
            SET
                status = 'cancelled',
                resolution = %s,
                resolved_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
              AND company_id = %s
              AND status != 'resolved'
            RETURNING *
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    reason,
                    escalation_id,
                    company_id,
                ),
            )
            row = cursor.fetchone()

        self.connection.commit()

        if not row:
            return None

        return Escalation.from_row(dict(row))

    # ------------------------------------------------------------------
    # REOPEN
    # ------------------------------------------------------------------

    def reopen(
        self,
        escalation_id: int,
        company_id: int,
        reason: Optional[str] = None,
    ) -> Optional[Escalation]:

        query = """
            UPDATE escalations
            SET
                status = 'pending',
                resolution = NULL,
                resolved_by = NULL,
                resolved_at = NULL,
                notes = %s,
                updated_at = NOW()
            WHERE id = %s
              AND company_id = %s
              AND status IN ('resolved', 'cancelled')
            RETURNING *
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    reason,
                    escalation_id,
                    company_id,
                ),
            )
            row = cursor.fetchone()

        self.connection.commit()

        if not row:
            return None

        return Escalation.from_row(dict(row))

    # ------------------------------------------------------------------
    # OVERDUE
    # ------------------------------------------------------------------

    def get_overdue(
        self,
        company_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[Escalation]:

        conditions = [
            "status IN ('pending', 'assigned')",
            "response_deadline IS NOT NULL",
            "response_deadline <= NOW()",
        ]

        params: list[Any] = []

        if company_id is not None:
            conditions.append("company_id = %s")
            params.append(company_id)

        params.append(limit)

        query = f"""
            SELECT *
            FROM escalations
            WHERE {" AND ".join(conditions)}
            ORDER BY response_deadline ASC
            LIMIT %s
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [Escalation.from_row(dict(row)) for row in rows]

    # ------------------------------------------------------------------
    # DEADLINE
    # ------------------------------------------------------------------

    def set_deadline(
        self,
        escalation_id: int,
        company_id: int,
        deadline: datetime,
    ) -> Optional[Escalation]:

        query = """
            UPDATE escalations
            SET
                response_deadline = %s,
                updated_at = NOW()
            WHERE id = %s
              AND company_id = %s
            RETURNING *
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    deadline,
                    escalation_id,
                    company_id,
                ),
            )
            row = cursor.fetchone()

        self.connection.commit()

        if not row:
            return None

        return Escalation.from_row(dict(row))