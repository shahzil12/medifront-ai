from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, Doctor, Patient
from app.models.scheduling import Appointment
from app.models.ehr import MedicalProfile, Vitals, Diagnosis, Prescription, FollowUp
from app.schemas.ehr import EHREntryCreate
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/v1/ehr", tags=["Electronic Health Records (EHR)"])

# UC-05 & UC-13: Read Patient Complete Medical History (Doctor or Own Patient)
@router.get("/patients/{patient_id}")
def get_patient_ehr(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # FR-EHR-06: Patient sirf apna record dekh sakta hai
    if current_user.role == "patient" and patient.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to another patient's record")

    patient_user = db.query(User).filter(User.user_id == patient.user_id).first()
    profile = db.query(MedicalProfile).filter(MedicalProfile.patient_id == patient_id).first()

    if not profile:
        profile = MedicalProfile(patient_id=patient_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    vitals = db.query(Vitals).filter(Vitals.profile_id == profile.profile_id).order_by(Vitals.recorded_at.desc()).all()
    diagnoses = db.query(Diagnosis).filter(Diagnosis.profile_id == profile.profile_id).order_by(Diagnosis.diagnosis_id.desc()).all()
    prescriptions = db.query(Prescription).filter(Prescription.profile_id == profile.profile_id).order_by(Prescription.prescription_id.desc()).all()
    follow_ups = db.query(FollowUp).filter(FollowUp.profile_id == profile.profile_id).order_by(FollowUp.due_date.desc()).all()

    # FR-EHR-08: Log clinical data read
    log_action(db, current_user.user_id, "READ_EHR", "medical_profiles", profile.profile_id)

    return {
        "patient": {
            "patient_id": patient.patient_id,
            "full_name": patient_user.full_name,
            "gender": patient.gender,
            "date_of_birth": patient.date_of_birth,
            "phone": patient_user.phone
        },
        "medical_profile": {
            "profile_id": profile.profile_id,
            "blood_group": profile.blood_group,
            "allergies": profile.allergies,
            "updated_at": profile.updated_at
        },
        "vitals": vitals,
        "diagnoses": diagnoses,
        "prescriptions": prescriptions,
        "follow_ups": follow_ups
    }

# UC-13 & FR-EHR-01..07: Physician-Authored Clinical Entry
@router.post("/entries")
def create_ehr_entry(
    payload: EHREntryCreate,
    current_user: User = Depends(require_role(["doctor"])),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.user_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    # FR-EHR-06: Verify treating doctor
    appt = db.query(Appointment).filter(
        Appointment.appointment_id == payload.appointment_id,
        Appointment.patient_id == payload.patient_id,
        Appointment.doctor_id == doctor.doctor_id
    ).first()
    if not appt:
        raise HTTPException(status_code=403, detail="Only the treating doctor can add clinical entries for this visit")

    profile = db.query(MedicalProfile).filter(MedicalProfile.patient_id == payload.patient_id).first()
    if not profile:
        profile = MedicalProfile(patient_id=payload.patient_id)
        db.add(profile)
        db.flush()

    # 1. Update Medical Profile (FR-EHR-01)
    if payload.blood_group is not None:
        profile.blood_group = payload.blood_group
    if payload.allergies is not None:
        profile.allergies = payload.allergies
    profile.updated_at = datetime.now(timezone.utc)

    # 2. Record Vitals (FR-EHR-02)
    if any([payload.bp_sys, payload.bp_dia, payload.heart_rate, payload.temp, payload.weight, payload.spo2]):
        vital = Vitals(
            profile_id=profile.profile_id,
            appointment_id=payload.appointment_id,
            bp_sys=payload.bp_sys,
            bp_dia=payload.bp_dia,
            heart_rate=payload.heart_rate,
            temp=payload.temp,
            weight=payload.weight,
            height=payload.height,
            spo2=payload.spo2
        )
        db.add(vital)

    # 3. Record Diagnosis (FR-EHR-03)
    diag = Diagnosis(
        profile_id=profile.profile_id,
        doctor_id=doctor.doctor_id,
        appointment_id=payload.appointment_id,
        icd_code=payload.icd_code,
        description=payload.diagnosis_description
    )
    db.add(diag)

    # 4. Record Prescription (FR-EHR-04)
    if payload.medication:
        rx = Prescription(
            profile_id=profile.profile_id,
            doctor_id=doctor.doctor_id,
            appointment_id=payload.appointment_id,
            medication=payload.medication,
            dosage=payload.dosage or "As directed",
            frequency=payload.frequency or "Daily",
            duration=payload.duration or "5 days",
            instructions=payload.instructions
        )
        db.add(rx)

    # 5. Schedule Follow-up (FR-EHR-05)
    if payload.follow_up_date:
        fu = FollowUp(
            profile_id=profile.profile_id,
            doctor_id=doctor.doctor_id,
            due_date=payload.follow_up_date,
            notes=payload.follow_up_notes
        )
        db.add(fu)

    # Mark appointment Completed (Figure 38 State Machine)
    appt.status = "Completed"
    db.commit()

    # FR-EHR-08: Audit trail
    log_action(db, current_user.user_id, "WRITE_EHR_ENTRY", "medical_profiles", profile.profile_id)
    return {"message": "Clinical record saved successfully and visit marked Completed"}