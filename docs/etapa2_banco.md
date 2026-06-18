# ETAPA 2 — Modelagem do Banco de Dados
## API REST Clínica Veterinária

> **Status:** ✅ Concluída  
> **Entregáveis:** Models SQLAlchemy 2.0 · Alembic · 3 Migrations · Config · Session

---

## 1. Arquivos Criados

```
api_clinica_veterinaria/
├── requirements.txt                        ← Dependências pinadas (Python 3.12)
├── .env                                    ← Variáveis de ambiente (Docker)
├── .env.example                            ← Template para novos devs
├── alembic.ini                             ← Configuração do Alembic
├── alembic/
│   ├── env.py                              ← Ambiente Alembic (URL dinâmica)
│   ├── script.py.mako                      ← Template de migration
│   └── versions/
│       ├── 001_initial.py                  ← Migration 1: estrutura inicial
│       ├── 002_microchip_unique_index.py   ← Migration 2: índice parcial
│       └── 003_auditoria_transferencia.py  ← Migration 3: auditoria e transferência
└── app/
    ├── core/
    │   └── config.py                       ← Pydantic Settings V2
    ├── database/
    │   ├── base.py                         ← Base + TimestampMixin
    │   └── session.py                      ← Engine async + get_db()
    └── models/
        ├── enums.py                        ← Enums + mapa de transições
        ├── tutor.py
        ├── animal.py
        ├── veterinario.py
        ├── consulta.py                     ← Helpers máquina de estados
        ├── vacina.py
        ├── transferencia_animal.py
        ├── auditoria.py
        └── usuario.py
```

---

## 2. Decisões de Design — SQLAlchemy

### UUID como Primary Key (todas as tabelas)

```python
id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
)
```

**Justificativa:** IDs sequenciais (INTEGER) expõem volume de dados, permitem enumeração
de recursos (`GET /animais/1`, `GET /animais/2`...) e dificultam fusões em sistemas
distribuídos. UUIDs eliminam esses problemas.

### TimestampMixin — Campos de Auditoria

```python
class TimestampMixin:
    criado_em:     Mapped[datetime]  # server_default=NOW(), UTC
    atualizado_em: Mapped[datetime]  # server_default=NOW(), onupdate=NOW()
    criado_por:    Mapped[str|None]  # email do usuário autenticado
    atualizado_por: Mapped[str|None]
```

**Justificativa:** Campos de auditoria são obrigatórios em sistemas médicos/veterinários
para rastreabilidade e conformidade. Implementados como mixin para evitar repetição.

### Soft Delete (campo `ativo`)

```python
ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

**Justificativa:** Dados médicos não devem ser apagados fisicamente. O histórico clínico
de um animal não pode ser perdido mesmo que o tutor "exclua" o registro.

### TIMESTAMPTZ (com fuso horário)

**Justificativa:** Uma clínica pode ter múltiplas unidades em fusos diferentes. Armazenar
em UTC e converter na apresentação evita inconsistências no histórico clínico.

---

## 3. Models SQLAlchemy 2.0

### `Consulta` — Máquina de Estados Embutida

O model `Consulta` encapsula a lógica da máquina de estados diretamente:

```python
@property
def is_terminal(self) -> bool:
    return self.status_enum in ESTADOS_TERMINAIS

def pode_transicionar_para(self, novo_status: StatusConsulta) -> bool:
    return novo_status in TRANSICOES_VALIDAS.get(self.status_enum, [])
```

**Justificativa:** A validação de transição no model garante consistência independente
de como a entidade é usada. O `ConsultaService` usa esses helpers para implementar RN-007 e RN-008.

### `Animal` — Propriedade Derivada

```python
@property
def idade_anos(self) -> float:
    return (date.today() - self.data_nascimento).days / 365.25
