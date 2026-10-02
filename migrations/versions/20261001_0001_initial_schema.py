"""Initial secured prototype schema.

Revision ID: 20261001_0001
Revises:
Create Date: 2026-10-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261001_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


estado_cita = postgresql.ENUM(
    "programada",
    "en_consulta",
    "completada",
    "cancelada",
    name="estadocita",
    create_type=False,
)
sexo_paciente = postgresql.ENUM(
    "masculino", "femenino", "otro", name="sexopaciente", create_type=False
)


def upgrade() -> None:
    estado_cita.create(op.get_bind(), checkfirst=True)
    sexo_paciente.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "medicos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("especialidad", sa.String(100), nullable=True),
        sa.Column("numero_colegiado", sa.String(50), nullable=True),
        sa.Column("telefono", sa.String(20), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_medicos_email"),
    )
    op.create_table(
        "pacientes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("medico_id", sa.Integer(), sa.ForeignKey("medicos.id"), nullable=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("documento", sa.String(30), nullable=True),
        sa.Column("fecha_nacimiento", sa.String(20), nullable=True),
        sa.Column("sexo", sexo_paciente, nullable=True),
        sa.Column("telefono", sa.String(20), nullable=True),
        sa.Column("email", sa.String(150), nullable=True),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("tipo_sangre", sa.String(5), nullable=True),
        sa.Column("alergias", sa.Text(), nullable=True),
        sa.Column("enfermedades_cronicas", sa.Text(), nullable=True),
        sa.Column("notas_generales", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("medico_id", "documento", name="uq_paciente_medico_documento"),
    )
    op.create_index("ix_pacientes_medico_id", "pacientes", ["medico_id"])

    op.create_table(
        "citas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paciente_id", sa.Integer(), sa.ForeignKey("pacientes.id"), nullable=False),
        sa.Column("medico_id", sa.Integer(), sa.ForeignKey("medicos.id"), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("estado", estado_cita, nullable=False, server_default="programada"),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_citas_medico_fecha", "citas", ["medico_id", "fecha_hora"])

    op.create_table(
        "historias_clinicas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paciente_id", sa.Integer(), sa.ForeignKey("pacientes.id"), nullable=False),
        sa.Column("medico_id", sa.Integer(), sa.ForeignKey("medicos.id"), nullable=False),
        sa.Column("cita_id", sa.Integer(), sa.ForeignKey("citas.id"), nullable=True),
        sa.Column("transcripcion", sa.Text(), nullable=True),
        sa.Column("s_subjetivo", sa.Text(), nullable=True),
        sa.Column("o_objetivo", sa.Text(), nullable=True),
        sa.Column("a_analisis", sa.Text(), nullable=True),
        sa.Column("p_plan", sa.Text(), nullable=True),
        sa.Column("receta", sa.JSON(), nullable=True),
        sa.Column("pdf_path", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("cita_id", name="uq_historia_cita"),
    )
    op.create_index(
        "ix_historias_medico_created", "historias_clinicas", ["medico_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("historias_clinicas")
    op.drop_table("citas")
    op.drop_table("pacientes")
    op.drop_table("medicos")
    sexo_paciente.drop(op.get_bind(), checkfirst=True)
    estado_cita.drop(op.get_bind(), checkfirst=True)
