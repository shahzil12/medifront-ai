from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User, Patient
from app.models.ehr import MedicalProfile
from app.schemas.auth import PatientRegisterRequest, LoginRequest, TokenResponse
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_patient(payload: PatientRegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    new_user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role="patient",
        status="Active",
        email_verified=True
    )
    db.add(new_user)
    db.flush()

    new_patient = Patient(
        user_id=new_user.user_id,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender
    )
    db.add(new_patient)
    db.flush()

    med_profile = MedicalProfile(patient_id=new_patient.patient_id)
    db.add(med_profile)
    db.commit()

    log_action(db, new_user.user_id, "REGISTER_PATIENT", "users", new_user.user_id)
    return {"message": "Patient registered successfully", "user_id": new_user.user_id}

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.status != "Active":
        raise HTTPException(status_code=403, detail=f"Account is {user.status}")

    token = create_access_token({"user_id": user.user_id, "role": user.role, "email": user.email})
    log_action(db, user.user_id, "LOGIN", "users", user.user_id)

    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.user_id,
        full_name=user.full_name
    )