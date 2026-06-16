import logging
from datetime import datetime
from typing import Any, Dict
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.core import Project, Workforce, AuditLog, SafetyFinding
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def reconcile_client_item(
    db: Session,
    company_id: int,
    user_id: str,
    table_name: str,
    action: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Reconciles a single synchronization payload item with Aiven PostgreSQL.
    Enforces multi-tenancy by validating and injecting company_id.
    """
    try:
        # Enforce company_id boundary
        payload["company_id"] = company_id

        if table_name == "projects":
            client_uuid = payload.get("client_uuid")
            existing_project = None

            if client_uuid:
                existing_project = db.query(Project).filter(
                    Project.client_uuid == client_uuid,
                    Project.company_id == company_id
                ).first()
            else:
                project_id = payload.get("id")
                if project_id:
                    existing_project = db.query(Project).filter(
                        Project.id == int(project_id),
                        Project.company_id == company_id
                    ).first()

            if action in ("INSERT", "UPDATE"):
                clean_data = {
                    k: v for k, v in payload.items() 
                    if k in Project.__table__.columns.keys() and k not in ("id", "created_at", "updated_at")
                }
                
                if existing_project:
                    for key, val in clean_data.items():
                        setattr(existing_project, key, val)
                    db.flush()
                    db.refresh(existing_project)
                    result = existing_project
                else:
                    new_project = Project(**clean_data)
                    db.add(new_project)
                    db.flush()
                    db.refresh(new_project)
                    result = new_project
                
                return {"id": result.id, "status": "synced"}

            elif action == "DELETE":
                lookup_id = client_uuid or payload.get("id")
                if existing_project:
                    db.delete(existing_project)
                    db.flush()
                    return {"id": lookup_id, "status": "deleted"}
                return {"id": lookup_id, "status": "not_found"}

        elif table_name == "workforce":
            client_uuid = payload.get("client_uuid")
            existing_worker = None

            if client_uuid:
                existing_worker = db.query(Workforce).filter(
                    Workforce.client_uuid == client_uuid,
                    Workforce.company_id == company_id
                ).first()
            else:
                worker_id = payload.get("id")
                if worker_id:
                    existing_worker = db.query(Workforce).filter(
                        Workforce.id == int(worker_id),
                        Workforce.company_id == company_id
                    ).first()

            if action in ("INSERT", "UPDATE"):
                clean_data = {
                    k: v for k, v in payload.items()
                    if k in Workforce.__table__.columns.keys() and k not in ("id", "created_at", "updated_at")
                }
                
                pid = clean_data.get("project_id")
                if pid and str(pid).strip() == "":
                    clean_data["project_id"] = None
                elif pid:
                    clean_data["project_id"] = int(pid)

                if existing_worker:
                    for key, val in clean_data.items():
                        setattr(existing_worker, key, val)
                    db.flush()
                    db.refresh(existing_worker)
                    result = existing_worker
                else:
                    new_worker = Workforce(**clean_data)
                    db.add(new_worker)
                    db.flush()
                    db.refresh(new_worker)
                    result = new_worker
                
                return {"id": result.id, "status": "synced"}

            elif action == "DELETE":
                lookup_id = client_uuid or payload.get("id")
                if existing_worker:
                    db.delete(existing_worker)
                    db.flush()
                    return {"id": lookup_id, "status": "deleted"}
                return {"id": lookup_id, "status": "not_found"}

        elif table_name == "inspections" or table_name == "safety_findings":
            # Map inspections logs to SafetyFinding Postgres entity
            finding_id = payload.get("id")
            
            clean_data = {
                "project_id": int(payload.get("project_id")) if payload.get("project_id") else None,
                "log_text": payload.get("notes") or payload.get("title") or "Offline inspection log",
                "findings_json": payload,
                "overall_risk_level": "medium",
                "company_id": company_id
            }

            new_finding = SafetyFinding(**clean_data)
            db.add(new_finding)
            db.flush()
            db.refresh(new_finding)
            return {"id": new_finding.id, "status": "synced"}

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported offline sync table: {table_name}")

    except Exception as err:
        logger.error(f"Error during single item reconciliation on table {table_name}: {err}")
        raise HTTPException(status_code=400, detail=f"Reconciliation error: {str(err)}")
