from typing import Any

from fastapi import APIRouter

from app.ai.gateway import ai_gateway
from app.core.errors import VYRAError

router = APIRouter(
    prefix="/whatsapp",
    tags=["WhatsApp"],
)


@router.post("/webhook")
async def whatsapp_webhook(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Reçoit un message WhatsApp via AutoResponder,
    l'envoie à Gemini via VYRA et retourne la réponse.
    """

    query = payload.get("query", {})

    if not isinstance(query, dict):
        query = {}

    message = str(
        query.get("message", "")
    ).strip()

    if not message:
        return {
            "replies": []
        }

    system_prompt = """
Tu es VYRA, un assistant IA commercial et personnel.

Tu réponds naturellement, clairement et brièvement
aux messages reçus sur WhatsApp.

Tu aides l'utilisateur dans ses échanges avec ses clients
et prospects.

Ne prétends jamais avoir effectué une action que tu n'as
pas réellement effectuée.

Si une information manque, pose simplement la question
nécessaire.

Réponds dans la langue utilisée par ton interlocuteur.
""".strip()

    try:
        response = ai_gateway.generate_text(
            message,
            system_prompt=system_prompt,
        )

        reply = response.text.strip()

        if not reply:
            reply = "Je suis VYRA. Comment puis-je vous aider ?"

        return {
            "replies": [
                {
                    "message": reply
                }
            ]
        }

    except Exception as exc:
        raise VYRAError(
            message="VYRA AI response failed.",
            details={
                "error": str(exc),
            },
        ) from exc
