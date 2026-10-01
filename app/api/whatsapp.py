from typing import Any

from fastapi import APIRouter

router = APIRouter(
    prefix="/whatsapp",
    tags=["WhatsApp"],
)


@router.post("/webhook")
async def whatsapp_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Point d'entrée utilisé par AutoResponder.

    Reçoit le message WhatsApp et renvoie une réponse
    dans le format attendu par le connecteur.
    """

    query = payload.get("query", {})

    if not isinstance(query, dict):
        query = {}

    message = str(query.get("message", "")).strip()

    if not message:
        return {
            "replies": []
        }

    return {
        "replies": [
            {
                "message": "Bonjour ! Je suis VYRA. Comment puis-je vous aider ?"
            }
        ]
    }