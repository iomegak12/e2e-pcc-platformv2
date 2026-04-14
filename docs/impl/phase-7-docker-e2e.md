# Phase 7 — Docker & End-to-End Integration

**Status:** Not started
**Depends on:** Phase 6 (all components built and instrumented)
**Produces:** Dockerfiles for all services, updated docker-compose.app.yml, full E2E integration test

---

## Overview

Package everything into Docker containers, verify the full stack starts with `docker compose up`, and run an end-to-end integration test that exercises the complete patient journey.

---

## Step 1: Dockerfiles

### MCP Server Dockerfile

File: `docker/Dockerfile.mcp`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements-base.txt requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-base.txt -r requirements-api.txt

COPY config/ ./config/
COPY mcp_servers/ ./mcp_servers/

# Overridden per service in docker-compose via command
CMD ["uvicorn", "mcp_servers.ehr.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Orchestrator Dockerfile

File: `docker/Dockerfile.orchestrator`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements-base.txt requirements-api.txt requirements-ai.txt ./
RUN pip install --no-cache-dir -r requirements-base.txt -r requirements-api.txt -r requirements-ai.txt

COPY config/ ./config/
COPY agents/ ./agents/
COPY orchestrator/ ./orchestrator/
COPY mcp_servers/ ./mcp_servers/

CMD ["uvicorn", "orchestrator.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose App Updates

Update `docker-compose.app.yml` to use correct build contexts:

```yaml
services:
  orchestrator:
    build:
      context: .
      dockerfile: docker/Dockerfile.orchestrator
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - CHROMADB_HOST=chromadb
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      chromadb:
        condition: service_healthy
      mcp-ehr:
        condition: service_healthy
      mcp-lab:
        condition: service_healthy
      mcp-pharmacy:
        condition: service_healthy
      mcp-appointments:
        condition: service_healthy

  mcp-ehr:
    build:
      context: .
      dockerfile: docker/Dockerfile.mcp
    command: ["uvicorn", "mcp_servers.ehr.main:app", "--host", "0.0.0.0", "--port", "8001"]
    ports:
      - "8001:8001"
    env_file: .env
    environment:
      - POSTGRES_HOST=postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 15s
      timeout: 5s
      retries: 3
    depends_on:
      postgres:
        condition: service_healthy

  mcp-lab:
    build:
      context: .
      dockerfile: docker/Dockerfile.mcp
    command: ["uvicorn", "mcp_servers.lab.main:app", "--host", "0.0.0.0", "--port", "8002"]
    ports:
      - "8002:8002"
    env_file: .env
    environment:
      - POSTGRES_HOST=postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 15s
      timeout: 5s
      retries: 3
    depends_on:
      postgres:
        condition: service_healthy

  mcp-pharmacy:
    build:
      context: .
      dockerfile: docker/Dockerfile.mcp
    command: ["uvicorn", "mcp_servers.pharmacy.main:app", "--host", "0.0.0.0", "--port", "8003"]
    ports:
      - "8003:8003"
    env_file: .env
    environment:
      - POSTGRES_HOST=postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 15s
      timeout: 5s
      retries: 3
    depends_on:
      postgres:
        condition: service_healthy

  mcp-appointments:
    build:
      context: .
      dockerfile: docker/Dockerfile.mcp
    command: ["uvicorn", "mcp_servers.appointments.main:app", "--host", "0.0.0.0", "--port", "8004"]
    ports:
      - "8004:8004"
    env_file: .env
    environment:
      - POSTGRES_HOST=postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 15s
      timeout: 5s
      retries: 3
    depends_on:
      postgres:
        condition: service_healthy

networks:
  default:
    name: pcc-network
    external: true
```

**Key:** In Docker, services reference each other by service name (`postgres`, `redis`, `chromadb`), not `localhost`. The `environment` overrides in docker-compose handle this.

### Verification

```bash
# Build all images
docker compose -f docker-compose.infra.yml -f docker-compose.app.yml build

# Start full stack
docker compose -f docker-compose.infra.yml -f docker-compose.app.yml up -d

# Check all healthy
docker compose -f docker-compose.infra.yml -f docker-compose.app.yml ps
```

Expected: All 9 services (4 infra + 5 app) showing "healthy".

```bash
# Quick smoke test
curl -s http://localhost:8000/api/v1/health | python -m json.tool
curl -s http://localhost:8001/health | python -m json.tool
curl -s http://localhost:8002/health | python -m json.tool
curl -s http://localhost:8003/health | python -m json.tool
curl -s http://localhost:8004/health | python -m json.tool
```

Expected: All return healthy status.

---

## Step 2: End-to-End Integration Test

File: `tests/integration/test_end_to_end.py`

### Test Contract

```python
class TestEndToEndPatientJourney:
    """
    Full patient journey:
    IDA patient → intake → triage → diagnostics → treatment → HITL → discharge
    
    Preconditions:
      - Full Docker stack running
      - Known test patient with IDA-relevant history in DB
      - Known clinician for approval
    """

    def test_step_1_submit_symptoms(self):
        """POST /symptoms → returns triage_ref_id, urgency = 'urgent'"""

    def test_step_2_check_case_diagnostics_started(self):
        """GET /cases/{id} → diagnostics_output present or in-progress"""

    def test_step_3_wait_for_diagnostics(self):
        """
        Poll GET /cases/{id} until diagnostics_output is populated.
        Self-RAG may request labs → wait for simulated result.
        Timeout: 5 minutes.
        """

    def test_step_4_verify_diagnosis(self):
        """GET /cases/{id} → primary_diagnosis contains IDA (D50.x)"""

    def test_step_5_verify_approval_pending(self):
        """
        GET /approvals/pending → includes task for this episode.
        Treatment plan present with awaiting_human_approval = True.
        """

    def test_step_6_approve_treatment(self):
        """
        POST /approvals/{task_id} action=approved
        Verify: approval_events updated, audit_log entry created.
        """

    def test_step_7_verify_discharge_plan_created(self):
        """GET /patients/{id}/discharge-plan → plan exists with status 'active'"""

    def test_step_8_scheduler_updates_risk_scores(self):
        """
        Wait for scheduler cycle (15 min in dev — or trigger manually).
        Verify: discharge_plans.risk_score populated, risk_score_updated_at set.
        """

    def test_step_9_anomaly_detection(self):
        """
        For a test patient with seeded anomalies after day 18:
        Advance/simulate wearable readings → scheduler detects anomaly.
        Verify: risk_score > 65.
        """

    def test_step_10_verify_escalation(self):
        """
        After anomaly detection, verify:
          - New approval_events row with task_type = 'high_risk_escalation'
          - Notification published to Redis hitl-notifications channel
        """
```

### Running the Test

```bash
# Ensure full stack is running
docker compose -f docker-compose.infra.yml -f docker-compose.app.yml up -d

# Run E2E test
python -m pytest tests/integration/test_end_to_end.py -v --timeout=600
```

Expected: All 10 steps pass.

### Test Configuration

```python
# tests/conftest.py

import pytest

@pytest.fixture
def api_url():
    return "http://localhost:8000"

@pytest.fixture
def test_patient_uuid():
    """A known patient with IDA-relevant history."""
    # Query from DB or hardcode a UUID that exists in test data
    ...

@pytest.fixture
def test_clinician_id():
    """A known clinician for approvals."""
    ...

@pytest.fixture
def auth_token(api_url, test_clinician_id):
    """Get a JWT token for the test clinician."""
    response = httpx.post(f"{api_url}/api/v1/auth/token", json={
        "clinician_id": str(test_clinician_id),
        "password": "dev"
    })
    return response.json()["access_token"]
```

---

## Step 3: OTel Trace Verification

After a successful E2E run, verify the complete trace:

```bash
# Check OTel collector received spans
docker logs pcc-platform-otel-collector-1 2>&1 | grep "Span" | tail -20

# Verify trace completeness — should have spans for:
# intake.extract, intake.normalise, intake.validate
# triage.retrieve (with 3 children)
# diagnostics.retrieve, diagnostics.reflect_*, diagnostics.generate_*
# treatment.react_iteration.*
# hitl.submit, hitl.resume
# discharge.scheduler_run
# mcp.ehr.query, mcp.lab.*, mcp.pharmacy.*
```

---

## Phase 7 Checkpoint (Final)

- [ ] `docker compose build` succeeds for all images
- [ ] `docker compose up` starts all 9 services healthy
- [ ] Health endpoints respond on all 5 app services
- [ ] E2E test: symptom submission → triage completes
- [ ] E2E test: diagnostics produces IDA diagnosis
- [ ] E2E test: treatment plan generated with awaiting approval
- [ ] E2E test: approval resumes workflow, discharge plan created
- [ ] E2E test: scheduler updates risk scores
- [ ] E2E test: anomaly detection identifies seeded patients
- [ ] E2E test: escalation triggered on threshold crossing
- [ ] Complete OTel trace visible for full patient episode
- [ ] All 5 SQL analytics queries return in < 2 seconds
- [ ] `python -m pytest tests/` — all tests pass

---

## Overall Implementation Complete

When Phase 7 passes, the full platform is operational:

| Component | Status |
|---|---|
| PostgreSQL (14 tables, 1.7M rows) | ✅ Phase 1 |
| ChromaDB (14 guideline chunks) | ✅ Phase 1 |
| Shared config (settings, DB, Redis, ChromaDB) | ✅ Phase 2 |
| EHR MCP Server :8001 | ✅ Phase 3 |
| Lab MCP Server :8002 | ✅ Phase 3 |
| Pharmacy MCP Server :8003 | ✅ Phase 3 |
| Appointments MCP Server :8004 | ✅ Phase 3 |
| Intake Chain (LangChain) | ✅ Phase 4 |
| Triage Agent (Enterprise RAG) | ✅ Phase 4 |
| Diagnostics Agent (Self-RAG) | ✅ Phase 4 |
| Treatment Agent (Agentic RAG) | ✅ Phase 4 |
| HITL Mechanism | ✅ Phase 5 |
| LangGraph Workflow | ✅ Phase 5 |
| REST API + JWT Auth | ✅ Phase 5 |
| Post-Discharge Agent | ✅ Phase 6 |
| OTel Instrumentation | ✅ Phase 6 |
| Docker packaging | ✅ Phase 7 |
| E2E Integration Test | ✅ Phase 7 |
