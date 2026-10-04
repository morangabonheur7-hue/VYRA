from __future__ import annotations

import logging
import signal
import time

from app.core.database import get_connection
from app.services.webhooks import WebhookService
from app.services.webhook_processor import WebhookProcessor


logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger(
    "vyra.production-worker"
)


class ProductionWorker:

    def __init__(self):
        self.running = True

    def stop(self, *_args):
        logger.info(
            "Arrêt du worker VYRA demandé."
        )
        self.running = False

    def run(self):

        signal.signal(
            signal.SIGTERM,
            self.stop,
        )

        signal.signal(
            signal.SIGINT,
            self.stop,
        )

        connection = get_connection()

        try:
            logger.info(
                "VYRA production worker started."
            )

            while self.running:

                service = WebhookService(
                    connection
                )

                events = service.get_pending(
                    limit=20
                )

                if not events:
                    time.sleep(2)
                    continue

                processor = WebhookProcessor(
                    connection
                )

                for event in events:

                    event_id = event.get(
                        "event_id"
                    )

                    if not event_id:
                        continue

                    try:
                        processor.process(
                            event_id
                        )

                    except Exception:
                        logger.exception(
                            "Erreur traitement webhook %s",
                            event_id,
                        )

        finally:
            connection.close()

            logger.info(
                "VYRA production worker stopped."
            )


if __name__ == "__main__":
    ProductionWorker().run()