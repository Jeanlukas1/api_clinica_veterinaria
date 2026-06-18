# 🐾 API REST — Clínica Veterinária

> **Projeto Acadêmico** — Disciplina de Engenharia de Software  
> Stack: **FastAPI · PostgreSQL · SQLAlchemy 2.0 · Alembic · Pydantic V2 · JWT · Docker**

---

## 📋 Descrição do Domínio

Sistema de gerenciamento completo para clínicas veterinárias. Permite:

- Cadastro de **tutores** (donos de animais) e seus **animais**
- Agendamento e gestão de **consultas veterinárias** com máquina de estados
- Registro de **vacinas** e acompanhamento de doses futuras
- **Histórico clínico consolidado** por animal
- **Transferência de guarda** entre tutores com auditoria obrigatória
- **Autenticação JWT** com controle de acesso por perfil (RBAC)

---

## 🗂️ Diagrama ER — ASCII

```
┌─────────────┐        ┌─────────────┐        ┌─────────────────┐
│   TUTORES   │ 1 ── N │   ANIMAIS   │ 1 ── N │    CONSULTAS    │
│─────────────│        │─────────────│        │─────────────────│
│ id (UUID)   │        │ id (UUID)   │        │ id (UUID)       │
│ nome        │        │ tutor_id FK │        │ animal_id FK    │
│ cpf (único) │        │ nome        │        │ veterinario_id  │
│ email       │        │ especie     │        │ data_hora       │
│ telefone    │        │ raca        │        │ status (FSM)    │
│ ativo       │        │ sexo        │        │ tipo            │
└─────────────┘        │ data_nasc.  │        │ diagnostico     │
       │               │ peso        │        │ observacoes     │
       │               │ microchip   │        └─────────────────┘
       │               │ ativo       │               │
       │               └─────────────┘          1   │   N
       │                     │                       ▼
       │               1 ── N│              ┌─────────────────┐
       │               ▼     │              │     VACINAS     │
       │         ┌───────────┤              │─────────────────│
       │         │  VACINAS  │◄─────────────│ animal_id FK    │
       │         │  (direto) │              │ consulta_id FK? │
       │         └───────────┘              │ nome_vacina     │
       │                                   │ lote            │
       │         ┌──────────────────────┐   │ data_aplicacao  │
       ├─────────► TRANSFERENCIAS_ANIM.  │  │ data_proxima   │
       │ (orig.) │──────────────────────│   └─────────────────┘
       └─────────► tutor_origem_id FK   │
         (dest.) │ tutor_destino_id FK  │   ┌─────────────────┐
                 │ animal_id FK         │   │  VETERINARIOS   │
                 │ motivo               │   │─────────────────│
                 │ data_transferencia   │   │ id (UUID)       │
                 └──────────────────────┘   │ nome            │
                                            │ crmv (único)   │
┌──────────────────────┐                    │ especialidade   │
│     AUDITORIAS       │                    │ ativo           │
│──────────────────────│                    └─────────────────┘
│ evento (enum)        │
│ entidade + id        │   ┌──────────────┐
│ usuario              │   │   USUARIOS   │
│ payload (JSONB)      │   │──────────────│
│ timestamp            │   │ email (único)│
│ ip_address           │   │ senha_hash   │
└──────────────────────┘   │ perfil       │
  (append-only)            │ tutor_id FK? │
                           │ vet_id FK?   │
                           └──────────────┘
```

---

## 📏 Regras de Negócio

| ID | Descrição | Violação |
|---|---|---|
| RN-001 | Tutor com animais ativos não pode ser inativado | HTTP 422 |
| RN-002 | Data de nascimento do animal não pode ser futura | HTTP 422 |
| RN-003 | Microchip deve ser único (entre animais com microchip) | HTTP 409 |
| RN-004 | Veterinário não pode ter consultas sobrepostas (±30min) | HTTP 409 |
| RN-005 | Consultas não podem ser agendadas no passado | HTTP 422 |
| RN-006 | Emergências ignoram conflito de agenda (mas geram auditoria) | — |
| RN-007 | Diagnóstico é obrigatório para concluir consulta | HTTP 422 |
| RN-008 | Consultas concluídas/canceladas são imutáveis | HTTP 422 |
| RN-009 | Data de aplicação de vacina não pode ser futura | HTTP 422 |
| RN-010 | Transferência exige motivo (≥10 chars) e gera auditoria | HTTP 422 |
| RN-011 | Veterinário inativo não pode receber consultas | HTTP 422 |
| RN-012 | Peso do animal deve ser maior que zero | HTTP 422 |

---

## 🔄 Máquina de Estados — Consulta

