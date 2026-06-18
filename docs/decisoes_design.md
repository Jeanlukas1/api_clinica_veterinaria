# Decisões de Design — ADRs
## API REST Clínica Veterinária

> **ADR** = Architecture Decision Record — registro das principais decisões técnicas com justificativas.

---

## ADR-001 — UUID como Primary Key

**Decisão:** Todas as entidades usam UUID v4 como chave primária.

**Alternativas consideradas:**
- INTEGER SERIAL (auto-incremento)
- BIGSERIAL

**Justificativa:**
- Evita enumeração de recursos (`/animais/1`, `/animais/2` → detectar total de registros)
- Compatível com sistemas distribuídos (sem colisão entre instâncias)
- IDs podem ser gerados na aplicação antes de persistir (útil para testes)
- Padrão de mercado para APIs públicas

**Consequências:** Índices ligeiramente maiores, queries de range não aplicáveis.

---

## ADR-002 — Soft Delete via campo `ativo`

**Decisão:** Entidades principais não são deletadas fisicamente — apenas `ativo=false`.

**Alternativas consideradas:**
- DELETE físico
- Campo `deleted_at` (timestamp de exclusão)

**Justificativa:**
- Dados médicos/veterinários têm valor histórico e legal
- O histórico clínico de um animal não pode ser perdido
- Integridade referencial preservada (FKs continuam válidas)
- Facilita auditoria e possibilidade de reativação

**Consequências:** Queries de listagem devem sempre filtrar `WHERE ativo = true`.

---

## ADR-003 — SQLAlchemy 2.0 Async com asyncpg

**Decisão:** Engine assíncrono com `asyncpg` para a API; `psycopg2` apenas para Alembic.

**Alternativas consideradas:**
- SQLAlchemy síncrono (bloqueante)
- Tortoise ORM (async-first)
- databases library

**Justificativa:**
- FastAPI é async-first — misturar sync/async causa deadlocks com o event loop
- `asyncpg` é o driver async mais performático para PostgreSQL
- SQLAlchemy 2.0 mantém a maturidade do ORM com suporte async completo
- Dois DATABASE_URLs necessários pois Alembic não suporta drivers async

---

## ADR-004 — Pydantic V2 para Schemas

**Decisão:** Pydantic V2 com `BaseModel` e decorators `@field_validator` / `@model_validator`.

**Justificativa:**
- Pydantic V2 é 5-50x mais rápido que V1 (Rust core)
- FastAPI 0.100+ nativo com Pydantic V2
- `@field_validator` separa validações por campo
- `@model_validator` permite validações cruzadas (ex: data_proxima > data_aplicacao)
- `ConfigDict(from_attributes=True)` substitui o antigo `orm_mode = True`

---

## ADR-005 — Máquina de Estados Explícita

**Decisão:** Status da Consulta governado por mapa de transições em `enums.py` e helpers no model.

**Alternativas consideradas:**
- Validação apenas no service
- Biblioteca de state machine (transitions, pytransitions)

**Justificativa:**
- Centralizar em `TRANSICOES_VALIDAS` garante única fonte de verdade
- Helpers `is_terminal` e `pode_transicionar_para()` no model permitem uso em qualquer camada
- Sem dependências externas desnecessárias
- Facilita testes unitários da lógica de estado isoladamente

---

## ADR-006 — Índice Único Parcial para Microchip

**Decisão:** `CREATE UNIQUE INDEX WHERE microchip IS NOT NULL` em vez de `UNIQUE CONSTRAINT`.

**Justificativa:**
- `UNIQUE CONSTRAINT` padrão bloqueia múltiplos NULLs (comportamento SQL padrão)
- Animais sem microchip são comuns e legítimos
- O índice parcial resolve exatamente o requisito: unicidade apenas quando preenchido
- Feature nativa do PostgreSQL — sem workarounds na aplicação

---

## ADR-007 — Auditoria Append-Only com JSONB

**Decisão:** Tabela `auditorias` sem UPDATE/DELETE; payload em JSONB.

**Justificativa:**
- Registros de auditoria são imutáveis por natureza e por requisito legal (LGPD)
- JSONB permite capturar estado antes/depois sem criar schemas rígidos por evento
- Índice em `(entidade, entidade_id)` permite consulta eficiente por objeto auditado
- Em produção, adicionar Row Security Policy no PostgreSQL para impedir DELETE

---

## ADR-008 — Separação de Responsabilidades (Layered Architecture)

**Decisão:** Router → Service → Repository → Database.

**Justificativa:**
- **Routers**: única responsabilidade é mapear HTTP → lógica
- **Services**: única responsabilidade é aplicar regras de negócio
- **Repositories**: única responsabilidade é persistir/consultar dados
- Testabilidade: cada camada pode ser testada isoladamente com mocks
- Manutenibilidade: mudança de banco de dados afeta apenas Repositories

**Regras:**
- Nenhuma query SQL nos Services
- Nenhuma regra de negócio nos Routers
- Nenhum `import` de HTTP (FastAPI) nos Services ou Repositories

---

## ADR-009 — JWT com Access + Refresh Token

**Decisão:** Dois tokens: Access (30 min) e Refresh (7 dias).

**Justificativa:**
- Access token de curta duração minimiza janela de comprometimento
- Refresh token permite renovação sem reautenticação frequente
- Stateless: sem necessidade de blacklist em sessão simples
- Em produção: implementar blacklist de refresh tokens revogados

---

## ADR-010 — 3 Migrations Alembic Separadas

**Decisão:** Separar em estrutura base, índice parcial e tabelas de auditoria.

**Justificativa:**
1. **Migration 1**: estrutura inicial — pode ser revisada isoladamente
2. **Migration 2**: otimização de índice — separada para demonstrar adição incremental sem recriar tabelas
3. **Migration 3**: preocupações transversais (auditoria, transferência) — adicionadas sem risco para o núcleo

**Acadêmica:** Demonstra boas práticas de versionamento de schema incremental.
