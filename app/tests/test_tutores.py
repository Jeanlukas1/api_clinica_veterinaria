"""
app/tests/test_tutores.py
──────────────────────────
Testes para o recurso /tutores.

Casos cobertos:
  TC-001: Criar tutor com dados válidos (CPF correto, email único)
  TC-002: CPF com dígito verificador inválido é rejeitado (HTTP 422)
  TC-003: RN-001 — Inativar tutor com animais ativos é bloqueado (HTTP 422)
  TC-004: Email duplicado retorna HTTP 409
  TC-005: CPF duplicado retorna HTTP 409
  TC-006: Listar tutores paginado com filtro de nome
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.animal import Animal
from app.models.tutor import Tutor


pytestmark = pytest.mark.asyncio


class TestCriarTutor:
    """TC-001 / TC-002 / TC-004 / TC-005 — criação de tutores."""

    async def test_TC001_criar_tutor_valido(
        self, client: AsyncClient, headers_admin: dict
    ) -> None:
        """TC-001: Tutor com dados válidos deve ser criado com status 201."""
        response = await client.post(
            "/tutores",
            json={
                "nome": "João Pereira",
                "cpf": "529.982.247-25",
                "email": "joao.pereira@email.com",
                "telefone": "(11) 98765-4321",
            },
            headers=headers_admin,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["nome"] == "João Pereira"
        assert body["cpf"] == "529.982.247-25"
        assert body["email"] == "joao.pereira@email.com"
        assert body["ativo"] is True
        assert "id" in body

    async def test_TC002_cpf_invalido_rejeitado(
        self, client: AsyncClient, headers_admin: dict
    ) -> None:
        """TC-002: CPF com dígitos verificadores inválidos deve retornar 422."""
        response = await client.post(
            "/tutores",
            json={
                "nome": "Tutor Inválido",
                "cpf": "111.111.111-11",   # todos iguais — inválido
                "email": "invalido@test.com",
                "telefone": "(11) 99999-0000",
            },
            headers=headers_admin,
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"] == "VALIDATION_ERROR"

    async def test_TC002b_cpf_com_digito_errado(
        self, client: AsyncClient, headers_admin: dict
    ) -> None:
        """TC-002b: CPF estruturalmente plausível mas dígito verificador errado."""
        response = await client.post(
            "/tutores",
            json={
                "nome": "Tutor Inválido",
                "cpf": "529.982.247-99",   # dígitos verificadores errados
                "email": "invalido2@test.com",
                "telefone": "(11) 99999-0001",
            },
            headers=headers_admin,
        )
        assert response.status_code == 422

    async def test_TC004_email_duplicado_retorna_409(
        self, client: AsyncClient, headers_admin: dict, tutor_ativo: Tutor
    ) -> None:
        """TC-004: Mesmo e-mail de tutor existente deve retornar 409."""
        response = await client.post(
            "/tutores",
            json={
                "nome": "Outro Carlos",
                "cpf": "048.576.853-03",     # CPF diferente
                "email": tutor_ativo.email,  # email duplicado
                "telefone": "(11) 99999-3333",
            },
            headers=headers_admin,
        )
        assert response.status_code == 409
        assert response.json()["error"] == "EMAIL_DUPLICADO"

    async def test_TC005_cpf_duplicado_retorna_409(
        self, client: AsyncClient, headers_admin: dict, tutor_ativo: Tutor
    ) -> None:
        """TC-005: Mesmo CPF de tutor existente deve retornar 409."""
        response = await client.post(
            "/tutores",
            json={
                "nome": "Outro Tutor",
                "cpf": tutor_ativo.cpf,       # CPF duplicado
                "email": "diferente@test.com",
                "telefone": "(11) 99999-4444",
            },
            headers=headers_admin,
        )
        assert response.status_code == 409
        assert response.json()["error"] == "CPF_DUPLICADO"


class TestInativarTutor:
    """TC-003 — RN-001."""

    async def test_TC003_inativar_tutor_com_animais_ativos_bloqueado(
        self,
        client: AsyncClient,
        headers_admin: dict,
        tutor_ativo: Tutor,
        animal_ativo: Animal,
    ) -> None:
        """
        TC-003: RN-001 — inativar tutor com animais ativos deve retornar 422
        com error=TUTOR_HAS_ACTIVE_ANIMALS.
        """
        response = await client.patch(
            f"/tutores/{tutor_ativo.id}",
            json={"ativo": False},
            headers=headers_admin,
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"] == "TUTOR_HAS_ACTIVE_ANIMALS"
        assert body["details"]["animais_ativos"] >= 1

    async def test_TC003b_inativar_tutor_sem_animais_permitido(
        self,
        client: AsyncClient,
        headers_admin: dict,
        tutor_ativo: Tutor,
    ) -> None:
        """TC-003b: Tutor sem animais ativos pode ser inativado normalmente."""
        response = await client.patch(
            f"/tutores/{tutor_ativo.id}",
            json={"ativo": False},
            headers=headers_admin,
        )
        assert response.status_code == 200
        assert response.json()["ativo"] is False


class TestListarTutores:
    """TC-006 — Paginação e filtro."""

    async def test_TC006_listar_tutores_paginado(
        self,
        client: AsyncClient,
        headers_admin: dict,
        tutor_ativo: Tutor,
    ) -> None:
        """TC-006: GET /tutores deve retornar estrutura paginada com o tutor criado."""
        response = await client.get(
            "/tutores?limit=10&offset=0",
            headers=headers_admin,
        )
        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 1
        # Verifica que o tutor da fixture está na lista
        ids = [item["id"] for item in body["items"]]
        assert str(tutor_ativo.id) in ids

    async def test_TC006b_filtro_por_nome(
        self,
        client: AsyncClient,
        headers_admin: dict,
        tutor_ativo: Tutor,
    ) -> None:
        """TC-006b: Filtro por nome parcial deve funcionar."""
        nome_parcial = tutor_ativo.nome[:5]  # primeiros 5 chars
        response = await client.get(
            f"/tutores?nome={nome_parcial}",
            headers=headers_admin,
        )
        assert response.status_code == 200
        ids = [item["id"] for item in response.json()["items"]]
        assert str(tutor_ativo.id) in ids
