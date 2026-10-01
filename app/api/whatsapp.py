from typing import Any

from fastapi import APIRouter

router = APIRouter(
    prefix="/whatsapp",
    tags=["WhatsApp"],
)


@router.post("/webhook")
async def whatsapp_webhook(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Test minimal du pont AutoResponder -> VYRA.
    """

    return {
        "replies": [
            {
                "message": "VYRA TEST OK 🚀"
            }
        ]
    }
