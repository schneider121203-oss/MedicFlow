from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@event.listens_for(Session, "after_begin")
def restore_tenant_context(session, _transaction, connection) -> None:
    """Reapply tenant RLS context whenever a session opens a new transaction."""
    organization_id = session.info.get("organization_id")
    if organization_id is not None:
        connection.execute(
            text("SELECT set_config('app.current_organization_id', :organization_id, false)"),
            {"organization_id": str(organization_id)},
        )


@event.listens_for(engine, "checkin")
def reset_tenant_context(dbapi_connection, _connection_record) -> None:
    if dbapi_connection is None:
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("RESET app.current_organization_id")
        dbapi_connection.commit()
    finally:
        cursor.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_tenant_context(db, organization_id: int) -> None:
    db.info["organization_id"] = organization_id
    db.execute(
        text("SELECT set_config('app.current_organization_id', :organization_id, false)"),
        {"organization_id": str(organization_id)},
    )
