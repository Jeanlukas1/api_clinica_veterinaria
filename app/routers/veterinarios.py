"""
app/routers/veterinarios.py
────────────────────────────
Endpoints de Veterinários — implementação completa (ETAPA 8).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_perfil, require_staff, get_current_user
from app.database.session import get_db
from app.models.enums import PerfilUsuario
from app.models.usuario import Usuario
from app.schemas.common import PaginatedResponse
from app.schemas.consulta import AgendaVeterinarioResponse
from app.schemas.veterinario import (
    VeterinarioCreate,
    VeterinarioResponse,
    VeterinarioUpdate,
)
from app.services.consulta import ConsultaService
from app.services.veterinario import VeterinarioService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> VeterinarioService:
    return VeterinarioService(session)

def _consulta_service(session: AsyncSession = Depends(get_db)) -> ConsultaService:
    return ConsultaService(session)


@router.get(
    "/",
    response_model=PaginatedResponse[VeterinarioResponse],
    summary="Listar veterinários",
)
async def listar_veterinarios(
    nome: str | None = Query(None),
    especialidade: str | None = Query(None),
    ativo: bool | None = Query(True),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: VeterinarioService = Depends(_service),
    _: Usuario = Depends(get_current_user),
) -> PaginatedResponse[VeterinarioResponse]:
    items, total = await service.listar(
        nome=nome, especialidade=especialidade, ativo=ativo,
        limit=limit, offset=offset,
    )
    return PaginatedResponse(
        items=[VeterinarioResponse.model_validate(v) for v in items],
        total=total, limit=limit, offset=offset,
    )


@router.post(
    "/",
    response_model=VeterinarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar veterinário",
    description="Cadastra novo veterinário. Valida formato CRMV e unicidade.",
)
async def criar_veterinario(
    data: VeterinarioCreate,
    service: VeterinarioService = Depends(_service),
    current_user: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN)),
) -> VeterinarioResponse:
    vet = await service.criar(data, usuario=current_user.email)
    return VeterinarioResponse.model_validate(vet)


@router.get(
    "/{veterinario_id}",
    response_model=VeterinarioResponse,
    summary="Buscar veterinário por ID",
)
async def buscar_veterinario(
    veterinario_id: uuid.UUID,
    service: VeterinarioService = Depends(_service),
    _: Usuario = Depends(get_current_user),
) -> VeterinarioResponse:
    vet = await service.buscar_por_id(veterinario_id)
    return VeterinarioResponse.model_validate(vet)


@router.patch(
    "/{veterinario_id}",
    response_model=VeterinarioResponse,
    summary="Atualizar veterinário",
)
async def atualizar_veterinario(
    veterinario_id: uuid.UUID,
    data: VeterinarioUpdate,
    service: VeterinarioService = Depends(_service),
    current_user: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN)),
) -> VeterinarioResponse:
    vet = await service.atualizar(veterinario_id, data, usuario=current_user.email)
    return VeterinarioResponse.model_validate(vet)


@router.delete(
    "/{veterinario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Inativar veterinário",
)
async def inativar_veterinario(
    veterinario_id: uuid.UUID,
    service: VeterinarioService = Depends(_service),
    current_user: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN)),
) -> None:
    await service.inativar(veterinario_id, usuario=current_user.email)


@router.get(
    "/{veterinario_id}/agenda",
    response_model=list[AgendaVeterinarioResponse],
    summary="Agenda do veterinário",
    description="Retorna consultas ativas (não canceladas) do veterinário no período.",
)
async def agenda_veterinario(
    veterinario_id: uuid.UUID,
    data_inicio: datetime | None = Query(None),
    data_fim: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: Usuario = Depends(get_current_user),
    consulta_service: ConsultaService = Depends(_consulta_service),
) -> list[AgendaVeterinarioResponse]:
    # VETERINARIO só pode ver sua própria agenda
    if current_user.perfil == PerfilUsuario.VETERINARIO.value:
        if (
            not current_user.veterinario_id
            or current_user.veterinario_id != veterinario_id
        ):
            from app.core.exceptions import AcessoNegadoError
            raise AcessoNegadoError("Veterinários só podem ver sua própria agenda.")

    consultas = await consulta_service.agenda_veterinario(
        veterinario_id, data_inicio=data_inicio, data_fim=data_fim, limit=limit
    )
    return [AgendaVeterinarioResponse.model_validate(c) for c in consultas]
