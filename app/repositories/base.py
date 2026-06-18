"""
app/repositories/base.py
─────────────────────────
BaseRepository genérico com operações CRUD comuns.
Todos os repositories específicos herdam desta classe.
Implementação completa na ETAPA 7.
"""
from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Repository base com operações CRUD genéricas.

    Uso:
        class TutorRepository(BaseRepository[Tutor]):
            def __init__(self, session: AsyncSession):
                super().__init__(Tutor, session)
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        """Busca por ID. Retorna None se não encontrado."""
        stmt = select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ModelType], int]:
        """Lista todos os registros com paginação. Retorna (items, total)."""
        count_stmt = select(func.count()).select_from(self.model)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def create(self, obj: ModelType) -> ModelType:
        """Persiste um novo objeto e retorna o objeto atualizado."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: ModelType) -> ModelType:
        """Persiste alterações em um objeto existente."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, obj: ModelType) -> ModelType:
        """Soft delete: define ativo=False."""
        obj.ativo = False  # type: ignore[attr-defined]
        return await self.update(obj)