```

**Justificativa:** Cálculo derivado documentado no domínio. Usar 365.25 dias considera anos bissextos.

### `enums.py` — Mapa de Transições Centralizado

```python
TRANSICOES_VALIDAS: dict[StatusConsulta, list[StatusConsulta]] = {
    StatusConsulta.AGENDADA:     [StatusConsulta.CONFIRMADA, StatusConsulta.CANCELADA],
    StatusConsulta.CONFIRMADA:   [StatusConsulta.EM_ANDAMENTO, StatusConsulta.CANCELADA],
    StatusConsulta.EM_ANDAMENTO: [StatusConsulta.CONCLUIDA],
    StatusConsulta.CONCLUIDA:    [],
    StatusConsulta.CANCELADA:    [],
}
```

**Justificativa:** Centralizar as transições válidas em um único dict evita duplicação e
garante que qualquer camada (service, test) use a mesma fonte de verdade.

---

## 4. Alembic — 3 Migrations

### Migration 1 — `001_initial.py`

**Conteúdo:** Cria as tabelas principais do domínio.

```
tutores → animais → consultas → vacinas
veterinarios → consultas
usuarios (referencia tutores e veterinarios)
```

**Destaques técnicos:**
- `ON DELETE RESTRICT` nas FKs principais — impede exclusão física acidental
- `ON DELETE SET NULL` em FKs opcionais (consulta_id em vacinas, tutor_id/veterinario_id em usuarios)
- Índice composto `(veterinario_id, data_hora)` — detecção de conflitos de agenda O(log n)
- Índice composto `(animal_id, data_hora)` — montagem do histórico clínico em ordem

**Rollback:** `downgrade()` remove tabelas na ordem inversa das dependências FK.

### Migration 2 — `002_microchip_unique_index.py`

**Conteúdo:** Índice único parcial no campo `microchip`.

```sql
CREATE UNIQUE INDEX uix_animais_microchip_not_null
ON animais (microchip)
WHERE microchip IS NOT NULL;
```

**Justificativa técnica:**
- Um `UNIQUE CONSTRAINT` convencional bloquearia múltiplos `NULL` (pois `NULL ≠ NULL` para unicidade no SQL padrão)
- Animais sem microchip devem coexistir sem conflito
- O índice parcial resolve exatamente isso: apenas valores não-nulos participam da verificação de unicidade

**Rollback:** `DROP INDEX IF EXISTS uix_animais_microchip_not_null` — não afeta dados.

### Migration 3 — `003_auditoria_transferencia.py`

**Conteúdo:** Tabelas de rastreabilidade.

**`auditorias`:**
- `payload JSONB` — armazena estado antes/depois sem schema fixo
- Índice em `(entidade, entidade_id)` — consulta rápida por objeto auditado
- Design append-only: sem UPDATE/DELETE via policy de serviço

**`transferencias_animais`:**
- Dois FKs para `tutores` com nomes explícitos (`fk_transferencias_tutor_origem_id`, `fk_transferencias_tutor_destino_id`)
- `data_transferencia` com `server_default=NOW()` — momento exato da operação
- Imutável por design: sem campos `atualizado_*`

**Rollback:** Remove índices antes das tabelas (ordem obrigatória no PostgreSQL).

---

## 5. Configuração — `app/core/config.py`

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", ...)
    
    DATABASE_URL: str           # asyncpg (API)
    DATABASE_URL_SYNC: str      # psycopg2 (Alembic)
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
```

**Justificativa:** Dois DATABASE_URLs porque:
- `asyncpg` é necessário para o FastAPI async
- `psycopg2` é necessário para o Alembic (que é síncrono)

---

## 6. Session — `app/database/session.py`

```python
engine = create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Justificativa:** Padrão Unit of Work via context manager. O `commit` automático ao final
simplifica os routers (sem precisar chamar `await session.commit()` em cada endpoint).
O `rollback` em exceção garante consistência transacional.

---

## 7. Diagrama ER — ASCII

```
tutores (1) ──────────────────────────── (N) animais
    │                                         │
    │ (via transferencias)                     ├──── (N) consultas ──── (1) veterinarios
    │                                         │         │
    │                                         │         └──── (N) vacinas
    │                                         │
    │                                         └──── (N) vacinas (direto, sem consulta)
    │
    ├── tutor_origem  ──── transferencias_animais ──── tutor_destino
    │
auditorias (append-only, sem FK — referencia por entidade+entidade_id)
usuarios (referencia tutores e veterinarios via FK opcional)
```

---

## 8. Como Executar as Migrations

```bash
# Aplicar todas as migrations
alembic upgrade head

# Aplicar até uma migration específica
alembic upgrade 002_microchip_unique_index

# Rollback da última migration
alembic downgrade -1

# Rollback completo
alembic downgrade base

# Ver histórico
alembic history --verbose

# Ver migration atual
alembic current
```
