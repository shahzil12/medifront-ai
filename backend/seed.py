from datetime import datetime, date, time, timedelta
from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models.user import User, Specialty, Doctor, Patient
from app.models.scheduling import DoctorWorkingHours, Appointment
from app.models.ehr import MedicalProfile, Vitals, Diagnosis, Prescription

Base.metadata.create_all(bind=engine)
db = SessionLocal()

def seed():
    if db.query(User).filter(User.email == "dr.sara@medifront.ai").first():
        print("Seed data already exists!")
        return

    # 1. Specialties
    cardio = Specialty(name="Cardiology", intake_protocol="Check BP and chest pain history.")
    derma = Specialty(name="Dermatology", intake_protocol="Check skin allergies and duration.")
    db.add_all([cardio, derma])
    db.flush()

    # 2. Verified Doctors
    u_doc1 = User(email="dr.sara@medifront.ai", password_hash=hash_password("doctor123"), full_name="Dr. Sara Ahmed", phone="0300-1112233", role="doctor", status="Active")
    u_doc2 = User(email="dr.ali@medifront.ai", password_hash=hash_password("doctor123"), full_name="Dr. Ali Raza", phone="0300-4445566", role="doctor", status="Active")
    db.add_all([u_doc1, u_doc2])
    db.flush()

    doc1 = Doctor(user_id=u_doc1.user_id, specialty_id=cardio.specialty_id, license_no="PMC-78412", qualification="MBBS, FCPS Cardiology", verified=True)
    doc2 = Doctor(user_id=u_doc2.user_id, specialty_id=derma.specialty_id, license_no="PMC-99231", qualification="MBBS, MD Dermatology", verified=True)
    db.add_all([doc1, doc2])
    db.flush()

    # 3. Working Hours (Monday=0 to Saturday=5, 09:00 to 14:00, 30 min slots)
    for day in range(6):
        db.add(DoctorWorkingHours(doctor_id=doc1.doctor_id, weekday=day, start_time=time(9, 0), end_time=time(14, 0), slot_minutes=30))
        db.add(DoctorWorkingHours(doctor_id=doc2.doctor_id, weekday=day, start_time=time(10, 0), end_time=time(15, 0), slot_minutes=30))

    # 4. Patients
    u_pat1 = User(email="usman@patient.com", password_hash=hash_password("patient123"), full_name="Usman Tariq", phone="0312-9876543", role="patient", status="Active")
    u_pat2 = User(email="ayesha@patient.com", password_hash=hash_password("patient123"), full_name="Ayesha Khan", phone="0321-5556677", role="patient", status="Active")
    db.add_all([u_pat1, u_pat2])
    db.flush()

    pat1 = Patient(user_id=u_pat1.user_id, date_of_birth=date(1998, 5, 14), gender="Male")
    pat2 = Patient(user_id=u_pat2.user_id, date_of_birth=date(2001, 9, 22), gender="Female")
    db.add_all([pat1, pat2])
    db.flush()

    prof1 = MedicalProfile(patient_id=pat1.patient_id, blood_group="B+", allergies="Penicillin")
    prof2 = MedicalProfile(patient_id=pat2.patient_id, blood_group="O+", allergies="None")
    db.add_all([prof1, prof2])
    db.flush()

    # 5. Today's Appointments for Dr. Sara (for live Command Center demo)
    today = date.today()
    appt1 = Appointment(
        patient_id=pat1.patient_id, doctor_id=doc1.doctor_id,
        slot_start=datetime.combine(today, time(9, 30)),
        slot_end=datetime.combine(today, time(10, 0)),
        channel="Web", status="Checked-In"
    )
    appt2 = Appointment(
        patient_id=pat2.patient_id, doctor_id=doc1.doctor_id,
        slot_start=datetime.combine(today, time(10, 0)),
        slot_end=datetime.combine(today, time(10, 30)),
        channel="Phone", status="Confirmed"
    )
    db.add_all([appt1, appt2])
    db.flush()

    # 6. Historical EHR entry for Usman so history view isn't empty
    db.add(Vitals(profile_id=prof1.profile_id, appointment_id=appt1.appointment_id, bp_sys=128, bp_dia=84, heart_rate=78, temp=98.6, weight=74.5, spo2=98))
    db.add(Diagnosis(profile_id=prof1.profile_id, doctor_id=doc1.doctor_id, appointment_id=appt1.appointment_id, icd_code="I10", description="Mild Essential Hypertension - Lifestyle & monitoring advised"))
    db.add(Prescription(profile_id=prof1.profile_id, doctor_id=doc1.doctor_id, appointment_id=appt1.appointment_id, medication="Amlodipine", dosage="5mg", frequency="Once daily", duration="30 days", instructions="Take in the morning after breakfast"))

    db.commit()
    print("Database seeded successfully!")
    print("Doctor Login: dr.sara@medifront.ai / doctor123")
    print("Patient Login: usman@patient.com / patient123")

if __name__ == "__main__":
    seed()