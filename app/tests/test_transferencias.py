"""
app/tests/test_transferencias.py
──────────────────────────────────
Testes para o recurso /transferencias.

Casos cobertos:
  TC-022: RN-010 — Transferência com motivo válido (HTTP 201)
  TC-023: RN-010 — Motivo muito curto rejeitado (HTTP 422)
  TC-024: Transferência para o mesmo tutor atual rejeitada (HTTP 409)
  TC-025: Após transferência, animal.tutor_id é atualizado
  TC-026: Auditoria é criada automaticamente após transferência
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.animal import Animal
from app.models.auditoria import Auditoria
from app.models.tutor import Tutor


pytestmark = pytest.mark.asyncio


class TestTransferencia:
    """TC-022 a TC-026 — RN-010."""

    async def test_TC022_transferencia_valida(
        self,
        client: AsyncClient,
        headers_admin: dict,
        animal_ativo: Animal,
        tutor_secundario: Tutor,
    ) -> None:
        """TC-022: Transferência com motivo válido deve retornar 201."""
        response = await client.post(
            "/transferencias",
            json={
                "animal_id": str(animal_ativo.id),
                "tutor_destino_id": str(tutor_secundario.id),
                "motivo": "Tutor original viajou ao exterior e não pode cuidar do animal.",
            },
            headers=headers_admin,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["animal_id"] == str(animal_ativo.id)
        assert body["tutor_destino_id"] == str(tutor_secundario.id)
        assert body["tutor_origem_id"] is not None

    async def test_TC023_motivo_curto_rejeitado(
        self,
        client: AsyncClient,
        headers_admin: dict,
        animal_ativo: Animal,
        tutor_secundario: Tutor,
    ) -> None:
        """
        TC-023: RN-010 — motivo com menos de 10 caracteres deve retornar 422
        com error=VALIDATION_ERROR (validado no schema Pydantic).
        """
        response = await client.post(
            "/transferencias",
            json={
                "animal_id": str(animal_ativo.id),
                "tutor_destino_id": str(tutor_secundario.id),
                "motivo": "curto",  # ← 5 chars, abaixo do mínimo
            },
            headers=headers_admin,
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"] == "VALIDATION_ERROR"
        erros = body["details"]["errors"]
        campos = [e["field"] for e in erros]
        assert any("motivo" in c for c in campos)

    async def test_TC024_mesmo_tutor_rejeitado(
        self,
        client: AsyncClient,
        headers_admin: dict,
        animal_ativo: Animal,
        tutor_ativo: Tutor,
    ) -> None:
        """TC-024: Transferir para o mesmo tutor atual deve retornar 409."""
        response = await client.post(
            "/transferencias",
            json={
                "animal_id": str(animal_ativo.id),
                "tutor_destino_id": str(tutor_ativo.id),  # ← mesmo tutor
                "motivo": "Tentativa de transferência inválida para o mesmo tutor",
            },
            headers=headers_admin,
        )
        assert response.status_code == 409
        assert response.json()["error"] == "TRANSFERENCIA_MESMO_TUTOR"

    async def test_TC025_animal_atualizado_apos_transferencia(
        self,
        client: AsyncClient,
        headers_admin: dict,
        animal_ativo: Animal,
        tutor_secundario: Tutor,
        session: AsyncSession,
    ) -> None:
        """
        TC-025: Após transferência bem-sucedida, animal.tutor_id deve
        apontar para o novo tutor.
        """
        tutor_original_id = animal_ativo.tutor_id

        # Executa transferência
        resp = await client.post(
            "/transferencias",
            json={
                "animal_id": str(animal_ativo.id),
                "tutor_destino_id": str(tutor_secundario.id),
                "motivo": "Mudança de responsabilidade por motivo de saúde do tutor.",
            },
            headers=headers_admin,
        )
        assert resp.status_code == 201

        # Verifica que o animal foi atualizado no banco
        await session.refresh(animal_ativo)
        assert animal_ativo.tutor_id == tutor_secundario.id
        assert animal_ativo.tutor_id != tutor_original_id

    async def test_TC026_auditoria_criada_automaticamente(
        self,
        client: AsyncClient,
        headers_admin: dict,
        animal_ativo: Animal,
        tutor_secundario: Tutor,
        session: AsyncSession,
    ) -> None:
        """
        TC-026: Transferência deve gerar registro na tabela auditorias
        com evento=TRANSFERENCIA_ANIMAL (RN-010).
        """
        # Executa transferência
        resp = await client.post(
            "/transferencias",
            json={
                "animal_id": str(animal_ativo.id),
                "tutor_destino_id": str(tutor_secundario.id),
                "motivo": "Tutor cedeu o animal a familiar por questões financeiras.",
            },
            headers=headers_admin,
        )
        assert resp.status_code == 201

        # Verifica auditoria no banco
        stmt = select(Auditoria).where(
            Auditoria.entidade == "animais",
            Auditoria.entidade_id == animal_ativo.id,
            Auditoria.evento == "TRANSFERENCIA_ANIMAL",
        )
        result = await session.execute(stmt)
        auditoria = result.scalar_one_or_none()

        assert auditoria is not None
        assert auditoria.payload is not None
        assert str(tutor_secundario.id) in auditoria.payload.get("tutor_destino_id", "")


class TestVacinas:
    """Testes de vacinas cobrindo RN-009."""

    async def test_vacina_data_aplicacao_nao_futura(
        self,
        client: AsyncClient,
        headers_admin: dict,
        animal_ativo: Animal,
    ) -> None:
        """RN-009: Data de aplicação futura deve retornar 422."""
        response = await client.post(
            "/vacinas",
            json={
                "animal_id": str(animal_ativo.id),
                "nome_vacina": "Antirrábica",
                "lote": "LT2024A",
                "data_aplicacao": "2099-12-31",  # ← futura
            },
            headers=headers_admin,
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"] == "VALIDATION_ERROR"

    async def test_vacina_data_proxima_anterior_rejeitada(
        self,
        client: AsyncClient,
        headers_admin: dict,
        animal_ativo: Animal,
    ) -> None:
        """Cross-field: data_proxima deve ser posterior à data_aplicacao."""
        response = await client.post(
            "/vacinas",
            json={
                "animal_id": str(animal_ativo.id),
                "nome_vacina": "V10",
                "lote": "LT2024B",
                "data_aplicacao": "2024-01-15",
                "data_proxima": "2024-01-14",  # ← anterior à aplicação
            },
            headers=headers_admin,
        )
        assert response.status_code == 422

    async def test_vacina_valida_criada(
        self,
        client: AsyncClient,
        headers_admin: dict,
        animal_ativo: Animal,
    ) -> None:
        """Vacina com dados válidos deve ser criada com status 201."""
        response = await client.post(
            "/vacinas",
            json={
                "animal_id": str(animal_ativo.id),
                "nome_vacina": "Antirrábica",
                "lote": "LT2025A",
                "data_aplicacao": "2024-06-01",
                "data_proxima": "2025-06-01",
            },
            headers=headers_admin,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["nome_vacina"] == "Antirrábica"
        assert body["data_aplicacao"] == "2024-06-01"
