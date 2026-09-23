"""Database CRUD operations for Patients and Call Audits."""
import json
import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_

from app.models import Patient, CallLog, get_utc_now
from app.schemas import PatientCreate, PatientUpdate

logger = logging.getLogger(__name__)


def get_patient_by_id(db: Session, patient_id: str, include_deleted: bool = False) -> Optional[Patient]:
    """Retrieve a single patient by their UUID."""
    query = select(Patient).where(Patient.patient_id == patient_id)
    if not include_deleted:
        query = query.where(Patient.deleted_at.is_(None))
    return db.execute(query).scalars().first()


def get_patients(
    db: Session,
    last_name: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    phone_number: Optional[str] = None,
    include_deleted: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> List[Patient]:
    """List patients with optional filtering by last name, DOB, or phone number."""
    query = select(Patient)
    if not include_deleted:
        query = query.where(Patient.deleted_at.is_(None))
    
    if last_name:
        query = query.where(Patient.last_name.ilike(f"%{last_name.strip()}%"))
    if date_of_birth:
        query = query.where(Patient.date_of_birth == date_of_birth.strip())
    if phone_number:
        # Match normalized phone
        clean_p = "".join(c for c in phone_number if c.isdigit() or c == "+")
        query = query.where(Patient.phone_number.like(f"%{clean_p}%"))

    query = query.order_by(Patient.created_at.desc()).offset(offset).limit(limit)
    return list(db.execute(query).scalars().all())


def create_patient(db: Session, patient_in: PatientCreate) -> Patient:
    """Create a new patient record in the database."""
    patient_data = patient_in.model_dump()
    db_patient = Patient(**patient_data)
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    logger.info(f"Registered patient {db_patient.patient_id} ({db_patient.first_name} {db_patient.last_name})")
    return db_patient


def update_patient(db: Session, patient_id: str, patient_update: PatientUpdate) -> Optional[Patient]:
    """Update an existing patient record (supports partial updates)."""
    db_patient = get_patient_by_id(db, patient_id=patient_id)
    if not db_patient:
        return None

    update_data = patient_update.model_dump(exclude_unset=True)
    if not update_data:
        return db_patient

    for field, value in update_data.items():
        setattr(db_patient, field, value)

    db_patient.updated_at = get_utc_now()
    db.commit()
    db.refresh(db_patient)
    logger.info(f"Updated patient {patient_id}")
    return db_patient


def soft_delete_patient(db: Session, patient_id: str) -> Optional[Patient]:
    """Perform a soft delete on a patient by setting deleted_at timestamp."""
    db_patient = get_patient_by_id(db, patient_id=patient_id)
    if not db_patient:
        return None

    db_patient.deleted_at = get_utc_now()
    db.commit()
    db.refresh(db_patient)
    logger.info(f"Soft-deleted patient {patient_id}")
    return db_patient


def log_call_action(
    db: Session,
    action_type: str,
    caller_phone: Optional[str] = None,
    patient_id: Optional[str] = None,
    payload: Optional[dict] = None,
    status: str = "SUCCESS",
) -> CallLog:
    """Log an audit entry for inbound call/tool actions."""
    try:
        log_entry = CallLog(
            caller_phone=caller_phone,
            patient_id=patient_id,
            action_type=action_type,
            payload=json.dumps(payload) if payload else None,
            status=status,
        )
        db.add(log_entry)
        db.commit()
        return log_entry
    except Exception as e:
        logger.error(f"Failed to write call log: {e}")
        db.rollback()
