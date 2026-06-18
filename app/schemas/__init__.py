"""
app/schemas/__init__.py
────────────────────────
Exportações centralizadas de todos os schemas Pydantic V2.
"""
from app.schemas.animal import (
    AnimalCreate,
    AnimalResumoResponse,
    AnimalResponse,
    AnimalUpdate,
    EstatisticasAnimalResponse,
    EvolucaoPesoItem,
    HistoricoClinicoResponse,
)
from app.schemas.auditoria import AuditoriaFiltros, AuditoriaResponse
from app.schemas.auth import (
    AlterarSenhaRequest,
    LoginRequest,
    RefreshRequest,
    TokenPayload,
    TokenResponse,
    UsuarioCreate,
    UsuarioResponse,
    UsuarioUpdate,
)
from app.schemas.common import (
    BaseSchema,
    ErrorResponse,
    HealthResponse,
    MessageResponse,
    PaginatedResponse,
)
from app.schemas.consulta import (
    AgendaVeterinarioResponse,
    ConsultaCreate,
    ConsultaDetalheResponse,
    ConsultaResponse,
    ConsultaStatusUpdate,
    ConsultaUpdate,
)
from app.schemas.transferencia import (
    TransferenciaCreate,
    TransferenciaDetalheResponse,
    TransferenciaResponse,
)
from app.schemas.tutor import (
    TutorCreate,
    TutorResponse,
    TutorResumoResponse,
    TutorUpdate,
)
from app.schemas.vacina import (
    VacinaCreate,
    VacinaResponse,
    VacinaResumoResponse,
    VacinaUpdate,
)
from app.schemas.veterinario import (
    VeterinarioCreate,
    VeterinarioResponse,
    VeterinarioResumoResponse,
    VeterinarioUpdate,
)

__all__ = [
    # Common
    "BaseSchema", "PaginatedResponse", "ErrorResponse",
    "MessageResponse", "HealthResponse",
    # Tutor
    "TutorCreate", "TutorUpdate", "TutorResponse", "TutorResumoResponse",
    # Animal
    "AnimalCreate", "AnimalUpdate", "AnimalResponse", "AnimalResumoResponse",
    "EstatisticasAnimalResponse", "EvolucaoPesoItem", "HistoricoClinicoResponse",
    # Veterinario
    "VeterinarioCreate", "VeterinarioUpdate",
    "VeterinarioResponse", "VeterinarioResumoResponse",
    # Consulta
    "ConsultaCreate", "ConsultaUpdate", "ConsultaStatusUpdate",
    "ConsultaResponse", "ConsultaDetalheResponse", "AgendaVeterinarioResponse",
    # Vacina
    "VacinaCreate", "VacinaUpdate", "VacinaResponse", "VacinaResumoResponse",
    # Transferencia
    "TransferenciaCreate", "TransferenciaResponse", "TransferenciaDetalheResponse",
    # Auditoria
    "AuditoriaResponse", "AuditoriaFiltros",
    # Auth
    "LoginRequest", "RefreshRequest", "TokenResponse", "TokenPayload",
    "UsuarioCreate", "UsuarioUpdate", "UsuarioResponse", "AlterarSenhaRequest",
]
