"""
app/services/consulta.py
─────────────────────────
ConsultaService — a peça central do sistema.

Regras implementadas:
  RN-004: Veterinário não pode ter consultas sobrepostas (janela de ±30 min)
  RN-005: Consultas não podem ser agendadas no passado (schema + service)
  RN-006: Consultas de emergência ignoram conflito de agenda (geram auditoria)
  RN-007: Diagnóstico obrigatório para concluir consulta (schema + service)
  RN-008: Consultas em estado terminal são imutáveis
  RN-011: Veterinário inativo não pode receber consultas

Máquina de estados:
  AGENDADA → CONFIRMADA → EM_ANDAMENTO → CONCLUÍDA
  AGENDADA → CANCELADA
  CONFIRMADA → CANCELADA
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import AuditoriaService
from app.core.exceptions import (
    AnimalInativoError,
    AnimalNaoEncontradoError,
    ConsultaConflictError,
    ConsultaImutavelError,
    ConsultaNaoEncontradaError,
    DiagnosticoObrigatorioError,
    TransicaoInvalidaError,
    VeterinarioInativoError,
    VeterinarioNaoEncontradoError,
)
from app.models.animal import Animal
from app.models.consulta import Consulta
from app.models.enums import (
    ESTADOS_TERMINAIS,
    EventoAuditoria,
    StatusConsulta,
    TipoConsulta,
)
from app.models.veterinario import Veterinario
from app.schemas.consulta import ConsultaCreate, ConsultaStatusUpdate, ConsultaUpdate

# Janela de conflito de agenda em minutos (RN-004)
JANELA_CONFLITO_MINUTOS = 30


class ConsultaService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit = AuditoriaService(session)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    async def _buscar_ou_404(self, consulta_id: uuid.UUID) -> Consulta:
        stmt = select(Consulta).where(Consulta.id == consulta_id)
        result = await self.session.execute(stmt)
        consulta = result.scalar_one_or_none()
        if not consulta:
            raise ConsultaNaoEncontradaError(f"Consulta {consulta_id} não encontrada.")
        return consulta

    async def _verificar_veterinario(self, vet_id: uuid.UUID) -> Veterinario:
        """Verifica que o veterinário existe e está ativo (RN-011)."""
        stmt = select(Veterinario).where(Veterinario.id == vet_id)
        result = await self.session.execute(stmt)
        vet = result.scalar_one_or_none()
        if not vet:
            raise VeterinarioNaoEncontradoError()
        if not vet.ativo:
            raise VeterinarioInativoError()
        return vet

    async def _verificar_animal(self, animal_id: uuid.UUID) -> Animal:
        """Verifica que o animal existe e está ativo."""
        stmt = select(Animal).where(Animal.id == animal_id)
        result = await self.session.execute(stmt)
        animal = result.scalar_one_or_none()
        if not animal:
            raise AnimalNaoEncontradoError()
        if not animal.ativo:
            raise AnimalInativoError()
        return animal

    async def _verificar_conflito_agenda(
        self,
        veterinario_id: uuid.UUID,
        data_hora: datetime,
        excluir_id: uuid.UUID | None = None,
    ) -> bool:
        """
        RN-004: Verifica se o veterinário já tem consulta dentro da janela de ±30 min.
        Retorna True se há conflito.
        Exclui estados terminais (CONCLUIDA, CANCELADA) da verificação.
        """
        inicio = data_hora - timedelta(minutes=JANELA_CONFLITO_MINUTOS)
        fim = data_hora + timedelta(minutes=JANELA_CONFLITO_MINUTOS)

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

    # ─── CRUD ─────────────────────────────────────────────────────────────────

    async def criar(
        self,
        data: ConsultaCreate,
        usuario: str,
        ip_address: str | None = None,
    ) -> Consulta:
        """
        Agenda nova consulta.

        Aplica (na ordem):
          1. RN-011: veterinário deve estar ativo
          2. RN-005: data_hora não pode ser passado (exceto emergência)
          3. RN-004: sem sobreposição de agenda (exceto emergência — RN-006)
        """
        # RN-011: veterinário ativo
        await self._verificar_veterinario(data.veterinario_id)

        # RN-005: data passada (schema já bloqueia para não-emergência;
        # service revalida para garantia)
        agora = datetime.now(timezone.utc)
        data_hora_utc = data.data_hora
        if data_hora_utc.tzinfo is None:
            data_hora_utc = data_hora_utc.replace(tzinfo=timezone.utc)

        if data_hora_utc < agora and data.tipo != TipoConsulta.EMERGENCIA:
            raise ConsultaNaoEncontradaError(
                "data_hora não pode ser no passado para consultas não-emergenciais."
            )

        # RN-004 / RN-006: conflito de agenda
        tem_conflito = await self._verificar_conflito_agenda(
            data.veterinario_id, data_hora_utc
        )
        if tem_conflito:
            if data.tipo != TipoConsulta.EMERGENCIA:
                raise ConsultaConflictError(
                    details={
                        "veterinario_id": str(data.veterinario_id),
                        "data_hora": data_hora_utc.isoformat(),
                        "janela_minutos": JANELA_CONFLITO_MINUTOS,
                    }
                )
            # RN-006: emergência — permite, mas registra auditoria
            await self.audit.registrar(
                evento=EventoAuditoria.EMERGENCIA_SOBREPOSTA,
                entidade="consultas",
                entidade_id=uuid.uuid4(),  # ID provisório — será atualizado
                usuario=usuario,
                payload={
                    "veterinario_id": str(data.veterinario_id),
                    "data_hora": data_hora_utc.isoformat(),
                },
                ip_address=ip_address,
            )

        # Verifica animal ativo
        await self._verificar_animal(data.animal_id)

        consulta = Consulta(
            animal_id=data.animal_id,
            veterinario_id=data.veterinario_id,
            data_hora=data_hora_utc,
            status=StatusConsulta.AGENDADA.value,
            tipo=data.tipo.value,
            observacoes=data.observacoes,
            criado_por=usuario,
            atualizado_por=usuario,
        )
        self.session.add(consulta)
        await self.session.flush()
        await self.session.refresh(consulta)
        return consulta

    async def listar(
        self,
        limit: int = 20,
        offset: int = 0,
        animal_id: uuid.UUID | None = None,
        veterinario_id: uuid.UUID | None = None,
        status: str | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
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

    async def buscar_por_id(self, consulta_id: uuid.UUID) -> Consulta:
        return await self._buscar_ou_404(consulta_id)

    async def atualizar(
        self,
        consulta_id: uuid.UUID,
        data: ConsultaUpdate,
        usuario: str,
    ) -> Consulta:
        """
        Atualiza campos editáveis da consulta.
        RN-008: bloqueia qualquer atualização em estado terminal.
        """
        consulta = await self._buscar_ou_404(consulta_id)

        # RN-008: estado terminal é imutável
        if consulta.is_terminal:
            raise ConsultaImutavelError(
                details={"status_atual": consulta.status}
            )

        if data.observacoes is not None:
            consulta.observacoes = data.observacoes
        if data.veterinario_id is not None:
            await self._verificar_veterinario(data.veterinario_id)
            # Verifica conflito no novo horário
            data_hora = consulta.data_hora
            if data.data_hora:
                data_hora = data.data_hora
            tem_conflito = await self._verificar_conflito_agenda(
                data.veterinario_id, data_hora, excluir_id=consulta_id
            )
            if tem_conflito:
                raise ConsultaConflictError()
            consulta.veterinario_id = data.veterinario_id
        if data.data_hora is not None:
            tem_conflito = await self._verificar_conflito_agenda(
                consulta.veterinario_id, data.data_hora, excluir_id=consulta_id
            )
            if tem_conflito:
                raise ConsultaConflictError()
            consulta.data_hora = data.data_hora

        consulta.atualizado_por = usuario
        consulta.atualizado_em = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(consulta)
        return consulta

    async def mudar_status(
        self,
        consulta_id: uuid.UUID,
        data: ConsultaStatusUpdate,
        usuario: str,
        ip_address: str | None = None,
    ) -> Consulta:
        """
        Aplica transição de estado da máquina de estados.

        RN-007: diagnóstico obrigatório para CONCLUIDA (já validado no schema,
                revalidado aqui como segunda barreira)
        RN-008: estado terminal bloqueia qualquer transição
        Máquina de estados: valida via Consulta.pode_transicionar_para()
        """
        consulta = await self._buscar_ou_404(consulta_id)

        # RN-008: estado terminal é imutável
        if consulta.is_terminal:
            raise ConsultaImutavelError(
                details={"status_atual": consulta.status}
            )

        novo_status = data.status

        # Valida transição pela máquina de estados do model
        if not consulta.pode_transicionar_para(novo_status):
            raise TransicaoInvalidaError(
                f"Transição {consulta.status} → {novo_status.value} não é permitida.",
                details={
                    "status_atual": consulta.status,
                    "status_solicitado": novo_status.value,
                    "transicoes_validas": [
                        s.value for s in
                        __import__("app.models.enums", fromlist=["TRANSICOES_VALIDAS"])
                        .TRANSICOES_VALIDAS.get(consulta.status_enum, [])
                    ],
                },
            )

        # RN-007: diagnóstico obrigatório ao concluir (segunda barreira)
        if novo_status == StatusConsulta.CONCLUIDA:
            diagnostico = data.diagnostico or consulta.diagnostico
            if not diagnostico or not diagnostico.strip():
                raise DiagnosticoObrigatorioError()
            consulta.diagnostico = diagnostico

        # Aplica a transição
        consulta.status = novo_status.value
        consulta.atualizado_por = usuario
        consulta.atualizado_em = datetime.now(timezone.utc)

        # Registra auditoria para eventos críticos
        if novo_status == StatusConsulta.CANCELADA:
            await self.audit.registrar(
                evento=EventoAuditoria.CANCELAMENTO_CONSULTA,
                entidade="consultas",
                entidade_id=consulta_id,
                usuario=usuario,
                payload={"status_anterior": consulta.status},
                ip_address=ip_address,
            )
        elif novo_status == StatusConsulta.CONCLUIDA:
            await self.audit.registrar(
                evento=EventoAuditoria.CONCLUSAO_CONSULTA,
                entidade="consultas",
                entidade_id=consulta_id,
                usuario=usuario,
                payload={"diagnostico": consulta.diagnostico},
                ip_address=ip_address,
            )

        await self.session.flush()
        await self.session.refresh(consulta)
        return consulta

    async def agenda_veterinario(
        self,
        veterinario_id: uuid.UUID,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        limit: int = 50,
    ) -> list[Consulta]:
        """Retorna a agenda de um veterinário em um período."""
        stmt = (
            select(Consulta)
            .where(
                Consulta.veterinario_id == veterinario_id,
                Consulta.status.notin_(
                    [StatusConsulta.CANCELADA.value]
                ),
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
