import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.errors import (
    ConversationNotFoundError,
    DatabaseError,
    MessageNotFoundError,
)
from app.models.message import (
    Message,
    MessageStatus,
)
from app.models.user import User
from app.schemas.message import (
    AIDraftCreate,
    AIDraftResponse,
    IncomingMessageCreate,
    MessageApproval,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    MessageStatusUpdate,
    MessageUpdate,
)
from app.services.conversations import ConversationService


router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
)


# ======================================================================
# INTERNAL HELPERS
# ======================================================================


def _get_conversation_for_user(
    *,
    connection: sqlite3.Connection,
    user_id: int,
    conversation_id: int,
):
    """
    Vérifie que la conversation appartient bien à l'utilisateur.
    """

    service = ConversationService(
        connection
    )

    try:
        return service.get_conversation(
            user_id=user_id,
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


def _get_message(
    *,
    connection: sqlite3.Connection,
    user_id: int,
    message_id: int,
) -> Message:
    """
    Récupère un message uniquement si sa conversation
    appartient à l'utilisateur connecté.
    """

    query = """
        SELECT
            m.*
        FROM messages AS m
        INNER JOIN conversations AS c
            ON c.id = m.conversation_id
        WHERE m.id = ?
          AND c.user_id = ?
        LIMIT 1
    """

    try:
        row = connection.execute(
            query,
            (
                message_id,
                user_id,
            ),
        ).fetchone()

    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de récupérer le message.",
        ) from exc

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Le message {message_id} est introuvable.",
        )

    return Message.from_row(row)


