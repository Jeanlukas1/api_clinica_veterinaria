"""
app/routers/auth.py
────────────────────
Router de autenticação — login, refresh e registro de usuários.
Implementação completa na ETAPA 8.
"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenResponse, create_token_pair, decode_token, hash_password
from app.core.exceptions import CredenciaisInvalidasError, TokenInvalidoError
from app.database.session import get_db

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Autentica usuário e retorna par de tokens JWT (access + refresh).",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    from sqlalchemy import select
    from app.models.usuario import Usuario
    from app.core.security import verify_password

    stmt = select(Usuario).where(
        Usuario.email == form_data.username,
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
    summary="Renovar token",
    description="Gera novo par de tokens a partir de um refresh token válido.",
)
async def refresh_token(
    refresh_token: str,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    from sqlalchemy import select
    from app.models.usuario import Usuario
    from app.core.security import TOKEN_TYPE_REFRESH

    payload = decode_token(refresh_token)
    if payload.tipo != TOKEN_TYPE_REFRESH:
        raise TokenInvalidoError("Token fornecido não é um refresh token.")

    stmt = select(Usuario).where(Usuario.email == payload.sub, Usuario.ativo == True)
    result = await session.execute(stmt)
    usuario = result.scalar_one_or_none()

    if not usuario:
        raise TokenInvalidoError()

    return create_token_pair(usuario.email, usuario.perfil)
