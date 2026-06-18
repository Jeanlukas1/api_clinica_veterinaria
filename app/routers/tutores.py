"""
app/routers/tutores.py — Stub (implementação completa na ETAPA 8)
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Listar tutores [ETAPA 8]")
async def listar_tutores():
    return {"detail": "Implementação na ETAPA 8"}


@router.post("/", status_code=201, summary="Criar tutor [ETAPA 8]")
async def criar_tutor():
    return {"detail": "Implementação na ETAPA 8"}


@router.get("/{tutor_id}", summary="Buscar tutor [ETAPA 8]")
async def buscar_tutor(tutor_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.patch("/{tutor_id}", summary="Atualizar tutor [ETAPA 8]")
async def atualizar_tutor(tutor_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.delete("/{tutor_id}", status_code=204, summary="Inativar tutor [ETAPA 8]")
async def inativar_tutor(tutor_id: str):
    return None
