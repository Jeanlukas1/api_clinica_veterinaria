# ETAPA 4 — Models SQLAlchemy
## API REST Clínica Veterinária

> **Status:** ✅ Concluída (implementada junto à Etapa 2)  
> **Referência completa:** Ver [etapa2_banco.md](./etapa2_banco.md)

---

## Resumo dos Models

| Model | Arquivo | Herda | Destaques |
|---|---|---|---|
| `Tutor` | `app/models/tutor.py` | Base + TimestampMixin | CPF e email únicos |
| `Animal` | `app/models/animal.py` | Base + TimestampMixin | `idade_anos` derivado, microchip parcial |
| `Veterinario` | `app/models/veterinario.py` | Base + TimestampMixin | CRMV único |
| `Consulta` | `app/models/consulta.py` | Base + TimestampMixin | `is_terminal`, `pode_transicionar_para()` |
| `Vacina` | `app/models/vacina.py` | Base + TimestampMixin | `consulta_id` opcional |
| `TransferenciaAnimal` | `app/models/transferencia_animal.py` | Base | Imutável, 2 FKs para tutores |
| `Auditoria` | `app/models/auditoria.py` | Base | Append-only, payload JSONB |
| `Usuario` | `app/models/usuario.py` | Base + TimestampMixin | JWT auth + RBAC |

## Enums Disponíveis (`app/models/enums.py`)

```python
EspecieAnimal:           CANINO, FELINO, AVE, REPTIL, ROEDOR, OUTRO
SexoAnimal:              M (macho), F (fêmea)
EspecialidadeVeterinario: CLINICA_GERAL, ORTOPEDIA, ONCOLOGIA, DERMATOLOGIA, CARDIOLOGIA, OFTALMOLOGIA, OUTRO
StatusConsulta:          AGENDADA, CONFIRMADA, EM_ANDAMENTO, CONCLUIDA, CANCELADA
TipoConsulta:            ROTINA, RETORNO, EMERGENCIA, CIRURGIA, EXAME
EventoAuditoria:         TRANSFERENCIA_ANIMAL, INATIVACAO_TUTOR, CANCELAMENTO_CONSULTA, ...
PerfilUsuario:           ADMIN, VETERINARIO, RECEPCIONISTA, TUTOR
```

## Índices Criados

| Índice | Tabela | Colunas | Propósito |
|---|---|---|---|
| `ix_animais_tutor_id` | animais | tutor_id | Listar animais por tutor |
| `uix_animais_microchip_not_null` | animais | microchip (parcial) | RN-003 unicidade |
| `ix_consultas_veterinario_data` | consultas | (veterinario_id, data_hora) | RN-004 conflito de agenda |
| `ix_consultas_animal_data` | consultas | (animal_id, data_hora) | Histórico clínico |
| `ix_vacinas_animal_proxima` | vacinas | (animal_id, data_proxima) | Próxima vacina |
| `ix_auditorias_entidade_id` | auditorias | (entidade, entidade_id) | Auditoria por objeto |
| `ix_auditorias_timestamp` | auditorias | timestamp | Cronologia |
| `ix_transferencias_animal` | transferencias_animais | animal_id | Histórico de guarda |
