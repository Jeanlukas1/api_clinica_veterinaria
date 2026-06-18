# ETAPA 5 — Schemas Pydantic V2
## API REST Clínica Veterinária

> **Status:** ⏳ Pendente  
> **Objetivo:** Implementar todos os schemas de entrada/saída com validações robustas.

---

## 1. Princípios Adotados

- **Separação Input/Output:** Schemas distintos para criação (`Create`), atualização (`Update`) e resposta (`Response`)
- **`@field_validator`** para validações de campo único (CPF, datas, peso)
- **`@model_validator`** para validações cruzadas entre campos
- **Herança:** `BaseSchema` com configuração compartilhada
- **Sem ORM direto:** `model_config = ConfigDict(from_attributes=True)` permite conversão de models

---

## 2. Schemas por Entidade

### `schemas/common.py` — Utilitários

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict = {}
```

### `schemas/tutor.py`

```python
class TutorCreate(BaseModel):
    nome: str              # mín 3 chars
    cpf: str               # validado: dígitos verificadores
    email: EmailStr        # validado automaticamente
    telefone: str

    @field_validator("cpf")
    def validate_cpf(cls, v): ...   # algoritmo CPF BR

class TutorUpdate(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    email: EmailStr | None = None
    ativo: bool | None = None

class TutorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    nome: str
    cpf: str
    email: str
    telefone: str
    ativo: bool
    criado_em: datetime
```

### `schemas/animal.py`

```python
class AnimalCreate(BaseModel):
    tutor_id: UUID
    nome: str
    especie: EspecieAnimal
    raca: str | None = None
    sexo: SexoAnimal
    data_nascimento: date
    peso: Decimal
    microchip: str | None = None

    @field_validator("data_nascimento")
    def data_nao_futura(cls, v):
        if v > date.today():
            raise ValueError("data_nascimento não pode ser futura")
        return v

    @field_validator("peso")
    def peso_positivo(cls, v):
        if v <= 0:
            raise ValueError("Peso deve ser maior que zero")
        return v
```

### `schemas/consulta.py`

```python
class ConsultaCreate(BaseModel):
    animal_id: UUID
    veterinario_id: UUID
    data_hora: datetime
    tipo: TipoConsulta
    observacoes: str | None = None

    @field_validator("data_hora")
    def data_nao_passado(cls, v):
        if v.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            if tipo != TipoConsulta.EMERGENCIA:
                raise ValueError("data_hora não pode ser no passado")
        return v

class ConsultaStatusUpdate(BaseModel):
    status: StatusConsulta
    diagnostico: str | None = None  # obrigatório quando status=CONCLUIDA

    @model_validator(mode="after")
    def diagnostico_obrigatorio(self):
        if self.status == StatusConsulta.CONCLUIDA and not self.diagnostico:
            raise ValueError("Diagnóstico obrigatório para concluir consulta")
        return self
```

### `schemas/vacina.py`

```python
class VacinaCreate(BaseModel):
    animal_id: UUID
    consulta_id: UUID | None = None
    nome_vacina: str
    lote: str
    data_aplicacao: date
    data_proxima: date | None = None

    @field_validator("data_aplicacao")
    def aplicacao_nao_futura(cls, v):
        if v > date.today():
            raise ValueError("data_aplicacao não pode ser futura")
        return v

    @model_validator(mode="after")
    def proxima_posterior(self):
        if self.data_proxima and self.data_proxima <= self.data_aplicacao:
            raise ValueError("data_proxima deve ser posterior à data_aplicacao")
        return self
```

### `schemas/transferencia.py`

```python
class TransferenciaCreate(BaseModel):
    animal_id: UUID
    tutor_destino_id: UUID
    motivo: str

    @field_validator("motivo")
    def motivo_minimo(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("Motivo deve ter no mínimo 10 caracteres")
        return v
```

### `schemas/auth.py`

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenPayload(BaseModel):
    sub: str        # email do usuário
    perfil: str
    exp: int
```

---

## 3. Estratégia de Validação em Camadas

```
Request Body
    │
    ▼
Schema Pydantic ──► @field_validator (campo único: CPF, datas, peso)
    │               @model_validator (cruzado: diagnostico+status)
    │
    ▼
Router ──────────── Recebe objeto já validado
    │
    ▼
Service ─────────── Valida regras de negócio (RN-001..RN-012)
                    Lança ClinicaException (→ HTTP 409/422)
```

---

## 4. Validação de CPF — Algoritmo

```python
def validate_cpf(cpf: str) -> str:
    # Remove formatação
    nums = re.sub(r'\D', '', cpf)
    if len(nums) != 11 or len(set(nums)) == 1:
        raise ValueError("CPF inválido")
    
    # Calcula dígitos verificadores
    for i in range(9, 11):
        soma = sum(int(nums[j]) * (i + 1 - j) for j in range(i))
        digito = (soma * 10 % 11) % 10
        if digito != int(nums[i]):
            raise ValueError("CPF inválido")
    
    return f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"
```

---

## 5. Schemas de Resposta Consolidada

```python
class HistoricoClinicoResponse(BaseModel):
    animal: AnimalResponse
    tutor_atual: TutorResponse
    consultas: list[ConsultaDetalheResponse]
    vacinas: list[VacinaResponse]
    evolucao_peso: list[EvolucaoPesoItem]
    resumo: EstatisticasAnimalResponse

class EstatisticasAnimalResponse(BaseModel):
    total_consultas: int
    ultima_consulta: datetime | None
    proxima_vacina: date | None
    total_vacinas: int
    consultas_por_status: dict[str, int]
    idade_anos: float
```
