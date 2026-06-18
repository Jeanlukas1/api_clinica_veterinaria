"""
app/routers/animais.py
───────────────────────
Endpoints de Animais — implementação completa (ETAPA 8).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_perfil, require_staff
from app.database.session import get_db
from app.models.enums import PerfilUsuario
from app.models.usuario import Usuario
from app.schemas.animal import (
    AnimalCreate,
    AnimalResponse,
    AnimalResumoResponse,
    EstatisticasAnimalResponse,
    HistoricoClinicoResponse,
    AnimalUpdate,
)
from app.schemas.common import PaginatedResponse
from app.services.animal import AnimalService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> AnimalService:
    return AnimalService(session)


# ─── Guard helper ─────────────────────────────────────────────────────────────

def _verificar_acesso_animal(current_user: Usuario, animal) -> None:
    """TUTOR só pode ver/editar seus próprios animais."""
    if current_user.perfil == PerfilUsuario.TUTOR.value:
        if (
            not current_user.tutor_id
            or current_user.tutor_id != animal.tutor_id
        ):
            from app.core.exceptions import AcessoNegadoError
            raise AcessoNegadoError("Acesso restrito ao animal do próprio tutor.")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=PaginatedResponse[AnimalResumoResponse],
    summary="Listar animais",
    description="Lista animais com filtros por nome, espécie e tutor. Paginado.",
)
async def listar_animais(
    nome: str | None = Query(None),
    especie: str | None = Query(None),
    tutor_id: uuid.UUID | None = Query(None),
    ativo: bool | None = Query(True),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: AnimalService = Depends(_service),
    _: Usuario = Depends(require_staff()),
) -> PaginatedResponse[AnimalResumoResponse]:
    items, total = await service.listar(
        nome=nome, especie=especie, tutor_id=tutor_id,
        ativo=ativo, limit=limit, offset=offset,
    )
    return PaginatedResponse(
        items=[AnimalResumoResponse.model_validate(a) for a in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/",
    response_model=AnimalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar animal",
    description=(
        "Cadastra novo animal. "
        "Valida RN-002 (data_nascimento), RN-003 (microchip único), RN-012 (peso > 0)."
    ),
)
async def criar_animal(
    data: AnimalCreate,
    service: AnimalService = Depends(_service),
    current_user: Usuario = Depends(
        require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.RECEPCIONISTA)
    ),
) -> AnimalResponse:
    animal = await service.criar(data, usuario=current_user.email)
    return AnimalResponse.model_validate(animal)


@router.get(
    "/{animal_id}",
    response_model=AnimalResponse,
    summary="Buscar animal por ID",
)
async def buscar_animal(
    animal_id: uuid.UUID,
    service: AnimalService = Depends(_service),
    current_user: Usuario = Depends(get_current_user),
) -> AnimalResponse:
    animal = await service.buscar_por_id(animal_id)
    _verificar_acesso_animal(current_user, animal)
    return AnimalResponse.model_validate(animal)


@router.patch(
    "/{animal_id}",
    response_model=AnimalResponse,
    summary="Atualizar animal",
    description="Atualiza campos do animal. RN-003 revalidado para microchip.",
)
async def atualizar_animal(
    animal_id: uuid.UUID,
    data: AnimalUpdate,
    service: AnimalService = Depends(_service),
    current_user: Usuario = Depends(
        require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.RECEPCIONISTA)
    ),
) -> AnimalResponse:
    animal = await service.atualizar(animal_id, data, usuario=current_user.email)
    return AnimalResponse.model_validate(animal)


@router.delete(
    "/{animal_id}",
    status_code=status.HTTP_200_OK,
    summary="Inativar animal",
    description="Soft delete: define ativo=false. Gera auditoria.",
)
async def inativar_animal(
    animal_id: uuid.UUID,
    service: AnimalService = Depends(_service),
    current_user: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN)),
) -> dict:
    await service.inativar(animal_id, usuario=current_user.email)
    return {"message": "Animal inativado com sucesso."}


@router.get(
    "/{animal_id}/historico",
    response_model=HistoricoClinicoResponse,
    summary="Histórico clínico consolidado",
    description=(
        "Retorna histórico clínico completo: consultas, vacinas e evolução de peso. "
        "Tutor só pode ver seus próprios animais."
    ),
)
async def historico_clinico(
    animal_id: uuid.UUID,
    service: AnimalService = Depends(_service),
    current_user: Usuario = Depends(get_current_user),
) -> HistoricoClinicoResponse:
    historico = await service.historico_clinico(animal_id)
    # TUTOR: verificar acesso ao animal
    if current_user.perfil == PerfilUsuario.TUTOR.value:
        _verificar_acesso_animal(current_user, historico.animal)
    return historico


@router.get(
    "/{animal_id}/resumo",
    response_model=EstatisticasAnimalResponse,
    summary="Resumo estatístico do animal",
    description=(
        "Estatísticas agregadas: total de consultas, última consulta, "
        "próxima vacina, total de vacinas, consultas por status e idade."
    ),
)
async def resumo_estatistico(
    animal_id: uuid.UUID,
    service: AnimalService = Depends(_service),
    current_user: Usuario = Depends(get_current_user),
) -> EstatisticasAnimalResponse:
    return await service.resumo_estatistico(animal_id)
