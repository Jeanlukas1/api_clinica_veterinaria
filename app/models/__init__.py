"""
app/models/__init__.py
───────────────────────
Exporta todos os models para que o Alembic os detecte automaticamente
ao importar app.models no env.py.
"""
from app.models.animal import Animal
from app.models.auditoria import Auditoria
from app.models.consulta import Consulta
from app.models.enums import (
    ESTADOS_TERMINAIS,
    TRANSICOES_VALIDAS,
    EspecialidadeVeterinario,
    EspecieAnimal,
    EventoAuditoria,
    PerfilUsuario,
    SexoAnimal,
    StatusConsulta,
    TipoConsulta,
)
from app.models.transferencia_animal import TransferenciaAnimal
from app.models.tutor import Tutor
from app.models.usuario import Usuario
from app.models.vacina import Vacina
from app.models.veterinario import Veterinario

__all__ = [
    "Tutor",
    "Animal",
    "Veterinario",
    "Consulta",
    "Vacina",
    "TransferenciaAnimal",
    "Auditoria",
    "Usuario",
    # Enums
    "EspecieAnimal",
    "SexoAnimal",
    "EspecialidadeVeterinario",
    "StatusConsulta",
    "TipoConsulta",
    "EventoAuditoria",
    "PerfilUsuario",
    "TRANSICOES_VALIDAS",
    "ESTADOS_TERMINAIS",
]
