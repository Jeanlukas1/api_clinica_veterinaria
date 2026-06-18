"""
app/services/transferencia.py
──────────────────────────────
TransferenciaService — regras de negócio para transferência de guarda.

Regras implementadas:
  RN-010: Motivo obrigatório com mínimo 10 caracteres + auditoria obrigatória.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditoriaService
from app.core.exceptions import (
    AnimalNaoEncontradoError,
    TransferenciaMesmoTutorError,
    TutorInativoError,
    TutorNaoEncontradoError,
)
from app.models.animal import Animal
from app.models.enums import EventoAuditoria
from app.models.transferencia_animal import TransferenciaAnimal
from app.models.tutor import Tutor
from app.schemas.transferencia import TransferenciaCreate


class TransferenciaService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit = AuditoriaService(session)

    async def transferir(
        self,
        data: TransferenciaCreate,
        usuario: str,
        ip_address: str | None = None,
    ) -> TransferenciaAnimal:
        """
        Transfere a guarda de um animal de um tutor para outro.

        Ordem de validações:
          1. Animal existe e está ativo
          2. Tutor destino existe e está ativo
          3. Tutor destino é diferente do tutor atual
          4. Cria registro imutável de transferência
          5. Atualiza tutor do animal
          6. Registra auditoria obrigatória (RN-010)
        """
        # 1. Verifica animal
        stmt = select(Animal).where(Animal.id == data.animal_id)
        result = await self.session.execute(stmt)
        animal = result.scalar_one_or_none()
        if not animal:
            raise AnimalNaoEncontradoError("Animal não encontrado.")
        if not animal.ativo:
            raise AnimalNaoEncontradoError("Animal está inativo.")

        # 2. Verifica tutor destino
        stmt = select(Tutor).where(Tutor.id == data.tutor_destino_id)
        result = await self.session.execute(stmt)
        tutor_destino = result.scalar_one_or_none()
        if not tutor_destino:
            raise TutorNaoEncontradoError("Tutor destino não encontrado.")
        if not tutor_destino.ativo:
            raise TutorInativoError("Tutor destino está inativo.")

        # 3. Tutor destino ≠ tutor atual
        if animal.tutor_id == data.tutor_destino_id:
            raise TransferenciaMesmoTutorError()

        tutor_origem_id = animal.tutor_id

        # 4. Cria registro imutável (ANTES de alterar o animal)
        transferencia = TransferenciaAnimal(
            animal_id=data.animal_id,
            tutor_origem_id=tutor_origem_id,
            tutor_destino_id=data.tutor_destino_id,
            motivo=data.motivo,
            criado_por=usuario,
        )
        self.session.add(transferencia)
        await self.session.flush()

        # 5. Atualiza o tutor do animal
        animal.tutor_id = data.tutor_destino_id

        # 6. Auditoria obrigatória (RN-010)
        await self.audit.registrar(
            evento=EventoAuditoria.TRANSFERENCIA_ANIMAL,
            entidade="animais",
            entidade_id=data.animal_id,
            usuario=usuario,
            payload={
                "transferencia_id": str(transferencia.id),
                "tutor_origem_id": str(tutor_origem_id),
                "tutor_destino_id": str(data.tutor_destino_id),
                "motivo": data.motivo,
            },
            ip_address=ip_address,
        )

        await self.session.flush()
        await self.session.refresh(transferencia)
        return transferencia

    async def listar(
        self,
        animal_id: uuid.UUID | None = None,
        tutor_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[TransferenciaAnimal], int]:
        from sqlalchemy import func

        stmt = select(TransferenciaAnimal)
        if animal_id:
            stmt = stmt.where(TransferenciaAnimal.animal_id == animal_id)
        if tutor_id:
            stmt = stmt.where(
                (TransferenciaAnimal.tutor_origem_id == tutor_id)
                | (TransferenciaAnimal.tutor_destino_id == tutor_id)
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(
            TransferenciaAnimal.data_transferencia.desc()
        ).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def buscar_por_id(
        self, transferencia_id: uuid.UUID
    ) -> TransferenciaAnimal:
        stmt = select(TransferenciaAnimal).where(
            TransferenciaAnimal.id == transferencia_id
        )
        result = await self.session.execute(stmt)
        t = result.scalar_one_or_none()
        if not t:
            from app.core.exceptions import TransferenciaNaoEncontradaError
            raise TransferenciaNaoEncontradaError()
        return t
