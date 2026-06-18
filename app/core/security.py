"""
app/core/security.py
─────────────────────
Autenticação JWT, hashing de senha e controle de acesso por perfil (RBAC).

Componentes:
  1. hash_password / verify_password  → bcrypt via passlib
  2. create_access_token              → JWT de curta duração (30 min)
  3. create_refresh_token             → JWT de longa duração (7 dias)
  4. decode_token                     → valida e decodifica JWT
  5. get_current_user                 → dependência FastAPI (extrai usuário do token)
  6. require_perfil                   → factory de dependências RBAC

Decisões de design:
  - Dois tipos de token (access/refresh) seguem o padrão OAuth2
  - Access token: vida curta para minimizar janela de comprometimento
  - Refresh token: vida longa para UX sem relogin frequente
  - bcrypt é o algoritmo recomendado para hashing de senhas (custo adaptável)
  - TokenPayload como Pydantic model garante tipagem forte no payload do JWT
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AcessoNegadoError, TokenInvalidoError
from app.database.session import get_db
from app.models.enums import PerfilUsuario

# ─── Configuração ─────────────────────────────────────────────────────────────

# Esquema OAuth2 para Swagger UI (campo "Authorize")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Contexto bcrypt para hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tipo de token para diferenciar access de refresh no payload
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


# ─── Schemas de Token ─────────────────────────────────────────────────────────

class TokenPayload(BaseModel):
    """Payload decodificado do JWT."""
    sub: str           # email do usuário (subject)
    perfil: str        # perfil RBAC
    tipo: str          # "access" ou "refresh"
    jti: str           # JWT ID único (para blacklist futura)
    exp: int           # timestamp de expiração


class TokenResponse(BaseModel):
    """Resposta do endpoint de login/refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int    # segundos até expiração do access token


# ─── Password Hashing ─────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Gera hash bcrypt da senha em texto puro."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto puro corresponde ao hash armazenado."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── Criação de Tokens JWT ────────────────────────────────────────────────────

def _create_token(
    subject: str,
    perfil: str,
    tipo: str,
    expires_delta: timedelta,
) -> str:
    """
    Função interna para criar tokens JWT.
    Inclui jti (JWT ID) único para suporte a blacklist futura.
    """
    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": subject,
        "perfil": perfil,
        "tipo": tipo,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str, perfil: str) -> str:
    """
    Cria Access Token JWT.
    Expiração: ACCESS_TOKEN_EXPIRE_MINUTES (padrão: 30 min).
    """
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(subject, perfil, TOKEN_TYPE_ACCESS, expires)


def create_refresh_token(subject: str, perfil: str) -> str:
    """
    Cria Refresh Token JWT.
    Expiração: REFRESH_TOKEN_EXPIRE_DAYS (padrão: 7 dias).
    """
    expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(subject, perfil, TOKEN_TYPE_REFRESH, expires)


def decode_token(token: str) -> TokenPayload:
    """
    Decodifica e valida um JWT.
    Lança TokenInvalidoError se o token for inválido ou expirado.
    """
    try:
        raw = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return TokenPayload(**raw)
    except JWTError as exc:
        raise TokenInvalidoError() from exc


def create_token_pair(email: str, perfil: str) -> TokenResponse:
    """Cria o par access + refresh token. Usado no login e refresh."""
    access = create_access_token(email, perfil)
    refresh = create_refresh_token(email, perfil)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ─── Dependências FastAPI ─────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """
    Dependência FastAPI: extrai e valida o usuário a partir do Bearer token.

    1. Decodifica o JWT (lança TokenInvalidoError se inválido)
    2. Verifica que é um access token (não refresh)
    3. Busca o usuário no banco
    4. Verifica que o usuário está ativo

    Retorna o objeto Usuario do banco.
    """
    # Importação local para evitar ciclo de importação
    from app.models.usuario import Usuario
    from sqlalchemy import select

    payload = decode_token(token)

    if payload.tipo != TOKEN_TYPE_ACCESS:
        raise TokenInvalidoError("Token inválido para este endpoint.")

    stmt = select(Usuario).where(Usuario.email == payload.sub, Usuario.ativo == True)
    result = await session.execute(stmt)
    usuario = result.scalar_one_or_none()

    if not usuario:
        raise TokenInvalidoError("Usuário não encontrado ou inativo.")

    return usuario


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> Any | None:
    """Variante opcional — retorna None se não houver token."""
    if not token:
        return None
    try:
        return await get_current_user(token, session)
    except (TokenInvalidoError, AcessoNegadoError):
        return None


def require_perfil(*perfis: PerfilUsuario):
    """
    Factory de dependência RBAC.

    Uso:
        @router.get("/rota")
        async def endpoint(
            user = Depends(require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.RECEPCIONISTA))
        ): ...

    Lança AcessoNegadoError (HTTP 403) se o perfil do usuário não estiver na lista.
    """
    async def dependency(
        current_user: Any = Depends(get_current_user),
    ) -> Any:
        from app.models.enums import PerfilUsuario as P
        user_perfil = P(current_user.perfil)
        if user_perfil not in perfis:
            raise AcessoNegadoError(
                f"Acesso restrito a: {', '.join(p.value for p in perfis)}."
            )
        return current_user

    return dependency


def require_admin():
    """Atalho: requer perfil ADMIN."""
    return require_perfil(PerfilUsuario.ADMIN)


def require_staff():
    """Atalho: ADMIN, VETERINARIO ou RECEPCIONISTA."""
    return require_perfil(
        PerfilUsuario.ADMIN,
        PerfilUsuario.VETERINARIO,
        PerfilUsuario.RECEPCIONISTA,
    )
