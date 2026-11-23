from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey
from app.core.database import Base

class MedicalProfile(Base):
    __tablename__ = "medical_profiles"
    profile_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), unique=True, nullable=False)
    blood_group = Column(String(10), nullable=True)
    allergies = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Vitals(Base):
    __tablename__ = "vitals"
    vital_id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("medical_profiles.profile_id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.appointment_id"), nullable=False)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    bp_sys = Column(Integer, nullable=True)
    bp_dia = Column(Integer, nullable=True)
    heart_rate = Column(Integer, nullable=True)
    temp = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    spo2 = Column(Integer, nullable=True)

class Diagnosis(Base):
    __tablename__ = "diagnoses"
    diagnosis_id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("medical_profiles.profile_id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.appointment_id"), nullable=False)
    icd_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=False)

class Prescription(Base):
    __tablename__ = "prescriptions"
    prescription_id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("medical_profiles.profile_id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.appointment_id"), nullable=False)
    medication = Column(String(255), nullable=False)
    dosage = Column(String(100), nullable=False)
    frequency = Column(String(100), nullable=False)
    duration = Column(String(100), nullable=False)
    instructions = Column(Text, nullable=True)

class FollowUp(Base):
    __tablename__ = "follow_ups"
    followup_id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("medical_profiles.profile_id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    due_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="Scheduled")