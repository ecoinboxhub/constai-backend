import logging
from datetime import UTC, datetime
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.core import Company, Project, User

logger = logging.getLogger(__name__)

COMPANIES_SEED = [
    {"name": "BuildSmart Nigeria Ltd", "industry": "Construction", "country": "Nigeria"},
    {"name": "Lagos Infra group", "industry": "Infrastructure", "country": "Nigeria"},
    {"name": "Abuja Urban Developers", "industry": "Real Estate", "country": "Nigeria"},
    {"name": "Enugu Construction Hub", "industry": "Construction", "country": "Nigeria"},
    {"name": "Rivers Maritime Builders", "industry": "Maritime", "country": "Nigeria"},
]

DEFAULT_ACCOUNTS = [
    {"name": "Invoice Sales", "type": "income"},
    {"name": "Materials Purchase", "type": "expense"},
    {"name": "Labor Expense", "type": "expense"},
]


PROJECTS_SEED = [
    {
        "name": "Eko Atlantic Phase 2", 
        "location": "Victoria Island, Lagos", 
        "state": "Lagos",
        "budget_allocated": 1500000000.0, 
        "budget_spent": 450000000.0,
        "contractor_name": "BuildSmart Nigeria", 
        "project_type": "Infrastructure", 
        "workforce_count": 120, 
        "completion_percentage": 30.0,
        "weather_delay_days": 2,
        "delay_status": "on_time",
        "risk_level": "low",
        "task_completion_rate": 0.92,
        "daily_progress_rate": 0.45
    },
    {
        "name": "Abuja Tech Hub", 
        "location": "Central Business District, Abuja", 
        "state": "Abuja",
        "budget_allocated": 850000000.0, 
        "budget_spent": 780000000.0,
        "contractor_name": "Abuja Developers", 
        "project_type": "Commercial", 
        "workforce_count": 85, 
        "completion_percentage": 85.0,
        "weather_delay_days": 0,
        "delay_status": "delayed",
        "risk_level": "high",
        "task_completion_rate": 0.65,
        "daily_progress_rate": 0.20
    },
    {
        "name": "Port Harcourt Bridge", 
        "location": "Trans Amadi, Port Harcourt", 
        "state": "Rivers",
        "budget_allocated": 420000000.0, 
        "budget_spent": 120000000.0,
        "contractor_name": "Rivers Builders", 
        "project_type": "Bridge", 
        "workforce_count": 45, 
        "completion_percentage": 25.0,
        "weather_delay_days": 5,
        "delay_status": "on_time",
        "risk_level": "medium",
        "task_completion_rate": 0.80,
        "daily_progress_rate": 0.35
    },
    {
        "name": "Lekki Smart City", 
        "location": "Lekki Phase 1, Lagos", 
        "state": "Lagos",
        "budget_allocated": 2100000000.0, 
        "budget_spent": 1800000000.0,
        "contractor_name": "Lagos Infra", 
        "project_type": "Residential", 
        "workforce_count": 200, 
        "completion_percentage": 75.0,
        "weather_delay_days": 1,
        "delay_status": "delayed",
        "risk_level": "high",
        "task_completion_rate": 0.55,
        "daily_progress_rate": 0.15
    },
]

def seed_erp_data(company_id: int = None):
    session: Session = SessionLocal()
    try:
        # 1. Seed Companies
        companies = []
        if not company_id:
            for c_data in COMPANIES_SEED:
                company = session.query(Company).filter_by(name=c_data["name"]).first()
                if not company:
                    company = Company(**c_data)
                    session.add(company)
                    session.commit()
                    session.refresh(company)
                    logger.info(f"Seeded company: {company.name}")
                companies.append(company)
        else:
            companies = [session.query(Company).get(company_id)]

        # 3. Seed Projects and assign to companies
        for idx, p_data in enumerate(PROJECTS_SEED):
            project = session.query(Project).filter_by(name=p_data["name"]).first()
            if not project:
                target_company = companies[idx % len(companies)]
                project = Project(
                    **p_data,
                    company_id=target_company.id,
                    project_status="active",
                    start_date=datetime.now(UTC)
                )
                session.add(project)
        session.commit()
        logger.info("Seeded and assigned projects.")

    except Exception as e:
        session.rollback()
        logger.error(f"ERP seeding failed: {e}")
    finally:
        session.close()


def seed_materials():
    """
    Materials are now seeded automatically during init_db() in app/db/session.py
    for the local storage node.
    """
    pass


if __name__ == "__main__":
    seed_erp_data()
