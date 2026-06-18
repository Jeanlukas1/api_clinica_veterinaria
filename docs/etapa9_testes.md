# ETAPA 9 — Testes Automatizados
## API REST Clínica Veterinária

> **Status:** ⏳ Pendente  
> **Objetivo:** Implementar ≥ 10 testes cobrindo casos válidos, inválidos, regras de negócio, transições de estado e conflitos.

---

## 1. Configuração

### Stack de Testes

```
pytest==8.3.4
pytest-asyncio==0.24.0
pytest-cov==6.0.0
httpx==0.27.2      ← cliente HTTP assíncrono para FastAPI
anyio==4.7.0
```

### Banco de Dados Isolado

```python
# tests/conftest.py

# Usa banco separado: clinica_veterinaria_test
# Recria o schema antes de cada sessão de teste
# Usa transações revertidas por teste (rollback automático)
```

---

## 2. `conftest.py` — Fixtures Globais

```python
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine_test():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def session(engine_test):
    async with AsyncSession(engine_test) as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(session):
    app.dependency_overrides[get_db] = lambda: session
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# Fixtures de dados
@pytest.fixture
async def tutor_ativo(session) -> Tutor: ...

@pytest.fixture
async def animal_ativo(session, tutor_ativo) -> Animal: ...

@pytest.fixture
async def veterinario_ativo(session) -> Veterinario: ...

@pytest.fixture
async def consulta_agendada(session, animal_ativo, veterinario_ativo) -> Consulta: ...

@pytest.fixture
async def token_admin(client) -> str: ...
```

---

## 3. Plano de Testes (≥ 10)

### `test_tutores.py`

```python
# TC-001: Criar tutor com dados válidos
async def test_criar_tutor_valido(client, token_admin):
    response = await client.post("/tutores", json={
        "nome": "João Silva",
        "cpf": "529.982.247-25",
        "email": "joao@email.com",
        "telefone": "(11) 99999-9999"
    }, headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 201
    assert response.json()["cpf"] == "529.982.247-25"

# TC-002: CPF inválido rejeitado
async def test_criar_tutor_cpf_invalido(client, token_admin):
    response = await client.post("/tutores", json={"cpf": "111.111.111-11", ...})
    assert response.status_code == 422

# TC-003: RN-001 — Inativar tutor com animais ativos
async def test_inativar_tutor_com_animais_ativos(client, token_admin, animal_ativo):
    response = await client.patch(
        f"/tutores/{animal_ativo.tutor_id}",
        json={"ativo": False},
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert response.status_code == 422
    assert response.json()["error"] == "TUTOR_HAS_ACTIVE_ANIMALS"
```

### `test_animais.py`

```python
# TC-004: RN-002 — Data de nascimento futura rejeitada
async def test_animal_data_nascimento_futura(client, token_admin, tutor_ativo):
    response = await client.post("/animais", json={
        "data_nascimento": "2099-01-01", ...
    })
    assert response.status_code == 422

# TC-005: RN-003 — Microchip duplicado rejeitado
async def test_microchip_duplicado(client, token_admin, animal_ativo):
    response = await client.post("/animais", json={
        "microchip": animal_ativo.microchip, ...
    })
    assert response.status_code == 409
    assert response.json()["error"] == "MICROCHIP_DUPLICADO"

# TC-006: Peso zero rejeitado (RN-012)
async def test_peso_zero_invalido(client, token_admin, tutor_ativo):
    response = await client.post("/animais", json={"peso": 0, ...})
    assert response.status_code == 422
```

### `test_consultas.py`

