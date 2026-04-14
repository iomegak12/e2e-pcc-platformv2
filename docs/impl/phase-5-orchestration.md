# Phase 5 — Orchestration Layer (HITL + Workflow + API)

**Status:** Not started
**Depends on:** Phase 4 (all agents built and tested)
**Produces:** LangGraph workflow, HITL mechanism, REST API gateway with JWT auth

---

## Overview

Wire all agents into a single LangGraph episode workflow. Add the HITL approval gate. Expose everything through a JWT-secured FastAPI REST API. This phase produces the core runnable system.

---

## Step 1: Human-in-the-Loop Mechanism

### Files

| File | Purpose |
|---|---|
| `orchestrator/hitl.py` | HITL interrupt node + approval logic |

### Contract

```python
async def submit_for_approval(
    episode_id: UUID,
    task_type: str,  # "diagnosis_confirmation" | "treatment_plan_approval" | "high_risk_escalation"
    plan_payload: dict,
    clinician_id: UUID | None = None
) -> UUID:
    """
    1. INSERT approval_events row (status='pending', plan_payload=JSONB)
    2. Serialize workflow state to Redis (key=episode:{task_id})
    3. PUBLISH to Redis channel 'hitl-notifications'
    4. Return approval task_id
    """

async def process_approval(
    task_id: UUID,
    clinician_id: UUID,
    action: str,  # "approved" | "rejected" | "modified"
    notes: str | None = None
) -> dict:
    """
    1. Validate JWT claims (clinician has ward access)
    2. UPDATE approval_events (status, clinician_id, decided_at, clinician_notes)
    3. INSERT audit_log entry
    4. Write resume signal to Redis
    5. Return {task_id, status, episode_id}
    """

async def check_escalation_timeouts() -> list[UUID]:
    """
    Query approval_events WHERE status='pending' AND submitted_at < now() - interval '24h'
    Escalate: re-publish notification with elevated urgency.
    72h: escalate to department head (second notification).
    Returns list of escalated task_ids.
    """
```

### HITL as LangGraph Interrupt Node

```python
def hitl_interrupt_node(state: EpisodeState) -> EpisodeState:
    """
    LangGraph node that:
      1. Calls submit_for_approval with the treatment plan
      2. Uses graph.interrupt() to pause the workflow
      3. On resume (from process_approval), reads approval_status
      4. If rejected: routes back to treatment agent
      5. If approved: routes to discharge_activation
    """
```

### Verification

```bash
python -c "
import asyncio
from orchestrator.hitl import submit_for_approval, process_approval

# Submit
task_id = asyncio.run(submit_for_approval(
    episode_id='test-episode-id',
    task_type='treatment_plan_approval',
    plan_payload={'treatment': 'iron sucrose 200mg IV'}
))
print(f'Task created: {task_id}')

# Verify in DB
# psql: SELECT * FROM approval_events WHERE approval_id = '<task_id>'
# Expected: status = 'pending'

# Approve
result = asyncio.run(process_approval(
    task_id=task_id,
    clinician_id='test-clinician-id',
    action='approved',
    notes='Plan looks good'
))
print(f'Approval result: {result}')

# Verify in DB
# psql: SELECT * FROM approval_events WHERE approval_id = '<task_id>'
# Expected: status = 'approved', decided_at populated
# psql: SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 1
# Expected: action_type = 'approval', actor_type = 'user'
"
```

---

## Step 2: LangGraph Workflow Orchestrator

### Files

| File | Purpose |
|---|---|
| `orchestrator/workflow.py` | Full episode graph |

### Contract

```python
class EpisodeState(TypedDict):
    patient_uuid: str
    episode_id: str
    intake_output: dict | None      # ClinicalEntity
    triage_output: dict | None      # TriageOutput
    diagnostics_output: dict | None # DiagnosticsOutput
    treatment_plan: dict | None     # TreatmentPlan
    approval_status: str | None     # "pending" | "approved" | "rejected" | "modified"
    discharge_plan_id: str | None

def build_episode_workflow() -> CompiledGraph:
    """
    LangGraph StateGraph with nodes:
      intake             — runs intake chain
      triage             — runs triage agent
      diagnostics        — runs diagnostics Self-RAG subgraph
      treatment          — runs treatment ReAct agent
      hitl_interrupt     — HITL approval gate
      discharge_activation — activates discharge plan
    
    Edges:
      START → intake → triage
      triage → hitl_interrupt         (if emergency urgency)
      triage → diagnostics            (otherwise)
      diagnostics → treatment
      treatment → hitl_interrupt
      hitl_interrupt → treatment      (if rejected)
      hitl_interrupt → discharge_activation (if approved)
      discharge_activation → END
    
    Checkpointer: Redis (config/redis_client)
    """

async def run_episode(
    patient_uuid: UUID,
    symptoms_text: str
) -> EpisodeState:
    """Start a new patient episode. Returns initial state after triage."""
```

### State Persistence

All state checkpointed to Redis after each node transition. Use LangGraph's built-in `MemorySaver` backed by Redis for serialisation.

Key pattern: `episode:{episode_id}:{node_name}`

### Verification

```bash
python -c "
import asyncio
from orchestrator.workflow import run_episode

state = asyncio.run(run_episode(
    patient_uuid='KNOWN_PATIENT_UUID',
    symptoms_text='Tired for 3 weeks, breathless on stairs, dizzy sometimes'
))
print(f'Episode: {state[\"episode_id\"]}')
print(f'Triage: {state[\"triage_output\"][\"urgency_level\"]}')
# Workflow will be paused at hitl_interrupt awaiting approval
print(f'Approval status: {state[\"approval_status\"]}')
"
```

Expected: Episode created, triage completed, diagnostic and treatment run, workflow paused at HITL with approval_status = "pending".

---

## Step 3: JWT Authentication

### Files

| File | Purpose |
|---|---|
| `orchestrator/auth.py` | JWT token issuance + validation |

### Contract

```python
def create_access_token(
    clinician_id: str,
    role: str,      # "patient" | "nurse" | "physician" | "specialist" | "administrator"
    site_id: str,
    ward: str
) -> str:
    """
    Create JWT with:
      sub: clinician_id
      role: role
      site_id: site_id
      ward: ward
      exp: now + 8 hours
    Signs with JWT_SECRET from settings.
    """

def verify_token(token: str) -> dict:
    """
    Verify JWT signature and expiry.
    Returns decoded payload.
    Raises HTTPException(401) on invalid/expired.
    """

def require_role(*roles: str) -> Callable:
    """FastAPI dependency that checks token role against allowed roles."""
```

### Verification

```bash
python -c "
from orchestrator.auth import create_access_token, verify_token
token = create_access_token('doc-001', 'physician', 'site_001', 'ward_A')
payload = verify_token(token)
print(f'Sub: {payload[\"sub\"]}, Role: {payload[\"role\"]}, Ward: {payload[\"ward\"]}')
"
```

Expected: `Sub: doc-001, Role: physician, Ward: ward_A`

---

## Step 4: REST API Gateway

### Files

| File | Purpose |
|---|---|
| `orchestrator/api.py` | FastAPI app with all endpoints |

### Endpoint Contracts

**POST /api/v1/auth/token**

```python
# Request: {"clinician_id": str, "password": str}
# Response: {"access_token": str, "token_type": "bearer", "expires_in": 28800}
# For dev: any known clinician_id with password "dev" works
```

**POST /api/v1/symptoms**

```python
# Request: {"patient_uuid": str, "symptoms_text": str}
# Auth: JWT required
# Response: {"episode_id": str, "triage_ref_id": str, "urgency_level": str}
# Triggers: intake → triage (async), returns after triage completes
```

**GET /api/v1/cases/{case_id}**

```python
# Auth: JWT required (physician, specialist, nurse)
# Response: Full EpisodeState as JSON
# Includes: intake_output, triage_output, diagnostics_output, treatment_plan, approval_status
```

**GET /api/v1/approvals/pending**

```python
# Auth: JWT required (physician, specialist)
# Filters by JWT ward claim
# Response: {"approvals": [{"task_id", "episode_id", "task_type", "submitted_at", "plan_summary"}]}
```

**POST /api/v1/approvals/{task_id}**

```python
# Request: {"action": "approved" | "rejected" | "modified", "notes": str | None}
# Auth: JWT required (physician, specialist)
# Response: {"task_id", "status", "episode_id"}
# Side effects: updates approval_events, writes audit_log, resumes workflow
```

**GET /api/v1/patients/{patient_id}/discharge-plan**

```python
# Auth: JWT required (physician, nurse)
# Response: {"plan_id", "plan_type", "status", "risk_score", "completion_percentage", "risk_score_updated_at"}
```

**GET /api/v1/analytics/kpis**

```python
# Auth: JWT required (administrator only)
# Response: {"readmission_30d": float, "readmission_60d": float, "readmission_90d": float, ...}
```

**GET /api/v1/health**

```python
# No auth
# Response: {"status": "healthy", "services": {"postgres": "up", "redis": "up", "chromadb": "up"}}
```

### Error Handling

All 401/403 responses write to `audit_log` with:
- `actor_type = "user"` or `"system"`
- `action_type = "auth_failure"`
- `details` includes endpoint, method, IP (if available)

### Verification

```bash
# Start API
uvicorn orchestrator.api:app --port 8000

# Health check
curl -s http://localhost:8000/api/v1/health | python -m json.tool

# Get token
TOKEN=$(curl -s http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"clinician_id": "KNOWN_CLINICIAN_ID", "password": "dev"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Submit symptoms
curl -s http://localhost:8000/api/v1/symptoms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"patient_uuid": "KNOWN_PATIENT_UUID", "symptoms_text": "Tired for 3 weeks, breathless on stairs"}' | python -m json.tool

# Check case
curl -s http://localhost:8000/api/v1/cases/EPISODE_ID \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# List pending approvals
curl -s http://localhost:8000/api/v1/approvals/pending \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Approve
curl -s http://localhost:8000/api/v1/approvals/TASK_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "approved", "notes": "Looks good"}' | python -m json.tool

# Check KPIs (need admin token)
ADMIN_TOKEN=$(curl -s http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"clinician_id": "ADMIN_ID", "password": "dev"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:8000/api/v1/analytics/kpis \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python -m json.tool
```

---

## Phase 5 Checkpoint

- [ ] HITL: submit_for_approval creates pending row in approval_events
- [ ] HITL: process_approval updates row, writes audit_log, sends resume signal
- [ ] HITL: 24h escalation timeout works
- [ ] Workflow: full episode runs intake → triage → diagnostics → treatment → HITL pause
- [ ] Workflow: approval resumes workflow to discharge_activation
- [ ] Workflow: rejection routes back to treatment agent
- [ ] Workflow: emergency urgency routes to immediate HITL
- [ ] State: all checkpoints persist to Redis, survives restart
- [ ] JWT: token issuance with role/site/ward claims
- [ ] JWT: verification rejects expired/invalid tokens
- [ ] API: all 7 endpoints + auth endpoint responding
- [ ] API: RBAC enforced (admin-only KPIs, ward-scoped approvals)
- [ ] API: 401/403 responses logged to audit_log
