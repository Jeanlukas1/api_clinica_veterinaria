"""
app/schemas/animal.py
──────────────────────
Schemas Pydantic V2 para a entidade Animal.

Validações implementadas:
  - data_nascimento: não pode ser futura (RN-002)
  - peso: deve ser maior que zero (RN-012)
  - especie: deve ser um valor válido do enum EspecieAnimal
  - sexo: deve ser M ou F
  - microchip: formato básico (alfanumérico, 10-15 chars se preenchido)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import field_validator, model_validator

from app.models.enums import EspecieAnimal, SexoAnimal
from app.schemas.common import BaseSchema
from app.schemas.tutor import TutorResumoResponse


# ─── Schemas ──────────────────────────────────────────────────────────────────

class AnimalCreate(BaseSchema):
    """Schema para cadastro de animal (POST /animais)."""
    tutor_id: uuid.UUID
    nome: str
    especie: EspecieAnimal
    raca: str | None = None
    sexo: SexoAnimal
    data_nascimento: date
    peso: Decimal
    microchip: str | None = None

    @field_validator("nome")
    @classmethod
    def nome_minimo(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Nome do animal deve ter no mínimo 2 caracteres.")
        return v

    @field_validator("data_nascimento")
    @classmethod
    def data_nao_futura(cls, v: date) -> date:
        """RN-002: data de nascimento não pode ser futura."""
        if v > date.today():
            raise ValueError("data_nascimento não pode ser uma data futura.")
        return v

    @field_validator("peso")
    @classmethod
    def peso_positivo(cls, v: Decimal) -> Decimal:
        """RN-012: peso deve ser maior que zero."""
        if v <= 0:
            raise ValueError("Peso deve ser maior que zero.")
        if v > 999.999:
            raise ValueError("Peso excede o limite máximo de 999.999 kg.")
        return v

    @field_validator("microchip")
    @classmethod
    def microchip_formato(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if len(v) < 10 or len(v) > 15:
            raise ValueError("Microchip deve ter entre 10 e 15 caracteres.")
        if not v.isalnum():
            raise ValueError("Microchip deve conter apenas letras e números.")
        return v


class AnimalUpdate(BaseSchema):
    """Schema para atualização parcial de animal (PATCH /animais/{id})."""
    nome: str | None = None
    raca: str | None = None
    peso: Decimal | None = None
    microchip: str | None = None
    ativo: bool | None = None

    @field_validator("peso")
    @classmethod
    def peso_positivo(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("Peso deve ser maior que zero.")
        return v

    @field_validator("microchip")
    @classmethod
    def microchip_formato(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if len(v) < 10 or len(v) > 15:
            raise ValueError("Microchip deve ter entre 10 e 15 caracteres.")
        if not v.isalnum():
            raise ValueError("Microchip deve conter apenas letras e números.")
        return v


class AnimalResponse(BaseSchema):
    """Schema de resposta completo para animal."""
    id: uuid.UUID
    tutor_id: uuid.UUID
    nome: str
    especie: str
    raca: str | None
    sexo: str
    data_nascimento: date
    peso: Decimal
    microchip: str | None
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime
    # Campo calculado — exposto via property do model
    idade_anos: float | None = None

    @model_validator(mode="before")
    @classmethod
    def calcular_idade(cls, data):
        """Calcula idade em anos a partir de data_nascimento."""
        if hasattr(data, "data_nascimento") and data.data_nascimento:
            data_nasc = data.data_nascimento
            if isinstance(data_nasc, date):
                idade = (date.today() - data_nasc).days / 365.25
                # Injeta o campo calculado no dict de entrada
                if hasattr(data, "__dict__"):
                    object.__setattr__(data, "idade_anos", round(idade, 1))
        return data


class AnimalResumoResponse(BaseSchema):
    """Versão resumida para listagens."""
    id: uuid.UUID
    tutor_id: uuid.UUID
    nome: str
    especie: str
    raca: str | None
    sexo: str
    data_nascimento: date
    peso: Decimal
    microchip: str | None
    ativo: bool


# ─── Schemas de Histórico e Resumo ───────────────────────────────────────────

class EvolucaoPesoItem(BaseSchema):
    """Item da série temporal de evolução de peso."""
    data: date
    peso: Decimal


class EstatisticasAnimalResponse(BaseSchema):
    """
    Resumo estatístico calculado do animal.
    Cálculo derivado: combina dados de consultas e vacinas.
    """
    total_consultas: int
    ultima_consulta: datetime | None
    proxima_vacina: date | None
    total_vacinas: int
    consultas_por_status: dict[str, int]
    idade_anos: float


class HistoricoClinicoResponse(BaseSchema):
    """
    Histórico clínico consolidado — cálculo derivado principal do sistema.
    Combina consultas + vacinas + evolução de peso.
    """
    animal: AnimalResponse
    tutor_atual: TutorResumoResponse
    consultas: list  # list[ConsultaDetalheResponse] — importação circular evitada
    vacinas: list    # list[VacinaResponse]
    evolucao_peso: list[EvolucaoPesoItem]
    resumo: EstatisticasAnimalResponse
