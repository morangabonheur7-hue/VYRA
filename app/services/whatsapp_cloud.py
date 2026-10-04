from __future__ import annotations

import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from psycopg import Connection

from app.core.errors import VYRAError


@dataclass
class WhatsAppSendResult:
    success: bool
    message_id: Optional[str] = None
    raw_response: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


class WhatsAppCloudService:
    """
    Service officiel WhatsApp Cloud API de VYRA.

    Architecture :

        VYRA Worker
             ↓
        WhatsAppCloudService
             ↓
        Meta Graph API
             ↓
        WhatsApp

    Les informations propres à chaque entreprise sont récupérées
    depuis la table integrations.

    Variables globales :

        WHATSAPP_API_VERSION
        WHATSAPP_APP_SECRET
        WHATSAPP_VERIFY_TOKEN
    """

    DEFAULT_API_VERSION = "v26.0"

    def __init__(self, connection: Connection):
        self.connection = connection

        self.api_version = os.getenv(
            "WHATSAPP_API_VERSION",
            self.DEFAULT_API_VERSION,
        )

        self.app_secret = os.getenv(
            "WHATSAPP_APP_SECRET",
            "",
        )

        self.verify_token = os.getenv(
            "WHATSAPP_VERIFY_TOKEN",
            "",
        )

    # ------------------------------------------------------------------
    # CONFIGURATION
    # ------------------------------------------------------------------

    def _get_integration(
        self,
        company_id: int,
    ) -> dict[str, Any]:

        query = """
            SELECT *
            FROM integrations
            WHERE company_id = %s
              AND provider = 'whatsapp'
              AND integration_type = 'cloud_api'
              AND active = TRUE
            ORDER BY id ASC
            LIMIT 1
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (company_id,),
            )
            row = cursor.fetchone()

        if not row:
            raise VYRAError(
                "Aucune intégration WhatsApp Cloud active "
                "pour cette entreprise."
            )

        return dict(row)

    def _get_integration_by_phone_number_id(
        self,
        phone_number_id: str,
    ) -> Optional[dict[str, Any]]:

        query = """
            SELECT *
            FROM integrations
            WHERE provider = 'whatsapp'
              AND integration_type = 'cloud_api'
              AND external_phone_number_id = %s
              AND active = TRUE
            ORDER BY id ASC
            LIMIT 1
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (phone_number_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return dict(row)

    # ------------------------------------------------------------------
    # URL
    # ------------------------------------------------------------------

    def _messages_url(
        self,
        phone_number_id: str,
    ) -> str:

        return (
            "https://graph.facebook.com/"
            f"{self.api_version}/"
            f"{phone_number_id}/messages"
        )

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _request(
        self,
        url: str,
        access_token: str,
        payload: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:

        body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=30,
            ) as response:

                raw = response.read().decode(
                    "utf-8",
                    errors="replace",
                )

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {
                        "raw": raw,
                    }

                return response.status, data

        except urllib.error.HTTPError as exc:

            raw = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {
                    "error": raw,
                }

            return exc.code, data

        except urllib.error.URLError as exc:
            raise VYRAError(
                f"WhatsApp Cloud API inaccessible: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # SEND TEXT
    # ------------------------------------------------------------------

    def send_text(
        self,
        company_id: int,
        recipient: str,
        text: str,
        reply_to_message_id: Optional[str] = None,
        preview_url: bool = False,
    ) -> WhatsAppSendResult:

        if not recipient:
            raise VYRAError(
                "Le destinataire WhatsApp est obligatoire."
            )

        if not text:
            raise VYRAError(
                "Le message WhatsApp est vide."
            )

        integration = self._get_integration(
            company_id,
        )

        phone_number_id = integration.get(
            "external_phone_number_id"
        )

        access_token = integration.get(
            "access_token"
        )

        if not phone_number_id:
            raise VYRAError(
                "phone_number_id WhatsApp manquant."
            )

        if not access_token:
            raise VYRAError(
                "Access token WhatsApp manquant."
            )

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text,
            },
        }

        if reply_to_message_id:
            payload["context"] = {
                "message_id": reply_to_message_id,
            }

        status_code, response = self._request(
            url=self._messages_url(
                phone_number_id,
            ),
            access_token=access_token,
            payload=payload,
        )

        if status_code < 200 or status_code >= 300:

            self._mark_integration_error(
                integration_id=integration["id"],
                error=json.dumps(
                    response,
                    ensure_ascii=False,
                ),
            )

            return WhatsAppSendResult(
                success=False,
                raw_response=response,
                error=str(
                    response.get(
                        "error",
                        response,
                    )
                ),
                status_code=status_code,
            )

        message_id = self._extract_message_id(
            response,
        )

        self._mark_message_sent(
            integration_id=integration["id"],
        )

        return WhatsAppSendResult(
            success=True,
            message_id=message_id,
            raw_response=response,
            status_code=status_code,
        )

    # ------------------------------------------------------------------
    # RESPONSE ID
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_message_id(
        response: dict[str, Any],
    ) -> Optional[str]:

        messages = response.get(
            "messages"
        )

        if isinstance(messages, list) and messages:
            first = messages[0]

            if isinstance(first, dict):
                return first.get("id")

        return None

    # ------------------------------------------------------------------
    # MARK SENT
    # ------------------------------------------------------------------

    def _mark_message_sent(
        self,
        integration_id: int,
    ) -> None:

        query = """
            UPDATE integrations
            SET
                messages_sent = COALESCE(messages_sent, 0) + 1,
                last_used_at = NOW(),
                last_error = NULL,
                last_error_at = NULL,
                updated_at = NOW()
            WHERE id = %s
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (integration_id,),
                )

            self.connection.commit()

        except Exception:
            self.connection.rollback()
            raise

    # ------------------------------------------------------------------
    # MARK ERROR
    # ------------------------------------------------------------------

    def _mark_integration_error(
        self,
        integration_id: int,
        error: str,
    ) -> None:

        query = """
            UPDATE integrations
            SET
                last_error = %s,
                last_error_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        error[:4000],
                        integration_id,
                    ),
                )

            self.connection.commit()

        except Exception:
            self.connection.rollback()

    # ------------------------------------------------------------------
    # WEBHOOK VERIFY
    # ------------------------------------------------------------------

    def verify_webhook(
        self,
        mode: Optional[str],
        token: Optional[str],
        challenge: Optional[str],
    ) -> Optional[str]:

        configured_token = (
            os.getenv(
                "WHATSAPP_VERIFY_TOKEN",
                "",
            ).strip()
        )

        received_token = (
            token.strip()
            if token is not None
            else ""
        )

        received_mode = (
            mode.strip()
            if mode is not None
            else ""
        )

        if (
            received_mode == "subscribe"
            and received_token
            and configured_token
            and hmac.compare_digest(
                received_token,
                configured_token,
            )
        ):
            return challenge

        return None

    # ------------------------------------------------------------------
    # WEBHOOK SIGNATURE
    # ------------------------------------------------------------------

    def verify_signature(
        self,
        raw_body: bytes,
        signature: Optional[str],
    ) -> bool:

        if not self.app_secret:
            return False

        if not signature:
            return False

        if not signature.startswith(
            "sha256="
        ):
            return False

        received_signature = signature[
            len("sha256="):
        ]

        expected_signature = hmac.new(
            self.app_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(
            received_signature,
            expected_signature,
        )

    # ------------------------------------------------------------------
    # FIND COMPANY FROM PHONE NUMBER
    # ------------------------------------------------------------------

    def resolve_company(
        self,
        phone_number_id: str,
    ) -> Optional[int]:

        integration = (
            self._get_integration_by_phone_number_id(
                phone_number_id,
            )
        )

        if not integration:
            return None

        company_id = integration.get(
            "company_id"
        )

        if company_id is None:
            return None

        return int(company_id)

    # ------------------------------------------------------------------
    # RECORD INCOMING MESSAGE
    # ------------------------------------------------------------------

    def mark_message_received(
        self,
        phone_number_id: str,
    ) -> None:

        integration = (
            self._get_integration_by_phone_number_id(
                phone_number_id,
            )
        )

        if not integration:
            return

        query = """
            UPDATE integrations
            SET
                messages_received =
                    COALESCE(messages_received, 0) + 1,
                last_used_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    query,
                    (integration["id"],),
                )

            self.connection.commit()

        except Exception:
            self.connection.rollback()
            raise
