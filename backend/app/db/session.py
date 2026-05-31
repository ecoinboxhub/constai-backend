from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url, 
    pool_pre_ping=True, 
    pool_size=10, 
    max_overflow=20,
    future=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables and seeding initial data.
    """
    from sqlalchemy import inspect
    
    from app.db.models import core  # noqa: F401
    
    Base.metadata.create_all(bind=engine)
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Database initialized. Tables found: {', '.join(tables)}")

    db = SessionLocal()
    try:
        if db.query(core.Company).count() == 0:
            print("Seeding default company...")
            company = core.Company(name="ConstAI Default", industry="Construction", country="Nigeria")
            db.add(company)
            db.commit()
            db.refresh(company)
            default_company_id = company.id
        else:
            default_company_id = db.query(core.Company).first().id

        if db.query(core.Material).count() == 0:
            print("Seeding initial material data...")
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
            print("Seeding complete.")
        
        # Only seed projects if none exist (idempotent seeding)
        if db.query(core.Project).count() == 0:
            print("Seeding initial project data...")
            from app.db.seeds import seed_erp_data
            seed_erp_data(company_id=default_company_id)
            print("Project seeding complete.")
    finally:
        db.close()
