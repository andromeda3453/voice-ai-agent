"""Seed script to populate initial patient records for testing and demonstration."""
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, init_db
from app import crud
from app.schemas import PatientCreate

SAMPLE_PATIENTS = [
    PatientCreate(
        first_name="Jane",
        last_name="Doe",
        date_of_birth="1988-04-15",
        sex="Female",
        phone_number="+14155552671",
        email="jane.doe@example.com",
        address_line_1="123 Market Street",
        address_line_2="Apt 4B",
        city="San Francisco",
        state="CA",
        zip_code="94103",
        insurance_provider="Blue Cross Blue Shield",
        insurance_member_id="BC12345678",
        preferred_language="English",
        emergency_contact_name="John Doe",
        emergency_contact_phone="+14155559988",
    ),
    PatientCreate(
        first_name="Carlos",
        last_name="Rodriguez",
        date_of_birth="1975-11-22",
        sex="Male",
        phone_number="+13125558900",
        email="carlos.rodriguez@example.com",
        address_line_1="742 Michigan Ave",
        city="Chicago",
        state="IL",
        zip_code="60611",
        preferred_language="Spanish",
        emergency_contact_name="Maria Rodriguez",
        emergency_contact_phone="+13125558901",
    ),
    PatientCreate(
        first_name="Sarah",
        last_name="Chen",
        date_of_birth="1995-08-30",
        sex="Female",
        phone_number="+12065551234",
        email="sarah.chen@example.com",
        address_line_1="456 Pike Street",
        city="Seattle",
        state="WA",
        zip_code="98101",
        insurance_provider="Kaiser Permanente",
        insurance_member_id="KP98765432",
        preferred_language="English",
    ),
]


def seed():
    print("Initializing database tables...")
    init_db()
    db = SessionLocal()
    try:
        print("Seeding sample patients...")
        for p in SAMPLE_PATIENTS:
            existing = crud.get_patients(db, phone_number=p.phone_number)
            if not existing:
                created = crud.create_patient(db, p)
                print(f"Created: {created.first_name} {created.last_name} ({created.patient_id}) - {created.phone_number}")
            else:
                print(f"Skipped (already exists): {p.first_name} {p.last_name} ({p.phone_number})")
        print("Database seeding completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
