"""Pydantic schemas and response envelopes for Patient API and Vapi integration."""
import re
from datetime import datetime, date
from typing import Optional, List, Generic, TypeVar, Any, Dict, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum

T = TypeVar("T")


class SexEnum(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class StandardResponse(BaseModel, Generic[T]):
    """Standardized API response envelope."""
    data: Optional[T] = None
    error: Optional[str] = None


class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100, description="Patient's first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Patient's last name")
    date_of_birth: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    sex: str = Field(..., description="Sex/Gender (Male, Female, Other, Unknown)")
    phone_number: str = Field(..., min_length=7, max_length=30, description="Contact phone number")
    email: Optional[str] = Field(None, max_length=255, description="Email address")
    address_line_1: str = Field(..., min_length=1, max_length=255, description="Primary street address")
    address_line_2: Optional[str] = Field(None, max_length=255, description="Apartment, suite, unit, etc.")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    state: str = Field(..., min_length=2, max_length=50, description="State (e.g. CA, NY, California)")
    zip_code: str = Field(..., min_length=3, max_length=20, description="Postal / ZIP code")
    insurance_provider: Optional[str] = Field(None, max_length=100, description="Insurance company name")
    insurance_member_id: Optional[str] = Field(None, max_length=100, description="Insurance member/policy ID")
    preferred_language: Optional[str] = Field("English", max_length=50, description="Preferred language")
    emergency_contact_name: Optional[str] = Field(None, max_length=100, description="Emergency contact full name")
    emergency_contact_phone: Optional[str] = Field(None, max_length=30, description="Emergency contact phone number")

    @field_validator("phone_number", "emergency_contact_phone", mode="before")
    @classmethod
    def clean_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        # Strip extraneous conversational characters if any, keep digits and leading +
        cleaned = re.sub(r"[^\d+]", "", str(v))
        if len(cleaned) < 7:
            raise ValueError(f"Phone number '{v}' is invalid (too short).")
        return cleaned

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_dob(cls, v: Any) -> str:
        if isinstance(v, (date, datetime)):
            return v.strftime("%Y-%m-%d")
        v_str = str(v).strip()
        # Match YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", v_str):
            try:
                datetime.strptime(v_str, "%Y-%m-%d")
                return v_str
            except ValueError:
                raise ValueError(f"Invalid date value: {v_str}")
        # Match MM/DD/YYYY or MM-DD-YYYY conversational input
        m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", v_str)
        if m:
            month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                dt = datetime(year, month, day)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date value: {v_str}")
        raise ValueError("date_of_birth must be formatted as YYYY-MM-DD or MM/DD/YYYY")

    @field_validator("sex", mode="before")
    @classmethod
    def normalize_sex(cls, v: str) -> str:
        v_clean = str(v).strip().capitalize()
        mapping = {
            "M": "Male",
            "Male": "Male",
            "Man": "Male",
            "F": "Female",
            "Female": "Female",
            "Woman": "Female",
            "Other": "Other",
            "Non-binary": "Other",
            "Unknown": "Unknown",
            "Undisclosed": "Unknown"
        }
        if v_clean in mapping:
            return mapping[v_clean]
        return v_clean


class PatientCreate(PatientBase):
    """Schema for registering a new patient."""
    pass


class PatientUpdate(BaseModel):
    """Schema for updating an existing patient record (all fields optional)."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[str] = None
    sex: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    @field_validator("phone_number", "emergency_contact_phone", mode="before")
    @classmethod
    def clean_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        cleaned = re.sub(r"[^\d+]", "", str(v))
        if len(cleaned) < 7:
            raise ValueError(f"Phone number '{v}' is invalid (too short).")
        return cleaned

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_dob(cls, v: Any) -> Optional[str]:
        if not v:
            return v
        if isinstance(v, (date, datetime)):
            return v.strftime("%Y-%m-%d")
        v_str = str(v).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", v_str):
            datetime.strptime(v_str, "%Y-%m-%d")
            return v_str
        m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", v_str)
        if m:
            month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            dt = datetime(year, month, day)
            return dt.strftime("%Y-%m-%d")
        raise ValueError("date_of_birth must be formatted as YYYY-MM-DD or MM/DD/YYYY")


class PatientResponse(PatientBase):
    """Schema for returning patient records."""
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


# Vapi Integration Schemas
class VapiFunctionCall(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class VapiToolCall(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = "function"
    function: Optional[VapiFunctionCall] = None


class VapiMessagePayload(BaseModel):
    type: Optional[str] = None  # "tool-calls", "function-call", "status-update", etc.
    toolCalls: Optional[List[VapiToolCall]] = None
    toolCallList: Optional[List[VapiToolCall]] = None
    functionCall: Optional[VapiFunctionCall] = None
    call: Optional[Dict[str, Any]] = None


class VapiWebhookRequest(BaseModel):
    message: Optional[VapiMessagePayload] = None
    # Support direct tool invocation payload
    name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    toolCallId: Optional[str] = None


class VapiToolResult(BaseModel):
    toolCallId: Optional[str] = None
    result: Any
