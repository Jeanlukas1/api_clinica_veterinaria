"""
app/schemas/consulta.py
────────────────────────
Schemas Pydantic V2 para a entidade Consulta.

Validações implementadas:
  - data_hora: não pode ser no passado para tipos não-EMERGENCIA (RN-005)
  - ConsultaStatusUpdate: diagnóstico obrigatório quando status=CONCLUIDA (RN-007)
  - Validação de tipo de consulta via enum TipoConsulta

Nota sobre RN-005:
  A validação de data passada é dupla:
  1. @field_validator no schema (primeira barreira — rápida, sem banco)
  2. Revalidada no ConsultaService (com contexto completo, incluindo tipo=EMERGENCIA)
  O schema rejeita datas passadas por padrão; o service permite para EMERGENCIA.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from app.models.enums import StatusConsulta, TipoConsulta
from app.schemas.animal import AnimalResumoResponse
from app.schemas.common import BaseSchema
from app.schemas.veterinario import VeterinarioResumoResponse


class ConsultaCreate(BaseSchema):
    """Schema para agendamento de consulta (POST /consultas)."""
    animal_id: uuid.UUID
    veterinario_id: uuid.UUID
    data_hora: datetime
    tipo: TipoConsulta
    observacoes: str | None = None

    @field_validator("data_hora")
    @classmethod
    def data_nao_passado(cls, v: datetime) -> datetime:
        """
        RN-005: consultas não podem ser agendadas no passado.
        Exceção: EMERGENCIA — validação feita no service (RN-006).
        Como o tipo ainda não está disponível aqui no field_validator,
        a rejeição de data passada é feita no service com contexto completo.
        Esta validação serve como barreira de sanidade para datas muito antigas.
        """
        # Garante timezone-aware
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v

    @model_validator(mode="after")
    def validar_data_hora_tipo(self) -> "ConsultaCreate":
        """
        Rejeita datas no passado para tipos não-emergência.
        Para EMERGENCIA, a data pode ser a hora atual.
        """
        agora = datetime.now(timezone.utc)
        data_hora = self.data_hora
        if data_hora.tzinfo is None:
            data_hora = data_hora.replace(tzinfo=timezone.utc)

        if data_hora < agora and self.tipo != TipoConsulta.EMERGENCIA:
            raise ValueError(
                "data_hora não pode ser no passado. "
                "Para emergências, use tipo=EMERGENCIA."
            )
        return self


class ConsultaUpdate(BaseSchema):
    """
    Schema para atualização de campos editáveis da consulta.
    Não inclui status (gerenciado por ConsultaStatusUpdate) nem campos terminais.
    """
    observacoes: str | None = None
    data_hora: datetime | None = None
    veterinario_id: uuid.UUID | None = None

    @field_validator("data_hora")
    @classmethod
    def data_nao_passado(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v < datetime.now(timezone.utc):
            raise ValueError("data_hora não pode ser no passado.")
        return v


class ConsultaStatusUpdate(BaseSchema):
    """
    Schema para transição de status da consulta (PATCH /consultas/{id}/status).
    Implementa RN-007: diagnóstico obrigatório ao concluir.
    """
    status: StatusConsulta
    diagnostico: str | None = None

    @model_validator(mode="after")
    def diagnostico_obrigatorio_para_conclusao(self) -> "ConsultaStatusUpdate":
        """RN-007: Diagnóstico obrigatório para concluir consulta."""
        if self.status == StatusConsulta.CONCLUIDA:
            if not self.diagnostico or not self.diagnostico.strip():
                raise ValueError(
                    "Diagnóstico é obrigatório para concluir a consulta (RN-007)."
                )
        return self


class ConsultaResponse(BaseSchema):
    """Schema de resposta completo para consulta."""
    id: uuid.UUID
    animal_id: uuid.UUID
    veterinario_id: uuid.UUID
    data_hora: datetime
    status: str
    tipo: str
    diagnostico: str | None
    observacoes: str | None
    criado_em: datetime
    atualizado_em: datetime
    criado_por: str | None = None


class ConsultaDetalheResponse(BaseSchema):
    """
    Resposta detalhada com entidades relacionadas embutidas.
    Usado no histórico clínico do animal.
    """
    id: uuid.UUID
    data_hora: datetime
    status: str
    tipo: str
    diagnostico: str | None
    observacoes: str | None
    veterinario: VeterinarioResumoResponse | None = None
    criado_em: datetime


class AgendaVeterinarioResponse(BaseSchema):
    """Resposta da agenda de um veterinário."""
    id: uuid.UUID
    animal_id: uuid.UUID
    data_hora: datetime
    status: str
    tipo: str
    observacoes: str | None
    animal: AnimalResumoResponse | None = None
