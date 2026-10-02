from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ─── ENUMS ────────────────────────────────────────────────
class EstadoCita(str, Enum):
    programada = "programada"
    en_consulta = "en_consulta"
    completada = "completada"
    cancelada = "cancelada"


class SexoPaciente(str, Enum):
    masculino = "masculino"
    femenino = "femenino"
    otro = "otro"


# ─── MÉDICO ───────────────────────────────────────────────
class MedicoBase(BaseModel):
    nombre: str
    email: EmailStr
    especialidad: Optional[str] = "Medicina General"
    numero_colegiado: Optional[str] = None
    telefono: Optional[str] = None


class MedicoCreate(MedicoBase):
    password: str = Field(min_length=12, max_length=128)


class MedicoOut(MedicoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activo: bool
    created_at: datetime
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    role: Optional[str] = None


class MedicoUpdate(BaseModel):
    nombre: Optional[str] = None
    especialidad: Optional[str] = None
    numero_colegiado: Optional[str] = None
    telefono: Optional[str] = None


# ─── AUTH ─────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    medico: MedicoOut
    organization_id: int
    organization_name: str
    role: str


# ─── PACIENTE ─────────────────────────────────────────────
class PacienteBase(BaseModel):
    nombre: str
    documento: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    sexo: Optional[SexoPaciente] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    tipo_sangre: Optional[str] = None
    alergias: Optional[str] = None
    enfermedades_cronicas: Optional[str] = None
    notas_generales: Optional[str] = None


class PacienteCreate(PacienteBase):
    pass


class PacienteUpdate(PacienteBase):
    nombre: Optional[str] = None


class PacienteOut(PacienteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ─── CITA ─────────────────────────────────────────────────
class CitaBase(BaseModel):
    paciente_id: int
    fecha_hora: datetime
    motivo: Optional[str] = None
    notas: Optional[str] = None


class CitaCreate(CitaBase):
    pass


class CitaUpdate(BaseModel):
    fecha_hora: Optional[datetime] = None
    motivo: Optional[str] = None
    estado: Optional[EstadoCita] = None
    notas: Optional[str] = None


class CitaOut(CitaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medico_id: int
    estado: EstadoCita
    created_at: datetime
    paciente: Optional[PacienteOut] = None


# ─── HISTORIA CLÍNICA ─────────────────────────────────────
class MedicamentoReceta(BaseModel):
    medicamento: str
    dosis: str
    frecuencia: str
    duracion: str


class SOAPData(BaseModel):
    s_subjetivo: str
    o_objetivo: str
    a_analisis: str
    p_plan: str
    receta: List[MedicamentoReceta]


class HistoriaUpdate(BaseModel):
    transcripcion: Optional[str] = None
    s_subjetivo: Optional[str] = None
    o_objetivo: Optional[str] = None
    a_analisis: Optional[str] = None
    p_plan: Optional[str] = None
    receta: Optional[List[MedicamentoReceta]] = None
    motivo_cambio: Optional[str] = None


class ConsentimientoCreate(BaseModel):
    paciente_id: int
    otorgado: bool
    tipo: str = "grabacion_audio"
    policy_version: str = "1.0"


class ConsentimientoOut(ConsentimientoCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    medico_id: int
    created_at: datetime


class TrabajoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    paciente_id: int
    cita_id: Optional[int] = None
    estado: str
    transcripcion: Optional[str] = None
    resultado: Optional[dict] = None
    error_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SmartExchangeRequest(BaseModel):
    code: str


class SmartExchangeResponse(Token):
    patient_id: int
    encounter_id: Optional[int] = None


class HistoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    medico_id: int
    cita_id: Optional[int] = None
    transcripcion: Optional[str] = None
    s_subjetivo: Optional[str] = None
    o_objetivo: Optional[str] = None
    a_analisis: Optional[str] = None
    p_plan: Optional[str] = None
    receta: Optional[list] = None
    pdf_path: Optional[str] = None
    created_at: datetime
    paciente: Optional[PacienteOut] = None
    estado: str = "borrador"
    version_actual: int = 1
    signed_at: Optional[datetime] = None


# ─── DASHBOARD ────────────────────────────────────────────
class DashboardStats(BaseModel):
    pacientes_total: int
    citas_hoy: int
    consultas_mes: int
    citas_pendientes: int
