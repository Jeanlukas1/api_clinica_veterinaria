"""
app/repositories/tutor.py
──────────────────────────
TutorRepository — queries SQLAlchemy 2.0 para a entidade Tutor.
Sem lógica de negócio. Apenas acesso ao banco.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tutor import Tutor
from app.repositories.base import BaseRepository


class TutorRepository(BaseRepository[Tutor]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Tutor, session)

    async def buscar_por_cpf(self, cpf: str) -> Tutor | None:
        stmt = select(Tutor).where(Tutor.cpf == cpf)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def buscar_por_email(self, email: str) -> Tutor | None:
        stmt = select(Tutor).where(Tutor.email == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def listar_com_filtros(
        self,
        nome: str | None = None,
        ativo: bool | None = True,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Tutor], int]:
        stmt = select(Tutor)
        if nome:
            stmt = stmt.where(Tutor.nome.ilike(f"%{nome}%"))
        if ativo is not None:
            stmt = stmt.where(Tutor.ativo == ativo)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Tutor.nome).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
