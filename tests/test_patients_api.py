"""Unit and integration tests for Patient REST API endpoints."""
import pytest
from fastapi import status


def sample_patient_data():
    return {
        "first_name": "Alice",
        "last_name": "Smith",
        "date_of_birth": "1990-05-20",
        "sex": "Female",
        "phone_number": "+14155551234",
        "email": "alice.smith@example.com",
        "address_line_1": "100 Pine Street",
        "address_line_2": "Suite 300",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94111",
        "insurance_provider": "Aetna",
        "insurance_member_id": "AET-998811",
        "preferred_language": "English",
        "emergency_contact_name": "Bob Smith",
        "emergency_contact_phone": "+14155554321",
    }


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ok"


def test_create_patient_success(client):
    payload = sample_patient_data()
    response = client.post("/patients", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    res_json = response.json()
    assert res_json["error"] is None
    data = res_json["data"]
    assert data["first_name"] == "Alice"
    assert data["last_name"] == "Smith"
    assert data["phone_number"] == "+14155551234"
    assert "patient_id" in data
    assert data["deleted_at"] is None


def test_create_patient_conversational_dob(client):
    payload = sample_patient_data()
    payload["date_of_birth"] = "05/20/1990"
    response = client.post("/patients", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()["data"]
    assert data["date_of_birth"] == "1990-05-20"


def test_create_patient_missing_required_fields(client):
    # Missing last_name and address_line_1
    invalid_payload = {
        "first_name": "Alice",
        "date_of_birth": "1990-05-20",
        "sex": "Female",
        "phone_number": "+14155551234",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94111",
    }
    response = client.post("/patients", json=invalid_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    res_json = response.json()
    assert "Validation error" in res_json["error"]


def test_create_patient_invalid_phone(client):
    payload = sample_patient_data()
    payload["phone_number"] = "123"  # Too short
    response = client.post("/patients", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_patient_by_id(client):
    # Create patient first
    payload = sample_patient_data()
    create_resp = client.post("/patients", json=payload)
    patient_id = create_resp.json()["data"]["patient_id"]

    # Retrieve patient
    response = client.get(f"/patients/{patient_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["patient_id"] == patient_id
    assert response.json()["data"]["first_name"] == "Alice"


def test_get_patient_not_found(client):
    response = client.get("/patients/00000000-0000-0000-0000-000000000000")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_and_filter_patients(client):
    p1 = sample_patient_data()
    p1["first_name"] = "Alice"
    p1["last_name"] = "Johnson"
    p1["phone_number"] = "+14155551111"
    p1["date_of_birth"] = "1985-01-10"

    p2 = sample_patient_data()
    p2["first_name"] = "Bob"
    p2["last_name"] = "Johnson"
    p2["phone_number"] = "+14155552222"
    p2["date_of_birth"] = "1992-06-15"

    p3 = sample_patient_data()
    p3["first_name"] = "Charlie"
    p3["last_name"] = "Davis"
    p3["phone_number"] = "+13125553333"
    p3["date_of_birth"] = "1985-01-10"

    client.post("/patients", json=p1)
    client.post("/patients", json=p2)
    client.post("/patients", json=p3)

    # Filter by last_name
    r = client.get("/patients?last_name=Johnson")
    assert r.status_code == status.HTTP_200_OK
    assert len(r.json()["data"]) == 2

    # Filter by date_of_birth
    r = client.get("/patients?date_of_birth=1985-01-10")
    assert r.status_code == status.HTTP_200_OK
    assert len(r.json()["data"]) == 2

    # Filter by phone_number
    r = client.get("/patients?phone_number=13125553333")
    assert r.status_code == status.HTTP_200_OK
    assert len(r.json()["data"]) == 1
    assert r.json()["data"][0]["first_name"] == "Charlie"


def test_update_patient(client):
    create_resp = client.post("/patients", json=sample_patient_data())
    patient_id = create_resp.json()["data"]["patient_id"]

    update_payload = {
        "address_line_1": "999 Montgomery St",
        "city": "San Francisco",
        "insurance_provider": "United Healthcare",
    }
    response = client.put(f"/patients/{patient_id}", json=update_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert data["address_line_1"] == "999 Montgomery St"
    assert data["insurance_provider"] == "United Healthcare"
    # Unchanged fields remain intact
    assert data["first_name"] == "Alice"


def test_soft_delete_patient(client):
    create_resp = client.post("/patients", json=sample_patient_data())
    patient_id = create_resp.json()["data"]["patient_id"]

    # Delete
    del_resp = client.delete(f"/patients/{patient_id}")
    assert del_resp.status_code == status.HTTP_200_OK
    assert del_resp.json()["data"]["deleted"] is True

    # Check normal GET /patients/{id} returns 404
    get_resp = client.get(f"/patients/{patient_id}")
    assert get_resp.status_code == status.HTTP_404_NOT_FOUND

    # Check list /patients excludes it
    list_resp = client.get("/patients")
    assert len(list_resp.json()["data"]) == 0

    # Include deleted allows retrieving
    inc_resp = client.get(f"/patients/{patient_id}?include_deleted=true")
    assert inc_resp.status_code == status.HTTP_200_OK
    assert inc_resp.json()["data"]["deleted_at"] is not None
