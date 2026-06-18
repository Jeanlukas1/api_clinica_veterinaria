"""app/routers/consultas.py — Stub (implementação completa na ETAPA 8)"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Listar consultas [ETAPA 8]")
async def listar_consultas():
    return {"detail": "Implementação na ETAPA 8"}


@router.post("/", status_code=201, summary="Agendar consulta [ETAPA 8]")
async def criar_consulta():
    return {"detail": "Implementação na ETAPA 8"}


@router.get("/{consulta_id}", summary="Buscar consulta [ETAPA 8]")
async def buscar_consulta(consulta_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.patch("/{consulta_id}", summary="Atualizar consulta [ETAPA 8]")
async def atualizar_consulta(consulta_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.patch(
    "/{consulta_id}/status",
    summary="Transição de estado — Máquina de estados [ETAPA 8]",
    description="Aplica transição de status (AGENDADA→CONFIRMADA→EM_ANDAMENTO→CONCLUIDA / CANCELADA). Valida RN-007 e RN-008.",
)
async def mudar_status_consulta(consulta_id: str):
    return {"detail": "Implementação na ETAPA 8"}


@router.delete("/{consulta_id}", status_code=204, summary="Cancelar consulta [ETAPA 8]")
async def cancelar_consulta(consulta_id: str):
    return None
