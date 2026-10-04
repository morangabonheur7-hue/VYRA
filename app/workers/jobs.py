from __future__ import annotations

import logging
import time
from typing import Any

from psycopg import Connection

from app.workers.queue import ActionQueue
from app.workers.whatsapp import WhatsAppWorker


logger = logging.getLogger("vyra.worker")


class JobWorker:
    """
    Worker principal VYRA.

    Il récupère les actions persistées dans PostgreSQL
    et les exécute.
    """

    def __init__(
        self,
        connection: Connection,
        *,
        poll_interval: float = 2.0,
    ):
        self.connection = connection
        self.queue = ActionQueue(connection)
        self.whatsapp = WhatsAppWorker(connection)
        self.poll_interval = poll_interval

        self.running = True

    def stop(self) -> None:
        self.running = False

    def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        action_type = action.get("action_type")

        if action_type == "whatsapp_message":
            return self.whatsapp.execute_action(action)

        if action_type == "followup":
            return self.whatsapp.execute_action(action)

        if action_type == "notification":
            return self._notification(action)

        if action_type == "escalation":
            return self._escalation(action)

        if action_type == "ai_response":
            return self._ai_response(action)

        raise ValueError(
            f"Unknown action type: {action_type}"
        )

    def _notification(
        self,
        action: dict[str, Any],
    ) -> dict[str, Any]:

        logger.info(
            "Notification action received: %s",
            action.get("id"),
        )

        return {
            "success": True,
            "action": "notification",
        }

    def _escalation(
        self,
        action: dict[str, Any],
    ) -> dict[str, Any]:

        logger.info(
            "Escalation action received: %s",
            action.get("id"),
        )

        return {
            "success": True,
            "action": "escalation",
        }

    def _ai_response(
        self,
        action: dict[str, Any],
    ) -> dict[str, Any]:

        logger.info(
            "AI response action received: %s",
            action.get("id"),
        )

        return {
            "success": True,
            "action": "ai_response",
        }

    def process_once(self) -> bool:
        action = self.queue.claim()

        if action is None:
            return False

        action_id = action.get("id")

        try:
            result = self.execute(action)

            self.queue.complete(
                action_id=action_id,
                result=result,
            )

            logger.info(
                "Action %s completed successfully.",
                action_id,
            )

            return True

        except Exception as exc:
            logger.exception(
                "Action %s failed.",
                action_id,
            )

            self.queue.fail(
                action_id=action_id,
                error=str(exc),
            )

            return False

    def run_forever(self) -> None:
        logger.info("VYRA worker started.")

        while self.running:
            try:
                processed = self.process_once()

                if not processed:
                    time.sleep(self.poll_interval)

            except Exception:
                logger.exception(
                    "Unexpected worker error."
                )

                time.sleep(self.poll_interval)

        logger.info("VYRA worker stopped.")
