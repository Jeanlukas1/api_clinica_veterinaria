"""
app/models/enums.py
────────────────────
Enumerações de domínio utilizadas pelos models SQLAlchemy e schemas Pydantic.
Centralizar os enums evita duplicação e garante consistência entre camadas.
"""
from enum import Enum


# ─── Animal ───────────────────────────────────────────────────────────────────

class EspecieAnimal(str, Enum):
    CANINO = "CANINO"
    FELINO = "FELINO"
    AVE    = "AVE"
    REPTIL = "REPTIL"
    ROEDOR = "ROEDOR"
    OUTRO  = "OUTRO"


class SexoAnimal(str, Enum):
    MACHO  = "M"
    FEMEA  = "F"


# ─── Veterinário ──────────────────────────────────────────────────────────────

class EspecialidadeVeterinario(str, Enum):
    CLINICA_GERAL = "CLINICA_GERAL"
    ORTOPEDIA     = "ORTOPEDIA"
    ONCOLOGIA     = "ONCOLOGIA"
    DERMATOLOGIA  = "DERMATOLOGIA"
    CARDIOLOGIA   = "CARDIOLOGIA"
    OFTALMOLOGIA  = "OFTALMOLOGIA"
    OUTRO         = "OUTRO"


# ─── Consulta ─────────────────────────────────────────────────────────────────

class StatusConsulta(str, Enum):
    """
    Máquina de estados da Consulta.

    Transições válidas:
        AGENDADA    → CONFIRMADA
        CONFIRMADA  → EM_ANDAMENTO
        EM_ANDAMENTO → CONCLUIDA
        AGENDADA    → CANCELADA
        CONFIRMADA  → CANCELADA

    Terminais: CONCLUIDA, CANCELADA
    """
    AGENDADA     = "AGENDADA"
    CONFIRMADA   = "CONFIRMADA"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDA    = "CONCLUIDA"
    CANCELADA    = "CANCELADA"


# Mapa de transições válidas — usado pelo ConsultaService
TRANSICOES_VALIDAS: dict[StatusConsulta, list[StatusConsulta]] = {
    StatusConsulta.AGENDADA:     [StatusConsulta.CONFIRMADA, StatusConsulta.CANCELADA],
    StatusConsulta.CONFIRMADA:   [StatusConsulta.EM_ANDAMENTO, StatusConsulta.CANCELADA],
    StatusConsulta.EM_ANDAMENTO: [StatusConsulta.CONCLUIDA],
    StatusConsulta.CONCLUIDA:    [],   # terminal
    StatusConsulta.CANCELADA:    [],   # terminal
}

ESTADOS_TERMINAIS: set[StatusConsulta] = {
    StatusConsulta.CONCLUIDA,
    StatusConsulta.CANCELADA,
}


class TipoConsulta(str, Enum):
    ROTINA    = "ROTINA"
    RETORNO   = "RETORNO"
    EMERGENCIA = "EMERGENCIA"
    CIRURGIA  = "CIRURGIA"
    EXAME     = "EXAME"


# ─── Auditoria ────────────────────────────────────────────────────────────────

class EventoAuditoria(str, Enum):
    TRANSFERENCIA_ANIMAL    = "TRANSFERENCIA_ANIMAL"
    INATIVACAO_TUTOR        = "INATIVACAO_TUTOR"
    INATIVACAO_ANIMAL       = "INATIVACAO_ANIMAL"
    INATIVACAO_VETERINARIO  = "INATIVACAO_VETERINARIO"
    CANCELAMENTO_CONSULTA   = "CANCELAMENTO_CONSULTA"
    CONCLUSAO_CONSULTA      = "CONCLUSAO_CONSULTA"
    EMERGENCIA_SOBREPOSTA   = "EMERGENCIA_SOBREPOSTA"
    CRIACAO_USUARIO         = "CRIACAO_USUARIO"
    LOGIN                   = "LOGIN"
    ALTERACAO_PERMISSAO     = "ALTERACAO_PERMISSAO"


# ─── Usuário / RBAC ──────────────────────────────────────────────────────────

class PerfilUsuario(str, Enum):
    ADMIN         = "ADMIN"
    VETERINARIO   = "VETERINARIO"
    RECEPCIONISTA = "RECEPCIONISTA"
    TUTOR         = "TUTOR"
