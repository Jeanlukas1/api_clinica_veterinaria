"""
app/services/tutor.py
──────────────────────
TutorService — regras de negócio para a entidade Tutor.

Regras implementadas:
  RN-001: Tutor com animais ativos não pode ser inativado.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditoriaService
from app.core.exceptions import (
    CPFDuplicadoError,
    EmailDuplicadoError,
    TutorComAnimaisAtivosError,
    TutorNaoEncontradoError,
)
from app.models.animal import Animal
from app.models.enums import EventoAuditoria
from app.models.tutor import Tutor
from app.schemas.tutor import TutorCreate, TutorUpdate


class TutorService:
    """
    Serviço de domínio para Tutor.
    Todas as regras de negócio relativas a tutores estão aqui.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit = AuditoriaService(session)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    async def _buscar_ou_404(self, tutor_id: uuid.UUID) -> Tutor:
        """Busca tutor por ID ou lança TutorNaoEncontradoError."""
        stmt = select(Tutor).where(Tutor.id == tutor_id)
        result = await self.session.execute(stmt)
        tutor = result.scalar_one_or_none()
        if not tutor:
            raise TutorNaoEncontradoError(f"Tutor {tutor_id} não encontrado.")
        return tutor

    async def _verificar_cpf_unico(
        self, cpf: str, excluir_id: uuid.UUID | None = None
    ) -> None:
        """Verifica unicidade do CPF. Lança CPFDuplicadoError se duplicado."""
        stmt = select(Tutor).where(Tutor.cpf == cpf)
        if excluir_id:
            stmt = stmt.where(Tutor.id != excluir_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            raise CPFDuplicadoError(f"CPF {cpf} já cadastrado.")

    async def _verificar_email_unico(
        self, email: str, excluir_id: uuid.UUID | None = None
    ) -> None:
        """Verifica unicidade do email. Lança EmailDuplicadoError se duplicado."""
        stmt = select(Tutor).where(Tutor.email == email.lower())
        if excluir_id:
            stmt = stmt.where(Tutor.id != excluir_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            raise EmailDuplicadoError(f"E-mail {email} já cadastrado.")

    async def _contar_animais_ativos(self, tutor_id: uuid.UUID) -> int:
        """Conta animais ativos vinculados ao tutor."""
        stmt = select(func.count(Animal.id)).where(
            Animal.tutor_id == tutor_id,
            Animal.ativo == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ─── CRUD ─────────────────────────────────────────────────────────────────

    async def criar(self, data: TutorCreate, usuario: str) -> Tutor:
        """Cria novo tutor após verificar unicidade de CPF e email."""
        await self._verificar_cpf_unico(data.cpf)
        await self._verificar_email_unico(str(data.email))

        tutor = Tutor(
            nome=data.nome,
            cpf=data.cpf,
            email=str(data.email).lower(),
            telefone=data.telefone,
            criado_por=usuario,
            atualizado_por=usuario,
        )
        self.session.add(tutor)
        await self.session.flush()
        await self.session.refresh(tutor)
        return tutor

    async def listar(
        self,
        limit: int = 20,
        offset: int = 0,
        nome: str | None = None,
        ativo: bool | None = True,
    ) -> tuple[list[Tutor], int]:
        """Lista tutores com filtros e paginação."""
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

    async def buscar_por_id(self, tutor_id: uuid.UUID) -> Tutor:
        """Busca tutor por ID."""
        return await self._buscar_ou_404(tutor_id)

    async def atualizar(
        self, tutor_id: uuid.UUID, data: TutorUpdate, usuario: str
    ) -> Tutor:
        """
        Atualiza dados do tutor.
        RN-001 verificado ao inativar (ativo=False).
        """
        tutor = await self._buscar_ou_404(tutor_id)

        # RN-001: bloquear inativação se há animais ativos
        if data.ativo is False and tutor.ativo:
            qtd_ativos = await self._contar_animais_ativos(tutor_id)
            if qtd_ativos > 0:
                raise TutorComAnimaisAtivosError(
                    details={"animais_ativos": qtd_ativos}
                )
            # Registra auditoria da inativação
            await self.audit.registrar_inativacao(
                entidade="tutores",
                entidade_id=tutor_id,
                usuario=usuario,
                dados_anteriores={"nome": tutor.nome, "ativo": tutor.ativo},
            )

        # Aplica os campos fornecidos
        if data.nome is not None:
            tutor.nome = data.nome
        if data.email is not None:
            await self._verificar_email_unico(str(data.email), excluir_id=tutor_id)
            tutor.email = str(data.email).lower()
        if data.telefone is not None:
            tutor.telefone = data.telefone
        if data.ativo is not None:
            tutor.ativo = data.ativo

        tutor.atualizado_por = usuario
        tutor.atualizado_em = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(tutor)
        return tutor

    async def inativar(self, tutor_id: uuid.UUID, usuario: str) -> Tutor:
        """Inativa tutor via soft delete. Aplica RN-001."""
        data = TutorUpdate(ativo=False)
        return await self.atualizar(tutor_id, data, usuario)
