# Voice AI Agent — Patient Registration System

A voice-based AI agent, reachable by a real phone number, that conversationally registers patients, persists their data in a persistent SQLite database, and exposes it through a REST API.

---

## Architecture Overview

```
Phone Call (Caller)
        │
        ▼
Voice AI Agent (Vapi + Gemini LLM)
        │  tool calls (check_patient_by_phone, register_patient, update_patient)
        ▼
FastAPI Backend  ──────►  SQLite Database
        │
        ▼
REST API (Queried by reviewer, dashboard, or downstream services)
```

### System Components:
1. **Telephony & Speech**: Managed by **Vapi** (provisioned dialable number, STT, TTS).
2. **LLM Orchestration**: **Google Gemini** (via Vapi) guided by specialized medical intake system prompts and tool call schemas.
3. **Backend API**: **Python 3 + FastAPI** enforcing Pydantic data validation and structured responses.
4. **Data Persistence**: **SQLite** via SQLAlchemy with support for queries, indexing, and soft deletion.

---

## Features

- **Conversational Intake**: Collects all required U.S. patient demographic information naturally (one field at a time).
- **Duplicate Detection**: Real-time lookup on incoming phone number to detect returning patients and offer updates instead of duplicate registrations.
- **Read-Back & Confirmation**: Summarizes details to the caller before saving, allowing real-time corrections.
- **Strict Server-Side Validation**: Validates date formats (`YYYY-MM-DD` and `MM/DD/YYYY`), phone number lengths, and required demographic constraints.
- **Full RESTful CRUD**: Complete endpoints to create, read, filter, update, and soft-delete patients.
- **Automated Test Suite**: Pytest suite covering all CRUD endpoints, validation edge cases, and Vapi webhook payloads.

---

## Data Model

| Field | Type | Required | Notes |
|---|---|---|---|
| `patient_id` | UUID (String) | Auto | Unique identifier |
| `first_name` | String | Yes | Patient's first name |
| `last_name` | String | Yes | Patient's last name |
| `date_of_birth` | String | Yes | ISO format `YYYY-MM-DD` |
| `sex` | Enum | Yes | `Male`, `Female`, `Other`, `Unknown` |
| `phone_number` | String | Yes | Contact phone number |
| `email` | String | No | Email address |
| `address_line_1` | String | Yes | Street address |
| `address_line_2` | String | No | Apt/Suite/Unit |
| `city` | String | Yes | City |
| `state` | String | Yes | State (e.g. `CA`, `NY`) |
| `zip_code` | String | Yes | Postal/ZIP code |
| `insurance_provider` | String | No | Provider name |
| `insurance_member_id`| String | No | Member ID |
| `preferred_language` | String | No | Default: `English` |
| `emergency_contact_name` | String | No | Full name |
| `emergency_contact_phone`| String | No | Phone number |
| `created_at` | Timestamp | Auto | UTC timestamp |
| `updated_at` | Timestamp | Auto | UTC timestamp |
| `deleted_at` | Timestamp | Auto | Set upon soft delete |

---

## REST API Specification

### Envelope Format
All API responses return a standard envelope:
```json
{
  "data": { ... },
  "error": null
}
```

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check endpoint |
| `GET` | `/dashboard` | Web dashboard for viewing registered patients |
| `GET` | `/patients` | List patients. Query params: `?last_name=`, `?date_of_birth=`, `?phone_number=`, `?include_deleted=`, `?limit=`, `?offset=` |
| `GET` | `/patients/{patient_id}` | Retrieve patient by UUID |
| `POST` | `/patients` | Create a new patient |
| `PUT` | `/patients/{patient_id}` | Update existing patient (supports partial updates) |
| `DELETE` | `/patients/{patient_id}` | Soft delete patient (sets `deleted_at`) |
| `POST` | `/vapi/webhook` | Vapi webhook for tool calls and call status |
| `POST` | `/vapi/tools/lookup` | Direct tool endpoint to look up caller by phone |
| `POST` | `/vapi/tools/register` | Direct tool endpoint to register a patient |
| `POST` | `/vapi/tools/update` | Direct tool endpoint to update an existing patient |

---

## Quickstart & Local Setup

### 1. Prerequisites
- Python 3.10+
- `pip`

### 2. Installation
```bash
# Clone the repository
git clone <repo-url>
cd voice-ai-agent

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

### 3. Seed Sample Data
```bash
python3 app/seed.py
```

### 4. Run the API Server
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive API Docs (Swagger UI): `http://localhost:8000/docs`
- ReDoc Docs: `http://localhost:8000/redoc`

### 5. Run Automated Tests
```bash
pytest -v
```

---

## Vapi Integration Setup

### Dashboard Setup

