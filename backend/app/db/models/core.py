from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class Company(Base, TimestampMixin):
    """Tenant/company record — must be defined before any table that FK-references it."""
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    subscription_tier: Mapped[str] = mapped_column(String(50), default="free")

    # back-references
    users: Mapped[list["User"]] = relationship("User", back_populates="company", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="company", cascade="all, delete-orphan")
    equipment: Mapped[list["Equipment"]] = relationship("Equipment", back_populates="company", cascade="all, delete-orphan")
    safety_findings: Mapped[list["SafetyFinding"]] = relationship("SafetyFinding", back_populates="company", cascade="all, delete-orphan")
    workforce: Mapped[list["Workforce"]] = relationship("Workforce", back_populates="company", cascade="all, delete-orphan")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)

    company: Mapped["Company | None"] = relationship("Company", back_populates="users", foreign_keys=[company_id])


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    contractor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    lga: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    project_type: Mapped[str] = mapped_column(String(120), index=True)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    expected_end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    project_status: Mapped[str] = mapped_column(String(50), default="active")
    budget_allocated: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_spent: Mapped[float | None] = mapped_column(Float, nullable=True)
    workforce_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    equipment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    material_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    completion_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_delay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safety_incidents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inspection_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    task_completion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    daily_progress_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    delay_status: Mapped[str] = mapped_column(String(50), default="on_time")
    risk_level: Mapped[str] = mapped_column(String(20), default="medium")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)

    company: Mapped["Company | None"] = relationship("Company", back_populates="projects", foreign_keys=[company_id])
    workforce_assignments: Mapped[list["Workforce"]] = relationship("Workforce", back_populates="project")

class Workforce(Base, TimestampMixin):
    __tablename__ = "workforce"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(120), index=True)
    skills: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="workforce", foreign_keys=[company_id])
    project: Mapped["Project | None"] = relationship("Project", back_populates="workforce_assignments", foreign_keys=[project_id])


class ProjectDocument(Base, TimestampMixin):
    __tablename__ = "project_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    company: Mapped["Company | None"] = relationship("Company", foreign_keys=[company_id])


class DelayPrediction(Base):
    __tablename__ = "delay_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    features_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    delay_risk: Mapped[float] = mapped_column(Float)
    will_delay: Mapped[bool]
    model_version: Mapped[str] = mapped_column(String(100), default="v0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    company: Mapped["Company | None"] = relationship("Company", foreign_keys=[company_id])


class SupplierQuote(Base):
    __tablename__ = "supplier_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier: Mapped[str] = mapped_column(String(120), index=True)
    material: Mapped[str] = mapped_column(String(120), index=True)
    location: Mapped[str] = mapped_column(String(120), index=True)
    price_ngn: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(80), default="unit")
    reliability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_price_ngn: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class CostEstimate(Base):
    __tablename__ = "cost_estimates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    estimate_ngn: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(100), default="v0")
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    company: Mapped["Company | None"] = relationship("Company", foreign_keys=[company_id])


class Equipment(Base, TimestampMixin):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    equipment_type: Mapped[str] = mapped_column(String(120), index=True)
    serial_number: Mapped[str] = mapped_column(String(120), unique=True)
    purchase_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    last_maintenance_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    runtime_hours: Mapped[float] = mapped_column(Float, default=0.0)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)

    company: Mapped["Company | None"] = relationship("Company", back_populates="equipment", foreign_keys=[company_id])


class MaintenancePrediction(Base):
    __tablename__ = "maintenance_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipment.id"), nullable=True)
    equipment_type: Mapped[str] = mapped_column(String(120), index=True)
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    failure_risk: Mapped[float] = mapped_column(Float)
    due_days: Mapped[int] = mapped_column(Integer)
    model_version: Mapped[str] = mapped_column(String(100), default="v0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class WeatherLog(Base):
    __tablename__ = "weather_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    temperature_c: Mapped[float] = mapped_column(Float)
    rainfall_mm: Mapped[float] = mapped_column(Float)
    wind_speed_kmh: Mapped[float] = mapped_column(Float)
    humidity_pct: Mapped[float] = mapped_column(Float)
    condition: Mapped[str] = mapped_column(String(120))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SafetyFinding(Base):
    __tablename__ = "safety_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    log_text: Mapped[str] = mapped_column(Text)
    findings_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    overall_risk_level: Mapped[str] = mapped_column(String(20), default="low")
    model_version: Mapped[str] = mapped_column(String(100), default="v0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)

    company: Mapped["Company | None"] = relationship("Company", back_populates="safety_findings", foreign_keys=[company_id])


class Material(Base, TimestampMixin):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), default="unit")


class PricePoint(Base):
    __tablename__ = "price_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    source_name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    endpoint: Mapped[str] = mapped_column(String(255), index=True)
    method: Mapped[str] = mapped_column(String(10))
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_status: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class DeviceToken(Base, TimestampMixin):
    __tablename__ = "device_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(50))


class OTPVerification(Base, TimestampMixin):
    __tablename__ = "otp_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(50), index=True)
    code: Mapped[str] = mapped_column(String(10))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_verified: Mapped[bool] = mapped_column(default=False)


class PasswordResetToken(Base, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_used: Mapped[bool] = mapped_column(default=False)
