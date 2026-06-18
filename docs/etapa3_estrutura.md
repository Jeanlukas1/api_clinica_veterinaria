# ETAPA 3 — Estrutura do Projeto
## API REST Clínica Veterinária

> **Status:** ⏳ Pendente  
> **Objetivo:** Criar `main.py`, `security.py`, `exceptions.py` e a estrutura base de todas as camadas.

---

## 1. Estrutura Final Esperada

```
app/
├── __init__.py
├── main.py                         ← FastAPI app + middleware + handlers globais
│
├── core/
│   ├── __init__.py
│   ├── config.py                   ✅ (criado na Etapa 2)
│   ├── security.py                 ← JWT, hash de senha, RBAC
│   └── exceptions.py               ← Exceções de domínio + handlers HTTP
│
├── database/
│   ├── __init__.py                 ✅
│   ├── base.py                     ✅
│   └── session.py                  ✅
│
├── models/                         ✅ (todos criados na Etapa 2)
│   └── ...
│
├── schemas/                        ← Pydantic V2 (Etapa 5)
│   ├── __init__.py
│   ├── tutor.py
│   ├── animal.py
│   ├── veterinario.py
│   ├── consulta.py
│   ├── vacina.py
│   ├── transferencia.py
│   ├── auditoria.py
│   ├── auth.py
│   └── common.py                   ← PaginatedResponse, ErrorResponse
│
├── repositories/                   ← Acesso ao banco (Etapa 7)
│   ├── __init__.py
│   ├── base.py                     ← BaseRepository genérico
│   ├── tutor.py
│   ├── animal.py
│   ├── veterinario.py
│   ├── consulta.py
│   ├── vacina.py
│   ├── transferencia.py
│   └── auditoria.py
│
├── services/                       ← Regras de negócio (Etapa 6)
│   ├── __init__.py
│   ├── tutor.py
│   ├── animal.py
│   ├── veterinario.py
│   ├── consulta.py
│   ├── vacina.py
│   ├── transferencia.py
│   └── auth.py
│
├── routers/                        ← Endpoints FastAPI (Etapa 8)
│   ├── __init__.py
│   ├── auth.py
│   ├── tutores.py
│   ├── animais.py
│   ├── veterinarios.py
│   ├── consultas.py
│   ├── vacinas.py
│   └── transferencias.py
│
├── audit/                          ← Serviço de auditoria transversal
│   ├── __init__.py
│   └── service.py
│
└── tests/                          ← Testes automatizados (Etapa 9)
    ├── __init__.py
    ├── conftest.py                 ← Fixtures globais
    ├── test_tutores.py
    ├── test_animais.py
    ├── test_consultas.py
    ├── test_vacinas.py
    ├── test_transferencias.py
    └── test_auth.py
```

---

## 2. `app/main.py` — O que será implementado

```python
app = FastAPI(
    title="Clínica Veterinária API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware: CORS, RequestID, logging
# Handlers globais: HTTPException, ValidationError, DomainException
# Routers: /auth, /tutores, /animais, /veterinarios, /consultas, /vacinas, /transferencias
# Lifespan: conexão com DB no startup, fechamento no shutdown
```

---

## 3. `app/core/security.py` — O que será implementado

### JWT (Access + Refresh Token)

```python
def create_access_token(subject: str, perfil: str) -> str:
    """Gera JWT com expiração de ACCESS_TOKEN_EXPIRE_MINUTES."""

def create_refresh_token(subject: str) -> str:
    """Gera Refresh JWT com expiração de REFRESH_TOKEN_EXPIRE_DAYS."""

def decode_token(token: str) -> TokenPayload:
    """Decodifica e valida JWT. Lança JWTError em caso de inválido/expirado."""
```

### Password Hashing (bcrypt)

```python
def hash_password(plain: str) -> str: ...
def verify_password(plain: str, hashed: str) -> bool: ...
```

### RBAC — Dependências FastAPI

```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Usuario: ...
def require_perfil(*perfis: PerfilUsuario): ...  # Decorator de permissão
```

**Perfis e permissões:**

| Endpoint | ADMIN | VETERINÁRIO | RECEPCIONISTA | TUTOR |
|---|---|---|---|---|
| GET /tutores | ✓ | ✓ | ✓ | — |
| POST /tutores | ✓ | — | ✓ | — |
| GET /animais | ✓ | ✓ | ✓ | Próprio |
| POST /consultas | ✓ | — | ✓ | — |
| PATCH /consultas/{id}/status | ✓ | ✓ | — | — |
| GET /animais/{id}/historico | ✓ | ✓ | ✓ | Próprio |
| POST /transferencias | ✓ | — | ✓ | — |
| GET /auditorias | ✓ | — | — | — |

---

## 4. `app/core/exceptions.py` — O que será implementado

### Hierarquia de Exceções de Domínio

```python
class ClinicaException(Exception):
    """Base de todas as exceções de domínio."""
    error_code: str
    message: str
    status_code: int = 422

class TutorComAnimaisAtivosError(ClinicaException):    # RN-001
class MicrochipDuplicadoError(ClinicaException):       # RN-003
class ConsultaConflictError(ClinicaException):          # RN-004
class DiagnosticoObrigatorioError(ClinicaException):    # RN-007
class ConsultaImutavelError(ClinicaException):          # RN-008
class TransicaoInvalidaError(ClinicaException):         # Máquina de estados
class VeterinarioInativoError(ClinicaException):        # RN-011
class MotivoObrigatorioError(ClinicaException):         # RN-010
```

### Padrão de Resposta de Erro

```json
{
  "error": "CONSULTA_CONFLICT",
  "message": "Veterinário já possui consulta nesse horário.",
  "details": {
    "veterinario_id": "...",
    "data_hora": "2024-01-15T10:00:00Z"
  }
}
```

### Handlers Globais

```python
@app.exception_handler(ClinicaException)
@app.exception_handler(RequestValidationError)
@app.exception_handler(HTTPException)
@app.exception_handler(Exception)  # fallback 500
```

---

## 5. Separação de Responsabilidades

```
REQUEST
  │
  ▼
Router       ← recebe HTTP, valida schema Pydantic, chama service
  │
  ▼
Service      ← TODAS as regras de negócio (RN-001 a RN-012)
  │
  ▼
Repository   ← queries SQL via SQLAlchemy, sem lógica de negócio
  │
  ▼
Database     ← PostgreSQL
```

> **Regra de ouro:** Nenhuma regra de negócio nos Routers. Nenhuma query SQL nos Services.
