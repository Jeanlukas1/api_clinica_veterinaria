"""
app/routers/vacinas.py
───────────────────────
Endpoints de Vacinas — implementação completa (ETAPA 8).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_perfil, require_staff, get_current_user
from app.database.session import get_db
from app.models.enums import PerfilUsuario
from app.models.usuario import Usuario
from app.schemas.common import PaginatedResponse
from app.schemas.vacina import VacinaCreate, VacinaResponse, VacinaUpdate
from app.services.vacina import VacinaService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> VacinaService:
    return VacinaService(session)


@router.get(
    "/",
    response_model=PaginatedResponse[VacinaResponse],
    summary="Listar vacinas",
    description="Lista vacinas. Filtrar por animal_id para ver histórico de vacinação.",
)
async def listar_vacinas(
    animal_id: uuid.UUID | None = Query(None),
    consulta_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: VacinaService = Depends(_service),
    _: Usuario = Depends(get_current_user),
) -> PaginatedResponse[VacinaResponse]:
    items, total = await service.listar(
        animal_id=animal_id, consulta_id=consulta_id, limit=limit, offset=offset
    )
    return PaginatedResponse(
        items=[VacinaResponse.model_validate(v) for v in items],
        total=total, limit=limit, offset=offset,
    )


@router.post(
    "/",
    response_model=VacinaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar vacina",
    description=(
        "Registra aplicação de vacina. "
        "RN-009: data_aplicacao não pode ser futura. "
        "Se consulta_id fornecida, a consulta deve estar EM_ANDAMENTO ou CONCLUIDA."
    ),
)
async def criar_vacina(
    data: VacinaCreate,
    service: VacinaService = Depends(_service),
    current_user: Usuario = Depends(
        require_perfil(
            PerfilUsuario.ADMIN,
            PerfilUsuario.VETERINARIO,
            PerfilUsuario.RECEPCIONISTA,
        )
    ),
) -> VacinaResponse:
    vacina = await service.criar(data, usuario=current_user.email)
    return VacinaResponse.model_validate(vacina)


@router.get(
    "/{vacina_id}",
    response_model=VacinaResponse,
    summary="Buscar vacina por ID",
)
async def buscar_vacina(
    vacina_id: uuid.UUID,
    service: VacinaService = Depends(_service),
    _: Usuario = Depends(get_current_user),
) -> VacinaResponse:
    vacina = await service.buscar_por_id(vacina_id)
    return VacinaResponse.model_validate(vacina)


@router.patch(
    "/{vacina_id}",
    response_model=VacinaResponse,
    summary="Atualizar vacina",
)
async def atualizar_vacina(
    vacina_id: uuid.UUID,
    data: VacinaUpdate,
    service: VacinaService = Depends(_service),
    current_user: Usuario = Depends(
        require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VETERINARIO)
    ),
) -> VacinaResponse:
    vacina = await service.atualizar(vacina_id, data, usuario=current_user.email)
    return VacinaResponse.model_validate(vacina)


@router.delete(
    "/{vacina_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover vacina",
    description="Remove vacina fisicamente. Restrito a ADMIN.",
)
async def remover_vacina(
    vacina_id: uuid.UUID,
    service: VacinaService = Depends(_service),
    _: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN)),
) -> None:
    await service.remover(vacina_id)
