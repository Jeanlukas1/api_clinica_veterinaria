"""app/routers/vacinas.py — Stub (implementação completa na ETAPA 8)"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Listar vacinas [ETAPA 8]")
async def listar_vacinas(animal_id: str | None = None):
    return {"detail": "Implementação na ETAPA 8"}


@router.post("/", status_code=201, summary="Registrar vacina [ETAPA 8]")
async def criar_vacina():
    return {"detail": "Implementação na ETAPA 8"}


@router.get("/{vacina_id}", summary="Buscar vacina [ETAPA 8]")
async def buscar_vacina(vacina_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.patch("/{vacina_id}", summary="Atualizar vacina [ETAPA 8]")
async def atualizar_vacina(vacina_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.delete("/{vacina_id}", status_code=204, summary="Remover vacina [ETAPA 8]")
async def remover_vacina(vacina_id: str):
    return None
