"""
app/services/__init__.py
"""
from app.services.animal import AnimalService
from app.services.auth import AuthService
from app.services.consulta import ConsultaService
from app.services.transferencia import TransferenciaService
from app.services.tutor import TutorService
from app.services.vacina import VacinaService
from app.services.veterinario import VeterinarioService

__all__ = [
    "TutorService",
    "AnimalService",
    "VeterinarioService",
    "ConsultaService",
    "VacinaService",
    "TransferenciaService",
    "AuthService",
]
