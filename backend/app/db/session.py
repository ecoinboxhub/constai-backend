from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Generator

from app.core.config import settings

# Global state for lazy initialization
_engine = None
_SessionLocal = None
Base = declarative_base()


class LazySessionLocal:
    """Lazy proxy to SessionLocal that calls get_session_factory() when used."""
    
    def __call__(self, *args, **kwargs):
        SessionLocal = get_session_factory()
        return SessionLocal(*args, **kwargs)


def init_db_engine() -> None:
    """Initialize database engine and SessionLocal. Called once at FastAPI startup."""
    global _engine, _SessionLocal
    if _engine is not None:
        return  # Already initialized
    
    _engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        future=True
    )
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_engine():
    """Get the database engine. Ensures it's initialized."""
    global _engine
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_db_engine() at startup.")
    return _engine


def get_session_factory():
    """Get the session factory. Ensures engine is initialized."""
    global _SessionLocal
    if _SessionLocal is None:
        raise RuntimeError("SessionLocal not initialized. Call init_db_engine() at startup.")
    return _SessionLocal


# Create lazy proxies for backward compatibility
SessionLocal = LazySessionLocal()
engine = None  # Will be accessed via __getattr__


def get_db() -> Generator:
    """FastAPI dependency for database sessions."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables and seeding initial data.
    Must be called after init_db_engine() during startup (lazy loaded on first request).
    
    Runs with timeouts to prevent blocking on slow or offline databases.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from sqlalchemy import inspect, event, pool
        from sqlalchemy.exc import OperationalError
        from app.db.models import core  # noqa: F401
        
        engine = get_engine()
        
        # Set connection timeout to 5 seconds
        @event.listens_for(pool.Pool, "connect")
        def receive_connect(dbapi_conn, connection_record):
            if hasattr(dbapi_conn, 'timeout'):
                dbapi_conn.timeout = 5.0
        
        try:
            # Try to create tables with timeout
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
            # Seed default data idempotently
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
            
            # Only seed projects if none exist
            if db.query(core.Project).count() == 0:
                logger.info("Seeding initial project data...")
                from app.db.seeds import seed_erp_data
                seed_erp_data(company_id=default_company_id)
                logger.info("Project seeding complete.")
        finally:
            db.close()
    except Exception as exc:
        logger.warning(f"Database initialization error: {exc}. App will continue without persistence.")


# Provide backward-compatible module-level attributes for old-style imports
def __getattr__(name):
    """Allow lazy access to SessionLocal and engine for backward compatibility."""
    if name == "SessionLocal":
        return SessionLocal  # Return the LazySessionLocal proxy
    elif name == "engine":
        return get_engine()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
