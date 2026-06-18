"""
app/services/auth.py
─────────────────────
AuthService — autenticação, registro e gerenciamento de usuários.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditoriaService
from app.core.exceptions import (
    AcessoNegadoError,
    CredenciaisInvalidasError,
    EmailDuplicadoError,
    UsuarioNaoEncontradoError,
)
from app.core.security import (
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
    TOKEN_TYPE_REFRESH,
    TokenResponse,
)
from app.models.enums import EventoAuditoria, PerfilUsuario
from app.models.usuario import Usuario
from app.schemas.auth import AlterarSenhaRequest, UsuarioCreate, UsuarioUpdate


class AuthService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit = AuditoriaService(session)

    async def _buscar_por_email(self, email: str) -> Usuario | None:
        stmt = select(Usuario).where(
            Usuario.email == email.lower(), Usuario.ativo == True
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """
        Autentica usuário e retorna par de tokens JWT.
        Registra evento de login na auditoria.
        """
        usuario = await self._buscar_por_email(email)
        if not usuario or not verify_password(password, usuario.senha_hash):
            raise CredenciaisInvalidasError()

        token_pair = create_token_pair(usuario.email, usuario.perfil)

        await self.audit.registrar(
            evento=EventoAuditoria.LOGIN,
            entidade="usuarios",
            entidade_id=usuario.id,
            usuario=usuario.email,
            payload={"perfil": usuario.perfil},
            ip_address=ip_address,
        )

        return token_pair

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """
        Renova o par de tokens usando um refresh token válido.
        Lança TokenInvalidoError se o token não for do tipo 'refresh'.
        """
        from app.core.exceptions import TokenInvalidoError

        payload = decode_token(refresh_token)
        if payload.tipo != TOKEN_TYPE_REFRESH:
            raise TokenInvalidoError("Token fornecido não é um refresh token.")

        usuario = await self._buscar_por_email(payload.sub)
        if not usuario:
            raise TokenInvalidoError("Usuário não encontrado ou inativo.")

        return create_token_pair(usuario.email, usuario.perfil)

    async def registrar(
        self,
        data: UsuarioCreate,
        usuario_autenticado: str,
    ) -> Usuario:
        """
        Registra novo usuário no sistema (apenas ADMIN).
        Verifica unicidade do e-mail.
        """
        # Unicidade de email
        existente = await self._buscar_por_email(data.email)
        if existente:
            raise EmailDuplicadoError(f"E-mail {data.email} já cadastrado.")

        usuario = Usuario(
            nome=data.nome,
            email=str(data.email).lower(),
            senha_hash=hash_password(data.password),
            perfil=data.perfil.value,
            tutor_id=data.tutor_id,
            veterinario_id=data.veterinario_id,
            criado_por=usuario_autenticado,
            atualizado_por=usuario_autenticado,
        )
        self.session.add(usuario)
        await self.session.flush()
        await self.session.refresh(usuario)
        return usuario

    async def alterar_senha(
        self,
        usuario_id: uuid.UUID,
        data: AlterarSenhaRequest,
        usuario_autenticado: str,
    ) -> None:
        """Altera a senha do usuário após verificar a senha atual."""
        stmt = select(Usuario).where(Usuario.id == usuario_id)
        result = await self.session.execute(stmt)
        usuario = result.scalar_one_or_none()

        if not usuario:
            raise UsuarioNaoEncontradoError()
        if not verify_password(data.senha_atual, usuario.senha_hash):
            raise AcessoNegadoError("Senha atual incorreta.")

        usuario.senha_hash = hash_password(data.nova_senha)
        usuario.atualizado_por = usuario_autenticado
        await self.session.flush()

    async def atualizar(
        self,
        usuario_id: uuid.UUID,
        data: UsuarioUpdate,
        usuario_autenticado: str,
    ) -> Usuario:
        stmt = select(Usuario).where(Usuario.id == usuario_id)
        result = await self.session.execute(stmt)
        usuario = result.scalar_one_or_none()
        if not usuario:
            raise UsuarioNaoEncontradoError()

        if data.nome is not None:
            usuario.nome = data.nome
        if data.ativo is not None:
            usuario.ativo = data.ativo

        usuario.atualizado_por = usuario_autenticado
        await self.session.flush()
        await self.session.refresh(usuario)
        return usuario