def _save_message(
    *,
    connection: sqlite3.Connection,
    message: Message,
) -> Message:
    """
    Sauvegarde un message dans SQLite.
    """

    import json

    query = """
        INSERT INTO messages (
            conversation_id,
            sender,
            role,
            content,
            status,
            is_ai_generated,
            requires_approval,
            approved_by_user,
            external_message_id,
            metadata,
            created_at,
            updated_at,
            sent_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:
        cursor = connection.execute(
            query,
            (
                message.conversation_id,
                message.sender.value,
                message.role.value,
                message.content,
                message.status.value,
                int(message.is_ai_generated),
                int(message.requires_approval),
                int(message.approved_by_user),
                message.external_message_id,
                json.dumps(
                    message.metadata,
                    ensure_ascii=False,
                ),
                message.created_at.isoformat(),
                message.updated_at.isoformat(),
                (
                    message.sent_at.isoformat()
                    if message.sent_at
                    else None
                ),
            ),
        )

        connection.commit()

        message.id = cursor.lastrowid

        return message

    except sqlite3.IntegrityError as exc:
        connection.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible d'enregistrer le message.",
        ) from exc

    except sqlite3.Error as exc:
        connection.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'enregistrement du message.",
        ) from exc


# ======================================================================
# LIST CONVERSATION MESSAGES
# ======================================================================


@router.get(
    "/conversation/{conversation_id}",
    response_model=MessageListResponse,
)
def list_messages(
    conversation_id: int,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> MessageListResponse:
    """
    Retourne les messages d'une conversation.
    """

    _get_conversation_for_user(
        connection=connection,
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    offset = (
        page - 1
    ) * page_size

    count_query = """
        SELECT COUNT(*)
        FROM messages
        WHERE conversation_id = ?
    """

    data_query = """
        SELECT *
        FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
        LIMIT ? OFFSET ?
    """

    try:
        total = int(
            connection.execute(
                count_query,
                (conversation_id,),
            ).fetchone()[0]
        )

        rows = connection.execute(
            data_query,
            (
                conversation_id,
                page_size,
                offset,
            ),
        ).fetchall()

    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de récupérer les messages.",
        ) from exc

    messages = [
        Message.from_row(row)
        for row in rows
    ]

    return MessageListResponse(
        items=[
            MessageResponse(
                **message.to_dict()
            )
            for message in messages
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ======================================================================
# CREATE USER MESSAGE
# ======================================================================


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> MessageResponse:
    """
    Enregistre un message envoyé par l'utilisateur.

    Dans VYRA V1, cet endpoint enregistre le message.
    Il ne l'envoie pas automatiquement à WhatsApp,
    Instagram ou un autre canal externe.
    """

    conversation = _get_conversation_for_user(
        connection=connection,
        user_id=current_user.id,
        conversation_id=data.conversation_id,
    )

    if not conversation.can_receive_message():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette conversation est archivée.",
        )

    message = Message.user_message(
        conversation_id=data.conversation_id,
        content=data.content,
        external_message_id=data.external_message_id,
        metadata=data.metadata,
    )

    saved_message = _save_message(
        connection=connection,
        message=message,
    )

    _register_conversation_activity(
        connection=connection,
        user_id=current_user.id,
        conversation_id=data.conversation_id,
    )

    return MessageResponse(
        **saved_message.to_dict()
    )


# ======================================================================
# CREATE INCOMING CONTACT MESSAGE
# ======================================================================


@router.post(
    "/incoming",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_incoming_message(
    data: IncomingMessageCreate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> MessageResponse:
    """
    Enregistre un message reçu d'un contact.

    Plus tard, un connecteur WhatsApp pourra appeler
    une couche d'intégration qui utilisera ce même mécanisme.
    """

    conversation = _get_conversation_for_user(
        connection=connection,
        user_id=current_user.id,
        conversation_id=data.conversation_id,
    )

    if not conversation.can_receive_message():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette conversation est archivée.",
        )

    message = Message.incoming(
        conversation_id=data.conversation_id,
        content=data.content,
        external_message_id=data.external_message_id,
        metadata=data.metadata,
    )

    saved_message = _save_message(
        connection=connection,
        message=message,
    )

    _register_conversation_activity(
        connection=connection,
        user_id=current_user.id,
        conversation_id=data.conversation_id,
    )

    return MessageResponse(
        **saved_message.to_dict()
    )


# ======================================================================
# CREATE AI DRAFT
# ======================================================================


@router.post(
    "/ai-draft",
    response_model=AIDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ai_draft(
    data: AIDraftCreate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> AIDraftResponse:
    """
    Enregistre une proposition de réponse générée par l'IA.

    Cette route ne génère pas elle-même le texte.
    Le service Assistant s'occupera de la génération.

    Elle permet de conserver une architecture claire :
    génération IA ≠ persistance du message.
    """

    conversation = _get_conversation_for_user(
        connection=connection,
        user_id=current_user.id,
        conversation_id=data.conversation_id,
    )

    if not conversation.can_use_ai:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="L'assistance IA est désactivée.",
        )

    message = Message.ai_draft(
        conversation_id=data.conversation_id,
        content=data.content,
        metadata=data.metadata,
    )

    saved_message = _save_message(
        connection=connection,
        message=message,
    )

    return AIDraftResponse(
        message=MessageResponse(
            **saved_message.to_dict()
        ),
        requires_approval=True,
    )


# ======================================================================
# GET ONE MESSAGE
# ======================================================================


@router.get(
    "/{message_id}",
    response_model=MessageResponse,
)
def get_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> MessageResponse:
    """
    Retourne un message appartenant à l'utilisateur.
    """

    message = _get_message(
        connection=connection,
        user_id=current_user.id,
        message_id=message_id,
    )

    return MessageResponse(
        **message.to_dict()
    )


# ======================================================================
# UPDATE MESSAGE
# ======================================================================


@router.patch(
    "/{message_id}",
    response_model=MessageResponse,
)
def update_message(
    message_id: int,
    data: MessageUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> MessageResponse:
    """
    Modifie un message qui n'a pas encore été envoyé.
    """

    message = _get_message(
        connection=connection,
        user_id=current_user.id,
        message_id=message_id,
    )

    update_data = data.model_dump(
        exclude_unset=True
    )

    try:
        if "content" in update_data:
            message.update_content(
                update_data["content"]
            )

        if "metadata" in update_data:
            message.metadata = (
                update_data["metadata"] or {}
            )
            message.touch()

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    import json

    query = """
        UPDATE messages
        SET
            content = ?,
            metadata = ?,
            updated_at = ?
        WHERE id = ?
    """

    try:
        connection.execute(
            query,
            (
                message.content,
                json.dumps(
                    message.metadata,
                    ensure_ascii=False,
                ),
                message.updated_at.isoformat(),
                message.id,
            ),
        )

        connection.commit()

    except sqlite3.Error as exc:
        connection.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de modifier le message.",
        ) from exc

    return MessageResponse(
        **message.to_dict()
    )


# ======================================================================
# APPROVE / REJECT AI MESSAGE
# ======================================================================


@router.post(
    "/{message_id}/approval",
    response_model=MessageResponse,
)
def approve_message(
    message_id: int,
    data: MessageApproval,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> MessageResponse:
    """
    Approuve ou rejette une proposition IA.
    """

    message = _get_message(
        connection=connection,
        user_id=current_user.id,
        message_id=message_id,
    )

    try:
        if data.approved:
            message.approve()
        else:
            message.reject()

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    _save_message_state(
        connection=connection,
        message=message,
    )

    return MessageResponse(
        **message.to_dict()
    )


# ======================================================================
# MESSAGE STATUS
# ======================================================================


@router.patch(
    "/{message_id}/status",
    response_model=MessageResponse,
)
def update_message_status(
    message_id: int,
    data: MessageStatusUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> MessageResponse:
    """
    Modifie l'état d'un message.

    Les transitions importantes sont contrôlées
    par le modèle Message.
    """

    message = _get_message(
        connection=connection,
        user_id=current_user.id,
        message_id=message_id,
    )

    try:
        if data.status == MessageStatus.SENT:
            message.mark_as_sent()

        elif data.status == MessageStatus.DELIVERED:
            message.mark_as_delivered()

        elif data.status == MessageStatus.READ:
            message.mark_as_read()

        elif data.status == MessageStatus.FAILED:
            message.mark_as_failed()

        elif data.status == MessageStatus.CANCELLED:
            message.cancel()

        elif data.status == MessageStatus.APPROVED:
            message.approve()

        else:
            raise ValueError(
                f"Transition vers le statut "
                f"{data.status.value!r} non supportée par "
                "cette API."
            )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    _save_message_state(
        connection=connection,
        message=message,
    )

    return MessageResponse(
        **message.to_dict()
    )


# ======================================================================
# DELETE
# ======================================================================


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> None:
    """
    Supprime un message appartenant à l'utilisateur.
    """

    message = _get_message(
        connection=connection,
        user_id=current_user.id,
        message_id=message_id,
    )

    query = """
        DELETE FROM messages
        WHERE id = ?
    """

    try:
        cursor = connection.execute(
            query,
            (message.id,),
        )

        connection.commit()

    except sqlite3.Error as exc:
        connection.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de supprimer le message.",
        ) from exc

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message introuvable.",
        )


# ======================================================================
# INTERNAL STATE HELPERS
# ======================================================================


def _save_message_state(
    *,
    connection: sqlite3.Connection,
    message: Message,
) -> None:
    """
    Sauvegarde l'état actuel d'un message.
    """

    import json

    query = """
        UPDATE messages
        SET
            content = ?,
            status = ?,
            is_ai_generated = ?,
            requires_approval = ?,
            approved_by_user = ?,
            external_message_id = ?,
            metadata = ?,
            created_at = ?,
            updated_at = ?,
            sent_at = ?
        WHERE id = ?
    """

    try:
        connection.execute(
            query,
            (
                message.content,
                message.status.value,
                int(message.is_ai_generated),
                int(message.requires_approval),
                int(message.approved_by_user),
                message.external_message_id,
                json.dumps(
                    message.metadata,
                    ensure_ascii=False,
                ),
                message.created_at.isoformat(),
                message.updated_at.isoformat(),
                (
                    message.sent_at.isoformat()
                    if message.sent_at
                    else None
                ),
                message.id,
            ),
        )

        connection.commit()

    except sqlite3.Error as exc:
        connection.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de sauvegarder le message.",
        ) from exc


def _register_conversation_activity(
    *,
    connection: sqlite3.Connection,
    user_id: int,
    conversation_id: int,
) -> None:
    """
    Met à jour l'activité de la conversation après
    l'enregistrement d'un message.
    """

    service = ConversationService(
        connection
    )

    try:
        service.register_message(
            user_id=user_id,
            conversation_id=conversation_id,
        )

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc