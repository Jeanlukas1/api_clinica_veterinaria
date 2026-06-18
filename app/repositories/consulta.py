"""
app/repositories/consulta.py
─────────────────────────────
ConsultaRepository — queries para Consulta.
Inclui verificação de conflito de agenda (RN-004).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.consulta import Consulta
from app.models.enums import ESTADOS_TERMINAIS
from app.repositories.base import BaseRepository


class ConsultaRepository(BaseRepository[Consulta]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Consulta, session)

    async def verificar_conflito(
        self,
        veterinario_id: uuid.UUID,
        data_hora: datetime,
        janela_minutos: int = 30,
        excluir_id: uuid.UUID | None = None,
    ) -> bool:
        """
        RN-004: verifica se existe consulta ativa dentro da janela de conflito.
        Consultas CONCLUIDA ou CANCELADA não são consideradas.
        """
        inicio = data_hora - timedelta(minutes=janela_minutos)
        fim = data_hora + timedelta(minutes=janela_minutos)
        estados_terminais = [s.value for s in ESTADOS_TERMINAIS]

        stmt = select(Consulta).where(
            Consulta.veterinario_id == veterinario_id,
            Consulta.data_hora >= inicio,
            Consulta.data_hora <= fim,
            Consulta.status.notin_(estados_terminais),
        )
        if excluir_id:
            stmt = stmt.where(Consulta.id != excluir_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def historico_por_animal(
        self,
        animal_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Consulta]:
        """Retorna consultas de um animal ordenadas por data (mais recentes primeiro)."""
        stmt = (
            select(Consulta)
            .where(Consulta.animal_id == animal_id)
            .options(selectinload(Consulta.veterinario))
            .order_by(Consulta.data_hora.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def agenda_veterinario(
        self,
        veterinario_id: uuid.UUID,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        limit: int = 50,
    ) -> list[Consulta]:
        estados_terminais = [s.value for s in ESTADOS_TERMINAIS]
        stmt = (
            select(Consulta)
            .where(
                Consulta.veterinario_id == veterinario_id,
                Consulta.status.notin_(estados_terminais),
            )
            .options(selectinload(Consulta.animal))
            .order_by(Consulta.data_hora.asc())
            .limit(limit)
        )
        if data_inicio:
            stmt = stmt.where(Consulta.data_hora >= data_inicio)
        if data_fim:
            stmt = stmt.where(Consulta.data_hora <= data_fim)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def listar_com_filtros(
        self,
        animal_id: uuid.UUID | None = None,
        veterinario_id: uuid.UUID | None = None,
        status: str | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Consulta], int]:
        stmt = select(Consulta)
        if animal_id:
            stmt = stmt.where(Consulta.animal_id == animal_id)
        if veterinario_id:
            stmt = stmt.where(Consulta.veterinario_id == veterinario_id)
        if status:
            stmt = stmt.where(Consulta.status == status)
        if data_inicio:
            stmt = stmt.where(Consulta.data_hora >= data_inicio)
        if data_fim:
            stmt = stmt.where(Consulta.data_hora <= data_fim)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Consulta.data_hora.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
