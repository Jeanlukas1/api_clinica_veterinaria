"""
app/schemas/auth.py
────────────────────
Schemas Pydantic V2 para autenticação JWT e gerenciamento de usuários.

Validações implementadas:
  - senha: mínimo 8 chars, pelo menos 1 maiúscula, 1 número
  - email: via EmailStr
  - perfil: deve ser valor válido do enum PerfilUsuario
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import EmailStr, field_validator

from app.models.enums import PerfilUsuario
from app.schemas.common import BaseSchema


def _validar_senha(senha: str) -> str:
    """
    Valida requisitos mínimos de senha:
    - Mínimo 8 caracteres
    - Pelo menos 1 letra maiúscula
    - Pelo menos 1 número
    - Pelo menos 1 caractere especial
    """
    if len(senha) < 8:
        raise ValueError("Senha deve ter no mínimo 8 caracteres.")
    if not re.search(r"[A-Z]", senha):
        raise ValueError("Senha deve conter pelo menos uma letra maiúscula.")
    if not re.search(r"\d", senha):
        raise ValueError("Senha deve conter pelo menos um número.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
        raise ValueError("Senha deve conter pelo menos um caractere especial.")
    return senha


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseSchema):
    """Schema para login (POST /auth/login via form ou JSON)."""
    email: EmailStr
    password: str


class RefreshRequest(BaseSchema):
    """Schema para renovação de token (POST /auth/refresh)."""
    refresh_token: str


class TokenResponse(BaseSchema):
    """Resposta do login/refresh com par de tokens JWT."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos até expiração do access token


class TokenPayload(BaseSchema):
    """Payload decodificado do JWT (uso interno)."""
    sub: str       # email
    perfil: str
    tipo: str      # "access" ou "refresh"
    jti: str       # JWT unique ID
    exp: int


# ─── Usuário ──────────────────────────────────────────────────────────────────

class UsuarioCreate(BaseSchema):
    """Schema para criação de usuário (POST /auth/register — ADMIN only)."""
    nome: str
    email: EmailStr
    password: str
    perfil: PerfilUsuario
    tutor_id: uuid.UUID | None = None        # para perfil TUTOR
    veterinario_id: uuid.UUID | None = None  # para perfil VETERINARIO

    @field_validator("nome")
    @classmethod
    def nome_minimo(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Nome deve ter no mínimo 3 caracteres.")
        return v

    @field_validator("password")
    @classmethod
    def senha_forte(cls, v: str) -> str:
        return _validar_senha(v)


class UsuarioUpdate(BaseSchema):
    """Schema para atualização de usuário."""
    nome: str | None = None
    ativo: bool | None = None


class AlterarSenhaRequest(BaseSchema):
    """Schema para alteração de senha."""
    senha_atual: str
    nova_senha: str
    confirmacao_senha: str

    @field_validator("nova_senha")
    @classmethod
    def senha_forte(cls, v: str) -> str:
        return _validar_senha(v)

    def model_post_init(self, __context) -> None:
        if self.nova_senha != self.confirmacao_senha:
            raise ValueError("Nova senha e confirmação não coincidem.")


class UsuarioResponse(BaseSchema):
    """Schema de resposta para usuário (sem senha)."""
    id: uuid.UUID
    nome: str
    email: str
    perfil: str
    ativo: bool
    tutor_id: uuid.UUID | None
    veterinario_id: uuid.UUID | None
    criado_em: datetime
