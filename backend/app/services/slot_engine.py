from datetime import datetime, date, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.scheduling import DoctorWorkingHours, DoctorBlockedTime, Appointment
from app.services.audit_service import log_action

def compute_available_slots(db: Session, doctor_id: int, target_date: date) -> list[dict]:
    weekday = target_date.weekday()  # Monday=0, Sunday=6
    hours_list = db.query(DoctorWorkingHours).filter(
        DoctorWorkingHours.doctor_id == doctor_id,
        DoctorWorkingHours.weekday == weekday
    ).all()

    if not hours_list:
        return []

    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date, datetime.max.time())

    # Us din ke blocked times aur active bookings fetch karein
    blocked = db.query(DoctorBlockedTime).filter(
        DoctorBlockedTime.doctor_id == doctor_id,
        DoctorBlockedTime.start_at <= day_end,
        DoctorBlockedTime.end_at >= day_start
    ).all()

    booked = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.slot_start >= day_start,
        Appointment.slot_start <= day_end,
        Appointment.status.in_(["Pending", "Confirmed", "Checked-In", "In Consultation"])
    ).all()

    booked_starts = {appt.slot_start for appt in booked}
    available_slots = []

    for wh in hours_list:
        current_start = datetime.combine(target_date, wh.start_time)
        shift_end = datetime.combine(target_date, wh.end_time)
        delta = timedelta(minutes=wh.slot_minutes)

        while current_start + delta <= shift_end:
            current_end = current_start + delta

            # Check 1: Kya yeh slot blocked time se overlap karta hai?
            is_blocked = any(
                b.start_at < current_end and b.end_at > current_start for b in blocked
            )

            # Check 2: Kya yeh slot pehle se booked hai?
            is_booked = current_start in booked_starts

            if not is_blocked and not is_booked:
                available_slots.append({
                    "slot_start": current_start.isoformat(),
                    "slot_end": current_end.isoformat(),
                    "duration_minutes": wh.slot_minutes
                })

            current_start = current_end

    return available_slots

def book_appointment_with_lock(
    db: Session, patient_id: int, user_id: int, doctor_id: int, slot_start: datetime, channel: str = "Web"
) -> Appointment:
    # 1. Working hours verify karein aur slot_end calculate karein
    weekday = slot_start.weekday()
    wh = db.query(DoctorWorkingHours).filter(
        DoctorWorkingHours.doctor_id == doctor_id,
        DoctorWorkingHours.weekday == weekday,
        DoctorWorkingHours.start_time <= slot_start.time(),
        DoctorWorkingHours.end_time > slot_start.time()
    ).first()

    if not wh:
        raise HTTPException(status_code=400, detail="Requested slot is outside doctor's working hours")

    slot_end = slot_start + timedelta(minutes=wh.slot_minutes)

    # 2. Blocked time check karein
    blocked = db.query(DoctorBlockedTime).filter(
        DoctorBlockedTime.doctor_id == doctor_id,
        DoctorBlockedTime.start_at < slot_end,
        DoctorBlockedTime.end_at > slot_start
    ).first()
    if blocked:
        raise HTTPException(status_code=400, detail="Doctor is unavailable (blocked time)")

    # 3. Row-Level Lock (SELECT ... FOR UPDATE) + Unique Constraint Protection (SRDS Sec 5.6.1)
    try:
        existing = db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.slot_start == slot_start,
            Appointment.status.in_(["Pending", "Confirmed", "Checked-In", "In Consultation"])
        ).with_for_update().first()

        if existing:
            raise HTTPException(status_code=409, detail="Slot already booked by another user")

        new_appt = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            slot_start=slot_start,
            slot_end=slot_end,
            channel=channel,
            status="Confirmed"
        )
        db.add(new_appt)
        db.commit()
        db.refresh(new_appt)

        log_action(db, user_id, "BOOK_APPOINTMENT", "appointments", new_appt.appointment_id)
        return new_appt

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrent booking conflict detected. Slot taken.")