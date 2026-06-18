"""
app/core/exceptions.py
───────────────────────
Hierarquia de exceções de domínio e handlers HTTP globais.

Decisão de design:
  - Todas as exceções de domínio herdam de ClinicaException
  - Cada exceção carrega um error_code (string) para o cliente
  - O handler global converte para o padrão JSON de erro da API
  - Separar exceções de domínio de HTTPException evita vazar detalhes HTTP
    para a camada de serviço
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# ─── Base ─────────────────────────────────────────────────────────────────────

class ClinicaException(Exception):
    """
    Exceção base de domínio.
    Todas as exceções de negócio herdam desta classe.
    """
    error_code: str = "DOMAIN_ERROR"
    default_message: str = "Erro de domínio."
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(
        self,
        message: str | None = None,
        details: dict | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# ─── Exceções de Tutor ────────────────────────────────────────────────────────

class TutorNaoEncontradoError(ClinicaException):
    error_code = "TUTOR_NOT_FOUND"
    default_message = "Tutor não encontrado."
    status_code = status.HTTP_404_NOT_FOUND


class TutorComAnimaisAtivosError(ClinicaException):
    """RN-001: Tutor com animais ativos não pode ser inativado."""
    error_code = "TUTOR_HAS_ACTIVE_ANIMALS"
    default_message = (
        "Tutor possui animais ativos. "
        "Transfira ou inative os animais antes de inativar o tutor."
    )
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class TutorInativoError(ClinicaException):
    error_code = "TUTOR_INATIVO"
    default_message = "Tutor está inativo."
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class CPFDuplicadoError(ClinicaException):
    error_code = "CPF_DUPLICADO"
    default_message = "CPF já cadastrado."
    status_code = status.HTTP_409_CONFLICT


class EmailDuplicadoError(ClinicaException):
    error_code = "EMAIL_DUPLICADO"
    default_message = "E-mail já cadastrado."
    status_code = status.HTTP_409_CONFLICT


# ─── Exceções de Animal ───────────────────────────────────────────────────────

class AnimalNaoEncontradoError(ClinicaException):
    error_code = "ANIMAL_NOT_FOUND"
    default_message = "Animal não encontrado."
    status_code = status.HTTP_404_NOT_FOUND


class MicrochipDuplicadoError(ClinicaException):
    """RN-003: Microchip deve ser único entre animais ativos."""
    error_code = "MICROCHIP_DUPLICADO"
    default_message = "Microchip já cadastrado para outro animal."
    status_code = status.HTTP_409_CONFLICT


class AnimalInativoError(ClinicaException):
    error_code = "ANIMAL_INATIVO"
    default_message = "Animal está inativo."
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


# ─── Exceções de Veterinário ──────────────────────────────────────────────────

class VeterinarioNaoEncontradoError(ClinicaException):
    error_code = "VETERINARIO_NOT_FOUND"
    default_message = "Veterinário não encontrado."
    status_code = status.HTTP_404_NOT_FOUND


class VeterinarioInativoError(ClinicaException):
    """RN-011: Veterinário inativo não pode receber consultas."""
    error_code = "VETERINARIO_INATIVO"
    default_message = "Veterinário inativo não pode receber consultas."
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class CRMVDuplicadoError(ClinicaException):
    error_code = "CRMV_DUPLICADO"
    default_message = "CRMV já cadastrado."
    status_code = status.HTTP_409_CONFLICT


# ─── Exceções de Consulta ─────────────────────────────────────────────────────

class ConsultaNaoEncontradaError(ClinicaException):
    error_code = "CONSULTA_NOT_FOUND"
    default_message = "Consulta não encontrada."
    status_code = status.HTTP_404_NOT_FOUND


class ConsultaConflictError(ClinicaException):
    """RN-004: Veterinário já possui consulta nesse horário."""
    error_code = "CONSULTA_CONFLICT"
    default_message = "Veterinário já possui consulta nesse horário."
    status_code = status.HTTP_409_CONFLICT


class ConsultaImutavelError(ClinicaException):
    """RN-008: Consultas em estado terminal são imutáveis."""
    error_code = "CONSULTA_IMUTAVEL"
    default_message = "Consultas em estado terminal (CONCLUIDA/CANCELADA) não podem ser alteradas."
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class TransicaoInvalidaError(ClinicaException):
    """Transição de status inválida na máquina de estados."""
    error_code = "TRANSICAO_INVALIDA"
    default_message = "Transição de status inválida."
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class DiagnosticoObrigatorioError(ClinicaException):
    """RN-007: Diagnóstico obrigatório para concluir consulta."""
    error_code = "DIAGNOSTICO_OBRIGATORIO"
    default_message = "Diagnóstico é obrigatório para concluir a consulta."
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


# ─── Exceções de Vacina ───────────────────────────────────────────────────────

class VacinaNaoEncontradaError(ClinicaException):
    error_code = "VACINA_NOT_FOUND"
    default_message = "Vacina não encontrada."
    status_code = status.HTTP_404_NOT_FOUND


# ─── Exceções de Transferência ────────────────────────────────────────────────

class TransferenciaNaoEncontradaError(ClinicaException):
    error_code = "TRANSFERENCIA_NOT_FOUND"
    default_message = "Transferência não encontrada."
    status_code = status.HTTP_404_NOT_FOUND


class MotivoObrigatorioError(ClinicaException):
    """RN-010: Transferência exige motivo com pelo menos 10 caracteres."""
    error_code = "MOTIVO_OBRIGATORIO"
    default_message = "Motivo da transferência é obrigatório e deve ter no mínimo 10 caracteres."
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class TransferenciaMesmoTutorError(ClinicaException):
    error_code = "TRANSFERENCIA_MESMO_TUTOR"
    default_message = "O tutor destino é o mesmo que o tutor atual do animal."
    status_code = status.HTTP_409_CONFLICT


# ─── Exceções de Auth ─────────────────────────────────────────────────────────

class CredenciaisInvalidasError(ClinicaException):
    error_code = "CREDENCIAIS_INVALIDAS"
    default_message = "E-mail ou senha inválidos."
    status_code = status.HTTP_401_UNAUTHORIZED


class TokenInvalidoError(ClinicaException):
    error_code = "TOKEN_INVALIDO"
    default_message = "Token de autenticação inválido ou expirado."
    status_code = status.HTTP_401_UNAUTHORIZED


class AcessoNegadoError(ClinicaException):
    error_code = "ACESSO_NEGADO"
    default_message = "Você não tem permissão para acessar este recurso."
    status_code = status.HTTP_403_FORBIDDEN


class UsuarioNaoEncontradoError(ClinicaException):
    error_code = "USUARIO_NOT_FOUND"
    default_message = "Usuário não encontrado."
    status_code = status.HTTP_404_NOT_FOUND


# ─── Registro de Handlers Globais ─────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """
    Registra todos os handlers de exceção no app FastAPI.
    Chamado em main.py durante o setup da aplicação.
    """

    @app.exception_handler(ClinicaException)
    async def clinica_exception_handler(
        request: Request, exc: ClinicaException
    ) -> JSONResponse:
        """Handler para todas as exceções de domínio."""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Handler para erros de validação do Pydantic V2.
        Formata no padrão de erro da API.
        """
        errors = []
        for error in exc.errors():
            field = " → ".join(str(loc) for loc in error["loc"])
            errors.append({"field": field, "message": error["msg"]})

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Dados de entrada inválidos.",
                "details": {"errors": errors},
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handler para HTTPException do FastAPI — formata no padrão da API."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP_ERROR",
                "message": exc.detail,
                "details": {},
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Handler de fallback para exceções não tratadas.
        Em produção, não expõe detalhes internos.
        """
        import logging
        logging.getLogger(__name__).exception(
            "Erro não tratado: %s %s", request.method, request.url
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_ERROR",
                "message": "Erro interno do servidor.",
                "details": {},
            },
        )
