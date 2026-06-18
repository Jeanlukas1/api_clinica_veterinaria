# ETAPA 8 — Routers FastAPI
## API REST Clínica Veterinária

> **Status:** ⏳ Pendente  
> **Objetivo:** Implementar todos os endpoints REST. **Sem lógica de negócio — apenas receber, validar schema e delegar ao service.**

---

## 1. Endpoints Completos

### Auth — `/auth`

| Método | Path | Descrição | Perfis |
|---|---|---|---|
| POST | `/auth/login` | Autentica e retorna JWT | Público |
| POST | `/auth/refresh` | Renova access token | Autenticado |
| POST | `/auth/logout` | Invalida refresh token | Autenticado |
| POST | `/auth/register` | Cria novo usuário | ADMIN |

### Tutores — `/tutores`

| Método | Path | Descrição | Perfis |
|---|---|---|---|
| GET | `/tutores` | Lista tutores (paginado) | ADMIN, RECEPCIONISTA, VETERINARIO |
| POST | `/tutores` | Cria tutor | ADMIN, RECEPCIONISTA |
| GET | `/tutores/{id}` | Busca tutor por ID | ADMIN, RECEPCIONISTA, VETERINARIO |
| PATCH | `/tutores/{id}` | Atualiza tutor | ADMIN, RECEPCIONISTA |
| DELETE | `/tutores/{id}` | Inativa tutor (soft delete) | ADMIN |
| GET | `/tutores/{id}/animais` | Lista animais do tutor | ADMIN, RECEPCIONISTA, VETERINARIO, TUTOR (próprio) |

### Animais — `/animais`

| Método | Path | Descrição | Perfis |
|---|---|---|---|
| GET | `/animais` | Lista animais (filtros + paginação) | ADMIN, RECEPCIONISTA, VETERINARIO |
| POST | `/animais` | Cadastra animal | ADMIN, RECEPCIONISTA |
| GET | `/animais/{id}` | Busca animal | ADMIN, RECEPCIONISTA, VETERINARIO, TUTOR (próprio) |
| PATCH | `/animais/{id}` | Atualiza animal | ADMIN, RECEPCIONISTA |
| DELETE | `/animais/{id}` | Inativa animal | ADMIN |
| GET | `/animais/{id}/historico` | Histórico clínico consolidado | ADMIN, VETERINARIO, TUTOR (próprio) |
| GET | `/animais/{id}/resumo` | Resumo estatístico | ADMIN, VETERINARIO, TUTOR (próprio) |
| GET | `/animais/{id}/transferencias` | Histórico de transferências | ADMIN, RECEPCIONISTA |

### Veterinários — `/veterinarios`

| Método | Path | Descrição | Perfis |
|---|---|---|---|
| GET | `/veterinarios` | Lista veterinários | Todos autenticados |
| POST | `/veterinarios` | Cadastra veterinário | ADMIN |
| GET | `/veterinarios/{id}` | Busca veterinário | Todos autenticados |
| PATCH | `/veterinarios/{id}` | Atualiza veterinário | ADMIN |
| DELETE | `/veterinarios/{id}` | Inativa veterinário | ADMIN |
| GET | `/veterinarios/{id}/agenda` | Consultas do veterinário | ADMIN, RECEPCIONISTA, VETERINARIO (própria) |

### Consultas — `/consultas`

| Método | Path | Descrição | Perfis |
|---|---|---|---|
| GET | `/consultas` | Lista consultas (filtros) | ADMIN, RECEPCIONISTA, VETERINARIO |
| POST | `/consultas` | Agenda consulta | ADMIN, RECEPCIONISTA |
| GET | `/consultas/{id}` | Busca consulta | ADMIN, RECEPCIONISTA, VETERINARIO |
| PATCH | `/consultas/{id}` | Atualiza dados da consulta | ADMIN, RECEPCIONISTA, VETERINARIO |
| PATCH | `/consultas/{id}/status` | **Transição de estado** | ADMIN, VETERINARIO, RECEPCIONISTA |
| DELETE | `/consultas/{id}` | Cancela consulta | ADMIN, RECEPCIONISTA |

### Vacinas — `/vacinas`

| Método | Path | Descrição | Perfis |
|---|---|---|---|
| GET | `/vacinas` | Lista vacinas (filtro por animal) | ADMIN, VETERINARIO, RECEPCIONISTA |
| POST | `/vacinas` | Registra vacina | ADMIN, VETERINARIO, RECEPCIONISTA |
| GET | `/vacinas/{id}` | Busca vacina | Todos autenticados |
| PATCH | `/vacinas/{id}` | Atualiza vacina | ADMIN, VETERINARIO |
| DELETE | `/vacinas/{id}` | Remove vacina | ADMIN |

### Transferências — `/transferencias`

| Método | Path | Descrição | Perfis |
|---|---|---|---|
| POST | `/transferencias` | Transfere animal entre tutores | ADMIN, RECEPCIONISTA |
| GET | `/transferencias` | Lista transferências | ADMIN |
| GET | `/transferencias/{id}` | Busca transferência | ADMIN, RECEPCIONISTA |

---

## 2. Exemplo de Router (Consultas)

```python
router = APIRouter(prefix="/consultas", tags=["Consultas"])

@router.post(
    "/",
    response_model=ConsultaResponse,
    status_code=201,
    summary="Agendar nova consulta",
    description="Cria consulta com status inicial AGENDADA. Valida RN-004, RN-005, RN-006, RN-011.",
)
async def criar_consulta(
    data: ConsultaCreate,
    service: ConsultaService = Depends(get_consulta_service),
    current_user: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.RECEPCIONISTA)),
) -> ConsultaResponse:
    consulta = await service.criar(data, usuario=current_user.email)
    return ConsultaResponse.model_validate(consulta)


@router.patch(
    "/{consulta_id}/status",
    response_model=ConsultaResponse,
    summary="Transição de estado da consulta",
    description="Aplica a máquina de estados. Valida RN-007 (diagnóstico) e RN-008 (terminal).",
)
async def mudar_status_consulta(
    consulta_id: UUID,
    data: ConsultaStatusUpdate,
    service: ConsultaService = Depends(get_consulta_service),
    current_user: Usuario = Depends(require_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VETERINARIO)),
) -> ConsultaResponse:
    consulta = await service.mudar_status(
        consulta_id, data.status, data.diagnostico, usuario=current_user.email
    )
    return ConsultaResponse.model_validate(consulta)
```

---

## 3. Padrão de Resposta de Erro

```json
{
  "error": "CONSULTA_CONFLICT",
  "message": "Veterinário já possui consulta nesse horário.",
  "details": {
    "veterinario_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "data_hora": "2024-01-15T10:00:00Z",
    "conflito_com": "8fa95e74-1234-4562-b3fc-9d873f55bfa7"
  }
}
```

---

## 4. Filtros e Paginação

```
GET /animais?limit=20&offset=0&nome=rex&especie=CANINO&tutor_id=<uuid>
GET /consultas?limit=10&offset=0&status=AGENDADA&veterinario_id=<uuid>&data_inicio=2024-01-01
GET /vacinas?animal_id=<uuid>&limit=50
```

---

## 5. Documentação OpenAPI Automática

FastAPI gera automaticamente:
- `/docs` — Swagger UI interativa
- `/redoc` — ReDoc
- `/openapi.json` — Schema OpenAPI 3.1

Cada endpoint terá:
- `summary` — título curto
- `description` — regras de negócio aplicadas
- `response_model` — schema de resposta tipado
- `status_code` — código HTTP correto (200/201/204)
- `responses` — erros documentados (404, 409, 422)
