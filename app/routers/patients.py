"""FastAPI router for Patient CRUD operations."""
import logging
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud
from app.schemas import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    StandardResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("", response_model=StandardResponse[List[PatientResponse]])
def list_patients(
    last_name: Optional[str] = Query(None, description="Filter by patient last name"),
    date_of_birth: Optional[str] = Query(None, description="Filter by DOB (YYYY-MM-DD)"),
    phone_number: Optional[str] = Query(None, description="Filter by phone number"),
    include_deleted: bool = Query(False, description="Include soft-deleted records"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Offset pagination"),
    db: Session = Depends(get_db),
):
    """List registered patients with optional filtering."""
    try:
        patients = crud.get_patients(
            db=db,
            last_name=last_name,
            date_of_birth=date_of_birth,
            phone_number=phone_number,
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
        )
        return StandardResponse(data=patients, error=None)
    except Exception as e:
        logger.error(f"Error fetching patients: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"data": None, "error": "Internal server error fetching patient records."},
        )


@router.get("/{patient_id}", response_model=StandardResponse[PatientResponse])
def get_patient(
    patient_id: str,
    include_deleted: bool = Query(False, description="Include soft-deleted records"),
    db: Session = Depends(get_db),
):
    """Retrieve a single patient record by their UUID."""
    patient = crud.get_patient_by_id(db=db, patient_id=patient_id, include_deleted=include_deleted)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"data": None, "error": f"Patient with ID '{patient_id}' not found."},
        )
    return StandardResponse(data=patient, error=None)


@router.post("", response_model=StandardResponse[PatientResponse], status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_in: PatientCreate,
    db: Session = Depends(get_db),
):
    """Register a new patient."""
    try:
        new_patient = crud.create_patient(db=db, patient_in=patient_in)
        return StandardResponse(data=new_patient, error=None)
    except Exception as e:
        logger.error(f"Error creating patient: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"data": None, "error": f"Failed to register patient: {str(e)}"},
        )


@router.put("/{patient_id}", response_model=StandardResponse[PatientResponse])
def update_patient(
    patient_id: str,
    patient_update: PatientUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing patient record (supports partial updates)."""
    try:
        updated_patient = crud.update_patient(
            db=db, patient_id=patient_id, patient_update=patient_update
        )
        if not updated_patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"data": None, "error": f"Patient with ID '{patient_id}' not found."},
            )
        return StandardResponse(data=updated_patient, error=None)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating patient {patient_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"data": None, "error": f"Failed to update patient: {str(e)}"},
        )


@router.delete("/{patient_id}", response_model=StandardResponse[dict])
def delete_patient(
    patient_id: str,
    db: Session = Depends(get_db),
):
    """Soft delete a patient record."""
    try:
        deleted = crud.soft_delete_patient(db=db, patient_id=patient_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"data": None, "error": f"Patient with ID '{patient_id}' not found."},
            )
        return StandardResponse(
            data={"patient_id": patient_id, "deleted": True, "deleted_at": deleted.deleted_at.isoformat()},
            error=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting patient {patient_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"data": None, "error": f"Failed to delete patient: {str(e)}"},
        )
