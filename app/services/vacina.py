"""
app/services/vacina.py
───────────────────────
VacinaService — regras de negócio para a entidade Vacina.

Regras implementadas:
  RN-009: data_aplicacao não pode ser futura (dupla barreira: schema + service)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AnimalNaoEncontradoError,
    ConsultaNaoEncontradaError,
    VacinaNaoEncontradaError,
)
from app.models.animal import Animal
from app.models.consulta import Consulta
from app.models.enums import StatusConsulta
from app.models.vacina import Vacina
from app.schemas.vacina import VacinaCreate, VacinaUpdate


class VacinaService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _buscar_ou_404(self, vacina_id: uuid.UUID) -> Vacina:
        stmt = select(Vacina).where(Vacina.id == vacina_id)
        result = await self.session.execute(stmt)
        vacina = result.scalar_one_or_none()
        if not vacina:
            raise VacinaNaoEncontradaError(f"Vacina {vacina_id} não encontrada.")
        return vacina

    async def criar(self, data: VacinaCreate, usuario: str) -> Vacina:
        """
        Registra nova vacina.
        RN-009: data_aplicacao não futura (validado no schema; revalidado aqui).

        Se consulta_id for fornecido, verifica que a consulta existe e
        está em status compatível (EM_ANDAMENTO ou CONCLUIDA).
        """
        # Verifica animal
        stmt = select(Animal).where(Animal.id == data.animal_id, Animal.ativo == True)
        result = await self.session.execute(stmt)
        if not result.scalar_one_or_none():
            raise AnimalNaoEncontradoError("Animal não encontrado ou inativo.")

        # Verifica consulta se fornecida
        if data.consulta_id:
            stmt = select(Consulta).where(Consulta.id == data.consulta_id)
            result = await self.session.execute(stmt)
            consulta = result.scalar_one_or_none()
            if not consulta:
                raise ConsultaNaoEncontradaError("Consulta não encontrada.")
            if consulta.status not in (
                StatusConsulta.EM_ANDAMENTO.value,
                StatusConsulta.CONCLUIDA.value,
            ):
                raise ConsultaNaoEncontradaError(
                    "Vacinas só podem ser vinculadas a consultas EM_ANDAMENTO ou CONCLUIDA."
                )

        vacina = Vacina(
            animal_id=data.animal_id,
            consulta_id=data.consulta_id,
            nome_vacina=data.nome_vacina,
            lote=data.lote,
            data_aplicacao=data.data_aplicacao,
            data_proxima=data.data_proxima,
            criado_por=usuario,
            atualizado_por=usuario,
        )
        self.session.add(vacina)
        await self.session.flush()
        await self.session.refresh(vacina)
        return vacina

    async def listar(
        self,
        animal_id: uuid.UUID | None = None,
        consulta_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Vacina], int]:
        stmt = select(Vacina)
        if animal_id:
            stmt = stmt.where(Vacina.animal_id == animal_id)
        if consulta_id:
            stmt = stmt.where(Vacina.consulta_id == consulta_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Vacina.data_aplicacao.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def buscar_por_id(self, vacina_id: uuid.UUID) -> Vacina:
        return await self._buscar_ou_404(vacina_id)

    async def atualizar(
        self, vacina_id: uuid.UUID, data: VacinaUpdate, usuario: str
    ) -> Vacina:
        """Atualiza vacina. Revalida datas se alteradas."""
        vacina = await self._buscar_ou_404(vacina_id)

        if data.nome_vacina is not None:
            vacina.nome_vacina = data.nome_vacina
        if data.lote is not None:
            vacina.lote = data.lote
        if data.data_aplicacao is not None:
            vacina.data_aplicacao = data.data_aplicacao
        if data.data_proxima is not None:
            vacina.data_proxima = data.data_proxima

        vacina.atualizado_por = usuario
        vacina.atualizado_em = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(vacina)
        return vacina

    async def remover(self, vacina_id: uuid.UUID) -> None:
        """Remove vacina fisicamente (não é registro imutável)."""
        vacina = await self._buscar_ou_404(vacina_id)
        await self.session.delete(vacina)
        await self.session.flush()