```python
# TC-007: Máquina de estados — transição válida AGENDADA→CONFIRMADA
async def test_transicao_agendada_para_confirmada(client, token_admin, consulta_agendada):
    response = await client.patch(
        f"/consultas/{consulta_agendada.id}/status",
        json={"status": "CONFIRMADA"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMADA"

# TC-008: Transição inválida AGENDADA→CONCLUIDA (sem passar por EM_ANDAMENTO)
async def test_transicao_invalida_agendada_concluida(client, token_admin, consulta_agendada):
    response = await client.patch(
        f"/consultas/{consulta_agendada.id}/status",
        json={"status": "CONCLUIDA"}
    )
    assert response.status_code == 422
    assert response.json()["error"] == "TRANSICAO_INVALIDA"

# TC-009: RN-007 — Concluir sem diagnóstico rejeitado
async def test_concluir_sem_diagnostico(client, token_admin, consulta_em_andamento):
    response = await client.patch(
        f"/consultas/{consulta_em_andamento.id}/status",
        json={"status": "CONCLUIDA"}  # sem "diagnostico"
    )
    assert response.status_code == 422
    assert response.json()["error"] == "DIAGNOSTICO_OBRIGATORIO"

# TC-010: RN-008 — Editar consulta concluída rejeitado
async def test_editar_consulta_concluida_invalido(client, token_admin, consulta_concluida):
    response = await client.patch(
        f"/consultas/{consulta_concluida.id}",
        json={"observacoes": "Tentativa de edição"}
    )
    assert response.status_code == 422
    assert response.json()["error"] == "CONSULTA_IMUTAVEL"

# TC-011: RN-004 — Conflito de agenda veterinário
async def test_conflito_agenda_veterinario(client, token_admin, consulta_agendada, animal_ativo):
    response = await client.post("/consultas", json={
        "animal_id": str(animal_ativo.id),
        "veterinario_id": str(consulta_agendada.veterinario_id),
        "data_hora": consulta_agendada.data_hora.isoformat(),  # mesmo horário
        "tipo": "ROTINA"
    })
    assert response.status_code == 409
    assert response.json()["error"] == "CONSULTA_CONFLICT"

# TC-012: RN-006 — Emergência bypassa conflito de agenda
async def test_emergencia_bypassa_conflito(client, token_admin, consulta_agendada, animal_ativo):
    response = await client.post("/consultas", json={
        "animal_id": str(animal_ativo.id),
        "veterinario_id": str(consulta_agendada.veterinario_id),
        "data_hora": consulta_agendada.data_hora.isoformat(),
        "tipo": "EMERGENCIA"  # deve ser permitido
    })
    assert response.status_code == 201
```

### `test_transferencias.py`

```python
# TC-013: RN-010 — Transferência com motivo válido
async def test_transferencia_valida(client, token_admin, animal_ativo):
    tutor_novo = await criar_tutor_fixture(session)
    response = await client.post("/transferencias", json={
        "animal_id": str(animal_ativo.id),
        "tutor_destino_id": str(tutor_novo.id),
        "motivo": "Tutor original faleceu e família não pode cuidar"
    })
    assert response.status_code == 201
    # Verifica que o tutor do animal foi atualizado
    animal_response = await client.get(f"/animais/{animal_ativo.id}")
    assert animal_response.json()["tutor_id"] == str(tutor_novo.id)

# TC-014: RN-010 — Motivo muito curto rejeitado
async def test_transferencia_motivo_curto(client, token_admin, animal_ativo):
    response = await client.post("/transferencias", json={
        "motivo": "curto"  # < 10 chars
    })
    assert response.status_code == 422
    assert response.json()["error"] == "MOTIVO_OBRIGATORIO"
```

---

## 4. Cobertura Esperada

```bash
# Executar testes com cobertura
pytest app/tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# Meta de cobertura
--cov-fail-under=80
```

| Módulo | Cobertura Alvo |
|---|---|
| `services/` | ≥ 90% |
| `repositories/` | ≥ 85% |
| `routers/` | ≥ 80% |
| `models/` | ≥ 95% |
| `schemas/` | ≥ 90% |

---

## 5. Cenários de Borda

| Cenário | Teste |
|---|---|
| Animal com microchip=None — dois registros | TC-extra-001 |
| Consulta no exato limite de 30min | TC-extra-002 |
| Tutor com 0 animais sendo inativado | TC-extra-003 |
| Vacina com data_proxima = data_aplicacao | TC-extra-004 |
| Token expirado na requisição | TC-extra-005 |
| Perfil TUTOR acessando animal de outro tutor | TC-extra-006 |
