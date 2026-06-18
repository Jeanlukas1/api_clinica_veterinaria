"""
app/tests/test_animais.py
──────────────────────────
Testes para o recurso /animais.

Casos cobertos:
  TC-007: RN-002 — data_nascimento futura rejeitada (HTTP 422)
  TC-008: RN-003 — microchip duplicado rejeitado (HTTP 409)
  TC-009: RN-012 — peso zero rejeitado (HTTP 422)
  TC-010: Dois animais sem microchip são permitidos (unicidade parcial)
  TC-011: Criar animal com dados válidos (HTTP 201)
  TC-012: Histórico clínico retorna estrutura consolidada
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.animal import Animal
from app.models.tutor import Tutor
from app.models.veterinario import Veterinario


pytestmark = pytest.mark.asyncio


class TestCriarAnimal:
    """TC-007 / TC-008 / TC-009 / TC-010 / TC-011 — criação de animais."""

    async def test_TC011_criar_animal_valido(
        self,
        client: AsyncClient,
        headers_admin: dict,
        tutor_ativo: Tutor,
    ) -> None:
        """TC-011: Animal com dados válidos deve ser criado com status 201."""
        response = await client.post(
            "/animais",
            json={
                "tutor_id": str(tutor_ativo.id),
                "nome": "Bolinha",
                "especie": "CANINO",
                "raca": "Poodle",
                "sexo": "M",
                "data_nascimento": "2021-06-15",
                "peso": "5.30",
                "microchip": "XYZ9876543210",
            },
            headers=headers_admin,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["nome"] == "Bolinha"
        assert body["especie"] == "CANINO"
        assert body["tutor_id"] == str(tutor_ativo.id)
        assert body["ativo"] is True

    async def test_TC007_data_nascimento_futura_rejeitada(
        self,
        client: AsyncClient,
        headers_admin: dict,
        tutor_ativo: Tutor,
    ) -> None:
        """TC-007: RN-002 — data de nascimento futura deve retornar 422."""
        response = await client.post(
            "/animais",
            json={
                "tutor_id": str(tutor_ativo.id),
                "nome": "Futuro",
                "especie": "CANINO",
                "sexo": "M",
                "data_nascimento": "2099-01-01",  # ← data futura
                "peso": "10.0",
            },
            headers=headers_admin,
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"] == "VALIDATION_ERROR"
        # Verifica que a mensagem menciona data_nascimento
        erros = body["details"]["errors"]
        campos = [e["field"] for e in erros]
        assert any("data_nascimento" in c for c in campos)

    async def test_TC008_microchip_duplicado_rejeitado(
        self,
        client: AsyncClient,
        headers_admin: dict,
        tutor_ativo: Tutor,
        animal_ativo: Animal,
    ) -> None:
        """TC-008: RN-003 — microchip já cadastrado deve retornar 409."""
        response = await client.post(
            "/animais",
            json={
                "tutor_id": str(tutor_ativo.id),
                "nome": "Outro Animal",
                "especie": "FELINO",
                "sexo": "F",
                "data_nascimento": "2020-01-01",
                "peso": "4.0",
                "microchip": animal_ativo.microchip,  # ← duplicado
            },
            headers=headers_admin,
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"] == "MICROCHIP_DUPLICADO"
        assert animal_ativo.microchip in str(body["details"])

    async def test_TC009_peso_zero_rejeitado(
        self,
        client: AsyncClient,
        headers_admin: dict,
        tutor_ativo: Tutor,
    ) -> None:
        """TC-009: RN-012 — peso zero deve retornar 422."""
        response = await client.post(
            "/animais",
            json={
                "tutor_id": str(tutor_ativo.id),
                "nome": "SemPeso",
                "especie": "CANINO",
                "sexo": "M",
                "data_nascimento": "2020-01-01",
                "peso": "0",  # ← peso zero
            },
            headers=headers_admin,
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"] == "VALIDATION_ERROR"

    async def test_TC009b_peso_negativo_rejeitado(
        self,
        client: AsyncClient,
        headers_admin: dict,
        tutor_ativo: Tutor,
    ) -> None:
        """TC-009b: Peso negativo também deve ser rejeitado."""
        response = await client.post(
            "/animais",
            json={
                "tutor_id": str(tutor_ativo.id),
                "nome": "SemPeso",
                "especie": "CANINO",
                "sexo": "M",
                "data_nascimento": "2020-01-01",
                "peso": "-5.0",  # ← negativo
            },
            headers=headers_admin,
        )
        assert response.status_code == 422

    async def test_TC010_dois_animais_sem_microchip_permitidos(
        self,
        client: AsyncClient,
        headers_admin: dict,
        tutor_ativo: Tutor,
        animal_sem_microchip: Animal,
    ) -> None:
        """
        TC-010: Cenário de borda — dois animais sem microchip são permitidos.
        Demonstra o índice único parcial (WHERE microchip IS NOT NULL).
        """
        response = await client.post(
            "/animais",
            json={
                "tutor_id": str(tutor_ativo.id),
                "nome": "Outro Sem Microchip",
                "especie": "AVE",
                "sexo": "M",
                "data_nascimento": "2022-03-10",
                "peso": "0.3",
                # microchip ausente — null
            },
            headers=headers_admin,
        )
        # Deve criar com sucesso (NULL não viola o índice UNIQUE parcial)
        assert response.status_code == 201, response.text
        assert response.json()["microchip"] is None


class TestHistoricoAnimal:
    """TC-012 — Histórico clínico consolidado."""

    async def test_TC012_historico_retorna_estrutura_consolidada(
        self,
        client: AsyncClient,
        headers_admin: dict,
        animal_ativo: Animal,
        consulta_concluida,  # fixture — garante que há consulta no histórico
    ) -> None:
        """TC-012: GET /animais/{id}/historico deve retornar estrutura completa."""
        response = await client.get(
            f"/animais/{animal_ativo.id}/historico",
            headers=headers_admin,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        # Valida estrutura do histórico clínico
        assert "animal" in body
        assert "tutor_atual" in body
        assert "consultas" in body
        assert "vacinas" in body
        assert "evolucao_peso" in body
        assert "resumo" in body
        # Verifica que a consulta concluída aparece no histórico
        ids_consultas = [c["id"] for c in body["consultas"]]
        assert str(consulta_concluida.id) in ids_consultas
        # Verifica resumo estatístico
        assert body["resumo"]["total_consultas"] >= 1

    async def test_TC012b_resumo_estatistico(
        self,
        client: AsyncClient,
        headers_admin: dict,
        animal_ativo: Animal,
    ) -> None:
        """TC-012b: GET /animais/{id}/resumo deve retornar estatísticas calculadas."""
        response = await client.get(
            f"/animais/{animal_ativo.id}/resumo",
            headers=headers_admin,
        )
        assert response.status_code == 200
        body = response.json()
        assert "total_consultas" in body
        assert "total_vacinas" in body
        assert "idade_anos" in body
        assert body["idade_anos"] > 0  # animal nascido em 2020
