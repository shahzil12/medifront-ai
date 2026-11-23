from sqlalchemy import Column, Integer, String, Time, DateTime, Text, ForeignKey, UniqueConstraint
from app.core.database import Base

class DoctorWorkingHours(Base):
    __tablename__ = "doctor_working_hours"
    hours_id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    weekday = Column(Integer, nullable=False)  # 0 = Monday ... 6 = Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    slot_minutes = Column(Integer, default=30)

class DoctorBlockedTime(Base):
    __tablename__ = "doctor_blocked_times"
    block_id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)

class Appointment(Base):
    __tablename__ = "appointments"
    appointment_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"), nullable=False)
    slot_start = Column(DateTime, nullable=False)
    slot_end = Column(DateTime, nullable=False)
    channel = Column(String(20), default="Web")  # Web | Phone
    status = Column(String(50), default="Confirmed")  # Confirmed, Checked-In, In Consultation, Completed, Cancelled, No-Show

    __table_args__ = (
        UniqueConstraint("doctor_id", "slot_start", name="uq_doctor_slot_start"),
    )