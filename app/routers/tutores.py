"""
app/routers/tutores.py
───────────────────────
Endpoints de Tutores — implementação completa (ETAPA 8).
Sem lógica de negócio: apenas recebe HTTP → valida schema → delega ao service.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_perfil, require_staff
from app.database.session import get_db
from app.models.enums import PerfilUsuario
from app.models.usuario import Usuario
from app.schemas.animal import AnimalResumoResponse
from app.schemas.common import PaginatedResponse
from app.schemas.tutor import TutorCreate, TutorResponse, TutorUpdate
from app.services.animal import AnimalService
from app.services.tutor import TutorService

router = APIRouter()


def _tutor_service(session: AsyncSession = Depends(get_db)) -> TutorService:
    return TutorService(session)


def _animal_service(session: AsyncSession = Depends(get_db)) -> AnimalService:
    return AnimalService(session)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=PaginatedResponse[TutorResponse],
    summary="Listar tutores",
    description="Lista tutores com paginação e filtro por nome. Exclui inativos por padrão.",
)
async def listar_tutores(
    nome: str | None = Query(None, description="Filtro por nome (parcial)"),
    ativo: bool | None = Query(True, description="Filtrar por status ativo"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: TutorService = Depends(_tutor_service),
    _: Usuario = Depends(require_staff()),
) -> PaginatedResponse[TutorResponse]:
    items, total = await service.listar(limit=limit, offset=offset, nome=nome, ativo=ativo)
    return PaginatedResponse(
        items=[TutorResponse.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/",
    response_model=TutorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar tutor",
    description="Cadastra novo tutor. Valida CPF (dígitos verificadores) e unicidade de CPF/email.",
)
async def criar_tutor(
    data: TutorCreate,
    service: TutorService = Depends(_tutor_service),
    current_user: Usuario = Depends(
        require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.RECEPCIONISTA)
    ),
) -> TutorResponse:
    tutor = await service.criar(data, usuario=current_user.email)
    return TutorResponse.model_validate(tutor)


@router.get(
    "/{tutor_id}",
    response_model=TutorResponse,
    summary="Buscar tutor por ID",
)
async def buscar_tutor(
    tutor_id: uuid.UUID,
    service: TutorService = Depends(_tutor_service),
    _: Usuario = Depends(require_staff()),
) -> TutorResponse:
    tutor = await service.buscar_por_id(tutor_id)
    return TutorResponse.model_validate(tutor)


@router.patch(
    "/{tutor_id}",
    response_model=TutorResponse,
    summary="Atualizar tutor",
    description=(
        "Atualiza campos do tutor. "
        "Para inativar (ativo=false), verifica RN-001: sem animais ativos."
    ),
)
async def atualizar_tutor(
    tutor_id: uuid.UUID,
    data: TutorUpdate,
    service: TutorService = Depends(_tutor_service),
    current_user: Usuario = Depends(
        require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.RECEPCIONISTA)
    ),
) -> TutorResponse:
    tutor = await service.atualizar(tutor_id, data, usuario=current_user.email)
    return TutorResponse.model_validate(tutor)


@router.delete(
    "/{tutor_id}",
    status_code=status.HTTP_200_OK,
    summary="Inativar tutor",
    description="Soft delete: define ativo=false. Aplica RN-001.",
)
async def inativar_tutor(
    tutor_id: uuid.UUID,
    service: TutorService = Depends(_tutor_service),
    current_user: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN)),
) -> dict:
    await service.inativar(tutor_id, usuario=current_user.email)
    return {"message": "Tutor inativado com sucesso."}


@router.get(
    "/{tutor_id}/animais",
    response_model=PaginatedResponse[AnimalResumoResponse],
    summary="Listar animais do tutor",
)
async def listar_animais_tutor(
    tutor_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    animal_service: AnimalService = Depends(_animal_service),
    current_user: Usuario = Depends(get_current_user),
) -> PaginatedResponse[AnimalResumoResponse]:
    # TUTOR só pode ver seus próprios animais
    if current_user.perfil == PerfilUsuario.TUTOR.value:
        if not current_user.tutor_id or current_user.tutor_id != tutor_id:
            from app.core.exceptions import AcessoNegadoError
            raise AcessoNegadoError("Tutores só podem visualizar seus próprios animais.")

    items, total = await animal_service.listar(
        tutor_id=tutor_id, limit=limit, offset=offset
    )
    return PaginatedResponse(
        items=[AnimalResumoResponse.model_validate(a) for a in items],
        total=total,
        limit=limit,
        offset=offset,
    )
