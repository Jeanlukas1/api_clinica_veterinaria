"""
app/routers/auth.py
────────────────────
Router de autenticação — login, refresh, registro e alteração de senha.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CredenciaisInvalidasError, TokenInvalidoError
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    TokenResponse,
    create_token_pair,
    decode_token,
    get_current_user,
    require_perfil,
    verify_password,
)
from app.database.session import get_db
from app.models.enums import PerfilUsuario
from app.models.usuario import Usuario
from app.schemas.auth import (
    AlterarSenhaRequest,
    UsuarioCreate,
    UsuarioResponse,
    UsuarioUpdate,
)
from app.services.auth import AuthService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(session)


# ─── Endpoints Públicos ───────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description=(
        "Autentica usuário e retorna par de tokens JWT.\n\n"
        "- **access_token**: validade de 30 minutos\n"
        "- **refresh_token**: validade de 7 dias"
    ),
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    from sqlalchemy import select

    stmt = select(Usuario).where(
        Usuario.email == form_data.username.lower(),
        Usuario.ativo == True,
    )
    result = await session.execute(stmt)
    usuario = result.scalar_one_or_none()

    if not usuario or not verify_password(form_data.password, usuario.senha_hash):
        raise CredenciaisInvalidasError()

    return create_token_pair(usuario.email, usuario.perfil)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar tokens",
    description="Gera novo par de tokens a partir de um refresh token válido.",
)
async def refresh_token(
    refresh_token: str,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    from sqlalchemy import select

    payload = decode_token(refresh_token)
    if payload.tipo != TOKEN_TYPE_REFRESH:
        raise TokenInvalidoError("Token fornecido não é um refresh token.")

    stmt = select(Usuario).where(
        Usuario.email == payload.sub, Usuario.ativo == True
    )
    result = await session.execute(stmt)
    usuario = result.scalar_one_or_none()

    if not usuario:
        raise TokenInvalidoError("Usuário não encontrado ou inativo.")

    return create_token_pair(usuario.email, usuario.perfil)


# ─── Endpoints Protegidos ─────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar usuário",
    description=(
        "Registra novo usuário no sistema.\n\n"
        "**Restrito a ADMIN.**\n\n"
        "Requisitos de senha: ≥8 chars, 1 maiúscula, 1 número, 1 especial."
    ),
)
async def registrar_usuario(
    data: UsuarioCreate,
    service: AuthService = Depends(_service),
    current_user: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN)),
) -> UsuarioResponse:
    usuario = await service.registrar(data, usuario_autenticado=current_user.email)
    return UsuarioResponse.model_validate(usuario)


@router.patch(
    "/me",
    response_model=UsuarioResponse,
    summary="Atualizar meu perfil",
    description="Atualiza nome do usuário autenticado.",
)
async def atualizar_perfil(
    data: UsuarioUpdate,
    service: AuthService = Depends(_service),
    current_user: Usuario = Depends(get_current_user),
) -> UsuarioResponse:
    usuario = await service.atualizar(
        current_user.id, data, usuario_autenticado=current_user.email
    )
    return UsuarioResponse.model_validate(usuario)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Alterar senha",
    description="Altera a senha do usuário autenticado após verificar a senha atual.",
)
async def alterar_senha(
    data: AlterarSenhaRequest,
    service: AuthService = Depends(_service),
    current_user: Usuario = Depends(get_current_user),
) -> None:
    await service.alterar_senha(
        current_user.id, data, usuario_autenticado=current_user.email
    )


@router.get(
    "/me",
    response_model=UsuarioResponse,
    summary="Dados do usuário autenticado",
    description="Retorna os dados do usuário atual (extraídos do JWT).",
)
async def me(
    current_user: Usuario = Depends(get_current_user),
) -> UsuarioResponse:
    return UsuarioResponse.model_validate(current_user)
