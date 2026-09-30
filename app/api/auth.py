from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import VYRAError
from app.models.user import User
from app.schemas.user import (
    PasswordChange,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserLoginResponse,
    UserResponse,
)
from app.services.users import UserService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

security = HTTPBearer(auto_error=False)


def _create_token(
    *,
    user_id: int,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def _create_access_token(user_id: int) -> str:
    return _create_token(
        user_id=user_id,
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.access_token_expire_minutes
        ),
    )


def _create_refresh_token(user_id: int) -> str:
    return _create_token(
        user_id=user_id,
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.refresh_token_expire_days
        ),
    )


def _decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

    except jwt.ExpiredSignatureError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Le token a expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def _build_tokens(user_id: int) -> TokenResponse:
    return TokenResponse(
        access_token=_create_access_token(user_id),
        refresh_token=_create_refresh_token(user_id),
        token_type="bearer",
    )


def _service(
    connection: sqlite3.Connection,
) -> UserService:
    return UserService(connection)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    connection: sqlite3.Connection = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Un access token est requis.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    subject = payload.get("sub")

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Le token ne contient pas d'utilisateur.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant utilisateur invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    try:
        user = _service(connection).get_user(user_id)
    except VYRAError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.to_dict(),
        ) from error

    if not user.can_login():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ce compte est désactivé.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post(
    "/register",
    response_model=UserLoginResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: UserCreate,
    connection: sqlite3.Connection = Depends(get_db),
) -> UserLoginResponse:
    try:
        user = _service(connection).create_user(data)

        tokens = _build_tokens(user.id)

        return UserLoginResponse(
            user=UserResponse.model_validate(
                user.to_dict()
            ),
            tokens=tokens,
        )

    except VYRAError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.to_dict(),
        ) from error


@router.post(
    "/login",
    response_model=UserLoginResponse,
)
def login(
    data: UserLogin,
    connection: sqlite3.Connection = Depends(get_db),
) -> UserLoginResponse:
    try:
        user = _service(connection).authenticate(
            email=str(data.email),
            password=data.password,
        )

        tokens = _build_tokens(user.id)

        return UserLoginResponse(
            user=UserResponse.model_validate(
                user.to_dict()
            ),
            tokens=tokens,
        )

    except VYRAError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.to_dict(),
        ) from error


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(
        current_user.to_dict()
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    connection: sqlite3.Connection = Depends(get_db),
) -> TokenResponse:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token requis.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(credentials.credentials)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Un refresh token est requis.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    subject = payload.get("sub")

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Le refresh token ne contient pas d'utilisateur.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant utilisateur invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    try:
        user = _service(connection).get_user(user_id)
    except VYRAError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.to_dict(),
        ) from error

    if not user.can_login():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ce compte est désactivé.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _build_tokens(user.id)


@router.post(
    "/change-password",
    response_model=UserResponse,
)
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_db),
) -> UserResponse:
    try:
        user = _service(connection).change_password(
            user_id=current_user.id,
            data=data,
        )

        return UserResponse.model_validate(
            user.to_dict()
        )

    except VYRAError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.to_dict(),
        ) from error