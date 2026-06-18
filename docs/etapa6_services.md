# ETAPA 6 — Services (Regras de Negócio)
## API REST Clínica Veterinária

> **Status:** ⏳ Pendente  
> **Objetivo:** Implementar toda a lógica de domínio. **Nenhuma regra de negócio deve existir fora desta camada.**

---

## 1. Princípios

- Services recebem **schemas Pydantic** e retornam **models SQLAlchemy** ou **schemas de resposta**
- Cada service recebe o **Repository** correspondente via injeção de dependência
- Toda exceção de domínio é lançada aqui como `ClinicaException`
- Serviço de auditoria é injetado nos services que geram eventos críticos

---

## 2. TutorService

```python
class TutorService:
    async def criar(self, data: TutorCreate, usuario: str) -> Tutor: ...
    async def listar(self, filtros, paginacao) -> PaginatedResponse[TutorResponse]: ...
    async def buscar_por_id(self, id: UUID) -> Tutor: ...
    async def atualizar(self, id: UUID, data: TutorUpdate, usuario: str) -> Tutor: ...
    async def inativar(self, id: UUID, usuario: str) -> Tutor:
        # RN-001: verifica animais ativos antes de inativar
        animais_ativos = await self.animal_repo.contar_ativos_por_tutor(id)
        if animais_ativos > 0:
            raise TutorComAnimaisAtivosError()
        # Registra auditoria INATIVACAO_TUTOR
        await self.audit_service.registrar(EventoAuditoria.INATIVACAO_TUTOR, ...)
```

---

## 3. AnimalService

```python
class AnimalService:
    async def criar(self, data: AnimalCreate, usuario: str) -> Animal:
        # RN-003: verifica unicidade do microchip
        if data.microchip:
            existente = await self.repo.buscar_por_microchip(data.microchip)
            if existente:
                raise MicrochipDuplicadoError()
        # RN-002: validado no schema (data_nascimento não futura)
        # RN-012: validado no schema (peso > 0)

    async def atualizar_peso(self, id: UUID, peso: Decimal, usuario: str) -> Animal:
        # Registra evolução de peso para o histórico clínico
        await self.audit_service.registrar(
            EventoAuditoria.ATUALIZACAO_PESO,
            payload={"peso_anterior": animal.peso, "peso_novo": peso}
        )

    async def historico_clinico(self, id: UUID) -> HistoricoClinicoResponse:
        # Cálculo derivado: combina consultas + vacinas + evolução de peso

    async def resumo_estatistico(self, id: UUID) -> EstatisticasAnimalResponse:
        # Cálculo derivado: total_consultas, ultima_consulta, proxima_vacina, etc.
```

---

## 4. ConsultaService — Máquina de Estados

```python
class ConsultaService:
    async def criar(self, data: ConsultaCreate, usuario: str) -> Consulta:
        # RN-005: data_hora não no passado (exceto emergência — RN-006)
        # RN-011: veterinário ativo
        # RN-004: verificar conflito de horário
        agora = datetime.now(timezone.utc)
        if data.data_hora < agora and data.tipo != TipoConsulta.EMERGENCIA:
            raise ValueError("data_hora não pode ser no passado")

        vet = await self.vet_repo.buscar_por_id(data.veterinario_id)
        if not vet.ativo:
            raise VeterinarioInativoError()

        conflito = await self.repo.verificar_conflito(
            veterinario_id=data.veterinario_id,
            data_hora=data.data_hora,
            janela_minutos=30,
        )
        if conflito and data.tipo != TipoConsulta.EMERGENCIA:
            raise ConsultaConflictError()
        elif conflito and data.tipo == TipoConsulta.EMERGENCIA:
            # RN-006: permite, mas audita
            await self.audit_service.registrar(EventoAuditoria.EMERGENCIA_SOBREPOSTA, ...)

    async def mudar_status(
        self,
        id: UUID,
        novo_status: StatusConsulta,
        diagnostico: str | None,
        usuario: str,
    ) -> Consulta:
        consulta = await self.repo.buscar_por_id(id)

        # RN-008: estado terminal é imutável
        if consulta.is_terminal:
            raise ConsultaImutavelError()

        # Valida transição pela máquina de estados
        if not consulta.pode_transicionar_para(novo_status):
            raise TransicaoInvalidaError(
                f"Transição {consulta.status} → {novo_status.value} inválida"
            )

        # RN-007: diagnóstico obrigatório para concluir
        if novo_status == StatusConsulta.CONCLUIDA and not diagnostico:
            raise DiagnosticoObrigatorioError()

        consulta.status = novo_status.value
        if diagnostico:
            consulta.diagnostico = diagnostico

        if novo_status == StatusConsulta.CANCELADA:
            await self.audit_service.registrar(EventoAuditoria.CANCELAMENTO_CONSULTA, ...)
        elif novo_status == StatusConsulta.CONCLUIDA:
            await self.audit_service.registrar(EventoAuditoria.CONCLUSAO_CONSULTA, ...)

        return consulta
```

