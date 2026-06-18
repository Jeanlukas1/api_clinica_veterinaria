"""
app/audit/service.py
─────────────────────
Serviço transversal de auditoria — registra eventos críticos do sistema.

É injetado nos services que precisam gerar eventos de auditoria:
  - TutorService (inativação)
  - AnimalService (atualização de peso)
  - ConsultaService (conclusão, cancelamento, emergência sobreposta)
  - TransferenciaService (transferência de animal)
  - AuthService (login)

Decisão de design:
  - Separado como serviço independente para não poluir os services de domínio
  - Append-only: nunca atualiza ou deleta registros
  - Captura IP do request via contexto quando disponível
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auditoria import Auditoria
from app.models.enums import EventoAuditoria


class AuditoriaService:
    """
    Serviço de auditoria — registra eventos como logs imutáveis no banco.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def registrar(
        self,
        evento: EventoAuditoria,
        entidade: str,
        entidade_id: uuid.UUID,
        usuario: str,
        payload: dict | None = None,
        ip_address: str | None = None,
    ) -> Auditoria:
        """
        Cria um novo registro de auditoria.

        Args:
            evento:      Tipo do evento (EventoAuditoria enum)
            entidade:    Nome da tabela afetada (ex: "animais")
            entidade_id: UUID do registro afetado
            usuario:     Email do usuário que realizou a ação
            payload:     Dados antes/depois em formato dict (armazenado em JSONB)
            ip_address:  IP da requisição (opcional)

        Returns:
            Objeto Auditoria persistido.
        """
        auditoria = Auditoria(
            evento=evento.value,
            entidade=entidade,
            entidade_id=entidade_id,
            usuario=usuario,
            payload=payload,
            ip_address=ip_address,
        )
        self.session.add(auditoria)
        await self.session.flush()
        return auditoria

    async def registrar_inativacao(
        self,
        entidade: str,
        entidade_id: uuid.UUID,
        usuario: str,
        dados_anteriores: dict,
        ip_address: str | None = None,
    ) -> Auditoria:
        """Atalho para registrar inativação de entidade."""
        evento_map = {
            "tutores": EventoAuditoria.INATIVACAO_TUTOR,
            "animais": EventoAuditoria.INATIVACAO_ANIMAL,
            "veterinarios": EventoAuditoria.INATIVACAO_VETERINARIO,
        }
        evento = evento_map.get(entidade, EventoAuditoria.INATIVACAO_TUTOR)
        return await self.registrar(
            evento=evento,
            entidade=entidade,
            entidade_id=entidade_id,
            usuario=usuario,
            payload={"antes": dados_anteriores},
            ip_address=ip_address,
        )
