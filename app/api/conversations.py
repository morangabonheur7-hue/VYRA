from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.errors import (
    ConflictError,
    ConversationNotFoundError,
    DatabaseError,
)
from app.models.conversation import (
    ConversationChannel,
    ConversationStatus,
)
from app.models.user import User
from app.schemas.conversation import (
    ConversationAIUpdate,
    ConversationArchiveUpdate,
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    ConversationStatusUpdate,
    ConversationUpdate,
)
from app.services.conversations import ConversationService


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


# ======================================================================
# CREATE
# ======================================================================


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Crée une conversation avec un contact.
    """

    service = ConversationService(connection)

    try:
        conversation = service.create_conversation(
            user_id=current_user.id,
            data=data,
        )

    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# LIST
# ======================================================================


@router.get(
    "",
    response_model=ConversationListResponse,
)
def list_conversations(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    include_archived: bool = Query(
        default=False,
    ),
    conversation_status: ConversationStatus | None = Query(
        default=None,
        alias="status",
    ),
    channel: ConversationChannel | None = Query(
        default=None,
    ),
    contact_id: int | None = Query(
        default=None,
        gt=0,
    ),
    search: str | None = Query(
        default=None,
        max_length=200,
    ),
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationListResponse:
    """
    Retourne les conversations de l'utilisateur.
    """

    service = ConversationService(connection)

    try:
        conversations, total = service.list_conversations(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            include_archived=include_archived,
            status=conversation_status,
            channel=channel,
            contact_id=contact_id,
            search=search,
        )

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationListResponse(
        items=[
            ConversationResponse(
                **conversation.to_dict()
            )
            for conversation in conversations
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ======================================================================
# GET ONE
# ======================================================================


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Retourne une conversation appartenant
    à l'utilisateur connecté.
    """

    service = ConversationService(connection)

    try:
        conversation = service.get_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# CONTACT CONVERSATIONS
# ======================================================================


@router.get(
    "/contact/{contact_id}",
    response_model=list[ConversationResponse],
)
def get_contact_conversations(
    contact_id: int,
    include_archived: bool = Query(
        default=False,
    ),
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> list[ConversationResponse]:
    """
    Retourne toutes les conversations d'un contact.
    """

    service = ConversationService(connection)

    try:
        conversations = service.get_contact_conversations(
            user_id=current_user.id,
            contact_id=contact_id,
            include_archived=include_archived,
        )

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return [
        ConversationResponse(
            **conversation.to_dict()
        )
        for conversation in conversations
    ]


# ======================================================================
# UPDATE
# ======================================================================


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Modifie une conversation.
    """

    service = ConversationService(connection)

    try:
        conversation = service.update_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
            data=data,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# ACTIVATE
# ======================================================================


@router.post(
    "/{conversation_id}/activate",
    response_model=ConversationResponse,
)
def activate_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Réactive une conversation.
    """

    service = ConversationService(connection)

    try:
        conversation = service.activate_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# WAITING
# ======================================================================


@router.post(
    "/{conversation_id}/waiting",
    response_model=ConversationResponse,
)
def mark_conversation_waiting(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Place une conversation en attente.
    """

    service = ConversationService(connection)

    try:
        conversation = service.mark_as_waiting(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# CLOSE
# ======================================================================


@router.post(
    "/{conversation_id}/close",
    response_model=ConversationResponse,
)
def close_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Ferme une conversation.
    """

    service = ConversationService(connection)

    try:
        conversation = service.close_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# AI ENABLE
# ======================================================================


@router.post(
    "/{conversation_id}/ai/enable",
    response_model=ConversationResponse,
)
def enable_conversation_ai(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Active l'assistance IA pour une conversation.
    """

    service = ConversationService(connection)

    try:
        conversation = service.enable_ai(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# AI DISABLE
# ======================================================================


@router.post(
    "/{conversation_id}/ai/disable",
    response_model=ConversationResponse,
)
def disable_conversation_ai(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Désactive l'assistance IA pour une conversation.
    """

    service = ConversationService(connection)

    try:
        conversation = service.disable_ai(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# ARCHIVE
# ======================================================================


@router.post(
    "/{conversation_id}/archive",
    response_model=ConversationResponse,
)
def archive_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Archive une conversation.
    """

    service = ConversationService(connection)

    try:
        conversation = service.archive_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# UNARCHIVE
# ======================================================================


@router.post(
    "/{conversation_id}/unarchive",
    response_model=ConversationResponse,
)
def unarchive_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Désarchive une conversation.
    """

    service = ConversationService(connection)

    try:
        conversation = service.unarchive_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# ARCHIVE STATE
# ======================================================================


@router.patch(
    "/{conversation_id}/archive-state",
    response_model=ConversationResponse,
)
def update_archive_state(
    conversation_id: int,
    data: ConversationArchiveUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Active ou désactive l'archivage d'une conversation.
    """

    service = ConversationService(connection)

    try:
        if data.is_archived:
            conversation = service.archive_conversation(
                user_id=current_user.id,
                conversation_id=conversation_id,
            )
        else:
            conversation = service.unarchive_conversation(
                user_id=current_user.id,
                conversation_id=conversation_id,
            )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# REGISTER MESSAGE ACTIVITY
# ======================================================================


@router.post(
    "/{conversation_id}/activity",
    response_model=ConversationResponse,
)
def register_conversation_activity(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Met à jour l'activité récente de la conversation.
    """

    service = ConversationService(connection)

    try:
        conversation = service.register_message(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# SUMMARY
# ======================================================================


@router.patch(
    "/{conversation_id}/summary",
    response_model=ConversationResponse,
)
def update_conversation_summary(
    conversation_id: int,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ConversationResponse:
    """
    Met à jour le résumé d'une conversation.
    """

    service = ConversationService(connection)

    try:
        conversation = service.update_summary(
            user_id=current_user.id,
            conversation_id=conversation_id,
            summary=data.summary,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ConversationResponse(
        **conversation.to_dict()
    )


# ======================================================================
# DELETE
# ======================================================================


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> None:
    """
    Supprime définitivement une conversation.

    Les messages associés seront supprimés grâce
    à ON DELETE CASCADE.
    """

    service = ConversationService(connection)

    try:
        service.delete_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc