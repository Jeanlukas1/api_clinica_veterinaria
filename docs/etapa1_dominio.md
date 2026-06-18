# ETAPA 1 — Documento de Domínio
## API REST Clínica Veterinária

> **Status:** ✅ Concluída  
> **Entregável:** Documento completo de domínio — base para todas as decisões de implementação.

---

## 1. Descrição do Domínio

Uma **Clínica Veterinária** gerencia o ciclo de vida completo do atendimento animal:
cadastro de tutores e animais, agendamento e condução de consultas, registro de vacinas,
histórico clínico e transferência de guarda entre tutores — tudo com rastreabilidade via auditoria.

### Atores do Sistema

| Ator | Papel |
|---|---|
| **ADMIN** | Plataforma completa, usuários e auditoria |
| **VETERINÁRIO** | Conduz consultas, diagnósticos e vacinas |
| **RECEPCIONISTA** | Agenda consultas, cadastra tutores/animais |
| **TUTOR** | Acesso somente ao seu animal e histórico |

### Fluxo Principal

```
Tutor cadastrado
  └─► Animal cadastrado
        └─► Consulta AGENDADA → CONFIRMADA → EM_ANDAMENTO → CONCLUÍDA
                                                              └─► Vacinas registradas
                                                              └─► Histórico atualizado
```

---

## 2. Entidades

### 2.1 Tutor

| Atributo | Tipo | Obrig. | Constraint |
|---|---|---|---|
| id | UUID | ✓ | PK, auto |
| nome | VARCHAR(150) | ✓ | mín 3 chars |
| cpf | VARCHAR(14) | ✓ | único, algoritmo válido |
| email | VARCHAR(254) | ✓ | único, RFC 5321 |
| telefone | VARCHAR(20) | ✓ | — |
| ativo | BOOLEAN | ✓ | default TRUE (soft delete) |
| criado_em | TIMESTAMPTZ | ✓ | auto |
| atualizado_em | TIMESTAMPTZ | ✓ | auto |
| criado_por | VARCHAR(100) | — | usuário autenticado |
| atualizado_por | VARCHAR(100) | — | usuário autenticado |

### 2.2 Animal

| Atributo | Tipo | Obrig. | Constraint |
|---|---|---|---|
| id | UUID | ✓ | PK, auto |
| tutor_id | UUID | ✓ | FK → tutores (RESTRICT) |
| nome | VARCHAR(100) | ✓ | mín 2 chars |
| especie | VARCHAR(50) | ✓ | enum: CANINO,FELINO,AVE,REPTIL,ROEDOR,OUTRO |
| raca | VARCHAR(100) | — | livre |
| sexo | VARCHAR(1) | ✓ | M ou F |
| data_nascimento | DATE | ✓ | não futura (RN-002) |
| peso | NUMERIC(6,3) | ✓ | > 0 (RN-012) |
| microchip | VARCHAR(50) | — | único parcial WHERE NOT NULL (RN-003) |
| ativo | BOOLEAN | ✓ | default TRUE |

### 2.3 Veterinario

| Atributo | Tipo | Obrig. | Constraint |
|---|---|---|---|
| id | UUID | ✓ | PK, auto |
| nome | VARCHAR(150) | ✓ | mín 3 chars |
| crmv | VARCHAR(20) | ✓ | único, formato CRMV-UF-00000 |
| especialidade | VARCHAR(80) | ✓ | enum: CLINICA_GERAL,ORTOPEDIA,ONCOLOGIA,DERMATOLOGIA,CARDIOLOGIA,OFTALMOLOGIA,OUTRO |
| ativo | BOOLEAN | ✓ | default TRUE |

### 2.4 Consulta

| Atributo | Tipo | Obrig. | Constraint |
|---|---|---|---|
| id | UUID | ✓ | PK, auto |
| animal_id | UUID | ✓ | FK → animais |
| veterinario_id | UUID | ✓ | FK → veterinarios |
| data_hora | TIMESTAMPTZ | ✓ | não passado (RN-005), exceto emergência |
| status | VARCHAR(20) | ✓ | máquina de estados |
| tipo | VARCHAR(20) | ✓ | ROTINA,RETORNO,EMERGENCIA,CIRURGIA,EXAME |
| diagnostico | TEXT | — | obrigatório ao concluir (RN-007) |
| observacoes | TEXT | — | livre |

### 2.5 Vacina

| Atributo | Tipo | Obrig. | Constraint |
|---|---|---|---|
| id | UUID | ✓ | PK, auto |
| animal_id | UUID | ✓ | FK → animais |
| consulta_id | UUID | — | FK → consultas (SET NULL) |
| nome_vacina | VARCHAR(150) | ✓ | — |
| lote | VARCHAR(50) | ✓ | — |
| data_aplicacao | DATE | ✓ | não futura (RN-009) |
| data_proxima | DATE | — | posterior à data_aplicacao |

### 2.6 TransferenciaAnimal

| Atributo | Tipo | Obrig. | Constraint |
|---|---|---|---|
| id | UUID | ✓ | PK, auto |
| animal_id | UUID | ✓ | FK → animais |
| tutor_origem_id | UUID | ✓ | FK → tutores |
| tutor_destino_id | UUID | ✓ | FK → tutores, ≠ origem |
| motivo | TEXT | ✓ | mín 10 chars (RN-010) |
| data_transferencia | TIMESTAMPTZ | ✓ | auto NOW() |
| criado_por | VARCHAR(100) | ✓ | usuário autenticado |

### 2.7 Auditoria

| Atributo | Tipo | Obrig. | Constraint |
|---|---|---|---|
| id | UUID | ✓ | PK, auto |
| evento | VARCHAR(80) | ✓ | enum EventoAuditoria |
| entidade | VARCHAR(50) | ✓ | nome da tabela |
| entidade_id | UUID | ✓ | ID do registro |
| usuario | VARCHAR(100) | ✓ | email do ator |
| payload | JSONB | — | antes/depois |
| timestamp | TIMESTAMPTZ | ✓ | auto NOW() |
| ip_address | VARCHAR(45) | — | IPv4/IPv6 |

---

## 3. Relacionamentos

| Entidade A | Entidade B | Card. | Justificativa |
|---|---|---|---|
| Tutor | Animal | 1:N | Um tutor pode ter vários animais |
| Animal | Consulta | 1:N | Histórico acumulado de atendimentos |
| Veterinario | Consulta | 1:N | Veterinário conduz várias consultas |
| Animal | Vacina | 1:N | Imunização acumulada por animal |
| Consulta | Vacina | 1:N | Vacinas aplicadas durante consulta (opcional) |
| Animal | TransferenciaAnimal | 1:N | Animal pode ser transferido múltiplas vezes |

---

## 4. Máquina de Estados — Consulta

```
   ┌─────────────┐   confirmar()   ┌─────────────┐   iniciar()   ┌──────────────┐
   │  AGENDADA   │ ──────────────► │  CONFIRMADA │ ────────────► │ EM_ANDAMENTO │
   └─────────────┘                 └─────────────┘               └──────────────┘
          │                               │                              │
          │ cancelar()                    │ cancelar()          concluir() (+ diagnóstico)
          ▼                               ▼                              ▼
   ┌─────────────┐                 ┌─────────────┐               ┌──────────────┐
   │  CANCELADA  │◄────────────────│  CANCELADA  │               │   CONCLUÍDA  │
   │  (terminal) │                 │  (terminal) │               │   (terminal) │
   └─────────────┘                 └─────────────┘               └──────────────┘

   TRANSIÇÕES VÁLIDAS:
   AGENDADA     → CONFIRMADA, CANCELADA
   CONFIRMADA   → EM_ANDAMENTO, CANCELADA
   EM_ANDAMENTO → CONCLUÍDA
   CONCLUÍDA    → (nenhuma — terminal)
   CANCELADA    → (nenhuma — terminal)
```

---

## 5. Regras de Negócio

| ID | Nome | Gatilho | Pré-condição | Ação | Violação HTTP |
|---|---|---|---|---|---|
| RN-001 | Tutor com animais ativos não pode ser inativado | PATCH /tutores/{id} ativo=false | Animal ativo vinculado | Bloquear | 422 TUTOR_HAS_ACTIVE_ANIMALS |
| RN-002 | Data de nascimento não pode ser futura | POST/PATCH /animais | data_nascimento > hoje | Rejeitar (Pydantic) | 422 |
| RN-003 | Microchip único | POST/PATCH /animais | Microchip já cadastrado | Bloquear | 409 MICROCHIP_DUPLICADO |
| RN-004 | Sem sobreposição de agenda | POST /consultas | Veterinário ocupado ±30min | Bloquear (exceto emergência) | 409 CONSULTA_CONFLICT |
| RN-005 | Agendamento não no passado | POST /consultas | data_hora < agora | Rejeitar (Pydantic) | 422 |
| RN-006 | Emergência ignora conflito | POST /consultas tipo=EMERGENCIA | Conflito detectado | Permitir + auditar | — |
| RN-007 | Diagnóstico obrigatório na conclusão | Transição EM_ANDAMENTO→CONCLUÍDA | diagnostico vazio | Bloquear transição | 422 DIAGNOSTICO_OBRIGATORIO |
| RN-008 | Consultas terminais imutáveis | PATCH/DELETE /consultas/{id} | status CONCLUÍDA ou CANCELADA | Bloquear qualquer edição | 422 CONSULTA_IMUTAVEL |
| RN-009 | Data de vacina não futura | POST/PATCH /vacinas | data_aplicacao > hoje | Rejeitar (Pydantic) | 422 |
| RN-010 | Transferência exige motivo e auditoria | POST /transferencias | motivo < 10 chars | Bloquear; se válido: registrar auditoria | 422 MOTIVO_OBRIGATORIO |
| RN-011 | Veterinário inativo não recebe consultas | POST /consultas | veterinario.ativo=false | Bloquear | 422 VETERINARIO_INATIVO |
| RN-012 | Peso positivo | POST/PATCH /animais | peso ≤ 0 | Rejeitar (Pydantic) | 422 |

---

## 6. Cálculos Derivados

### Histórico Clínico (`GET /animais/{id}/historico`)
- Consultas com veterinário, status, diagnóstico
- Vacinas aplicadas e próximas doses
- Evolução de peso extraída de registros de atualização

### Resumo Estatístico (`GET /animais/{id}/resumo`)
```python
{
  "total_consultas": int,
  "ultima_consulta": datetime,
  "proxima_vacina": date,          # MIN(data_proxima) WHERE >= hoje
  "total_vacinas": int,
  "consultas_por_status": dict,
  "idade_anos": float              # (hoje - data_nascimento).days / 365.25
}
```
