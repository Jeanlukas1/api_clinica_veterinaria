"""
app/routers/transferencias.py
──────────────────────────────
Endpoints de Transferências — implementação completa (ETAPA 8).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_perfil
from app.database.session import get_db
from app.models.enums import PerfilUsuario
from app.models.usuario import Usuario
from app.schemas.common import PaginatedResponse
from app.schemas.transferencia import TransferenciaCreate, TransferenciaResponse
from app.services.transferencia import TransferenciaService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> TransferenciaService:
    return TransferenciaService(session)


@router.post(
    "/",
    response_model=TransferenciaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Transferir animal entre tutores",
    description=(
        "Transfere a guarda de um animal. "
        "**RN-010**: motivo obrigatório (≥10 caracteres) + auditoria obrigatória. "
        "O animal deve estar ativo e o tutor destino deve estar ativo."
    ),
    responses={
        409: {"description": "Tutor destino é o mesmo que o tutor atual"},
        422: {"description": "Motivo muito curto, animal ou tutor inativo"},
    },
)
async def transferir_animal(
    request: Request,
    data: TransferenciaCreate,
    service: TransferenciaService = Depends(_service),
    current_user: Usuario = Depends(
        require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.RECEPCIONISTA)
    ),
) -> TransferenciaResponse:
    ip = request.client.host if request.client else None
    transferencia = await service.transferir(
        data, usuario=current_user.email, ip_address=ip
    )
    return TransferenciaResponse.model_validate(transferencia)


@router.get(
    "/",
    response_model=PaginatedResponse[TransferenciaResponse],
    summary="Listar transferências",
    description="Lista histórico de transferências. Filtre por animal_id ou tutor_id.",
)
async def listar_transferencias(
    animal_id: uuid.UUID | None = Query(None),
    tutor_id: uuid.UUID | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: TransferenciaService = Depends(_service),
    _: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.RECEPCIONISTA)),
) -> PaginatedResponse[TransferenciaResponse]:
    items, total = await service.listar(
        animal_id=animal_id, tutor_id=tutor_id, limit=limit, offset=offset
    )
    return PaginatedResponse(
        items=[TransferenciaResponse.model_validate(t) for t in items],
        total=total, limit=limit, offset=offset,
    )


@router.get(
    "/{transferencia_id}",
    response_model=TransferenciaResponse,
    summary="Buscar transferência por ID",
)
async def buscar_transferencia(
    transferencia_id: uuid.UUID,
    service: TransferenciaService = Depends(_service),
    _: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.RECEPCIONISTA)),
) -> TransferenciaResponse:
    t = await service.buscar_por_id(transferencia_id)
    return TransferenciaResponse.model_validate(t)
