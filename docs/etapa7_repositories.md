# ETAPA 7 — Repositories (Acesso ao Banco)
## API REST Clínica Veterinária

> **Status:** ⏳ Pendente  
> **Objetivo:** Implementar a camada de acesso a dados com SQLAlchemy 2.0 async. **Sem lógica de negócio.**

---

## 1. Princípios

- Repositories recebem e retornam **models SQLAlchemy**
- Toda query usa `select()` do SQLAlchemy 2.0 (não `.query()` legado)
- **Paginação** via `limit` / `offset`
- **Filtros** como parâmetros opcionais
- Injetados nos services via FastAPI `Depends()`

---

## 2. BaseRepository — Genérico

```python
class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 20,
        offset: int = 0,
        **filters,
    ) -> tuple[list[ModelType], int]:
        stmt = select(self.model)
        for field, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, field) == value)
        
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar()
        
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        await self.session.delete(obj)
        await self.session.flush()
```

---

## 3. AnimalRepository

```python
class AnimalRepository(BaseRepository[Animal]):
    async def buscar_por_microchip(self, microchip: str) -> Animal | None:
        stmt = select(Animal).where(
            Animal.microchip == microchip,
            Animal.ativo == True,
        )
        ...

    async def contar_ativos_por_tutor(self, tutor_id: UUID) -> int:
        stmt = select(func.count(Animal.id)).where(
            Animal.tutor_id == tutor_id,
            Animal.ativo == True,
        )
        ...

    async def listar_com_filtros(
        self,
        nome: str | None = None,
        especie: str | None = None,
        tutor_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Animal], int]:
        # Filtros dinâmicos com AND
```

---

## 4. ConsultaRepository

```python
class ConsultaRepository(BaseRepository[Consulta]):
    async def verificar_conflito(
        self,
        veterinario_id: UUID,
        data_hora: datetime,
        janela_minutos: int = 30,
        excluir_id: UUID | None = None,
    ) -> bool:
        """
        Verifica se existe consulta para o mesmo veterinário
        dentro da janela de ±janela_minutos.
        Exclui estados terminais (CONCLUIDA, CANCELADA).
        """
        inicio = data_hora - timedelta(minutes=janela_minutos)
        fim = data_hora + timedelta(minutes=janela_minutos)

        stmt = select(Consulta).where(
            Consulta.veterinario_id == veterinario_id,
            Consulta.data_hora.between(inicio, fim),
            Consulta.status.notin_(["CONCLUIDA", "CANCELADA"]),
        )
        if excluir_id:
            stmt = stmt.where(Consulta.id != excluir_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def historico_por_animal(
        self, animal_id: UUID, limit: int = 50
    ) -> list[Consulta]:
        stmt = (
            select(Consulta)
            .where(Consulta.animal_id == animal_id)
            .order_by(Consulta.data_hora.desc())
            .limit(limit)
            .options(selectinload(Consulta.veterinario))
        )
        ...

    async def estatisticas_por_animal(self, animal_id: UUID) -> dict:
        """
        Retorna total, última consulta e consultas por status.
        Query agregada eficiente — evita carregar todos os registros.
        """
```

---

## 5. VacinaRepository

```python
class VacinaRepository(BaseRepository[Vacina]):
    async def proxima_vacina_por_animal(self, animal_id: UUID) -> date | None:
        stmt = select(func.min(Vacina.data_proxima)).where(
            Vacina.animal_id == animal_id,
            Vacina.data_proxima >= date.today(),
        )
        ...

    async def listar_por_animal(self, animal_id: UUID) -> list[Vacina]:
        stmt = (
            select(Vacina)
            .where(Vacina.animal_id == animal_id)
            .order_by(Vacina.data_aplicacao.desc())
        )
        ...
```

---

## 6. AuditoriaRepository

```python
class AuditoriaRepository(BaseRepository[Auditoria]):
    async def criar_evento(
        self,
        evento: EventoAuditoria,
        entidade: str,
        entidade_id: UUID,
        usuario: str,
        payload: dict | None = None,
        ip_address: str | None = None,
    ) -> Auditoria:
        """Append-only: nunca expõe update/delete."""
        auditoria = Auditoria(
            evento=evento.value,
            entidade=entidade,
            entidade_id=entidade_id,
            usuario=usuario,
            payload=payload,
            ip_address=ip_address,
        )
        self.session.add(auditoria)
        await self.session.flush()
        return auditoria

    async def listar_por_entidade(
        self, entidade: str, entidade_id: UUID
    ) -> list[Auditoria]:
        stmt = (
            select(Auditoria)
            .where(
                Auditoria.entidade == entidade,
                Auditoria.entidade_id == entidade_id,
            )
            .order_by(Auditoria.timestamp.desc())
        )
        ...
```

---

## 7. Injeção de Dependência (FastAPI)

```python
# Em cada router:
async def get_tutor_service(
    session: AsyncSession = Depends(get_db),
) -> TutorService:
    repo = TutorRepository(session)
    animal_repo = AnimalRepository(session)
    audit = AuditoriaService(AuditoriaRepository(session))
    return TutorService(repo, animal_repo, audit)
```

---

## 8. Paginação Padronizada

```
GET /animais?limit=20&offset=0&nome=rex&especie=CANINO&tutor_id=<uuid>

Response:
{
  "items": [...],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```