1. **Create account & add payment method**
   Sign up at [dashboard.vapi.ai](https://dashboard.vapi.ai). A payment method is required on file even for the free US number, though the free number itself isn't charged.

2. **Create an assistant**
   Go to **Assistants → Create Assistant**. Set the **Model** to Google Gemini, and choose a voice/transcriber (defaults work fine to start).

3. **Write the system prompt and first message**
   In the assistant's Model tab, set the first message (e.g. *"Thank you for calling Community Health Clinic, my name is CareAssist..."*) and paste in the full system prompt from [`vapi/system_prompt.md`](vapi/system_prompt.md): field collection order, confirmation step, correction handling, and re-prompt rules for invalid input.

4. **Create the custom tools**
   Go to **Tools → Create Tool**, using the **API Request** tool type for each of the three tools below (this calls this project's REST API directly with no extra webhook server needed). See [Custom Tool Configurations](#custom-tool-configurations) below for the exact endpoints and parameters.

5. **Attach the tools to the assistant**
   Back in the assistant config, under the **Tools/Functions** tab, add the three tools created above so the LLM knows when to call them mid-conversation.

6. **Provision a phone number**
   Go to **Phone Numbers → Create Phone Number → Free Vapi Number**, enter a US area code, and create it.

7. **Route the number to the assistant**
   Open the new phone number's settings, and under **Inbound Settings** select the assistant built above, then **Save**.

> **Note on Render cold starts**: The backend is deployed on Render's free tier, which sleeps after inactivity and takes ~50 seconds to wake. Ping `GET /health` before testing calls to warm up the service first.

### Custom Tool Configurations
Configure the following 3 custom API tools in your Vapi Assistant settings:

   #### 1. `check_patient_by_phone` (Lookup Existing Patient)
   - **Endpoint**: `POST https://voice-ai-agent-nu1v.onrender.com/vapi/tools/lookup`
   - **Description**: Checks if a patient record already exists in the system by their phone number.

   | Property | Type | Required | Description |
   |---|---|---|---|
   | `phone_number` | String | **Yes** | Caller contact phone number |

   ---

   #### 2. `register_patient` (Create Patient Registration)
   - **Endpoint**: `POST https://voice-ai-agent-nu1v.onrender.com/vapi/tools/register`
   - **Description**: Creates a new patient registration record once caller has confirmed all demographic details.

   | Property | Type | Required | Description |
   |---|---|---|---|
   | `first_name` | String | **Yes** | Patient's first name |
   | `last_name` | String | **Yes** | Patient's last name |
   | `date_of_birth` | String | **Yes** | Date of birth in `YYYY-MM-DD` format |
   | `sex` | String (Enum) | **Yes** | `Male`, `Female`, `Other`, `Prefer not to say` |
   | `phone_number` | String | **Yes** | Contact phone number |
   | `address_line_1` | String | **Yes** | Primary street address |
   | `address_line_2` | String | No | Apartment, suite, or unit number (optional) |
   | `city` | String | **Yes** | City name |
   | `state` | String | **Yes** | US State (e.g. `CA`, `NY`) |
   | `zip_code` | String | **Yes** | Postal ZIP code |
   | `email` | String | No | Email address (optional) |
   | `insurance_provider` | String | No | Health insurance provider name (optional) |
   | `insurance_member_id` | String | No | Insurance member ID / policy number (optional) |
   | `preferred_language` | String | No | Preferred spoken language (defaults to `English`) |
   | `emergency_contact_name` | String | No | Emergency contact full name (optional) |
   | `emergency_contact_phone` | String | No | Emergency contact phone number (optional) |

   ---

   #### 3. `update_patient` (Update Patient Details)
   - **Endpoint**: `POST https://voice-ai-agent-nu1v.onrender.com/vapi/tools/update`
   - **Description**: Updates an existing patient's details when requested by the caller.

   | Property | Type | Required | Description |
   |---|---|---|---|
   | `patient_id` | String | No | UUID of the existing patient record |
   | `phone_number` | String | No | Patient phone number for lookup if ID unknown |
   | `first_name` | String | No | Patient's first name |
   | `last_name` | String | No | Patient's last name |
   | `date_of_birth` | String | No | Date of birth (`YYYY-MM-DD`) |
   | `address_line_1` | String | No | Street address |
   | `city` | String | No | City name |
   | `state` | String | No | State abbreviation or name |
   | `zip_code` | String | No | Postal ZIP code |
   | `insurance_provider` | String | No | Insurance company name |
   | `insurance_member_id` | String | No | Insurance member ID |

### Reference Files
1. **System Prompt**: See [`vapi/system_prompt.md`](vapi/system_prompt.md) for the complete conversational flow.

---

## Deployment (Railway / Render)

1. Push this repository to GitHub.
2. In **Railway** or **Render**, create a new Web Service from the repo.
3. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Environment variables:
   - `DATABASE_URL=sqlite:///./patients.db`
   - `PORT=8000`