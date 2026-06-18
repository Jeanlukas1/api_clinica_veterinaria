"""
app/main.py
────────────
Ponto de entrada da aplicação FastAPI — Clínica Veterinária API.

Responsabilidades:
  - Criar e configurar o app FastAPI (metadata, docs, lifespan)
  - Registrar middleware (CORS, RequestID)
  - Registrar handlers globais de exceção
  - Montar todos os routers
  - Expor endpoint /health
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import register_exception_handlers

# ─── Logger ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Contexto de ciclo de vida da aplicação.
    - startup: verifica conectividade com o banco
    - shutdown: fecha o engine assíncrono
    """
    from sqlalchemy import text
    from app.database.session import engine

    logger.info("🚀 Iniciando %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # Verificação de conectividade no startup
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Banco de dados conectado com sucesso.")
    except Exception as exc:
        logger.critical("❌ Falha ao conectar ao banco: %s", exc)
        raise

    yield  # ← Aplicação rodando

    # Cleanup no shutdown
    await engine.dispose()
    logger.info("👋 Aplicação encerrada.")


# ─── Criação do App ───────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## API REST — Clínica Veterinária

Sistema de gerenciamento completo para clínicas veterinárias.

### Funcionalidades
- 🐾 Cadastro de tutores e animais
- 🏥 Gestão de consultas com máquina de estados
- 💉 Registro de vacinas e histórico de imunização
- 📋 Histórico clínico consolidado
- 🔄 Transferência de guarda entre tutores
- 🔐 Autenticação JWT com RBAC por perfil
- 📊 Auditoria de eventos críticos

### Perfis de Acesso
| Perfil | Descrição |
|--------|-----------|
| **ADMIN** | Acesso total ao sistema |
| **VETERINARIO** | Consultas, vacinas e histórico clínico |
| **RECEPCIONISTA** | Agendamentos, tutores e animais |
| **TUTOR** | Acesso somente ao seu animal |
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    license_info={"name": "MIT"},
    contact={"name": "Clínica Veterinária", "email": "suporte@clinica.com"},
    lifespan=lifespan,
)


# ─── Middleware ────────────────────────────────────────────────────────────────

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware de Request ID — adiciona X-Request-ID em todas as respostas
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Middleware de logging de requisições
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    logger.info("→ %s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.info("← %s %s [%d]", request.method, request.url.path, response.status_code)
    return response


# ─── Exception Handlers ───────────────────────────────────────────────────────

register_exception_handlers(app)


# ─── Routers ──────────────────────────────────────────────────────────────────
# Importados aqui para evitar importações circulares no startup

from app.routers import (  # noqa: E402
    auth,
    tutores,
    animais,
    veterinarios,
    consultas,
    vacinas,
    transferencias,
)

app.include_router(auth.router,           prefix="/auth",           tags=["Autenticação"])
app.include_router(tutores.router,        prefix="/tutores",        tags=["Tutores"])
app.include_router(animais.router,        prefix="/animais",        tags=["Animais"])
app.include_router(veterinarios.router,   prefix="/veterinarios",   tags=["Veterinários"])
app.include_router(consultas.router,      prefix="/consultas",      tags=["Consultas"])
app.include_router(vacinas.router,        prefix="/vacinas",        tags=["Vacinas"])
app.include_router(transferencias.router, prefix="/transferencias", tags=["Transferências"])


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get(
    "/health",
    tags=["Sistema"],
    summary="Health check",
    description="Verifica o estado da API e a conectividade com o banco de dados.",
)
async def health_check():
    """
    Endpoint de saúde — usado pelo Docker healthcheck e monitoramento.
    """
    from sqlalchemy import text
    from app.database.session import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "unavailable"

    return JSONResponse(
        content={
            "status": "healthy" if db_status == "connected" else "degraded",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "database": db_status,
        },
        status_code=200 if db_status == "connected" else 503,
    )


@app.get("/", tags=["Sistema"], include_in_schema=False)
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
