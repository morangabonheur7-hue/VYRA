from __future__ import annotations

import logging
import time

from app.core.database import get_connection
from app.services.webhooks import WebhookService
from app.services.webhook_processor import WebhookProcessor


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(
    "vyra.webhook-worker"
)


class WebhookWorker:

    def __init__(
        self,
        poll_interval: float = 2.0,
    ):
        self.poll_interval = poll_interval
        self.running = True

    def stop(self):
        self.running = False

    def run(self):

        connection = get_connection()

        try:
            while self.running:

                events = WebhookService(
                    connection
                ).get_pending(limit=20)

                if not events:
                    time.sleep(
                        self.poll_interval
                    )
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
                            "Webhook processing failed: %s",
                            event_id,
                        )

        finally:
            connection.close()


if __name__ == "__main__":
    WebhookWorker().run()