import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.errors import VYRAError
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.users import UserService


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


def _service(connection: sqlite3.Connection) -> UserService:
    return UserService(connection)


def _raise_http_error(error: VYRAError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail=error.to_dict(),
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(
        current_user.to_dict()
    )


@router.patch(
    "/me",
    response_model=UserResponse,
)
def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
) -> UserResponse:
    try:
        user = _service(connection).update_user(
            user_id=current_user.id,
            data=data,
        )

        return UserResponse.model_validate(
            user.to_dict()
        )

    except VYRAError as error:
        raise _raise_http_error(error) from error


@router.post(
    "/me/deactivate",
    response_model=UserResponse,
)
def deactivate_my_account(
    current_user: User = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
) -> UserResponse:
    try:
        user = _service(connection).deactivate_user(
            current_user.id
        )

        return UserResponse.model_validate(
            user.to_dict()
        )

    except VYRAError as error:
        raise _raise_http_error(error) from error


@router.post(
    "/me/activate",
    response_model=UserResponse,
)
def activate_my_account(
    current_user: User = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
) -> UserResponse:
    try:
        user = _service(connection).activate_user(
            current_user.id
        )

        return UserResponse.model_validate(
            user.to_dict()
        )

    except VYRAError as error:
        raise _raise_http_error(error) from error


@router.get("/me/status")
def get_my_account_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    return {
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
    }