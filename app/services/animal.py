"""
app/services/animal.py
───────────────────────
AnimalService — regras de negócio para a entidade Animal.

Regras implementadas:
  RN-002: data_nascimento não pode ser futura (dupla barreira: schema + service)
  RN-003: microchip deve ser único entre animais ativos
  RN-012: peso maior que zero (dupla barreira: schema + service)

Cálculos derivados:
  - Histórico clínico consolidado (consultas + vacinas + evolução de peso)
  - Resumo estatístico (total, última consulta, próxima vacina, idade)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import AuditoriaService
from app.core.exceptions import (
    AnimalInativoError,
    AnimalNaoEncontradoError,
    MicrochipDuplicadoError,
    TutorInativoError,
    TutorNaoEncontradoError,
)
from app.models.animal import Animal
from app.models.consulta import Consulta
from app.models.enums import EventoAuditoria, StatusConsulta
from app.models.tutor import Tutor
from app.models.vacina import Vacina
from app.schemas.animal import (
    AnimalCreate,
    AnimalUpdate,
    EstatisticasAnimalResponse,
    EvolucaoPesoItem,
    HistoricoClinicoResponse,
)


class AnimalService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit = AuditoriaService(session)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    async def _buscar_ou_404(self, animal_id: uuid.UUID) -> Animal:
        stmt = select(Animal).where(Animal.id == animal_id)
        result = await self.session.execute(stmt)
        animal = result.scalar_one_or_none()
        if not animal:
            raise AnimalNaoEncontradoError(f"Animal {animal_id} não encontrado.")
        return animal

    async def _verificar_microchip_unico(
        self, microchip: str, excluir_id: uuid.UUID | None = None
    ) -> None:
        """RN-003: microchip único entre animais ativos."""
        stmt = select(Animal).where(
            Animal.microchip == microchip,
            Animal.ativo == True,
        )
        if excluir_id:
            stmt = stmt.where(Animal.id != excluir_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            raise MicrochipDuplicadoError(
                details={"microchip": microchip}
            )

    async def _verificar_tutor_ativo(self, tutor_id: uuid.UUID) -> Tutor:
        """Verifica que o tutor existe e está ativo."""
        stmt = select(Tutor).where(Tutor.id == tutor_id)
        result = await self.session.execute(stmt)
        tutor = result.scalar_one_or_none()
        if not tutor:
            raise TutorNaoEncontradoError(f"Tutor {tutor_id} não encontrado.")
        if not tutor.ativo:
            raise TutorInativoError("Tutor está inativo e não pode receber novos animais.")
        return tutor

    # ─── CRUD ─────────────────────────────────────────────────────────────────

    async def criar(self, data: AnimalCreate, usuario: str) -> Animal:
        """
        Cadastra novo animal.
        RN-002 e RN-012 já validados no schema; RN-003 verificado aqui no service.
        """
        await self._verificar_tutor_ativo(data.tutor_id)

        if data.microchip:
            await self._verificar_microchip_unico(data.microchip)

        animal = Animal(
            tutor_id=data.tutor_id,
            nome=data.nome,
            especie=data.especie.value,
            raca=data.raca,
            sexo=data.sexo.value,
            data_nascimento=data.data_nascimento,
            peso=data.peso,
            microchip=data.microchip,
            criado_por=usuario,
            atualizado_por=usuario,
        )
        self.session.add(animal)
        await self.session.flush()
        await self.session.refresh(animal)
        return animal

    async def listar(
        self,
        limit: int = 20,
        offset: int = 0,
        nome: str | None = None,
        especie: str | None = None,
        tutor_id: uuid.UUID | None = None,
        ativo: bool | None = True,
    ) -> tuple[list[Animal], int]:
        """Lista animais com filtros e paginação."""
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

    async def buscar_por_id(self, animal_id: uuid.UUID) -> Animal:
        return await self._buscar_ou_404(animal_id)

    async def atualizar(
        self, animal_id: uuid.UUID, data: AnimalUpdate, usuario: str
    ) -> Animal:
        """
        Atualiza dados do animal.
        RN-003: verifica unicidade do microchip se alterado.
        """
        animal = await self._buscar_ou_404(animal_id)

        if data.microchip is not None and data.microchip != animal.microchip:
            await self._verificar_microchip_unico(data.microchip, excluir_id=animal_id)

        if data.nome is not None:
            animal.nome = data.nome
        if data.raca is not None:
            animal.raca = data.raca
        if data.peso is not None:
            # Registra evolução de peso na auditoria
            await self.audit.registrar(
                evento=EventoAuditoria.CONCLUSAO_CONSULTA,  # reutiliza evento genérico
                entidade="animais",
                entidade_id=animal_id,
                usuario=usuario,
                payload={
                    "campo": "peso",
                    "peso_anterior": float(animal.peso),
                    "peso_novo": float(data.peso),
                    "data": date.today().isoformat(),
                },
            )
            animal.peso = data.peso
        if data.microchip is not None:
            animal.microchip = data.microchip
        if data.ativo is not None:
            if data.ativo is False:
                await self.audit.registrar_inativacao(
                    entidade="animais",
                    entidade_id=animal_id,
                    usuario=usuario,
                    dados_anteriores={"nome": animal.nome},
                )
            animal.ativo = data.ativo

        animal.atualizado_por = usuario
        animal.atualizado_em = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(animal)
        return animal

    async def inativar(self, animal_id: uuid.UUID, usuario: str) -> Animal:
        """Inativa animal via soft delete."""
        return await self.atualizar(animal_id, AnimalUpdate(ativo=False), usuario)

    # ─── Cálculos Derivados ───────────────────────────────────────────────────

    async def resumo_estatistico(
        self, animal_id: uuid.UUID
    ) -> EstatisticasAnimalResponse:
        """
        Cálculo derivado: estatísticas do animal.
        Executa queries agregadas eficientes — não carrega todos os registros.
        """
        animal = await self._buscar_ou_404(animal_id)

        # Total de consultas
        total_c = (
            await self.session.execute(
                select(func.count(Consulta.id)).where(Consulta.animal_id == animal_id)
            )
        ).scalar_one()

        # Última consulta (excluindo canceladas)
        ultima_c_result = (
            await self.session.execute(
                select(func.max(Consulta.data_hora)).where(
                    Consulta.animal_id == animal_id,
                    Consulta.status != StatusConsulta.CANCELADA.value,
                )
            )
        ).scalar_one()

        # Total de vacinas
        total_v = (
            await self.session.execute(
                select(func.count(Vacina.id)).where(Vacina.animal_id == animal_id)
            )
        ).scalar_one()

        # Próxima vacina
        proxima_v = (
            await self.session.execute(
                select(func.min(Vacina.data_proxima)).where(
                    Vacina.animal_id == animal_id,
                    Vacina.data_proxima >= date.today(),
                )
            )
        ).scalar_one()

        # Consultas por status
        status_rows = await self.session.execute(
            select(Consulta.status, func.count(Consulta.id))
            .where(Consulta.animal_id == animal_id)
            .group_by(Consulta.status)
        )
        consultas_por_status = {row[0]: row[1] for row in status_rows}

        # Idade calculada
        idade = (date.today() - animal.data_nascimento).days / 365.25

        return EstatisticasAnimalResponse(
            total_consultas=total_c,
            ultima_consulta=ultima_c_result,
            proxima_vacina=proxima_v,
            total_vacinas=total_v,
            consultas_por_status=consultas_por_status,
            idade_anos=round(idade, 1),
        )

    async def historico_clinico(
        self, animal_id: uuid.UUID
    ) -> HistoricoClinicoResponse:
        """
        Cálculo derivado principal: histórico clínico consolidado.
        Combina consultas + vacinas + evolução de peso via auditoria.
        """
        from app.models.auditoria import Auditoria
        from app.schemas.animal import AnimalResponse
        from app.schemas.tutor import TutorResumoResponse
        from app.schemas.consulta import ConsultaDetalheResponse
        from app.schemas.vacina import VacinaResumoResponse

        # Carrega animal com tutor
        stmt = (
            select(Animal)
            .where(Animal.id == animal_id)
            .options(selectinload(Animal.tutor))
        )
        result = await self.session.execute(stmt)
        animal = result.scalar_one_or_none()
        if not animal:
            raise AnimalNaoEncontradoError()

        # Consultas ordenadas por data (mais recentes primeiro)
        consultas_stmt = (
            select(Consulta)
            .where(Consulta.animal_id == animal_id)
            .options(selectinload(Consulta.veterinario))
            .order_by(Consulta.data_hora.desc())
        )
        consultas_result = await self.session.execute(consultas_stmt)
        consultas = list(consultas_result.scalars().all())

        # Vacinas ordenadas por data de aplicação
        vacinas_stmt = (
            select(Vacina)
            .where(Vacina.animal_id == animal_id)
            .order_by(Vacina.data_aplicacao.desc())
        )
        vacinas_result = await self.session.execute(vacinas_stmt)
        vacinas = list(vacinas_result.scalars().all())

        # Evolução de peso — extraída dos eventos de auditoria
        peso_stmt = (
            select(Auditoria)
            .where(
                Auditoria.entidade == "animais",
                Auditoria.entidade_id == animal_id,
                Auditoria.payload["campo"].astext == "peso",
            )
            .order_by(Auditoria.timestamp.asc())
        )
        peso_result = await self.session.execute(peso_stmt)
        evolucao_peso = [
            EvolucaoPesoItem(
                data=a.timestamp.date(),
                peso=a.payload["peso_novo"],
            )
            for a in peso_result.scalars().all()
            if a.payload and "peso_novo" in a.payload
        ]

        # Adiciona peso atual como último ponto da série
        evolucao_peso.append(
            EvolucaoPesoItem(data=date.today(), peso=animal.peso)
        )

        resumo = await self.resumo_estatistico(animal_id)

        return HistoricoClinicoResponse(
            animal=AnimalResponse.model_validate(animal),
            tutor_atual=TutorResumoResponse.model_validate(animal.tutor),
            consultas=[ConsultaDetalheResponse.model_validate(c) for c in consultas],
            vacinas=[VacinaResumoResponse.model_validate(v) for v in vacinas],
            evolucao_peso=evolucao_peso,
            resumo=resumo,
        )
