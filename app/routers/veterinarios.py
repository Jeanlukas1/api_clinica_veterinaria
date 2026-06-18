"""app/routers/veterinarios.py — Stub (implementação completa na ETAPA 8)"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Listar veterinários [ETAPA 8]")
async def listar_veterinarios():
    return {"detail": "Implementação na ETAPA 8"}


@router.post("/", status_code=201, summary="Cadastrar veterinário [ETAPA 8]")
async def criar_veterinario():
    return {"detail": "Implementação na ETAPA 8"}


@router.get("/{veterinario_id}", summary="Buscar veterinário [ETAPA 8]")
async def buscar_veterinario(veterinario_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.patch("/{veterinario_id}", summary="Atualizar veterinário [ETAPA 8]")
async def atualizar_veterinario(veterinario_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.delete("/{veterinario_id}", status_code=204, summary="Inativar veterinário [ETAPA 8]")
async def inativar_veterinario(veterinario_id: str):
    return None


@router.get("/{veterinario_id}/agenda", summary="Agenda do veterinário [ETAPA 8]")
async def agenda_veterinario(veterinario_id: str):
    return {"detail": "Implementação na ETAPA 8"}