```
AGENDADA ──[confirmar]──► CONFIRMADA ──[iniciar]──► EM_ANDAMENTO ──[concluir*]──► CONCLUÍDA ✓
    │                          │                                                   (terminal)
    └──[cancelar]──►           └──[cancelar]──► CANCELADA ✗
                               CANCELADA ✗                (terminal)
                               (terminal)

* concluir exige diagnóstico preenchido (RN-007)
```

---

## 🚀 Como Executar

### Pré-requisitos

- [Docker](https://docker.com) e [Docker Compose](https://docs.docker.com/compose/)

### 1. Clonar e configurar

```bash
git clone <repo-url>
cd api_clinica_veterinaria
cp .env.example .env
# Edite .env com suas credenciais se necessário
```

### 2. Subir os serviços

```bash
docker compose up --build
```

### 3. Aplicar migrations (automático no startup)

```bash
# Se precisar rodar manualmente:
docker compose exec api alembic upgrade head
```

### 4. Acessar a API

| URL | Descrição |
|---|---|
| http://localhost:8000/docs | Swagger UI (documentação interativa) |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health | Health check |

### 5. Login inicial

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@clinica.com", "password": "Admin@123456"}'
```

---

## 🧪 Como Rodar os Testes

```bash
# Dentro do container
docker compose exec api pytest app/tests/ -v --cov=app --cov-report=term-missing

# Ou localmente (com banco de teste rodando)
pytest app/tests/ -v --cov=app
```

---

## 🏗️ Arquitetura em Camadas

```
┌────────────────────────────────────────┐
│           ROUTERS (FastAPI)            │  ← HTTP, schemas Pydantic, RBAC
├────────────────────────────────────────┤
│           SERVICES                     │  ← Regras de negócio (RN-001..012)
├────────────────────────────────────────┤
│           REPOSITORIES                 │  ← Queries SQLAlchemy async
├────────────────────────────────────────┤
│           MODELS                       │  ← SQLAlchemy 2.0, enums, FSM
├────────────────────────────────────────┤
│           PostgreSQL                   │  ← UUID PKs, JSONB, índices parciais
└────────────────────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```
api_clinica_veterinaria/
├── docs/                    ← Documentação completa
├── alembic/versions/        ← 3 migrations versionadas
├── app/
│   ├── core/               ← config, security, exceptions
│   ├── database/           ← engine, session, base
│   ├── models/             ← SQLAlchemy + enums + FSM
│   ├── schemas/            ← Pydantic V2
│   ├── repositories/       ← acesso ao banco
│   ├── services/           ← regras de negócio
│   ├── routers/            ← endpoints FastAPI
│   ├── audit/              ← serviço de auditoria
│   └── tests/              ← pytest
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── requirements.txt
```

---

## 🔐 Perfis e Permissões

| Perfil | Acesso |
|---|---|
| **ADMIN** | Acesso total |
| **VETERINÁRIO** | Consultas, vacinas, histórico, própria agenda |
| **RECEPCIONISTA** | Tutores, animais, agendamentos, transferências |
| **TUTOR** | Somente seus próprios animais e histórico |

---

## 📚 Documentação Detalhada

Consulte a pasta [`/docs`](./docs/INDEX.md):

- [Domínio e Regras de Negócio](./docs/etapa1_dominio.md)
- [Banco de Dados e Migrations](./docs/etapa2_banco.md)
- [Estrutura do Projeto](./docs/etapa3_estrutura.md)
- [Schemas Pydantic](./docs/etapa5_schemas.md)
- [Services — Regras de Negócio](./docs/etapa6_services.md)
- [Repositories](./docs/etapa7_repositories.md)
- [Endpoints da API](./docs/etapa8_routers.md)
- [Testes](./docs/etapa9_testes.md)
- [Docker e Deploy](./docs/etapa10_docker.md)
- [Decisões de Design (ADRs)](./docs/decisoes_design.md)

---

## 🧩 Cenários de Borda Documentados

| Cenário | Comportamento |
|---|---|
| Dois animais sem microchip | ✅ Permitido (índice parcial WHERE NOT NULL) |
| Emergência no horário ocupado | ✅ Criada + evento `EMERGENCIA_SOBREPOSTA` auditado |
| Tutor com 0 animais sendo inativado | ✅ Permitido |
| Consulta concluída sendo editada | ❌ HTTP 422 CONSULTA_IMUTAVEL |
| Salto de estado (AGENDADA→CONCLUIDA) | ❌ HTTP 422 TRANSICAO_INVALIDA |
| Microchip igual em animal inativo | ✅ Permitido (índice parcial considera apenas ativos) |

---

*Projeto Acadêmico — Engenharia de Software · Python 3.12 · FastAPI · PostgreSQL*
