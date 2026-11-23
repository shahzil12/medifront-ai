from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    role = Column(String(50), nullable=False)  # patient | doctor | medical_staff | administrator
    status = Column(String(50), default="Active")  # Active | Pending Verification | Locked | Deactivated
    email_verified = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Specialty(Base):
    __tablename__ = "specialties"
    specialty_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False)
    intake_protocol = Column(Text, nullable=True)

class Doctor(Base):
    __tablename__ = "doctors"
    doctor_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=True, nullable=False)
    specialty_id = Column(Integer, ForeignKey("specialties.specialty_id"), nullable=False)
    license_no = Column(String(100), unique=True, nullable=False)
    qualification = Column(String(255), nullable=False)
    verified = Column(Boolean, default=True)

class Patient(Base):
    __tablename__ = "patients"
    patient_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=True, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity = Column(String(100), nullable=False)
    entity_id = Column(Integer, nullable=True)
    logged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))