from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import (
    assistant,
    auth,
    contacts,
    conversations,
    messages,
    tasks,
    users,
    WhatsApp,
)
from app.core.config import settings
from app.core.database import initialize_database
from app.core.errors import VYRAError


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.exception_handler(VYRAError)
async def vyra_exception_handler(request: Request, exc: VYRAError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.get("/")
async def root():
    return {
        "name": "VYRA",
        "version": settings.app_version,
        "status": "online",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "VYRA API",
        "version": settings.app_version,
    }


app.include_router(
    auth.router,
    prefix=settings.api_prefix,
)

app.include_router(
    users.router,
    prefix=settings.api_prefix,
)

app.include_router(
    contacts.router,
    prefix=settings.api_prefix,
)

app.include_router(
    conversations.router,
    prefix=settings.api_prefix,
)

app.include_router(
    messages.router,
    prefix=settings.api_prefix,
)

app.include_router(
    tasks.router,
    prefix=settings.api_prefix,
)

app.include_router(
    assistant.router,
    prefix=settings.api_prefix,
)

app.include_router(
    whatsapp.router,
    prefix=settings.api_prefix,
)
