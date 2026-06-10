from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError
from typing import Generator, Optional

from app.core.config import settings

_engine = None
_SessionLocal = None
Base = declarative_base()


class LazySessionLocal:
    def __call__(self, *args, **kwargs):
        SessionLocal = get_session_factory()
        return SessionLocal(*args, **kwargs)


def init_db_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        return

    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args=connect_args,
        future=True,
    )
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_engine():
    global _engine
    if _engine is None:
        raise RuntimeError("Database engine not initialized.")
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        raise RuntimeError("SessionLocal not initialized.")
    return _SessionLocal


SessionLocal = LazySessionLocal()


def get_db() -> Generator:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import logging
    logger = logging.getLogger(__name__)

    try:
        from sqlalchemy import inspect
        from app.db.models import core

        engine = get_engine()

        @event.listens_for(pool.Pool, "connect")
        def receive_connect(dbapi_conn, connection_record):
            if hasattr(dbapi_conn, 'timeout'):
                dbapi_conn.timeout = 5.0

        try:
            Base.metadata.create_all(bind=engine, checkfirst=True)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            logger.info(f"Database initialized. Tables: {', '.join(tables)}")
        except OperationalError as e:
            logger.warning(f"Database connection failed: {e}. App will continue without persistence.")
            return

        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            if db.query(core.Company).count() == 0:
                logger.info("Seeding default company...")
                company = core.Company(name="ConstAI Default", industry="Construction", country="Nigeria")
                db.add(company)
                db.commit()
                db.refresh(company)
                default_company_id = company.id
            else:
                default_company_id = db.query(core.Company).first().id

            if db.query(core.Material).count() == 0:
                logger.info("Seeding initial material data...")
                materials = [
                    core.Material(name="Cement", category="Building Materials", unit="50kg Bag"),
                    core.Material(name="Steel Rebars", category="Building Materials", unit="Ton"),
                    core.Material(name="Sand", category="Aggregates", unit="Trip"),
                    core.Material(name="Granite", category="Aggregates", unit="Trip"),
                ]
                db.add_all(materials)
                db.commit()

                for m in materials:
                    pp = core.PricePoint(
                        material_id=m.id,
                        source_name="Market Standard",
                        price=12500.0 if m.name == "Cement" else 980000.0 if m.name == "Steel Rebars" else 45000.0,
                        source_url="internal://market-node"
                    )
                    db.add(pp)
                db.commit()
                logger.info("Material seeding complete.")

            if db.query(core.Project).count() == 0:
                logger.info("Seeding initial project data...")
                from app.db.seeds import seed_erp_data
                seed_erp_data(company_id=default_company_id)
                logger.info("Project seeding complete.")
        finally:
            db.close()
    except Exception as exc:
        logger.warning(f"Database initialization error: {exc}. App will continue without persistence.")


def __getattr__(name):
    if name == "SessionLocal":
        return SessionLocal
    elif name == "engine":
        return get_engine()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
