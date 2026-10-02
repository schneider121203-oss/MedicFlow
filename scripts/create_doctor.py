"""Create the first doctor without exposing a public registration endpoint."""

import argparse
import getpass

from backend.database import SessionLocal
from backend.models import Medico, Membresia, Organizacion, RolMembresia
from backend.routers.auth import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Crear un médico en MediFlow")
    parser.add_argument("--email", required=True)
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--especialidad", default="Medicina General")
    args = parser.parse_args()

    password = getpass.getpass("Contraseña: ")
    confirmation = getpass.getpass("Confirmar contraseña: ")
    if password != confirmation:
        raise SystemExit("Las contraseñas no coinciden")
    if len(password) < 12:
        raise SystemExit("La contraseña debe contener al menos 12 caracteres")

    with SessionLocal() as db:
        if db.query(Medico).filter(Medico.email == args.email).first():
            raise SystemExit("Ya existe un médico con ese email")
        db.add(
            doctor := Medico(
                nombre=args.nombre,
                email=args.email,
                especialidad=args.especialidad,
                password_hash=hash_password(password),
            )
        )
        db.flush()
        organization = Organizacion(
            nombre=f"Consultorio de {args.nombre}", slug=f"consultorio-{doctor.id}"
        )
        db.add(organization)
        db.flush()
        db.add(
            Membresia(
                organizacion_id=organization.id,
                medico_id=doctor.id,
                rol=RolMembresia.admin,
            )
        )
        db.commit()
    print("Médico creado correctamente")


if __name__ == "__main__":
    main()
