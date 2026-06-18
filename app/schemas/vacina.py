"""
app/schemas/vacina.py
──────────────────────
Schemas Pydantic V2 para a entidade Vacina.

Validações implementadas:
  - data_aplicacao: não pode ser futura (RN-009)
  - data_proxima: deve ser posterior à data_aplicacao (model_validator)
  - nome_vacina e lote: campos obrigatórios não vazios
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import field_validator, model_validator

from app.schemas.common import BaseSchema


class VacinaCreate(BaseSchema):
    """Schema para registro de vacina (POST /vacinas)."""
    animal_id: uuid.UUID
    consulta_id: uuid.UUID | None = None
    nome_vacina: str
    lote: str
    data_aplicacao: date
    data_proxima: date | None = None

    @field_validator("nome_vacina")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome da vacina não pode ser vazio.")
        return v

    @field_validator("lote")
    @classmethod
    def lote_nao_vazio(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Lote não pode ser vazio.")
        return v

    @field_validator("data_aplicacao")
    @classmethod
    def aplicacao_nao_futura(cls, v: date) -> date:
        """RN-009: Data de aplicação não pode ser futura."""
        if v > date.today():
            raise ValueError(
                "data_aplicacao não pode ser uma data futura. "
                "Vacinas só podem ser registradas após a aplicação."
            )
        return v

    @model_validator(mode="after")
    def data_proxima_posterior(self) -> "VacinaCreate":
        """Valida que data_proxima é posterior à data_aplicacao."""
        if self.data_proxima is not None:
            if self.data_proxima <= self.data_aplicacao:
                raise ValueError(
                    "data_proxima deve ser posterior à data_aplicacao."
                )
        return self


class VacinaUpdate(BaseSchema):
    """Schema para atualização de vacina (PATCH /vacinas/{id})."""
    nome_vacina: str | None = None
    lote: str | None = None
    data_aplicacao: date | None = None
    data_proxima: date | None = None

    @field_validator("data_aplicacao")
    @classmethod
    def aplicacao_nao_futura(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("data_aplicacao não pode ser uma data futura.")
        return v

    @model_validator(mode="after")
    def data_proxima_posterior(self) -> "VacinaUpdate":
        """Valida coerência entre datas quando ambas são fornecidas."""
        if self.data_proxima is not None and self.data_aplicacao is not None:
            if self.data_proxima <= self.data_aplicacao:
                raise ValueError(
                    "data_proxima deve ser posterior à data_aplicacao."
                )
        return self


class VacinaResponse(BaseSchema):
    """Schema de resposta para vacina."""
    id: uuid.UUID
    animal_id: uuid.UUID
    consulta_id: uuid.UUID | None
    nome_vacina: str
    lote: str
    data_aplicacao: date
    data_proxima: date | None
    criado_em: datetime
    atualizado_em: datetime


class VacinaResumoResponse(BaseSchema):
    """Versão resumida para embed no histórico clínico."""
    id: uuid.UUID
    nome_vacina: str
    lote: str
    data_aplicacao: date
    data_proxima: date | None
    consulta_id: uuid.UUID | None
