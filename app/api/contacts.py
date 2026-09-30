from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.errors import (
    ConflictError,
    ContactNotFoundError,
    DatabaseError,
)
from app.models.contact import ContactSource, ContactStatus
from app.models.user import User
from app.schemas.contact import (
    ContactArchiveUpdate,
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactStatusUpdate,
    ContactUpdate,
)
from app.services.contacts import ContactService


router = APIRouter(
    prefix="/contacts",
    tags=["Contacts"],
)


# ======================================================================
# CREATE
# ======================================================================


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_contact(
    data: ContactCreate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ContactResponse:
    """
    Crée un contact pour l'utilisateur connecté.
    """

    service = ContactService(connection)

    try:
        contact = service.create_contact(
            user_id=current_user.id,
            data=data,
        )

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

    return ContactResponse(
        **contact.to_dict()
    )


# ======================================================================
# LIST
# ======================================================================


@router.get(
    "",
    response_model=ContactListResponse,
)
def list_contacts(
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
    contact_status: ContactStatus | None = Query(
        default=None,
        alias="status",
    ),
    source: ContactSource | None = Query(
        default=None,
    ),
    search: str | None = Query(
        default=None,
        max_length=200,
    ),
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ContactListResponse:
    """
    Retourne la liste paginée des contacts de l'utilisateur.
    """

    service = ContactService(connection)

    try:
        contacts, total = service.list_contacts(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            include_archived=include_archived,
            status=contact_status,
            source=source,
            search=search,
        )

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ContactListResponse(
        items=[
            ContactResponse(
                **contact.to_dict()
            )
            for contact in contacts
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ======================================================================
# GET ONE
# ======================================================================


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
)
def get_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ContactResponse:
    """
    Retourne un contact appartenant à l'utilisateur connecté.
    """

    service = ContactService(connection)

    try:
        contact = service.get_contact(
            user_id=current_user.id,
            contact_id=contact_id,
        )

    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ContactResponse(
        **contact.to_dict()
    )


# ======================================================================
# UPDATE
# ======================================================================


@router.patch(
    "/{contact_id}",
    response_model=ContactResponse,
)
def update_contact(
    contact_id: int,
    data: ContactUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ContactResponse:
    """
    Modifie un contact.
    """

    service = ContactService(connection)

    try:
        contact = service.update_contact(
            user_id=current_user.id,
            contact_id=contact_id,
            data=data,
        )

    except ContactNotFoundError as exc:
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

    return ContactResponse(
        **contact.to_dict()
    )


# ======================================================================
# STATUS
# ======================================================================


@router.post(
    "/{contact_id}/status",
    response_model=ContactResponse,
)
def update_contact_status(
    contact_id: int,
    data: ContactStatusUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ContactResponse:
    """
    Modifie le statut commercial du contact.
    """

    service = ContactService(connection)

    try:
        contact = service.set_status(
            user_id=current_user.id,
            contact_id=contact_id,
            status=data.status,
        )

    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ContactResponse(
        **contact.to_dict()
    )


# ======================================================================
# ARCHIVE
# ======================================================================


@router.post(
    "/{contact_id}/archive",
    response_model=ContactResponse,
)
def archive_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ContactResponse:
    """
    Archive un contact.
    """

    service = ContactService(connection)

    try:
        contact = service.archive_contact(
            user_id=current_user.id,
            contact_id=contact_id,
        )

    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ContactResponse(
        **contact.to_dict()
    )


# ======================================================================
# UNARCHIVE
# ======================================================================


@router.post(
    "/{contact_id}/unarchive",
    response_model=ContactResponse,
)
def unarchive_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ContactResponse:
    """
    Désarchive un contact.
    """

    service = ContactService(connection)

    try:
        contact = service.unarchive_contact(
            user_id=current_user.id,
            contact_id=contact_id,
        )

    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ContactResponse(
        **contact.to_dict()
    )


# ======================================================================
# REGISTER ACTIVITY
# ======================================================================


@router.post(
    "/{contact_id}/activity",
    response_model=ContactResponse,
)
def register_contact_activity(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ContactResponse:
    """
    Enregistre une activité récente avec le contact.
    """

    service = ContactService(connection)

    try:
        contact = service.register_contact_activity(
            user_id=current_user.id,
            contact_id=contact_id,
        )

    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ContactResponse(
        **contact.to_dict()
    )


# ======================================================================
# ARCHIVE STATE
# ======================================================================


@router.patch(
    "/{contact_id}/archive-state",
    response_model=ContactResponse,
)
def update_archive_state(
    contact_id: int,
    data: ContactArchiveUpdate,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> ContactResponse:
    """
    Active ou désactive l'archivage d'un contact.
    """

    service = ContactService(connection)

    try:
        if data.is_archived:
            contact = service.archive_contact(
                user_id=current_user.id,
                contact_id=contact_id,
            )
        else:
            contact = service.unarchive_contact(
                user_id=current_user.id,
                contact_id=contact_id,
            )

    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ContactResponse(
        **contact.to_dict()
    )


# ======================================================================
# DELETE
# ======================================================================


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    connection=Depends(get_db),
) -> None:
    """
    Supprime définitivement un contact.

    Les conversations et données dépendantes configurées
    avec ON DELETE CASCADE seront également supprimées.
    """

    service = ContactService(connection)

    try:
        service.delete_contact(
            user_id=current_user.id,
            contact_id=contact_id,
        )

    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc