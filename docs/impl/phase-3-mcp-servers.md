# Phase 3 — MCP Tool Servers

**Status:** Not started
**Depends on:** Phase 2 (foundation layer)
**Produces:** 4 running FastAPI MCP servers (EHR :8001, Lab :8002, Pharmacy :8003, Appointments :8004)

---

## Overview

Build the four MCP tool servers that agents use to access structured data. Each is a standalone FastAPI app. Build and test all four independently via curl **before** connecting any agent.

All servers share: `config/settings.py`, `config/database.py`, Pydantic models for request/response.

---

## Step 1: EHR MCP Server (port 8001)

### Files

| File | Purpose |
|---|---|
| `mcp_servers/ehr/main.py` | FastAPI app, routes |
| `mcp_servers/ehr/models.py` | Pydantic request/response schemas |
| `mcp_servers/ehr/queries.py` | SQLAlchemy queries |

### Endpoint Contract

**POST /query**

```python
# Request
class EHRQueryRequest(BaseModel):
    patient_uuid: UUID
    resource_types: list[str]  # "demographics", "conditions", "lab_results", "medications", "vitals", "encounters"

# Response
class EHRQueryResponse(BaseModel):
    patient_uuid: UUID
    demographics: dict | None
    conditions: list[dict] | None
    lab_results: list[dict] | None
    medications: list[dict] | None
    vitals: list[dict] | None
    encounters: list[dict] | None

# Error responses
# 400: invalid resource_types value
# 404: patient_uuid not found
```

### Query Contract

```python
# queries.py
def get_patient_demographics(db: Session, patient_id: UUID) -> dict | None: ...
def get_patient_conditions(db: Session, patient_id: UUID) -> list[dict]: ...
def get_patient_lab_results(db: Session, patient_id: UUID, limit: int = 50) -> list[dict]: ...
def get_patient_medications(db: Session, patient_id: UUID) -> list[dict]: ...
def get_patient_vitals(db: Session, patient_id: UUID, limit: int = 50) -> list[dict]: ...
def get_patient_encounters(db: Session, patient_id: UUID) -> list[dict]: ...
```

### Verification

```bash
# Start server
uvicorn mcp_servers.ehr.main:app --port 8001

# Test with a known patient UUID (get one from DB first)
PATIENT_ID=$(psql -h localhost -U healthcare_app -d healthcare_platform -t -c "SELECT patient_id FROM patients LIMIT 1" | tr -d ' ')

curl -s http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d "{\"patient_uuid\": \"$PATIENT_ID\", \"resource_types\": [\"demographics\", \"conditions\"]}" | python -m json.tool
```

Expected: JSON with demographics dict and conditions array populated.

```bash
# Error cases
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"patient_uuid": "00000000-0000-0000-0000-000000000000", "resource_types": ["demographics"]}'
# Expected: 404

curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d "{\"patient_uuid\": \"$PATIENT_ID\", \"resource_types\": [\"invalid\"]}"
# Expected: 400
```

---

## Step 2: Lab MCP Server (port 8002)

### Files

| File | Purpose |
|---|---|
| `mcp_servers/lab/main.py` | FastAPI app, routes |
| `mcp_servers/lab/models.py` | Pydantic schemas |
| `mcp_servers/lab/queries.py` | SQLAlchemy queries |

### Endpoint Contracts

**POST /orders**

```python
class LabOrderRequest(BaseModel):
    patient_uuid: UUID
    test_name: str
    loinc_code: str | None = None

class LabOrderResponse(BaseModel):
    order_id: UUID
    status: str  # "pending"
    result_available_at: datetime  # now + 30 min
```

Inserts a row into `lab_results` with `result_status = "pending"` and `result_available_at = now() + interval '30 minutes'`.

**GET /results**

```python
# Query params: patient_id, test_name
# Returns:
#   202 + {"status": "pending", "result_available_at": ...} if not yet available
#   200 + {"lab_result_id", "test_name", "numeric_value", "unit", "reference_range", ...} if ready
```

### Verification

```bash
uvicorn mcp_servers.lab.main:app --port 8002

# Submit order
curl -s http://localhost:8002/orders \
  -H "Content-Type: application/json" \
  -d "{\"patient_uuid\": \"$PATIENT_ID\", \"test_name\": \"ferritin\"}" | python -m json.tool
# Expected: order_id, status: "pending", result_available_at ~30min from now

# Check results (should be pending)
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8002/results?patient_id=$PATIENT_ID&test_name=ferritin"
# Expected: 202

# Check existing results
curl -s "http://localhost:8002/results?patient_id=$PATIENT_ID&test_name=Hemoglobin" | python -m json.tool
# Expected: 200 with numeric_value
```

---

## Step 3: Pharmacy MCP Server (port 8003)

### Files

