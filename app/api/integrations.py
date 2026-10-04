from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection
from pydantic import BaseModel

from app.core.database import get_db
from app.services.integrations import IntegrationService


router = APIRouter(
    prefix="/integrations",
    tags=["Integrations"],
)


class WhatsAppIntegrationCreate(BaseModel):
    company_id: int
    phone_number_id: str
    access_token: str
    business_account_id: str | None = None
    metadata: dict[str, Any] = {}


@router.post("/whatsapp")
def create_whatsapp_integration(
    data: WhatsAppIntegrationCreate,
    db: Connection = Depends(get_db),
):

    service = IntegrationService(db)

    existing = service.get_company_integration(
        company_id=data.company_id,
        provider="whatsapp",
        integration_type="cloud_api",
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Cette entreprise possède déjà une intégration WhatsApp.",
        )

    return service.create(
        company_id=data.company_id,
        provider="whatsapp",
        integration_type="cloud_api",
        external_account_id=data.business_account_id,
        external_phone_number_id=data.phone_number_id,
        access_token=data.access_token,
        metadata=data.metadata,
    )


@router.get("/{integration_id}")
def get_integration(
    integration_id: int,
    db: Connection = Depends(get_db),
):

    service = IntegrationService(db)

    integration = service.get(integration_id)

    if integration is None:
        raise HTTPException(
            status_code=404,
            detail="Intégration introuvable.",
        )

    return integration


@router.post("/{integration_id}/activate")
def activate_integration(
    integration_id: int,
    db: Connection = Depends(get_db),
):

    result = IntegrationService(db).activate(
        integration_id
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Intégration introuvable.",
        )

    return result


@router.post("/{integration_id}/deactivate")
def deactivate_integration(
    integration_id: int,
    db: Connection = Depends(get_db),
):

    result = IntegrationService(db).deactivate(
        integration_id
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Intégration introuvable.",
        )

    return result