"""Tests for Vapi webhook and tool call endpoints."""
import pytest
from fastapi import status


def test_vapi_check_patient_not_found(client):
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "check_patient_by_phone",
                        "arguments": {"phone_number": "+14155550000"},
                    },
                }
            ],
        }
    }
    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    res = data["results"][0]["result"]
    assert res["found"] is False


def test_vapi_register_and_lookup_flow(client):
    # 1. Register via Vapi Webhook
    reg_payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "reg_call_001",
                    "type": "function",
                    "function": {
                        "name": "register_patient",
                        "arguments": {
                            "first_name": "David",
                            "last_name": "Miller",
                            "date_of_birth": "1982-12-05",
                            "sex": "Male",
                            "phone_number": "+16505559876",
                            "address_line_1": "550 University Ave",
                            "city": "Palo Alto",
                            "state": "CA",
                            "zip_code": "94301",
                        },
                    },
                }
            ],
        }
    }
    reg_resp = client.post("/vapi/webhook", json=reg_payload)
    assert reg_resp.status_code == status.HTTP_200_OK
    reg_res = reg_resp.json()["results"][0]["result"]
    assert reg_res["success"] is True
    patient_id = reg_res["patient_id"]
    assert patient_id is not None

    # 2. Subsequent call lookup
    lookup_payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "lookup_call_002",
                    "type": "function",
                    "function": {
                        "name": "check_patient_by_phone",
                        "arguments": {"phone_number": "+16505559876"},
                    },
                }
            ],
        }
    }
    look_resp = client.post("/vapi/webhook", json=lookup_payload)
    assert look_resp.status_code == status.HTTP_200_OK
    look_res = look_resp.json()["results"][0]["result"]
    assert look_res["found"] is True
    assert look_res["first_name"] == "David"
    assert look_res["patient_id"] == patient_id


def test_vapi_direct_tool_endpoints(client):
    # Test /vapi/tools/register direct call
    patient_args = {
        "first_name": "Emma",
        "last_name": "Watson",
        "date_of_birth": "1990-04-15",
        "sex": "Female",
        "phone_number": "+12125556789",
        "address_line_1": "350 5th Ave",
        "city": "New York",
        "state": "NY",
        "zip_code": "10118",
    }
    reg_resp = client.post("/vapi/tools/register", json={"arguments": patient_args})
    assert reg_resp.status_code == status.HTTP_200_OK
    assert reg_resp.json()["success"] is True

    # Test /vapi/tools/lookup direct call
    lookup_resp = client.post("/vapi/tools/lookup", json={"arguments": {"phone_number": "+12125556789"}})
    assert lookup_resp.status_code == status.HTTP_200_OK
    assert lookup_resp.json()["found"] is True
    assert lookup_resp.json()["last_name"] == "Watson"


def test_vapi_end_of_call_report(client):
    payload = {
        "message": {
            "type": "end-of-call-report",
            "summary": "Caller successfully registered as a new patient.",
            "transcript": "Agent: Thank you for calling... Caller: My name is ...",
            "call": {"id": "vapi-call-test-999"},
        }
    }
    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "received"
