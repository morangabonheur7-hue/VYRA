from __future__ import annotations

import logging
import os
import signal
import time
from typing import Optional

from app.workers.queue import JobQueue, QueueItem

logger = logging.getLogger("vyra.workers.jobs")


class JobWorker:
    """
    Worker général VYRA.

    Il récupère les AI Actions persistantes et décide
    quel handler doit les exécuter.

    Types prévus :

    - followup
    - whatsapp_message
    - ai_response
    - notification
    - escalation
    """

    def __init__(
        self,
        worker_id: Optional[str] = None,
        poll_interval: int = 3,
        batch_size: int = 10,
    ):
        self.worker_id = (
            worker_id
            or os.getenv(
                "VYRA_WORKER_ID",
                f"worker-{os.getpid()}",
            )
        )

        self.poll_interval = max(
            1,
            poll_interval,
        )

        self.batch_size = max(
            1,
            batch_size,
        )

        self.queue = JobQueue()
        self.running = False

    # ---------------------------------------------------------------
    # TRAITER UN JOB
    # ---------------------------------------------------------------

    def process(self, job: QueueItem):

        logger.info(
            "Traitement action=%s type=%s",
            job.id,
            job.action_type,
        )

        try:

            if job.action_type == "followup":
                return self.handle_followup(job)

            if job.action_type == "whatsapp_message":
                return self.handle_whatsapp_message(job)

            if job.action_type == "ai_response":
                return self.handle_ai_response(job)

            if job.action_type == "notification":
                return self.handle_notification(job)

            if job.action_type == "escalation":
                return self.handle_escalation(job)

            raise ValueError(
                f"Type d'action inconnu: {job.action_type}"
            )

        except Exception as exc:

            logger.exception(
                "Action %s échouée.",
                job.id,
            )

            retry = job.attempts < job.max_attempts

            self.queue.fail(
                action_id=job.id,
                error=str(exc),
                retry=retry,
            )

    # ---------------------------------------------------------------
    # FOLLOW-UP
    # ---------------------------------------------------------------

    def handle_followup(
        self,
        job: QueueItem,
    ):

        """
        Prépare l'envoi d'une relance.

        L'appel réel à WhatsApp Cloud sera branché
        dans le service d'intégration.
        """

        logger.info(
            "Follow-up %s prêt pour %s",
            job.id,
            job.recipient,
        )

        # IMPORTANT :
        # Pour l'instant on ne marque PAS l'action comme
        # completed si le message n'a pas réellement été envoyé.
        #
        # Le sender WhatsApp Cloud prendra cette responsabilité.

        return {
            "status": "ready_for_channel",
            "channel": job.channel,
            "recipient": job.recipient,
        }

    # ---------------------------------------------------------------
    # WHATSAPP
    # ---------------------------------------------------------------

    def handle_whatsapp_message(
        self,
        job: QueueItem,
    ):

        raise NotImplementedError(
            "WhatsApp Cloud sender non branché."
        )

    # ---------------------------------------------------------------
    # AI RESPONSE
    # ---------------------------------------------------------------

    def handle_ai_response(
        self,
        job: QueueItem,
    ):

        raise NotImplementedError(
            "AI response worker non branché."
        )

    # ---------------------------------------------------------------
    # NOTIFICATION
    # ---------------------------------------------------------------

    def handle_notification(
        self,
        job: QueueItem,
    ):

        raise NotImplementedError(
            "Notification worker non branché."
        )

    # ---------------------------------------------------------------
    # ESCALATION
    # ---------------------------------------------------------------

    def handle_escalation(
        self,
        job: QueueItem,
    ):

        raise NotImplementedError(
            "Escalation notification non branchée."
        )

    # ---------------------------------------------------------------
    # UNE ITÉRATION
    # ---------------------------------------------------------------

    def run_once(self) -> int:

        jobs = self.queue.claim(
            worker_id=self.worker_id,
            limit=self.batch_size,
        )

        for job in jobs:
            self.process(job)

        return len(jobs)

    # ---------------------------------------------------------------
    # BOUCLE 24/7
    # ---------------------------------------------------------------

    def run_forever(self):

        self.running = True

        logger.info(
            "VYRA JobWorker démarré: %s",
            self.worker_id,
        )

        while self.running:

            try:

                count = self.run_once()

                if count:
                    logger.info(
                        "%s job(s) traité(s).",
                        count,
                    )

            except Exception:
                logger.exception(
                    "Erreur principale JobWorker."
                )

            time.sleep(
                self.poll_interval
            )

    # ---------------------------------------------------------------
    # STOP
    # ---------------------------------------------------------------

    def stop(self):

        self.running = False

        logger.info(
            "Arrêt demandé au JobWorker."
        )


_worker: Optional[JobWorker] = None


def shutdown_handler(
    signum,
    frame,
):
    global _worker

    logger.info(
        "Signal %s reçu.",
        signum,
    )

    if _worker:
        _worker.stop()


def main():

    global _worker

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s "
            "%(message)s"
        ),
    )

    signal.signal(
        signal.SIGTERM,
        shutdown_handler,
    )

    signal.signal(
        signal.SIGINT,
        shutdown_handler,
    )

    _worker = JobWorker()

    try:
        _worker.run_forever()

    finally:
        _worker.stop()


if __name__ == "__main__":
    main()