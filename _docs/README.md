# Voice AI Agent — Patient Registration System

A voice-based AI agent, reachable by a real phone number, that conversationally
registers patients, persists their data, and exposes it through a REST API.

---

## Overview

A caller dials a phone number. A voice AI agent answers, greets the caller,
and collects standard U.S. patient demographic information through natural
conversation. Once the caller confirms the details, the agent saves the
record to a persistent database. A companion REST API allows querying and
viewing stored patient records at any time — including on a second call to
the same number.

```
Phone Call (Caller)
        │
        ▼
Voice AI Agent (Vapi + LLM)
        │  tool calls
        ▼
FastAPI Backend  ──────►  SQLite Database
        │
        ▼
REST API (queried by reviewer / dashboard)
```

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Telephony + Voice AI | **Vapi** | Provisions a real dialable number and handles STT/TTS/turn-taking out of the box. The agent is defined as a system prompt plus tool calls, so no telephony or speech code has to be written from scratch. (Retell is a comparable alternative.) |
| LLM | **Google Gemini** (via Vapi's model picker) | Needs to be fast, not just capable — voice latency matters more than raw reasoning depth for slot-filling and confirmation. Gemini's free tier also keeps this cost-free to build and test. |
| Backend / API | **Python + FastAPI** | Fast to scaffold CRUD with built-in Pydantic validation, and auto-generates OpenAPI docs, which doubles as reviewer-facing documentation. |
| Database | **SQLite** | Zero setup, file-based persistence that survives restarts, and fully capable of enforcing the required schema and constraints for this scope. |
| Hosting | **Railway or Render** | One-click deploy from GitHub with a stable public URL for both the Vapi webhook and the reviewer's direct API calls. |
| Logging | Python `logging` → stdout | Captured automatically by the hosting platform's log viewer; satisfies the observability requirement with minimal effort. |

**Deliberate trade-offs:**
- SQLite over Postgres — this is a take-home assessment, not a production
  deployment; file-based persistence meets every stated requirement without
  the setup tax of a managed database.
- A managed voice platform (Vapi) over raw Twilio + STT/TTS — the assessment
  explicitly values integration and system design over reimplementing speech
  infrastructure.

---

## Architecture

**Separation of concerns:**
- **Telephony / voice** — Vapi owns the phone number, call handling, and
  speech-to-text/text-to-speech.
- **Agent logic** — a system prompt plus tool (function) definitions that
  tell the LLM what fields to collect, when to confirm, and which API
  endpoints to call.
- **API / validation layer** — FastAPI, with Pydantic models enforcing types
  and constraints server-side, independent of whatever the voice agent
  itself already validated.
- **Data layer** — SQLite, accessed only through the FastAPI service.

**Call flow:**
1. Caller dials the Vapi number.
2. Vapi's LLM greets the caller and begins collecting required fields
   conversationally (not as a rigid script).
3. A tool call checks `GET /patients?phone_number=` to see if the caller is
   already registered.
   - If found: the agent offers to update the existing record instead of
     creating a new one.
4. Once all required fields are collected, the agent reads them back and
   asks the caller to confirm or correct any field.
5. On confirmation, a tool call fires `POST /patients` (or `PUT /patients/:id`
   for an update).
6. FastAPI validates the payload, writes to SQLite, and returns a
   `{ "data": {...}, "error": null }` envelope.
7. The agent relays success or a graceful error message back to the caller
   and ends the call.
8. The reviewer can independently query `GET /patients` or
   `GET /patients/:id` at any time to confirm persistence.

---

## Data Model

| Field | Type | Required |
|---|---|---|
| first_name | String | Yes |
| last_name | String | Yes |
| date_of_birth | Date | Yes |
| sex | Enum | Yes |
| phone_number | String | Yes |
| email | String | No |
| address_line_1 | String | Yes |
| address_line_2 | String | No |
| city | String | Yes |
| state | String | Yes |
| zip_code | String | Yes |
| insurance_provider | String | No |
| insurance_member_id | String | No |
| preferred_language | String | No (default: English) |
| emergency_contact_name | String | No |
| emergency_contact_phone | String | No |
| patient_id | UUID | Auto |
| created_at | Timestamp | Auto |
| updated_at | Timestamp | Auto |

The agent only asks for required fields by default, then offers optional
fields (insurance, emergency contact, preferred language) as an opt-in at
the end of the required flow.

---

## REST API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/patients` | List patients; supports `?last_name=`, `?date_of_birth=`, `?phone_number=` |
| GET | `/patients/:id` | Retrieve a single patient by UUID |
| POST | `/patients` | Create a new patient |
| PUT | `/patients/:id` | Update an existing patient (partial updates allowed) |
| DELETE | `/patients/:id` | Soft-delete (sets `deleted_at`; no hard delete) |

All endpoints validate input server-side and return proper HTTP status codes
(200, 201, 400, 404, 422, 500), independent of any validation the voice
agent performs.

---

## Build Process

1. **API and data layer first.** Build the FastAPI CRUD endpoints and SQLite
   schema before touching voice at all, and verify them directly (curl /
   Postman / the auto-generated OpenAPI docs). This gives a working,
   testable core regardless of how the voice integration goes.
2. **Deploy early.** Push the API to Railway/Render as soon as it works
   locally, so there's a stable public URL to build the voice integration
   against — and so the "live and callable" requirement is de-risked early
   rather than left to the end.
3. **Voice agent setup.** Provision a number in Vapi, write the system
   prompt (collection order, confirmation step, correction handling,
   re-prompting rules for invalid input), and define tool calls that hit
   the deployed API.
4. **End-to-end testing.** Place real calls, listen for unnatural phrasing
   or confirmation gaps, and iterate on the prompt. Add the duplicate-phone
   lookup and update-instead-of-create flow.
5. **Documentation and polish.** Write this README, add seed data, confirm
   logging is capturing at least the final collected payload per call.

---

## Known Limitations / Trade-offs

- SQLite is used for simplicity and is not intended to reflect a production
  database choice at scale.
- No HIPAA compliance measures are implemented; this system must not be used
  with real patient data.
- Duplicate detection is phone-number based only; it will not catch a
  returning patient calling from a new number.
- Multi-language support, appointment scheduling, and a dashboard UI are
  treated as stretch goals, not core requirements.

## Next Steps

- Add automated tests for the API layer.
- Store a transcript or summary of each call linked to its patient record.
- Add a lightweight dashboard for browsing registered patients.
- Consider migrating to Postgres if this moved beyond a take-home scope.

---

## Environment Variables

```
VAPI_API_KEY=
LLM_API_KEY=
DATABASE_URL=            # defaults to local SQLite file if unset
PORT=
```

## Setup

```bash
# clone and install
git clone <repo-url>
cd voice-ai-patient-registration
pip install -r requirements.txt

# run the API locally
uvicorn app.main:app --reload

# deploy
# push to GitHub, connect the repo in Railway/Render, set env vars, deploy
```

## Submission

- Repository: `<repo-url>`
- Phone number: `<phone-number>`
- API base URL: `<deployed-url>`
