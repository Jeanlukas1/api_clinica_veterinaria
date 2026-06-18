# ETAPA 10 — Docker e Deploy
## API REST Clínica Veterinária

> **Status:** ⏳ Pendente  
> **Objetivo:** Containerizar a aplicação com Docker Compose, incluindo API, PostgreSQL e pgAdmin.

---

## 1. Arquivos a Criar

```
api_clinica_veterinaria/
├── Dockerfile                    ← Build da API FastAPI
├── docker-compose.yml            ← Orquestração dos serviços
├── docker-compose.test.yml       ← Ambiente de testes isolado
└── .dockerignore
```

---

## 2. `Dockerfile` — Build da API

```dockerfile
# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Instala dependências de build
RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copia pacotes instalados do stage builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia o código da aplicação
COPY . .

# Usuário não-root por segurança
RUN addgroup --system clinica && adduser --system --group clinica
USER clinica

# Exposição da porta
EXPOSE 8000

# Entrypoint: roda migrations + inicia servidor
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

**Justificativa do multi-stage build:**
- Stage `builder`: instala dependências (camada pesada, não vai para produção)
- Stage `runtime`: apenas o necessário para rodar — imagem final menor (~200MB vs ~600MB)
- Usuário não-root: reduz superfície de ataque

---

## 3. `docker-compose.yml` — Desenvolvimento

```yaml
version: "3.9"

services:
  # ── API FastAPI ────────────────────────────────────────────────────────────
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    container_name: clinica_api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://clinica_user:clinica_pass@db:5432/clinica_veterinaria
      DATABASE_URL_SYNC: postgresql+psycopg2://clinica_user:clinica_pass@db:5432/clinica_veterinaria
      SECRET_KEY: dev_secret_key_minimo_32_chars_aqui
      DEBUG: "true"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app           # hot-reload em desenvolvimento
    networks:
      - clinica_network
    restart: unless-stopped

  # ── PostgreSQL ─────────────────────────────────────────────────────────────
  db:
    image: postgres:16-alpine
    container_name: clinica_db
    environment:
      POSTGRES_USER: clinica_user
      POSTGRES_PASSWORD: clinica_pass
      POSTGRES_DB: clinica_veterinaria
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U clinica_user -d clinica_veterinaria"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - clinica_network
    restart: unless-stopped

  # ── pgAdmin (opcional) ─────────────────────────────────────────────────────
  pgadmin:
    image: dpage/pgadmin4:8
    container_name: clinica_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@clinica.com
      PGADMIN_DEFAULT_PASSWORD: admin123
    ports:
      - "5050:80"
    depends_on:
      - db
    networks:
      - clinica_network
    profiles:
      - debug    # só sobe com: docker compose --profile debug up

volumes:
  postgres_data:

networks:
  clinica_network:
    driver: bridge
```

**Decisões de design:**
- `healthcheck` no PostgreSQL: API só sobe quando o banco está pronto (`depends_on: condition: service_healthy`)
- `volumes: .:/app`: hot-reload sem rebuild em desenvolvimento
- `pgAdmin` com `profiles: debug`: não sobe por padrão, economiza recursos
- `restart: unless-stopped`: reinicia em falha, para em `docker stop`

---

## 4. `.dockerignore`

```
.git
.env
*.pyc
__pycache__
.pytest_cache
.coverage
htmlcov/
*.egg-info/
dist/
docs/
```

---

## 5. Comandos de Operação

```bash
# ── Primeira execução ─────────────────────────────────────────────────────────
docker compose up --build

# ── Execução normal ───────────────────────────────────────────────────────────
docker compose up -d

# ── Com pgAdmin ───────────────────────────────────────────────────────────────
docker compose --profile debug up -d

# ── Parar serviços ────────────────────────────────────────────────────────────
docker compose down

# ── Parar e remover volumes (dados) ──────────────────────────────────────────
docker compose down -v

# ── Rodar migrations manualmente ─────────────────────────────────────────────
docker compose exec api alembic upgrade head

# ── Rollback de migration ─────────────────────────────────────────────────────
docker compose exec api alembic downgrade -1

# ── Rodar testes no container ─────────────────────────────────────────────────
docker compose exec api pytest app/tests/ -v --cov=app

# ── Ver logs da API ───────────────────────────────────────────────────────────
docker compose logs -f api

# ── Acessar shell do container ───────────────────────────────────────────────
docker compose exec api bash

# ── Acessar PostgreSQL ────────────────────────────────────────────────────────
docker compose exec db psql -U clinica_user -d clinica_veterinaria
```

---

## 6. URLs após `docker compose up`

| Serviço | URL |
|---|---|
| API FastAPI | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |
| Health Check | http://localhost:8000/health |
| pgAdmin | http://localhost:5050 (com `--profile debug`) |
| PostgreSQL | localhost:5432 |

---

## 7. Verificação de Saúde

```python
# app/routers/health.py
@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_db)):
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(503, "Database unavailable")
```
