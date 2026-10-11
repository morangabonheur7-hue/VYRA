
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from psycopg import Connection


@dataclass
class WhatsAppSendResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    response: Optional[dict[str, Any]] = None


class WhatsAppCloudService:
    """Service WhatsApp Cloud API de VYRA."""

    DEFAULT_API_VERSION = "v26.0"

    def __init__(self, connection: Connection):
        self.connection = connection
        self.api_version = os.getenv(
            "WHATSAPP_API_VERSION",
            self.DEFAULT_API_VERSION,
        )
        self.app_secret = os.getenv("WHATSAPP_APP_SECRET", "")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            try:
                result = json.loads(value)
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, TypeError):
                pass

        return {}

    def _fetchone_dict(self, cursor: Any) -> Optional[dict[str, Any]]:
        row = cursor.fetchone()

        if row is None:
            return None

        if isinstance(row, dict):
            return dict(row)

        columns = [item.name for item in cursor.description]
        return dict(zip(columns, row))

    def _internal_row(
        self,
        row: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        if row is None:
            return None

        result = dict(row)
        credentials = self._json_dict(result.get("credentials"))
        configuration = self._json_dict(result.get("configuration"))

        result["credentials"] = credentials
        result["configuration"] = configuration
        result["integration_type"] = result.get("type")
        result["external_account_id"] = (
            configuration.get("external_account_id")
        )
        result["external_phone_number_id"] = (
            configuration.get("external_phone_number_id")
        )
        result["access_token"] = credentials.get("access_token")
        result["metadata"] = configuration.get("metadata", {})
        result["active"] = result.get("is_active", False)

        return result

    def _get_integration(self, company_id: int) -> Optional[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM integrations
                WHERE company_id = %s
                  AND provider = 'whatsapp'
                  AND type = 'cloud_api'
                  AND is_active = TRUE
                ORDER BY id DESC
                LIMIT 1
                """,
                (company_id,),
            )
            row = self._fetchone_dict(cursor)

        return self._internal_row(row)

    def _get_integration_by_phone_number_id(
        self,
        phone_number_id: str,
    ) -> Optional[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM integrations
                WHERE provider = 'whatsapp'
                  AND type = 'cloud_api'
                  AND is_active = TRUE
                  AND configuration::jsonb
                      ->> 'external_phone_number_id' = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(phone_number_id),),
            )
            row = self._fetchone_dict(cursor)

        return self._internal_row(row)

    def resolve_company(self, phone_number_id: str) -> Optional[int]:
        integration = self._get_integration_by_phone_number_id(
            phone_number_id
        )

        if not integration:
            return None

        company_id = integration.get("company_id")
        return int(company_id) if company_id is not None else None

    def verify_webhook(
        self,
        mode: Optional[str],
        token: Optional[str],
        challenge: Optional[str],
    ) -> Optional[str]:
        if (
            mode == "subscribe"
            and token
            and self.verify_token
            and hmac.compare_digest(token, self.verify_token)
        ):
            return challenge

        return None

    def verify_signature(
        self,
        raw_body: bytes,
        signature: Optional[str],
    ) -> bool:
        if not self.app_secret or not signature:
            return False

        expected = "sha256=" + hmac.new(
            self.app_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def _update_integration_configuration(
        self,
        integration_id: int,
        configuration: dict[str, Any],
    ) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE integrations
                SET configuration = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    json.dumps(configuration),
                    self._now(),
                    integration_id,
                ),
            )

        self.connection.commit()

    def _mark_integration_error(
        self,
        integration: dict[str, Any],
        error: str,
    ) -> None:
        integration_id = integration.get("id")
        if integration_id is None:
            return

        configuration = self._json_dict(
            integration.get("configuration")
        )
        configuration["last_error"] = error
        configuration["last_error_at"] = self._now()

        try:
            self._update_integration_configuration(
                int(integration_id),
                configuration,
            )
        except Exception:
            self.connection.rollback()

    def _mark_message_sent(
        self,
        integration: dict[str, Any],
    ) -> None:
        integration_id = integration.get("id")
        if integration_id is None:
            return

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE integrations
                    SET updated_at = %s
                    WHERE id = %s
                    """,
                    (self._now(), int(integration_id)),
                )

            self.connection.commit()
        except Exception:
            self.connection.rollback()

    def mark_message_received(self, phone_number_id: str) -> None:
        integration = self._get_integration_by_phone_number_id(
            phone_number_id
        )

        if not integration:
            return

        integration_id = integration.get("id")
        if integration_id is None:
            return

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE integrations
                    SET updated_at = %s
                    WHERE id = %s
                    """,
                    (self._now(), int(integration_id)),
                )

            self.connection.commit()
        except Exception:
            self.connection.rollback()

    def send_text(
        self,
        company_id: int,
        recipient: str,
        text: str,
        reply_to_message_id: Optional[str] = None,
        preview_url: bool = False,
    ) -> WhatsAppSendResult:
        integration = self._get_integration(company_id)

        if not integration:
            return WhatsAppSendResult(
                success=False,
                error="Aucune intégration WhatsApp Cloud API active.",
            )

        phone_number_id = integration.get(
            "external_phone_number_id"
        )
        access_token = integration.get("access_token")

        if not phone_number_id or not access_token:
            return WhatsAppSendResult(
                success=False,
                error=(
                    "L'identifiant du numéro ou le jeton "
                    "d'accès manque dans la configuration."
                ),
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

        url = (
            f"https://graph.facebook.com/{self.api_version}/"
            f"{phone_number_id}/messages"
        )

        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=25) as response:
                status_code = response.status
                raw_response = response.read().decode("utf-8")
                response_data = json.loads(raw_response)

            messages = response_data.get("messages", [])
            message_id = (
                messages[0].get("id")
                if messages
                else None
            )

            self._mark_message_sent(integration)

            return WhatsAppSendResult(
                success=True,
                message_id=message_id,
                status_code=status_code,
                response=response_data,
            )

        except HTTPError as exc:
            try:
                raw_error = exc.read().decode("utf-8")
                error_data = json.loads(raw_error)
            except (json.JSONDecodeError, UnicodeDecodeError):
                error_data = {"message": str(exc)}

            error_message = json.dumps(error_data, ensure_ascii=False)
            self._mark_integration_error(integration, error_message)

            return WhatsAppSendResult(
                success=False,
                error=error_message,
                status_code=exc.code,
                response=error_data,
            )

        except (URLError, TimeoutError, OSError) as exc:
            error_message = str(exc)
            self._mark_integration_error(integration, error_message)

            return WhatsAppSendResult(
                success=False,
                error=error_message,
            )

        except Exception as exc:
            error_message = str(exc)
            self._mark_integration_error(integration, error_message)

            return WhatsAppSendResult(
                success=False,
                error=error_message,
    )
        
