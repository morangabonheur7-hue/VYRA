from __future__ import annotations

import logging
import os
import signal

from app.core.database import get_connection
from app.workers.jobs import JobWorker


logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger("vyra.worker.runner")


class WorkerRunner:

    def __init__(self):
        self.running = True

    def stop(self, *_args) -> None:
        logger.info("Stopping VYRA worker...")
        self.running = False

    def run(self) -> None:

        signal.signal(
            signal.SIGTERM,
            self.stop,
        )

        signal.signal(
            signal.SIGINT,
            self.stop,
        )

        poll_interval = float(
            os.getenv(
                "VYRA_WORKER_POLL_INTERVAL",
                "2",
            )
        )

        connection = get_connection()

        worker = JobWorker(
            connection,
            poll_interval=poll_interval,
        )

        try:
            worker.run_forever()

        finally:
            connection.close()
            logger.info(
                "VYRA worker connection closed."
            )


if __name__ == "__main__":
    WorkerRunner().run()