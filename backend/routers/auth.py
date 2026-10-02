from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.config import settings
from backend.database import get_db, set_tenant_context

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def get_current_medico(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        medico_id: int = payload.get("sub")
        organization_id: int = payload.get("org")
        if medico_id is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc
    medico = db.query(models.Medico).filter(models.Medico.id == int(medico_id)).first()
    if medico is None or not medico.activo:
        raise credentials_exception
    membership = (
        db.query(models.Membresia)
        .filter(
            models.Membresia.medico_id == medico.id,
            models.Membresia.organizacion_id == organization_id,
            models.Membresia.activa.is_(True),
        )
        .first()
    )
    if not membership or not membership.organizacion.activa:
        raise credentials_exception
    set_tenant_context(db, organization_id)
    medico.organization_id = organization_id
    medico.organization_name = membership.organizacion.nombre
    medico.role = membership.rol.value
    return medico


@router.post("/login", response_model=schemas.Token)
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    medico = db.query(models.Medico).filter(models.Medico.email == request.email).first()
    if not medico or not verify_password(request.password, medico.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    if not medico.activo:
        raise HTTPException(status_code=403, detail="Cuenta desactivada")
    membership = (
        db.query(models.Membresia)
        .filter(models.Membresia.medico_id == medico.id, models.Membresia.activa.is_(True))
        .order_by(models.Membresia.id)
        .first()
    )
    if not membership or not membership.organizacion.activa:
        raise HTTPException(
            status_code=403, detail="El usuario no pertenece a una organización activa"
        )
    medico.organization_id = membership.organizacion_id
    medico.organization_name = membership.organizacion.nombre
    medico.role = membership.rol.value
    token = create_access_token({"sub": str(medico.id), "org": membership.organizacion_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "medico": medico,
        "organization_id": membership.organizacion_id,
        "organization_name": membership.organizacion.nombre,
        "role": membership.rol.value,
    }


@router.post("/register", response_model=schemas.MedicoOut)
def register(medico_data: schemas.MedicoCreate, db: Session = Depends(get_db)):
    if not settings.registration_enabled:
        raise HTTPException(status_code=403, detail="El registro público está deshabilitado")
    existing = db.query(models.Medico).filter(models.Medico.email == medico_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    nuevo = models.Medico(
        nombre=medico_data.nombre,
        email=medico_data.email,
        password_hash=hash_password(medico_data.password),
        especialidad=medico_data.especialidad,
        numero_colegiado=medico_data.numero_colegiado,
        telefono=medico_data.telefono,
    )
    db.add(nuevo)
    db.flush()
    organization = models.Organizacion(
        nombre=f"Consultorio de {nuevo.nombre}", slug=f"consultorio-{nuevo.id}"
    )
    db.add(organization)
    db.flush()
    db.add(
        models.Membresia(
            organizacion_id=organization.id,
            medico_id=nuevo.id,
            rol=models.RolMembresia.admin,
        )
    )
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.get("/me", response_model=schemas.MedicoOut)
def get_me(current_medico=Depends(get_current_medico)):
    return current_medico


@router.put("/me", response_model=schemas.MedicoOut)
def update_me(
    data: schemas.MedicoUpdate,
    db: Session = Depends(get_db),
    current_medico=Depends(get_current_medico),
):
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(current_medico, key, value)
    db.commit()
    db.refresh(current_medico)
    return current_medico
