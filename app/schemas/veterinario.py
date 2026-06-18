"""
app/schemas/veterinario.py
───────────────────────────
Schemas Pydantic V2 para a entidade Veterinário.

Validações implementadas:
  - nome: mínimo 3 caracteres
  - crmv: formato CRMV-UF-XXXXX (ex: CRMV-SP-12345)
  - especialidade: deve ser valor válido do enum
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import field_validator

from app.models.enums import EspecialidadeVeterinario
from app.schemas.common import BaseSchema


def _validar_crmv(crmv: str) -> str:
    """
    Valida formato do CRMV: CRMV-UF-NNNNN
    Exemplos válidos: CRMV-SP-12345, CRMV-RJ-9999
    """
    crmv = crmv.strip().upper()
    pattern = r"^CRMV-[A-Z]{2}-\d{4,6}$"
    if not re.match(pattern, crmv):
        raise ValueError(
            "CRMV inválido. Use o formato CRMV-UF-XXXXX (ex: CRMV-SP-12345)."
        )
    return crmv


class VeterinarioCreate(BaseSchema):
    """Schema para cadastro de veterinário (POST /veterinarios)."""
    nome: str
    crmv: str
    especialidade: EspecialidadeVeterinario

    @field_validator("nome")
    @classmethod
    def nome_minimo(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Nome deve ter no mínimo 3 caracteres.")
        return v

    @field_validator("crmv")
    @classmethod
    def crmv_valido(cls, v: str) -> str:
        return _validar_crmv(v)


class VeterinarioUpdate(BaseSchema):
    """Schema para atualização parcial de veterinário (PATCH /veterinarios/{id})."""
    nome: str | None = None
    especialidade: EspecialidadeVeterinario | None = None
    ativo: bool | None = None

    @field_validator("nome")
    @classmethod
    def nome_minimo(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) < 3:
                raise ValueError("Nome deve ter no mínimo 3 caracteres.")
        return v


class VeterinarioResponse(BaseSchema):
    """Schema de resposta completo para veterinário."""
    id: uuid.UUID
    nome: str
    crmv: str
    especialidade: str
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime


class VeterinarioResumoResponse(BaseSchema):
    """Versão resumida para embed em ConsultaResponse."""
    id: uuid.UUID
    nome: str
    crmv: str
    especialidade: str
    ativo: bool
