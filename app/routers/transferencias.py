"""app/routers/transferencias.py — Stub (implementação completa na ETAPA 8)"""
from fastapi import APIRouter

router = APIRouter()


@router.post(
    "/",
    status_code=201,
    summary="Transferir animal entre tutores [ETAPA 8]",
    description="Transfere a guarda de um animal. Exige motivo (RN-010) e gera auditoria obrigatória.",
)
async def transferir_animal():
    return {"detail": "Implementação na ETAPA 8"}


@router.get("/", summary="Listar transferências [ETAPA 8]")
async def listar_transferencias():
    return {"detail": "Implementação na ETAPA 8"}


@router.get("/{transferencia_id}", summary="Buscar transferência [ETAPA 8]")
async def buscar_transferencia(transferencia_id: str):
    return {"detail": "Implementação na ETAPA 8"}