---

## 5. TransferenciaService

```python
class TransferenciaService:
    async def transferir(self, data: TransferenciaCreate, usuario: str) -> TransferenciaAnimal:
        # RN-010: motivo obrigatório (validado no schema, revalidado aqui)
        animal = await self.animal_repo.buscar_por_id(data.animal_id)
        tutor_destino = await self.tutor_repo.buscar_por_id(data.tutor_destino_id)

        if not tutor_destino.ativo:
            raise TutorInativoError("Tutor destino está inativo")

        if animal.tutor_id == data.tutor_destino_id:
            raise ValueError("Tutor destino é o mesmo que o tutor atual")

        tutor_origem_id = animal.tutor_id

        # Atualiza o tutor do animal
        animal.tutor_id = data.tutor_destino_id

        # Cria registro imutável
        transferencia = TransferenciaAnimal(
            animal_id=data.animal_id,
            tutor_origem_id=tutor_origem_id,
            tutor_destino_id=data.tutor_destino_id,
            motivo=data.motivo,
            criado_por=usuario,
        )

        # Auditoria obrigatória (RN-010)
        await self.audit_service.registrar(
            EventoAuditoria.TRANSFERENCIA_ANIMAL,
            entidade="animais",
            entidade_id=data.animal_id,
            usuario=usuario,
            payload={
                "tutor_origem": str(tutor_origem_id),
                "tutor_destino": str(data.tutor_destino_id),
                "motivo": data.motivo,
            }
        )

        return transferencia
```

---

## 6. AuthService

```python
class AuthService:
    async def login(self, email: str, password: str) -> TokenResponse:
        usuario = await self.repo.buscar_por_email(email)
        if not usuario or not verify_password(password, usuario.senha_hash):
            raise HTTPException(401, "Credenciais inválidas")
        
        access_token = create_access_token(email, usuario.perfil)
        refresh_token = create_refresh_token(email)
        
        await self.audit_service.registrar(EventoAuditoria.LOGIN, ...)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        # Gera novo par de tokens
```

---

## 7. Mapa de Regras de Negócio → Service

| RN | Service | Método |
|---|---|---|
| RN-001 | TutorService | `inativar()` |
| RN-002 | Pydantic Schema | `@field_validator("data_nascimento")` |
| RN-003 | AnimalService | `criar()`, `atualizar()` |
| RN-004 | ConsultaService | `criar()` |
| RN-005 | ConsultaService + Pydantic | `criar()` |
| RN-006 | ConsultaService | `criar()` (exceção de RN-004) |
| RN-007 | ConsultaService | `mudar_status()` |
| RN-008 | ConsultaService | `mudar_status()`, `atualizar()` |
| RN-009 | Pydantic Schema | `@field_validator("data_aplicacao")` |
| RN-010 | TransferenciaService | `transferir()` |
| RN-011 | ConsultaService | `criar()` |
| RN-012 | Pydantic Schema | `@field_validator("peso")` |
