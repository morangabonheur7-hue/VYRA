from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from psycopg import Connection

from app.core.errors import VYRAError
from app.models.followup import FollowUp


class FollowUpService:
    """
    Service de gestion des relances commerciales VYRA.

    Responsabilités :
    - créer une relance
    - récupérer les relances
    - récupérer les relances dues
    - marquer une relance comme traitée
    - gérer les échecs et nouvelles tentatives
    - annuler une relance
    - arrêter les relances après réponse du prospect
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
        followup_rule_id: Optional[int] = None,
        message: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        channel: str = "whatsapp",
        metadata: Optional[dict[str, Any]] = None,
    ) -> FollowUp:

        if not company_id:
            raise VYRAError("company_id est obligatoire.")

        if not contact_id:
            raise VYRAError("contact_id est obligatoire.")

        scheduled_at = scheduled_at or datetime.now(timezone.utc)

        query = """
            INSERT INTO followups (
                company_id,
                contact_id,
                conversation_id,
                followup_rule_id,
                message,
                channel,
                scheduled_at,
                status,
                metadata,
                created_at,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                'pending', %s, NOW(), NOW()
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
                        followup_rule_id,
                        message,
                        channel,
                        scheduled_at,
                        metadata or {},
                    ),
                )
                row = cursor.fetchone()

            self.connection.commit()

            if not row:
                raise VYRAError("Impossible de créer la relance.")

            return FollowUp.from_row(dict(row))

        except Exception as exc:
            self.connection.rollback()
            if isinstance(exc, VYRAError):
                raise
            raise VYRAError(f"Erreur création follow-up: {exc}") from exc

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def get(
        self,
        followup_id: int,
        company_id: int,
    ) -> Optional[FollowUp]:

        query = """
            SELECT *
            FROM followups
            WHERE id = %s
              AND company_id = %s
            LIMIT 1
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, (followup_id, company_id))
            row = cursor.fetchone()

        if not row:
            return None

        return FollowUp.from_row(dict(row))

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    def list(
        self,
        company_id: int,
        contact_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[FollowUp]:

        conditions = ["company_id = %s"]
        params: list[Any] = [company_id]

        if contact_id is not None:
            conditions.append("contact_id = %s")
            params.append(contact_id)

        if conversation_id is not None:
            conditions.append("conversation_id = %s")
            params.append(conversation_id)

        if status is not None:
            conditions.append("status = %s")
            params.append(status)

        params.append(limit)

        query = f"""
            SELECT *
            FROM followups
            WHERE {" AND ".join(conditions)}
            ORDER BY scheduled_at ASC, id ASC
            LIMIT %s
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [FollowUp.from_row(dict(row)) for row in rows]

    # ------------------------------------------------------------------
    # DUE FOLLOW-UPS
    # ------------------------------------------------------------------

    def get_due(
        self,
        company_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[FollowUp]:

        conditions = [
            "status = 'pending'",
            "scheduled_at <= NOW()",
        ]
        params: list[Any] = []

        if company_id is not None:
            conditions.append("company_id = %s")
            params.append(company_id)

        params.append(limit)

        query = f"""
            SELECT *
            FROM followups
            WHERE {" AND ".join(conditions)}
            ORDER BY scheduled_at ASC, id ASC
            LIMIT %s
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [FollowUp.from_row(dict(row)) for row in rows]

    # ------------------------------------------------------------------
    # PROCESSING
    # ------------------------------------------------------------------

    def mark_processing(
        self,
        followup_id: int,
        company_id: int,
    ) -> Optional[FollowUp]:

        query = """
            UPDATE followups
            SET
                status = 'processing',
                updated_at = NOW()
            WHERE id = %s
              AND company_id = %s
              AND status = 'pending'
            RETURNING *
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, (followup_id, company_id))
            row = cursor.fetchone()

        self.connection.commit()

        if not row:
            return None

        return FollowUp.from_row(dict(row))

    # ------------------------------------------------------------------
    # SENT
    # ------------------------------------------------------------------

    def mark_sent(
        self,
        followup_id: int,
        company_id: int,
        external_message_id: Optional[str] = None,
    ) -> Optional[FollowUp]:

        query = """
            UPDATE followups
            SET
                status = 'sent',
                sent_at = NOW(),
                external_message_id = %s,
                updated_at = NOW()
            WHERE id = %s
              AND company_id = %s
            RETURNING *
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    external_message_id,
                    followup_id,
                    company_id,
                ),
            )
            row = cursor.fetchone()

        self.connection.commit()

        if not row:
            return None

        return FollowUp.from_row(dict(row))

    # ------------------------------------------------------------------
    # FAILED
    # ------------------------------------------------------------------

    def mark_failed(
        self,
        followup_id: int,
        company_id: int,
        error: str,
        retry_at: Optional[datetime] = None,
    ) -> Optional[FollowUp]:

        query = """
            UPDATE followups
            SET
                status = 'failed',
                error_message = %s,
                retry_at = %s,
                attempts = COALESCE(attempts, 0) + 1,
                updated_at = NOW()
            WHERE id = %s
              AND company_id = %s
            RETURNING *
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    error,
                    retry_at,
                    followup_id,
                    company_id,
                ),
            )
            row = cursor.fetchone()

        self.connection.commit()

        if not row:
            return None

        return FollowUp.from_row(dict(row))

    # ------------------------------------------------------------------
    # CANCEL
    # ------------------------------------------------------------------

    def cancel(
        self,
        followup_id: int,
        company_id: int,
        reason: Optional[str] = None,
    ) -> Optional[FollowUp]:

        query = """
            UPDATE followups
            SET
                status = 'cancelled',
                error_message = %s,
                updated_at = NOW()
            WHERE id = %s
              AND company_id = %s
              AND status NOT IN ('sent', 'cancelled')
            RETURNING *
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    reason,
                    followup_id,
                    company_id,
                ),
            )
            row = cursor.fetchone()

        self.connection.commit()

        if not row:
            return None

        return FollowUp.from_row(dict(row))

    # ------------------------------------------------------------------
    # STOP FOLLOW-UPS FOR A CONTACT
    # ------------------------------------------------------------------

    def stop_for_contact(
        self,
        company_id: int,
        contact_id: int,
        reason: str = "Customer replied",
    ) -> int:

        query = """
            UPDATE followups
            SET
                status = 'cancelled',
                error_message = %s,
                updated_at = NOW()
            WHERE company_id = %s
              AND contact_id = %s
              AND status IN ('pending', 'processing')
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    reason,
                    company_id,
                    contact_id,
                ),
            )
            count = cursor.rowcount

        self.connection.commit()

        return count

    # ------------------------------------------------------------------
    # RETRY
    # ------------------------------------------------------------------

    def retry(
        self,
        followup_id: int,
        company_id: int,
        retry_at: Optional[datetime] = None,
    ) -> Optional[FollowUp]:

        retry_at = retry_at or datetime.now(timezone.utc)

        query = """
            UPDATE followups
            SET
                status = 'pending',
                retry_at = %s,
                scheduled_at = %s,
                updated_at = NOW()
            WHERE id = %s
              AND company_id = %s
              AND status = 'failed'
            RETURNING *
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    retry_at,
                    retry_at,
                    followup_id,
                    company_id,
                ),
            )
            row = cursor.fetchone()

        self.connection.commit()

        if not row:
            return None

        return FollowUp.from_row(dict(row))