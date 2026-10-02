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


class Paciente(Base):
    __tablename__ = "pacientes"
    __table_args__ = (
        UniqueConstraint("medico_id", "documento", name="uq_paciente_medico_documento"),
    )
    id = Column(Integer, primary_key=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False, index=True)
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
    __table_args__ = (Index("ix_citas_medico_fecha", "medico_id", "fecha_hora"),)

    id = Column(Integer, primary_key=True)
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
        Index("ix_historias_medico_created", "medico_id", "created_at"),
    )

    id = Column(Integer, primary_key=True)
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    paciente = relationship("Paciente", back_populates="historias")
    medico = relationship("Medico", back_populates="historias")
    cita = relationship("Cita", back_populates="historia")
