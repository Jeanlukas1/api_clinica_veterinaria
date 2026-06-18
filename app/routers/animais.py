"""app/routers/animais.py — Stub (implementação completa na ETAPA 8)"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Listar animais com filtros [ETAPA 8]")
async def listar_animais(
    nome: str | None = None,
    especie: str | None = None,
    tutor_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    return {"detail": "Implementação na ETAPA 8"}


@router.post("/", status_code=201, summary="Cadastrar animal [ETAPA 8]")
async def criar_animal():
    return {"detail": "Implementação na ETAPA 8"}


@router.get("/{animal_id}", summary="Buscar animal [ETAPA 8]")
async def buscar_animal(animal_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.patch("/{animal_id}", summary="Atualizar animal [ETAPA 8]")
async def atualizar_animal(animal_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.delete("/{animal_id}", status_code=204, summary="Inativar animal [ETAPA 8]")
async def inativar_animal(animal_id: str):
    return None


@router.get("/{animal_id}/historico", summary="Histórico clínico consolidado [ETAPA 8]")
async def historico_clinico(animal_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.get("/{animal_id}/resumo", summary="Resumo estatístico [ETAPA 8]")
async def resumo_estatistico(animal_id: str):
    return {"detail": "Implementação na ETAPA 8"}
