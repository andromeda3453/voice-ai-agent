"""Vapi Webhook & Custom Tool Call handlers for Voice Agent."""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud
from app.schemas import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vapi", tags=["Vapi Voice Integration"])


def execute_tool_call(tool_name: str, args: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Execute internal tool call based on name and parameters."""
    logger.info(f"Executing Vapi tool '{tool_name}' with args: {args}")

    if tool_name in ["check_patient_by_phone", "lookup_patient"]:
        phone = args.get("phone_number")
        if not phone:
            return {"found": False, "message": "No phone number provided."}
        
        matches = crud.get_patients(db=db, phone_number=phone)
        if matches:
            patient = matches[0]
            crud.log_call_action(
                db,
                action_type="vapi_lookup_found",
                caller_phone=phone,
                patient_id=patient.patient_id,
                payload=args,
            )
            return {
                "found": True,
                "patient_id": patient.patient_id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "date_of_birth": patient.date_of_birth,
                "phone_number": patient.phone_number,
                "address_line_1": patient.address_line_1,
                "city": patient.city,
                "state": patient.state,
                "zip_code": patient.zip_code,
                "message": f"Existing record found for {patient.first_name} {patient.last_name}."
            }
        else:
            crud.log_call_action(
                db,
                action_type="vapi_lookup_not_found",
                caller_phone=phone,
                payload=args,
            )
            return {
                "found": False,
                "message": f"No existing registration found for phone number {phone}."
            }

    elif tool_name in ["register_patient", "create_patient"]:
        try:
            # Map parameters into PatientCreate schema
            patient_in = PatientCreate(**args)
            new_patient = crud.create_patient(db=db, patient_in=patient_in)
            crud.log_call_action(
                db,
                action_type="vapi_register_success",
                caller_phone=patient_in.phone_number,
                patient_id=new_patient.patient_id,
                payload=args,
            )
            return {
                "success": True,
                "patient_id": new_patient.patient_id,
                "first_name": new_patient.first_name,
                "last_name": new_patient.last_name,
                "message": f"Patient {new_patient.first_name} {new_patient.last_name} successfully registered with ID {new_patient.patient_id}."
            }
        except Exception as e:
            logger.error(f"Error registering patient via Vapi tool: {e}", exc_info=True)
            db.rollback()
            return {
                "success": False,
                "error": str(e),
                "message": f"Registration failed: {str(e)}"
            }

    elif tool_name in ["update_patient", "update_patient_details"]:
        patient_id = args.pop("patient_id", None)
        if not patient_id:
            # Try finding patient by phone
            phone = args.get("phone_number")
            if phone:
                patients = crud.get_patients(db=db, phone_number=phone)
                if patients:
                    patient_id = patients[0].patient_id

        if not patient_id:
            return {"success": False, "message": "Cannot update without patient_id or registered phone number."}

        try:
            patient_up = PatientUpdate(**args)
            updated = crud.update_patient(db=db, patient_id=patient_id, patient_update=patient_up)
            if updated:
                crud.log_call_action(
                    db,
                    action_type="vapi_update_success",
                    caller_phone=updated.phone_number,
                    patient_id=updated.patient_id,
                    payload=args,
                )
                return {
                    "success": True,
                    "patient_id": updated.patient_id,
                    "message": f"Patient record for {updated.first_name} {updated.last_name} was successfully updated."
                }
            return {"success": False, "message": f"Patient {patient_id} not found."}
        except Exception as e:
            logger.error(f"Error updating patient via Vapi tool: {e}", exc_info=True)
            db.rollback()
            return {"success": False, "error": str(e), "message": f"Update failed: {str(e)}"}

    return {"error": f"Unknown tool name: {tool_name}"}


@router.post("/webhook")
async def handle_vapi_webhook(request: Request, db: Session = Depends(get_db)):
    """General webhook endpoint for Vapi call events and tool calls."""
    body = await request.json()
    logger.debug(f"Received Vapi webhook payload: {body}")

    message = body.get("message", {})
    msg_type = message.get("type")

    # Handle tool calls
    if msg_type in ["tool-calls", "function-call"]:
        tool_calls = message.get("toolCallList") or message.get("toolCalls") or []
        
        # If single functionCall
        if not tool_calls and "functionCall" in message:
            fc = message["functionCall"]
            tool_calls = [{"id": "fc_1", "function": fc}]

        results = []
        for tc in tool_calls:
            call_id = tc.get("id")
            func = tc.get("function", {})
            fn_name = func.get("name")
            fn_args = func.get("arguments", {})

            # In some payload versions, arguments could be JSON string
            if isinstance(fn_args, str):
                import json
                try:
                    fn_args = json.loads(fn_args)
                except Exception:
                    pass

            result_data = execute_tool_call(fn_name, fn_args, db)
            results.append({
                "toolCallId": call_id,
                "result": result_data
            })

        return {"results": results}

    # Handle end-of-call report or status updates
    if msg_type == "end-of-call-report":
        summary = message.get("summary")
        transcript = message.get("transcript")
        call_id = message.get("call", {}).get("id")
        logger.info(f"Vapi Call {call_id} ended. Summary: {summary}")
        crud.log_call_action(
            db,
            action_type="end_of_call_report",
            payload={"summary": summary, "transcript": transcript},
            status="COMPLETED"
        )
        return {"status": "received"}

    return {"status": "ignored", "type": msg_type}


@router.post("/tools/lookup")
async def tool_lookup_patient(request: Request, db: Session = Depends(get_db)):
    """Direct tool endpoint for looking up a patient by phone."""
    payload = await request.json()
    args = payload.get("arguments") or payload.get("message", {}).get("arguments") or payload
    return execute_tool_call("lookup_patient", args, db)


@router.post("/tools/register")
async def tool_register_patient(request: Request, db: Session = Depends(get_db)):
    """Direct tool endpoint for registering a patient."""
    payload = await request.json()
    args = payload.get("arguments") or payload.get("message", {}).get("arguments") or payload
    return execute_tool_call("register_patient", args, db)


@router.post("/tools/update")
async def tool_update_patient(request: Request, db: Session = Depends(get_db)):
    """Direct tool endpoint for updating a patient."""
    payload = await request.json()
    args = payload.get("arguments") or payload.get("message", {}).get("arguments") or payload
    return execute_tool_call("update_patient", args, db)
