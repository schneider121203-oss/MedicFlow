import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class EstadoCita(str, enum.Enum):
    programada = "programada"
    en_consulta = "en_consulta"
    completada = "completada"
    cancelada = "cancelada"


class SexoPaciente(str, enum.Enum):
    masculino = "masculino"
    femenino = "femenino"
    otro = "otro"


class RolMembresia(str, enum.Enum):
    admin = "admin"
    medico = "medico"
    auditor = "auditor"


class EstadoNota(str, enum.Enum):
    borrador = "borrador"
    firmada = "firmada"
    enmendada = "enmendada"


class EstadoTrabajo(str, enum.Enum):
    creado = "creado"
    transcribiendo = "transcribiendo"
    estructurando = "estructurando"
    listo = "listo"
    fallido = "fallido"


class Medico(Base):
    __tablename__ = "medicos"
    __table_args__ = (UniqueConstraint("email", name="uq_medicos_email"),)
    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False)
    password_hash = Column(String(255), nullable=False)
    especialidad = Column(String(100), default="Medicina General")
    numero_colegiado = Column(String(50), nullable=True)
    telefono = Column(String(20), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    citas = relationship("Cita", back_populates="medico")
    historias = relationship("HistoriaClinica", back_populates="medico")
    pacientes = relationship("Paciente", back_populates="medico")
    membresias = relationship("Membresia", back_populates="medico")


class Organizacion(Base):
    __tablename__ = "organizaciones"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    slug = Column(String(80), nullable=False, unique=True)
    activa = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    membresias = relationship("Membresia", back_populates="organizacion")
    sedes = relationship("Sede", back_populates="organizacion")


class Sede(Base):
    __tablename__ = "sedes"
    __table_args__ = (UniqueConstraint("organizacion_id", "nombre", name="uq_sede_org_nombre"),)
    id = Column(Integer, primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    direccion = Column(Text, nullable=True)
    activa = Column(Boolean, default=True, nullable=False)
    organizacion = relationship("Organizacion", back_populates="sedes")


class Membresia(Base):
    __tablename__ = "membresias"
    __table_args__ = (
        UniqueConstraint("organizacion_id", "medico_id", name="uq_membresia_org_medico"),
    )
    id = Column(Integer, primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False, index=True)
    rol = Column(Enum(RolMembresia), nullable=False, default=RolMembresia.medico)
    activa = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    organizacion = relationship("Organizacion", back_populates="membresias")
    medico = relationship("Medico", back_populates="membresias")


class Paciente(Base):
    __tablename__ = "pacientes"
    __table_args__ = (
        UniqueConstraint("organizacion_id", "documento", name="uq_paciente_org_documento"),
    )
    id = Column(Integer, primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=True, index=True)
    nombre = Column(String(150), nullable=False)
    documento = Column(String(30), nullable=True)
    fecha_nacimiento = Column(String(20), nullable=True)
    sexo = Column(Enum(SexoPaciente), nullable=True)
    telefono = Column(String(20), nullable=True)
    email = Column(String(150), nullable=True)
    direccion = Column(Text, nullable=True)
    tipo_sangre = Column(String(5), nullable=True)
    alergias = Column(Text, nullable=True)
    enfermedades_cronicas = Column(Text, nullable=True)
    notas_generales = Column(Text, nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    medico = relationship("Medico", back_populates="pacientes")
    citas = relationship("Cita", back_populates="paciente")
    historias = relationship("HistoriaClinica", back_populates="paciente")


class Cita(Base):
    __tablename__ = "citas"
    __table_args__ = (Index("ix_citas_org_fecha", "organizacion_id", "fecha_hora"),)
    id = Column(Integer, primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    fecha_hora = Column(DateTime(timezone=True), nullable=False)
    motivo = Column(Text, nullable=True)
    estado = Column(Enum(EstadoCita), default=EstadoCita.programada, nullable=False)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paciente = relationship("Paciente", back_populates="citas")
    medico = relationship("Medico", back_populates="citas")
    historia = relationship("HistoriaClinica", back_populates="cita", uselist=False)


class HistoriaClinica(Base):
    __tablename__ = "historias_clinicas"
    __table_args__ = (
        UniqueConstraint("cita_id", name="uq_historia_cita"),
        Index("ix_historias_org_created", "organizacion_id", "created_at"),
    )
    id = Column(Integer, primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    cita_id = Column(Integer, ForeignKey("citas.id"), nullable=True)
    transcripcion = Column(Text, nullable=True)
    s_subjetivo = Column(Text, nullable=True)
    o_objetivo = Column(Text, nullable=True)
    a_analisis = Column(Text, nullable=True)
    p_plan = Column(Text, nullable=True)
    receta = Column(JSON, nullable=True)
    pdf_path = Column(String(255), nullable=True)
    estado = Column(Enum(EstadoNota), default=EstadoNota.borrador, nullable=False)
    version_actual = Column(Integer, default=1, nullable=False)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paciente = relationship("Paciente", back_populates="historias")
    medico = relationship("Medico", back_populates="historias")
    cita = relationship("Cita", back_populates="historia")


class VersionHistoria(Base):
    __tablename__ = "versiones_historia"
    __table_args__ = (
        UniqueConstraint("historia_id", "version", name="uq_historia_version"),
        Index("ix_versiones_org_historia", "organizacion_id", "historia_id"),
    )
    id = Column(Integer, primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False)
    historia_id = Column(Integer, ForeignKey("historias_clinicas.id"), nullable=False)
    version = Column(Integer, nullable=False)
    autor_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    s_subjetivo = Column(Text, nullable=True)
    o_objetivo = Column(Text, nullable=True)
    a_analisis = Column(Text, nullable=True)
    p_plan = Column(Text, nullable=True)
    receta = Column(JSON, nullable=True)
    motivo_cambio = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Consentimiento(Base):
    __tablename__ = "consentimientos"
    __table_args__ = (Index("ix_consentimientos_org_paciente", "organizacion_id", "paciente_id"),)
    id = Column(Integer, primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    tipo = Column(String(50), nullable=False, default="grabacion_audio")
    otorgado = Column(Boolean, nullable=False)
    policy_version = Column(String(30), nullable=False, default="1.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TrabajoProcesamiento(Base):
    __tablename__ = "trabajos_procesamiento"
    __table_args__ = (Index("ix_trabajos_org_created", "organizacion_id", "created_at"),)
    id = Column(String(36), primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    cita_id = Column(Integer, ForeignKey("citas.id"), nullable=True)
    estado = Column(Enum(EstadoTrabajo), default=EstadoTrabajo.creado, nullable=False)
    object_key = Column(String(500), nullable=False)
    transcripcion = Column(Text, nullable=True)
    resultado = Column(JSON, nullable=True)
    error_code = Column(String(80), nullable=True)
    intentos = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EventoAuditoria(Base):
    __tablename__ = "eventos_auditoria"
    __table_args__ = (Index("ix_auditoria_org_created", "organizacion_id", "created_at"),)
    id = Column(Integer, primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("medicos.id"), nullable=True)
    accion = Column(String(100), nullable=False)
    recurso_tipo = Column(String(80), nullable=False)
    recurso_id = Column(String(80), nullable=True)
    detalles = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ConexionEHR(Base):
    __tablename__ = "conexiones_ehr"
    id = Column(Integer, primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    proveedor = Column(String(80), nullable=False, default="fhir")
    fhir_base_url = Column(String(500), nullable=False)
    client_id = Column(String(150), nullable=False)
    activa = Column(Boolean, default=True, nullable=False)


class SmartLaunch(Base):
    __tablename__ = "smart_launches"
    id = Column(String(64), primary_key=True)
    organizacion_id = Column(Integer, ForeignKey("organizaciones.id"), nullable=False)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    cita_id = Column(Integer, ForeignKey("citas.id"), nullable=True)
    usado = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
