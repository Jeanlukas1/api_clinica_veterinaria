"""
app/tests/test_consultas.py
────────────────────────────
Testes para o recurso /consultas — foco na máquina de estados.

Casos cobertos:
  TC-013: Transição válida AGENDADA → CONFIRMADA (HTTP 200)
  TC-014: Transição inválida AGENDADA → CONCLUIDA (HTTP 422 TRANSICAO_INVALIDA)
  TC-015: RN-007 — Concluir sem diagnóstico rejeitado (HTTP 422 DIAGNOSTICO_OBRIGATORIO)
  TC-016: RN-007 — Concluir com diagnóstico preenchido (HTTP 200)
  TC-017: RN-008 — Editar consulta concluída bloqueado (HTTP 422 CONSULTA_IMUTAVEL)
  TC-018: RN-008 — Mudar status de consulta cancelada bloqueado
  TC-019: RN-004 — Conflito de agenda retorna 409
  TC-020: RN-006 — Emergência bypassa conflito de agenda (HTTP 201)
  TC-021: Fluxo completo AGENDADA → CONFIRMADA → EM_ANDAMENTO → CONCLUIDA
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.models.animal import Animal
from app.models.consulta import Consulta
from app.models.tutor import Tutor
from app.models.veterinario import Veterinario


pytestmark = pytest.mark.asyncio


class TestTransicaoEstado:
    """TC-013 / TC-014 — Máquina de estados."""

    async def test_TC013_transicao_valida_agendada_para_confirmada(
        self,
        client: AsyncClient,
        headers_admin: dict,
        consulta_agendada: Consulta,
    ) -> None:
        """TC-013: AGENDADA → CONFIRMADA deve funcionar e retornar 200."""
        response = await client.patch(
            f"/consultas/{consulta_agendada.id}/status",
            json={"status": "CONFIRMADA"},
            headers=headers_admin,
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "CONFIRMADA"

    async def test_TC014_transicao_invalida_agendada_para_concluida(
        self,
        client: AsyncClient,
        headers_admin: dict,
        consulta_agendada: Consulta,
    ) -> None:
        """
        TC-014: AGENDADA → CONCLUIDA é transição inválida.
        Deve retornar 422 com error=TRANSICAO_INVALIDA.
        """
        response = await client.patch(
            f"/consultas/{consulta_agendada.id}/status",
            json={"status": "CONCLUIDA", "diagnostico": "Tentativa"},
            headers=headers_admin,
        )
        assert response.status_code == 422
        assert response.json()["error"] == "TRANSICAO_INVALIDA"

    async def test_TC014b_transicao_invalida_concluida_para_cancelada(
        self,
        client: AsyncClient,
        headers_admin: dict,
        consulta_concluida: Consulta,
    ) -> None:
        """TC-014b: CONCLUIDA → CANCELADA é inválida (CONCLUIDA é terminal)."""
        response = await client.patch(
            f"/consultas/{consulta_concluida.id}/status",
            json={"status": "CANCELADA"},
            headers=headers_admin,
        )
        assert response.status_code == 422
        # Terminal → imutável (RN-008 tem precedência sobre transição inválida)
        assert response.json()["error"] in ("CONSULTA_IMUTAVEL", "TRANSICAO_INVALIDA")


class TestDiagnosticoObrigatorio:
    """TC-015 / TC-016 — RN-007."""

    async def test_TC015_concluir_sem_diagnostico_rejeitado(
        self,
        client: AsyncClient,
        headers_admin: dict,
        consulta_em_andamento: Consulta,
    ) -> None:
        """
        TC-015: RN-007 — concluir consulta sem diagnóstico deve retornar 422
        com error=DIAGNOSTICO_OBRIGATORIO.
        """
        response = await client.patch(
            f"/consultas/{consulta_em_andamento.id}/status",
            json={"status": "CONCLUIDA"},  # ← sem diagnóstico
            headers=headers_admin,
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"] == "DIAGNOSTICO_OBRIGATORIO"

    async def test_TC016_concluir_com_diagnostico_aceito(
        self,
        client: AsyncClient,
        headers_admin: dict,
        consulta_em_andamento: Consulta,
    ) -> None:
        """TC-016: RN-007 — concluir com diagnóstico preenchido deve retornar 200."""
        response = await client.patch(
            f"/consultas/{consulta_em_andamento.id}/status",
            json={
                "status": "CONCLUIDA",
                "diagnostico": "Animal saudável, exames normais.",
            },
            headers=headers_admin,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "CONCLUIDA"
        assert body["diagnostico"] == "Animal saudável, exames normais."


class TestConsultaImutavel:
    """TC-017 / TC-018 — RN-008: estado terminal é imutável."""

    async def test_TC017_editar_consulta_concluida_bloqueado(
        self,
        client: AsyncClient,
        headers_admin: dict,
        consulta_concluida: Consulta,
    ) -> None:
        """
        TC-017: RN-008 — atualizar campos de consulta CONCLUIDA deve retornar 422
        com error=CONSULTA_IMUTAVEL.
        """
        response = await client.patch(
            f"/consultas/{consulta_concluida.id}",
            json={"observacoes": "Tentativa de edição após conclusão"},
            headers=headers_admin,
        )
        assert response.status_code == 422
        assert response.json()["error"] == "CONSULTA_IMUTAVEL"

    async def test_TC018_mudar_status_consulta_cancelada_bloqueado(
        self,
        client: AsyncClient,
        headers_admin: dict,
        consulta_agendada: Consulta,
    ) -> None:
        """
        TC-018: RN-008 — cancelar consulta e depois tentar mudar status
        deve ser bloqueado (CANCELADA é estado terminal).
        """
        # Passo 1: cancela a consulta
        resp1 = await client.patch(
            f"/consultas/{consulta_agendada.id}/status",
            json={"status": "CANCELADA"},
            headers=headers_admin,
        )
        assert resp1.status_code == 200

        # Passo 2: tenta mudar novamente — deve ser bloqueado
        resp2 = await client.patch(
            f"/consultas/{consulta_agendada.id}/status",
            json={"status": "CONFIRMADA"},
            headers=headers_admin,
        )
        assert resp2.status_code == 422
        assert resp2.json()["error"] == "CONSULTA_IMUTAVEL"


class TestConflitoAgenda:
    """TC-019 / TC-020 — RN-004 e RN-006."""

    async def test_TC019_conflito_agenda_retorna_409(
        self,
        client: AsyncClient,
        headers_admin: dict,
        consulta_agendada: Consulta,
        animal_ativo: Animal,
    ) -> None:
        """
        TC-019: RN-004 — tentar agendar no mesmo horário do veterinário
        (dentro da janela de 30min) deve retornar 409 CONSULTA_CONFLICT.
        """
        # Usa o mesmo horário e veterinário da consulta existente
        response = await client.post(
            "/consultas",
            json={
                "animal_id": str(animal_ativo.id),
                "veterinario_id": str(consulta_agendada.veterinario_id),
                "data_hora": consulta_agendada.data_hora.isoformat(),  # horário idêntico
                "tipo": "ROTINA",
            },
            headers=headers_admin,
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"] == "CONSULTA_CONFLICT"

    async def test_TC020_emergencia_bypassa_conflito(
        self,
        client: AsyncClient,
        headers_admin: dict,
        consulta_agendada: Consulta,
        animal_ativo: Animal,
    ) -> None:
        """
        TC-020: RN-006 — emergência deve ser criada mesmo com conflito de agenda.
        Deve retornar 201.
        """
        response = await client.post(
            "/consultas",
            json={
                "animal_id": str(animal_ativo.id),
                "veterinario_id": str(consulta_agendada.veterinario_id),
                "data_hora": consulta_agendada.data_hora.isoformat(),
                "tipo": "EMERGENCIA",  # ← bypassa RN-004
            },
            headers=headers_admin,
        )
        assert response.status_code == 201, response.text
        assert response.json()["tipo"] == "EMERGENCIA"


class TestFluxoCompleto:
    """TC-021 — Fluxo de ponta a ponta da consulta."""

    async def test_TC021_fluxo_completo_consulta(
        self,
        client: AsyncClient,
        headers_admin: dict,
        animal_ativo: Animal,
        veterinario_ativo: Veterinario,
    ) -> None:
        """
        TC-021: Fluxo completo da máquina de estados.
        AGENDADA → CONFIRMADA → EM_ANDAMENTO → CONCLUIDA
        """
        amanha = (
            datetime.now(timezone.utc) + timedelta(days=5)
        ).isoformat()

        # 1. Agendar
        r1 = await client.post(
            "/consultas",
            json={
                "animal_id": str(animal_ativo.id),
                "veterinario_id": str(veterinario_ativo.id),
                "data_hora": amanha,
                "tipo": "RETORNO",
            },
            headers=headers_admin,
        )
        assert r1.status_code == 201
        consulta_id = r1.json()["id"]
        assert r1.json()["status"] == "AGENDADA"

        # 2. Confirmar
        r2 = await client.patch(
            f"/consultas/{consulta_id}/status",
            json={"status": "CONFIRMADA"},
            headers=headers_admin,
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "CONFIRMADA"

        # 3. Iniciar atendimento
        r3 = await client.patch(
            f"/consultas/{consulta_id}/status",
            json={"status": "EM_ANDAMENTO"},
            headers=headers_admin,
        )
        assert r3.status_code == 200
        assert r3.json()["status"] == "EM_ANDAMENTO"

        # 4. Concluir (com diagnóstico)
        r4 = await client.patch(
            f"/consultas/{consulta_id}/status",
            json={
                "status": "CONCLUIDA",
                "diagnostico": "Animal saudável. Recomendado retorno em 6 meses.",
            },
            headers=headers_admin,
        )
        assert r4.status_code == 200
        assert r4.json()["status"] == "CONCLUIDA"
        assert r4.json()["diagnostico"] == "Animal saudável. Recomendado retorno em 6 meses."

        # 5. Tentar alterar após conclusão — deve falhar
        r5 = await client.patch(
            f"/consultas/{consulta_id}/status",
            json={"status": "CANCELADA"},
            headers=headers_admin,
        )
        assert r5.status_code == 422
        assert r5.json()["error"] == "CONSULTA_IMUTAVEL"
