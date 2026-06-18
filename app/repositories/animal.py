"""
app/repositories/animal.py
───────────────────────────
AnimalRepository — queries para Animal.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.animal import Animal
from app.repositories.base import BaseRepository


class AnimalRepository(BaseRepository[Animal]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Animal, session)

    async def buscar_por_microchip(self, microchip: str) -> Animal | None:
        """Busca animal ativo por microchip (usado para RN-003)."""
        stmt = select(Animal).where(
            Animal.microchip == microchip,
            Animal.ativo == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def contar_ativos_por_tutor(self, tutor_id: uuid.UUID) -> int:
        """Conta animais ativos de um tutor (usado para RN-001)."""
        stmt = select(func.count(Animal.id)).where(
            Animal.tutor_id == tutor_id,
            Animal.ativo == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def listar_com_filtros(
        self,
        nome: str | None = None,
        especie: str | None = None,
        tutor_id: uuid.UUID | None = None,
        ativo: bool | None = True,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Animal], int]:
        stmt = select(Animal)
        if nome:
            stmt = stmt.where(Animal.nome.ilike(f"%{nome}%"))
        if especie:
            stmt = stmt.where(Animal.especie == especie)
        if tutor_id:
            stmt = stmt.where(Animal.tutor_id == tutor_id)
        if ativo is not None:
            stmt = stmt.where(Animal.ativo == ativo)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Animal.nome).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
