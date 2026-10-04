from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.services.followups import FollowUpService
from app.workers.queue import JobQueue

logger = logging.getLogger("vyra.workers.followups")


class FollowUpWorker:
    """
    Worker responsable des relances automatiques.

    Fonctionnement :

        PostgreSQL
             ↓
        followups dus
             ↓
        worker
             ↓
        AI Action
             ↓
        Job Queue
             ↓
        WhatsApp Cloud API

    L'envoi WhatsApp réel sera branché dans l'étape
    d'intégration WhatsApp Cloud.
    """

    def __init__(
        self,
        poll_interval: int = 10,
        batch_size: int = 20,
    ):
        self.poll_interval = max(1, poll_interval)
        self.batch_size = max(1, batch_size)

        self.queue = JobQueue()
        self.running = False

    # ---------------------------------------------------------------
    # UNE ITÉRATION
    # ---------------------------------------------------------------

    def run_once(self) -> int:
        """
        Recherche les follow-ups arrivés à échéance.

        Retourne le nombre de relances détectées.
        """

        processed = 0

        try:
            with self.queue.connection() as connection:
                service = FollowUpService(connection)

                followups = service.get_due(
                    limit=self.batch_size,
                )

                for followup in followups:
                    try:
                        company_id = followup.company_id
                        followup_id = followup.id

                        if not company_id or not followup_id:
                            continue

                        claimed = service.mark_processing(
                            followup_id=followup_id,
                            company_id=company_id,
                        )

                        if not claimed:
                            continue

                        self._create_action(
                            followup=claimed,
                        )

                        processed += 1

                    except Exception:
                        logger.exception(
                            "Erreur traitement follow-up %s",
                            getattr(followup, "id", None),
                        )

        except Exception:
            logger.exception("Erreur worker follow-ups")

        return processed

    # ---------------------------------------------------------------
    # CRÉER UNE AI ACTION
    # ---------------------------------------------------------------

    def _create_action(self, followup) -> int:
        """
        Transforme une relance en AI Action persistante.

        Cette action sera ensuite exécutée par le worker général.
        """

        query = """
            INSERT INTO ai_actions (
                company_id,
                contact_id,
                conversation_id,
                followup_id,
                action_type,
                channel,
                status,
                priority,
                message_text,
                recipient,
                payload,
                scheduled_at,
                attempts,
                max_attempts,
                idempotency_key,
                created_at,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s,
                'followup',
                %s,
                'pending',
                %s,
                %s,
                %s,
                %s,
                NOW(),
                0,
                3,
                %s,
                NOW(),
                NOW()
            )
            RETURNING id
        """

        metadata = getattr(followup, "metadata", {}) or {}

        recipient = getattr(
            followup,
            "recipient",
            None,
        )

        message = getattr(
            followup,
            "message",
            None,
        )

        idempotency_key = (
            f"followup:{followup.id}"
        )

        with self.queue.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        followup.company_id,
                        followup.contact_id,
                        followup.conversation_id,
                        followup.id,
                        getattr(
                            followup,
                            "channel",
                            "whatsapp",
                        ),
                        "normal",
                        message,
                        recipient,
                        metadata,
                        idempotency_key,
                    ),
                )

                row = cursor.fetchone()

        return int(row["id"])

    # ---------------------------------------------------------------
    # BOUCLE 24/7
    # ---------------------------------------------------------------

    def run_forever(self):
        """
        Boucle principale du worker.

        Le processus reste vivant tant que Render le maintient actif.
        """

        self.running = True

        logger.info(
            "VYRA FollowUpWorker démarré."
        )

        while self.running:

            try:
                count = self.run_once()

                if count:
                    logger.info(
                        "%s follow-up(s) préparé(s).",
                        count,
                    )

            except Exception:
                logger.exception(
                    "Erreur inattendue dans FollowUpWorker."
                )

            time.sleep(self.poll_interval)

    # ---------------------------------------------------------------
    # ARRÊT
    # ---------------------------------------------------------------

    def stop(self):
        self.running = False
        logger.info(
            "Arrêt demandé au FollowUpWorker."
        )


def main():
    logging.basicConfig(
        level=logging.INFO,
    )

    worker = FollowUpWorker(
        poll_interval=10,
        batch_size=20,
    )

    try:
        worker.run_forever()
    except KeyboardInterrupt:
        worker.stop()


if __name__ == "__main__":
    main()