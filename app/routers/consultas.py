"""
app/routers/consultas.py
─────────────────────────
Endpoints de Consultas — implementação completa (ETAPA 8).
Destaque: PATCH /{id}/status implementa a máquina de estados.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_perfil, require_staff
from app.database.session import get_db
from app.models.enums import PerfilUsuario
from app.models.usuario import Usuario
from app.schemas.common import PaginatedResponse
from app.schemas.consulta import (
    ConsultaCreate,
    ConsultaDetalheResponse,
    ConsultaResponse,
    ConsultaStatusUpdate,
    ConsultaUpdate,
)
from app.services.consulta import ConsultaService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> ConsultaService:
    return ConsultaService(session)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=PaginatedResponse[ConsultaResponse],
    summary="Listar consultas",
    description="Lista consultas com filtros por animal, veterinário, status e período.",
)
async def listar_consultas(
    animal_id: uuid.UUID | None = Query(None),
    veterinario_id: uuid.UUID | None = Query(None),
    status_consulta: str | None = Query(None, alias="status"),
    data_inicio: datetime | None = Query(None),
    data_fim: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ConsultaService = Depends(_service),
    _: Usuario = Depends(require_staff()),
) -> PaginatedResponse[ConsultaResponse]:
    items, total = await service.listar(
        animal_id=animal_id,
        veterinario_id=veterinario_id,
        status=status_consulta,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(
        items=[ConsultaResponse.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/",
    response_model=ConsultaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agendar consulta",
    description=(
        "Agenda nova consulta com status inicial AGENDADA. "
        "Valida: RN-004 (conflito de agenda), RN-005 (data passada), "
        "RN-006 (emergência ignora conflito), RN-011 (veterinário ativo)."
    ),
    responses={
        409: {"description": "Conflito de agenda (RN-004)"},
        422: {"description": "Dados inválidos ou veterinário inativo (RN-011)"},
    },
)
async def criar_consulta(
    request: Request,
    data: ConsultaCreate,
    service: ConsultaService = Depends(_service),
    current_user: Usuario = Depends(
        require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.RECEPCIONISTA)
    ),
) -> ConsultaResponse:
    ip = request.client.host if request.client else None
    consulta = await service.criar(data, usuario=current_user.email, ip_address=ip)
    return ConsultaResponse.model_validate(consulta)


@router.get(
    "/{consulta_id}",
    response_model=ConsultaResponse,
    summary="Buscar consulta por ID",
)
async def buscar_consulta(
    consulta_id: uuid.UUID,
    service: ConsultaService = Depends(_service),
    _: Usuario = Depends(require_staff()),
) -> ConsultaResponse:
    consulta = await service.buscar_por_id(consulta_id)
    return ConsultaResponse.model_validate(consulta)


@router.patch(
    "/{consulta_id}",
    response_model=ConsultaResponse,
    summary="Atualizar consulta",
    description=(
        "Atualiza campos editáveis (observações, horário, veterinário). "
        "RN-008: bloqueia atualização em estado terminal."
    ),
)
async def atualizar_consulta(
    consulta_id: uuid.UUID,
    data: ConsultaUpdate,
    service: ConsultaService = Depends(_service),
    current_user: Usuario = Depends(
        require_perfil(
            PerfilUsuario.ADMIN,
            PerfilUsuario.RECEPCIONISTA,
            PerfilUsuario.VETERINARIO,
        )
    ),
) -> ConsultaResponse:
    consulta = await service.atualizar(
        consulta_id, data, usuario=current_user.email
    )
    return ConsultaResponse.model_validate(consulta)


@router.patch(
    "/{consulta_id}/status",
    response_model=ConsultaResponse,
    summary="Transição de estado",
    description=(
        "**Máquina de estados da consulta.**\n\n"
        "Transições válidas:\n"
        "- `AGENDADA` → `CONFIRMADA` | `CANCELADA`\n"
        "- `CONFIRMADA` → `EM_ANDAMENTO` | `CANCELADA`\n"
        "- `EM_ANDAMENTO` → `CONCLUIDA`\n\n"
        "RN-007: Diagnóstico obrigatório ao concluir.\n"
        "RN-008: Estado terminal (CONCLUIDA/CANCELADA) é imutável."
    ),
    responses={
        422: {
            "description": "Transição inválida (TRANSICAO_INVALIDA) ou diagnóstico ausente (DIAGNOSTICO_OBRIGATORIO)"
        },
    },
)
async def mudar_status_consulta(
    request: Request,
    consulta_id: uuid.UUID,
    data: ConsultaStatusUpdate,
    service: ConsultaService = Depends(_service),
    current_user: Usuario = Depends(
        require_perfil(
            PerfilUsuario.ADMIN,
            PerfilUsuario.VETERINARIO,
            PerfilUsuario.RECEPCIONISTA,
        )
    ),
) -> ConsultaResponse:
    ip = request.client.host if request.client else None
    consulta = await service.mudar_status(
        consulta_id, data, usuario=current_user.email, ip_address=ip
    )
    return ConsultaResponse.model_validate(consulta)


@router.delete(
    "/{consulta_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancelar consulta",
    description=(
        "Cancela a consulta via transição de estado → CANCELADA. "
        "RN-008: não é possível cancelar consultas CONCLUIDAS."
    ),
)
async def cancelar_consulta(
    request: Request,
    consulta_id: uuid.UUID,
    service: ConsultaService = Depends(_service),
    current_user: Usuario = Depends(
        require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.RECEPCIONISTA)
    ),
) -> None:
    from app.models.enums import StatusConsulta
    ip = request.client.host if request.client else None
    data = ConsultaStatusUpdate(status=StatusConsulta.CANCELADA)
    await service.mudar_status(
        consulta_id, data, usuario=current_user.email, ip_address=ip
    )
