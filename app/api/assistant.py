from typing import Any

import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.ai.gateway import ai_gateway
from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.errors import (
    AIConfigurationError,
    AIProviderError,
    AIProviderTimeoutError,
    AuthenticationError,
    AuthorizationError,
    ConversationNotFoundError,
    DatabaseError,
    VYRAError,
)
from app.models.user import User
from app.services.assistant import AssistantService


router = APIRouter(
    prefix="/assistant",
    tags=["Assistant"],
)


class AssistantRequest(BaseModel):
    """
    Paramètres optionnels permettant de contrôler
    la génération d'une réponse IA.
    """

    system_prompt: str | None = None

    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
    )

    max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=10000,
    )


class ContextResponse(BaseModel):
    conversation_id: int
    context: dict[str, Any]


class AssistantDraftResponse(BaseModel):
    message_id: int
    conversation_id: int
    content: str
    status: str
    requires_human_validation: bool
    is_ai_generated: bool
    created_at: str


class AssistantAnalysisResponse(BaseModel):
    conversation_id: int
    analysis: Any


def _handle_service_error(error: VYRAError) -> HTTPException:
    """
    Transforme les erreurs internes de VYRA
    en réponses HTTP propres.
    """

    return HTTPException(
        status_code=error.status_code,
        detail=error.to_dict(),
    )


def _build_assistant_service(
    connection: sqlite3.Connection,
) -> AssistantService:
    """
    Construit le service Assistant avec la connexion
    SQLite et le gateway IA centralisé.
    """

    return AssistantService(
        connection=connection,
        ai_gateway=ai_gateway,
    )


@router.post(
    "/conversations/{conversation_id}/suggest-reply",
    response_model=AssistantDraftResponse,
)
def suggest_reply(
    conversation_id: int,
    request: AssistantRequest | None = None,
    current_user: User = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
) -> AssistantDraftResponse:
    """
    Génère une réponse suggérée par VYRA pour une conversation.

    IMPORTANT :
    cette route crée uniquement un brouillon.

    Aucun message n'est envoyé automatiquement au contact.
    L'utilisateur doit valider le brouillon avant tout envoi.
    """

    service = _build_assistant_service(connection)

    try:
        draft = service.suggest_reply(
            user_id=current_user.id,
            conversation_id=conversation_id,
            system_prompt=(
                request.system_prompt
                if request
                else None
            ),
            temperature=(
                request.temperature
                if request
                else None
            ),
            max_tokens=(
                request.max_tokens
                if request
                else None
            ),
        )

        return AssistantDraftResponse(
            message_id=draft.id,
            conversation_id=draft.conversation_id,
            content=draft.content,
            status=draft.status.value,
            requires_human_validation=draft.requires_human_validation,
            is_ai_generated=draft.is_ai_generated,
            created_at=draft.created_at.isoformat(),
        )

    except VYRAError as error:
        raise _handle_service_error(error) from error


@router.post(
    "/conversations/{conversation_id}/analyze",
    response_model=AssistantAnalysisResponse,
)
def analyze_conversation(
    conversation_id: int,
    request: AssistantRequest | None = None,
    current_user: User = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
) -> AssistantAnalysisResponse:
    """
    Analyse une conversation avec l'IA.

    Cette route ne crée pas de message et n'envoie rien
    au contact.
    """

    service = _build_assistant_service(connection)

    try:
        analysis = service.analyze_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
            system_prompt=(
                request.system_prompt
                if request
                else None
            ),
            temperature=(
                request.temperature
                if request
                else None
            ),
            max_tokens=(
                request.max_tokens
                if request
                else None
            ),
        )

        return AssistantAnalysisResponse(
            conversation_id=conversation_id,
            analysis=analysis,
        )

    except VYRAError as error:
        raise _handle_service_error(error) from error


@router.get(
    "/conversations/{conversation_id}/context",
    response_model=ContextResponse,
)
def get_conversation_context(
    conversation_id: int,
    max_messages: int = 20,
    max_memories: int = 20,
    current_user: User = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
) -> ContextResponse:
    """
    Retourne le contexte actuellement utilisé par VYRA
    pour comprendre une conversation.
    """

    if max_messages < 1 or max_messages > 100:
        raise HTTPException(
            status_code=422,
            detail="max_messages doit être compris entre 1 et 100.",
        )

    if max_memories < 1 or max_memories > 100:
        raise HTTPException(
            status_code=422,
            detail="max_memories doit être compris entre 1 et 100.",
        )

    service = _build_assistant_service(connection)

    try:
        context = service.build_conversation_context(
            user_id=current_user.id,
            conversation_id=conversation_id,
            max_messages=max_messages,
            max_memories=max_memories,
        )

        return ContextResponse(
            conversation_id=conversation_id,
            context=context,
        )

    except VYRAError as error:
        raise _handle_service_error(error) from error


@router.get("/health")
def assistant_health() -> dict[str, Any]:
    """
    Vérifie simplement que le module API Assistant
    est correctement chargé.
    """

    return {
        "status": "ok",
        "service": "assistant",
        "ai_gateway": "configured",
    }