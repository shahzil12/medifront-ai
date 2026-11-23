from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, Doctor, Patient, Specialty
from app.models.scheduling import DoctorWorkingHours, DoctorBlockedTime, Appointment
from app.schemas.scheduling import (
    WorkingHoursCreate, BlockedTimeCreate, AppointmentBookRequest, AppointmentRescheduleRequest
)
from app.services.slot_engine import compute_available_slots, book_appointment_with_lock
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/v1", tags=["Scheduling Engine"])

# UC-04: Verified Doctors List (Search by specialty or name)
@router.get("/doctors")
def list_verified_doctors(specialty: str | None = None, db: Session = Depends(get_db)):
    query = (
        db.query(Doctor, User, Specialty)
        .join(User, Doctor.user_id == User.user_id)
        .join(Specialty, Doctor.specialty_id == Specialty.specialty_id)
        .filter(Doctor.verified == True, User.status == "Active")
    )
    if specialty:
        query = query.filter(Specialty.name.ilike(f"%{specialty}%"))

    results = []
    for doc, usr, spec in query.all():
        results.append({
            "doctor_id": doc.doctor_id,
            "full_name": usr.full_name,
            "specialty": spec.name,
            "qualification": doc.qualification,
            "license_no": doc.license_no
        })
    return results

# UC-11: Doctor Sets Weekly Working Hours
@router.post("/schedule/hours")
def set_working_hours(
    payload: WorkingHoursCreate,
    current_user: User = Depends(require_role(["doctor"])),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.user_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    # Purana same weekday ka schedule replace karein taake clean rahe
    db.query(DoctorWorkingHours).filter(
        DoctorWorkingHours.doctor_id == doctor.doctor_id,
        DoctorWorkingHours.weekday == payload.weekday
    ).delete()

    new_hours = DoctorWorkingHours(
        doctor_id=doctor.doctor_id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
        slot_minutes=payload.slot_minutes
    )
    db.add(new_hours)
    db.commit()
    db.refresh(new_hours)
    return {"message": "Working hours updated", "hours_id": new_hours.hours_id}

# UC-11: Doctor Blocks Personal Time
@router.post("/schedule/block")
def block_time(
    payload: BlockedTimeCreate,
    current_user: User = Depends(require_role(["doctor"])),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.user_id).first()
    block = DoctorBlockedTime(
        doctor_id=doctor.doctor_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        reason=payload.reason
    )
    db.add(block)
    db.commit()
    return {"message": "Time blocked successfully"}

# Get Doctor's Current Schedule
@router.get("/schedule/my")
def get_my_schedule(
    current_user: User = Depends(require_role(["doctor"])),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.user_id).first()
    hours = db.query(DoctorWorkingHours).filter(DoctorWorkingHours.doctor_id == doctor.doctor_id).all()
    blocks = db.query(DoctorBlockedTime).filter(DoctorBlockedTime.doctor_id == doctor.doctor_id).all()
    return {"working_hours": hours, "blocked_times": blocks}

# FR-SCH-03: Compute Available Slots for a Doctor on a Date
@router.get("/doctors/{doctor_id}/slots")
def get_doctor_slots(doctor_id: int, date: date, db: Session = Depends(get_db)):
    slots = compute_available_slots(db, doctor_id, date)
    return {"doctor_id": doctor_id, "date": str(date), "available_slots": slots}

# UC-02: Book Appointment (Web/Phone) with Row Lock
@router.post("/appointments")
def create_appointment(
    payload: AppointmentBookRequest,
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    appt = book_appointment_with_lock(
        db=db,
        patient_id=patient.patient_id,
        user_id=current_user.user_id,
        doctor_id=payload.doctor_id,
        slot_start=payload.slot_start,
        channel=payload.channel
    )
    return {
        "message": "Appointment confirmed",
        "appointment_id": appt.appointment_id,
        "slot_start": appt.slot_start,
        "status": appt.status
    }

# Patient's Appointments List (UC-03)
@router.get("/appointments/my")
def get_my_appointments(
    current_user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.user_id).first()
    appts = (
        db.query(Appointment, User)
        .join(Doctor, Appointment.doctor_id == Doctor.doctor_id)
        .join(User, Doctor.user_id == User.user_id)
        .filter(Appointment.patient_id == patient.patient_id)
        .order_by(Appointment.slot_start.desc())
        .all()
    )
    return [
        {
            "appointment_id": a.appointment_id,
            "doctor_id": a.doctor_id,
            "doctor_name": u.full_name,
            "slot_start": a.slot_start,
            "slot_end": a.slot_end,
            "status": a.status,
            "channel": a.channel
        }
        for a, u in appts
    ]

# UC-03: Cancel Appointment
@router.delete("/appointments/{appointment_id}")
def cancel_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    appt = db.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appt.status = "Cancelled"
    db.commit()
    log_action(db, current_user.user_id, "CANCEL_APPOINTMENT", "appointments", appointment_id)
    return {"message": "Appointment cancelled and slot released"}