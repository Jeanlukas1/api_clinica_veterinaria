"""
app/services/veterinario.py
────────────────────────────
VeterinarioService — regras de negócio para a entidade Veterinário.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditoriaService
from app.core.exceptions import (
    CRMVDuplicadoError,
    VeterinarioNaoEncontradoError,
)
from app.models.veterinario import Veterinario
from app.schemas.veterinario import VeterinarioCreate, VeterinarioUpdate


class VeterinarioService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit = AuditoriaService(session)

    async def _buscar_ou_404(self, vet_id: uuid.UUID) -> Veterinario:
        stmt = select(Veterinario).where(Veterinario.id == vet_id)
        result = await self.session.execute(stmt)
        vet = result.scalar_one_or_none()
        if not vet:
            raise VeterinarioNaoEncontradoError(f"Veterinário {vet_id} não encontrado.")
        return vet

    async def _verificar_crmv_unico(
        self, crmv: str, excluir_id: uuid.UUID | None = None
    ) -> None:
        stmt = select(Veterinario).where(Veterinario.crmv == crmv)
        if excluir_id:
            stmt = stmt.where(Veterinario.id != excluir_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            raise CRMVDuplicadoError(f"CRMV {crmv} já cadastrado.")

    async def criar(self, data: VeterinarioCreate, usuario: str) -> Veterinario:
        await self._verificar_crmv_unico(data.crmv)

        vet = Veterinario(
            nome=data.nome,
            crmv=data.crmv,
            especialidade=data.especialidade.value,
            criado_por=usuario,
            atualizado_por=usuario,
        )
        self.session.add(vet)
        await self.session.flush()
        await self.session.refresh(vet)
        return vet

    async def listar(
        self,
        limit: int = 20,
        offset: int = 0,
        nome: str | None = None,
        especialidade: str | None = None,
        ativo: bool | None = True,
    ) -> tuple[list[Veterinario], int]:
        stmt = select(Veterinario)
        if nome:
            stmt = stmt.where(Veterinario.nome.ilike(f"%{nome}%"))
        if especialidade:
            stmt = stmt.where(Veterinario.especialidade == especialidade)
        if ativo is not None:
            stmt = stmt.where(Veterinario.ativo == ativo)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Veterinario.nome).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def buscar_por_id(self, vet_id: uuid.UUID) -> Veterinario:
        return await self._buscar_ou_404(vet_id)

    async def atualizar(
        self, vet_id: uuid.UUID, data: VeterinarioUpdate, usuario: str
    ) -> Veterinario:
        vet = await self._buscar_ou_404(vet_id)

        if data.nome is not None:
            vet.nome = data.nome
        if data.especialidade is not None:
            vet.especialidade = data.especialidade.value
        if data.ativo is not None:
            if data.ativo is False and vet.ativo:
                await self.audit.registrar_inativacao(
                    entidade="veterinarios",
                    entidade_id=vet_id,
                    usuario=usuario,
                    dados_anteriores={"nome": vet.nome, "crmv": vet.crmv},
                )
            vet.ativo = data.ativo

        vet.atualizado_por = usuario
        vet.atualizado_em = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(vet)
        return vet

    async def inativar(self, vet_id: uuid.UUID, usuario: str) -> Veterinario:
        return await self.atualizar(vet_id, VeterinarioUpdate(ativo=False), usuario)
