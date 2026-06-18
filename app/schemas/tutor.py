"""
app/schemas/tutor.py
─────────────────────
Schemas Pydantic V2 para a entidade Tutor.

Validações implementadas:
  - CPF: algoritmo de dígitos verificadores brasileiro
  - Email: via EmailStr (pydantic-email-validator)
  - Telefone: formato (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import EmailStr, field_validator, model_validator

from app.schemas.common import BaseSchema


# ─── Helpers de Validação ─────────────────────────────────────────────────────

def _validar_cpf(cpf: str) -> str:
    """
    Valida CPF pelo algoritmo de dígitos verificadores.
    Aceita formatos: '529.982.247-25' ou '52998224725'.
    Retorna sempre no formato '000.000.000-00'.
    """
    nums = re.sub(r"\D", "", cpf)

    if len(nums) != 11:
        raise ValueError("CPF deve ter 11 dígitos.")

    if len(set(nums)) == 1:
        raise ValueError("CPF inválido (dígitos repetidos).")

    for i in range(9, 11):
        soma = sum(int(nums[j]) * (i + 1 - j) for j in range(i))
        digito = (soma * 10 % 11) % 10
        if digito != int(nums[i]):
            raise ValueError("CPF inválido.")

    return f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"


def _validar_telefone(telefone: str) -> str:
    """
    Valida e formata telefone brasileiro.
    Aceita: '(11) 99999-9999' ou '(11) 9999-9999'.
    """
    nums = re.sub(r"\D", "", telefone)
    if len(nums) == 11:
        return f"({nums[:2]}) {nums[2:7]}-{nums[7:]}"
    elif len(nums) == 10:
        return f"({nums[:2]}) {nums[2:6]}-{nums[6:]}"
    raise ValueError("Telefone inválido. Use formato (XX) XXXXX-XXXX.")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class TutorCreate(BaseSchema):
    """Schema para criação de tutor (POST /tutores)."""
    nome: str
    cpf: str
    email: EmailStr
    telefone: str

    @field_validator("nome")
    @classmethod
    def nome_minimo(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Nome deve ter no mínimo 3 caracteres.")
        return v

    @field_validator("cpf")
    @classmethod
    def cpf_valido(cls, v: str) -> str:
        return _validar_cpf(v)

    @field_validator("telefone")
    @classmethod
    def telefone_valido(cls, v: str) -> str:
        return _validar_telefone(v)


class TutorUpdate(BaseSchema):
    """Schema para atualização parcial de tutor (PATCH /tutores/{id})."""
    nome: str | None = None
    email: EmailStr | None = None
    telefone: str | None = None
    ativo: bool | None = None

    @field_validator("nome")
    @classmethod
    def nome_minimo(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) < 3:
                raise ValueError("Nome deve ter no mínimo 3 caracteres.")
        return v

    @field_validator("telefone")
    @classmethod
    def telefone_valido(cls, v: str | None) -> str | None:
        if v is not None:
            return _validar_telefone(v)
        return v


class TutorResponse(BaseSchema):
    """Schema de resposta para tutor."""
    id: uuid.UUID
    nome: str
    cpf: str
    email: str
    telefone: str
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime
    criado_por: str | None = None


class TutorResumoResponse(BaseSchema):
    """Versão resumida para listagens (sem campos de auditoria)."""
    id: uuid.UUID
    nome: str
    cpf: str
    email: str
    telefone: str
    ativo: bool