| File | Purpose |
|---|---|
| `mcp_servers/pharmacy/main.py` | FastAPI app, routes |
| `mcp_servers/pharmacy/models.py` | Pydantic schemas |
| `mcp_servers/pharmacy/queries.py` | SQLAlchemy queries |

### Pre-populated Reference Data

Before the server runs, populate two reference tables (add to schema or seed script):

**Drug Interactions Table:**

```sql
CREATE TABLE IF NOT EXISTS drug_interactions (
    interaction_id SERIAL PRIMARY KEY,
    drug_a VARCHAR(255) NOT NULL,
    drug_b VARCHAR(255) NOT NULL,
    severity VARCHAR(50) CHECK (severity IN ('mild', 'moderate', 'severe', 'contraindicated')),
    description TEXT
);
```

**Formulary Table:**

```sql
CREATE TABLE IF NOT EXISTS formulary (
    formulary_id SERIAL PRIMARY KEY,
    drug_name VARCHAR(255) NOT NULL,
    site_id VARCHAR(50) NOT NULL,
    available BOOLEAN DEFAULT TRUE,
    formulations TEXT[]
);
```

### Endpoint Contracts

**POST /interactions**

```python
class DrugInteractionRequest(BaseModel):
    drug_list: list[str]

class DrugInteractionResponse(BaseModel):
    interactions: list[dict]  # [{drug_a, drug_b, severity, description}]
```

**POST /formulary**

```python
class FormularyRequest(BaseModel):
    drug_name: str
    site_id: str

class FormularyResponse(BaseModel):
    available: bool
    formulations: list[str]
```

**POST /prescriptions**

```python
class PrescriptionRequest(BaseModel):
    patient_uuid: UUID
    clinician_id: UUID
    drug_name: str
    dose: str
    route: str
    frequency: str

class PrescriptionResponse(BaseModel):
    medication_id: UUID
```

Inserts into `medications` table.

### Verification

```bash
uvicorn mcp_servers.pharmacy.main:app --port 8003

# Check interactions
curl -s http://localhost:8003/interactions \
  -H "Content-Type: application/json" \
  -d '{"drug_list": ["metformin", "lisinopril"]}' | python -m json.tool

# Check formulary
curl -s http://localhost:8003/formulary \
  -H "Content-Type: application/json" \
  -d '{"drug_name": "iron sucrose", "site_id": "site_001"}' | python -m json.tool

# Submit prescription
curl -s http://localhost:8003/prescriptions \
  -H "Content-Type: application/json" \
  -d "{\"patient_uuid\": \"$PATIENT_ID\", \"clinician_id\": \"$CLINICIAN_ID\", \"drug_name\": \"iron sucrose\", \"dose\": \"200mg\", \"route\": \"IV\", \"frequency\": \"fortnightly\"}" | python -m json.tool
# Expected: medication_id returned
```

---

## Step 4: Appointments MCP Server (port 8004)

### Files

| File | Purpose |
|---|---|
| `mcp_servers/appointments/main.py` | FastAPI app, routes |
| `mcp_servers/appointments/models.py` | Pydantic schemas |
| `mcp_servers/appointments/queries.py` | SQLAlchemy queries |

### Endpoint Contracts

**POST /appointments**

```python
class AppointmentRequest(BaseModel):
    patient_uuid: UUID
    clinician_id: UUID
    appointment_type: str
    scheduled_datetime: datetime

class AppointmentResponse(BaseModel):
    appointment_id: UUID
    status: str  # "scheduled"
```

**GET /appointments/{patient_id}**

```python
# Returns: list of upcoming appointments (status = "scheduled", datetime > now)
class AppointmentListResponse(BaseModel):
    appointments: list[dict]  # [{appointment_id, clinician_id, type, datetime, status}]
```

### Verification

```bash
uvicorn mcp_servers.appointments.main:app --port 8004

# Create appointment
curl -s http://localhost:8004/appointments \
  -H "Content-Type: application/json" \
  -d "{\"patient_uuid\": \"$PATIENT_ID\", \"clinician_id\": \"$CLINICIAN_ID\", \"appointment_type\": \"follow-up\", \"scheduled_datetime\": \"2025-02-01T10:00:00Z\"}" | python -m json.tool

# List appointments
curl -s "http://localhost:8004/appointments/$PATIENT_ID" | python -m json.tool
```

---

## Phase 3 Checkpoint

- [ ] All 4 MCP servers start independently without errors
- [ ] EHR: POST /query returns demographics + conditions for a known patient
- [ ] EHR: 404 for unknown patient, 400 for invalid resource types
- [ ] Lab: POST /orders creates pending result with future result_available_at
- [ ] Lab: GET /results returns 202 for pending, 200 for available
- [ ] Pharmacy: POST /interactions returns interaction data
- [ ] Pharmacy: POST /formulary returns availability
- [ ] Pharmacy: POST /prescriptions inserts into medications table
- [ ] Appointments: POST creates, GET lists upcoming
- [ ] Each server uses shared config/database from Phase 2
