"""SQLAlchemy database models for patient registration."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Boolean, Index
from app.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class Patient(Base):
    """Patient record model."""
    __tablename__ = "patients"

    patient_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False, index=True)
    date_of_birth = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    sex = Column(String(20), nullable=False)  # Male, Female, Other, Unknown
    phone_number = Column(String(30), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    
    # Address
    address_line_1 = Column(String(255), nullable=False)
    address_line_2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    zip_code = Column(String(20), nullable=False)

    # Insurance & Preferences
    insurance_provider = Column(String(100), nullable=True)
    insurance_member_id = Column(String(100), nullable=True)
    preferred_language = Column(String(50), nullable=False, default="English")

    # Emergency Contact
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(30), nullable=True)

    # Metadata & Soft Delete
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("ix_patients_phone_not_deleted", "phone_number", "deleted_at"),
        Index("ix_patients_name_dob", "last_name", "date_of_birth"),
    )


class CallLog(Base):
    """Audit log for incoming voice calls and tool executions."""
    __tablename__ = "call_logs"

    call_id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    caller_phone = Column(String(30), nullable=True)
    patient_id = Column(String(36), nullable=True, index=True)
    action_type = Column(String(50), nullable=False)  # e.g., lookup, register, update
    payload = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="SUCCESS")
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
