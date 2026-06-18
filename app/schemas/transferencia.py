"""
app/schemas/transferencia.py
─────────────────────────────
Schemas Pydantic V2 para a entidade TransferenciaAnimal.

Validações implementadas:
  - motivo: mínimo 10 caracteres (RN-010)
  - tutor_destino_id: não pode ser igual ao tutor de origem (validado no service)

Nota: TransferenciaAnimal é imutável — só existe TransferenciaCreate (sem Update).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import field_validator

from app.schemas.common import BaseSchema
from app.schemas.tutor import TutorResumoResponse
from app.schemas.animal import AnimalResumoResponse


class TransferenciaCreate(BaseSchema):
    """
    Schema para transferência de animal entre tutores (POST /transferencias).
    Implementa RN-010: motivo obrigatório com mínimo de 10 caracteres.
    """
    animal_id: uuid.UUID
    tutor_destino_id: uuid.UUID
    motivo: str

    @field_validator("motivo")
    @classmethod
    def motivo_minimo(cls, v: str) -> str:
        """RN-010: Motivo deve ter no mínimo 10 caracteres."""
        v = v.strip()
        if len(v) < 10:
            raise ValueError(
                "Motivo da transferência deve ter no mínimo 10 caracteres (RN-010)."
            )
        return v


class TransferenciaResponse(BaseSchema):
    """Schema de resposta para transferência (registro imutável)."""
    id: uuid.UUID
    animal_id: uuid.UUID
    tutor_origem_id: uuid.UUID
    tutor_destino_id: uuid.UUID
    motivo: str
    data_transferencia: datetime
    criado_por: str


class TransferenciaDetalheResponse(BaseSchema):
    """Resposta detalhada com entidades relacionadas embutidas."""
    id: uuid.UUID
    motivo: str
    data_transferencia: datetime
    criado_por: str
    animal: AnimalResumoResponse | None = None
    tutor_origem: TutorResumoResponse | None = None
    tutor_destino: TutorResumoResponse | None = None
