# Phase 6 — Post-Discharge Agent & Observability

**Status:** Not started
**Depends on:** Phase 5 (orchestration layer running)
**Produces:** Post-discharge monitoring agent with scheduler, OTel instrumentation across all components

---

## Overview

Two parallel workstreams: (A) the Post-Discharge Agent that runs on a schedule and monitors active care plans using SQL analytics, and (B) OpenTelemetry instrumentation across every agent, MCP server, and orchestrator node.

---

## Part A: Post-Discharge Agent

### Files

| File | Purpose |
|---|---|
| `agents/discharge/schemas.py` | DischargeOutput, RiskScore models |
| `agents/discharge/queries.py` | 5 SQL analytics query implementations |
| `agents/discharge/agent.py` | Risk scoring logic |
| `agents/discharge/scheduler.py` | APScheduler 15-min loop |

### Schema Contract

```python
class RiskScore(BaseModel):
    patient_uuid: UUID
    plan_id: UUID
    cohort_component: float       # 0-100
    adherence_component: float    # 0-100
    anomaly_component: float      # 0-100
    checkin_component: float      # 0-100
    composite_score: float        # 0-100, weighted
    threshold_crossed: bool
    timestamp: datetime

class DischargeOutput(BaseModel):
    active_plans_processed: int
    risk_scores_updated: int
    escalations_triggered: int
    run_timestamp: datetime
```

### SQL Queries Contract

```python
# queries.py — 5 analytics patterns

def readmission_cohort_score(
    db: Session, patient_id: UUID, diagnosis_code: str
) -> float:
    """
    Query: historical 30-day readmission rate for patients with same diagnosis,
    segmented by age band (±4 years) and comorbidity count (±1).
    Returns: cohort readmission rate as 0-100 score.
    """

def medication_adherence_score(
    db: Session, patient_id: UUID
) -> float:
    """
    Query: pharmacy_events for this patient.
    Calculate: % of refills where gap_days > 3.
    Returns: 100 - (adherence_gap_percentage), so higher = better adherence.
    Flag: if any gap > 7 days, return max penalty score.
    """

def vital_anomaly_score(
    db: Session, patient_id: UUID, plan_id: UUID
) -> float:
    """
    Query: wearable_readings for this patient's discharge plan.
    Compare: last 3 readings vs 30-day baseline (mean + stddev).
    Returns: anomaly severity score 0-100. 
    Threshold: > 2 stddev from baseline = elevated score.
    """

def outcome_kpis(db: Session) -> dict:
    """
    Query: aggregate 30/60/90-day readmission rates.
    Segment by: ward, primary_diagnosis_code, clinician.
    Returns: {"readmission_30d": float, "readmission_60d": float, "readmission_90d": float, ...}
    """

def population_segmentation(db: Session) -> list[dict]:
    """
    Query: all active discharge plans with composite risk ranking.
    Returns: [{patient_uuid, plan_id, composite_score}] sorted descending.
    Used for outreach prioritisation.
    """
```

### Composite Risk Score

```python
def calculate_composite_risk(
    cohort: float, adherence: float, anomaly: float, checkin_days: int
) -> float:
    """
    Weights:
      0.4 * cohort_rate
      0.3 * (100 - adherence_score)  # invert: lower adherence = higher risk
      0.2 * anomaly_score
      0.1 * min(checkin_days * 10, 100)  # days since last check-in, capped
    
    Returns: composite 0-100
    """
```

### Scheduler Contract

```python
# scheduler.py

def create_discharge_scheduler() -> AsyncIOScheduler:
    """
    APScheduler with IntervalTrigger:
      interval: 15 minutes (dev), 6 hours (prod, controlled by ENVIRONMENT)
    
    Each run:
      1. Query discharge_plans WHERE status = 'active'
      2. For each plan:
         a. Run 5 SQL analytics queries
         b. Calculate composite risk score
         c. UPDATE discharge_plans SET risk_score = ..., risk_score_updated_at = now()
         d. If score > 65 AND previous_score <= 65: trigger HITL escalation
      3. Log run summary to OTel
    """

def start_scheduler() -> None:
    """Start the scheduler (called from orchestrator startup)."""
```

### Escalation Logic

```python
async def check_and_escalate(
    patient_uuid: UUID, plan_id: UUID, new_score: float, previous_score: float
) -> UUID | None:
    """
    If new_score > 65 AND previous_score <= 65:
      1. Create escalation via orchestrator.hitl.submit_for_approval
         task_type = "high_risk_escalation"
      2. Return escalation task_id
    
    If new_score > 80:
      Mark as critical in escalation payload
    
    Returns: task_id or None
    """
```

### Verification

```bash
# Test individual queries
python -c "
from config.database import get_engine
from agents.discharge.queries import readmission_cohort_score, medication_adherence_score, vital_anomaly_score
from sqlalchemy.orm import Session

# Get a known patient with discharge plan
# Run each query and verify results + timing
"

# Test scheduler (manual single run)
python -c "
import asyncio
from agents.discharge.agent import run_discharge_cycle

result = asyncio.run(run_discharge_cycle())
print(f'Plans processed: {result.active_plans_processed}')
print(f'Scores updated: {result.risk_scores_updated}')
print(f'Escalations: {result.escalations_triggered}')
"
```

**Anomaly detection validation:**
The 10% of Faker-seeded anomaly patients should trigger escalation by Day 20-22. Query:

```sql
SELECT dp.plan_id, dp.risk_score, dp.risk_score_updated_at,
       wr.anomaly_flag, wr.reading_date
FROM discharge_plans dp
JOIN wearable_readings wr ON wr.discharge_plan_id = dp.plan_id
WHERE wr.anomaly_flag = TRUE
ORDER BY wr.reading_date;
```

Expected: Anomaly patients have risk_score > 65 after day 20-22 readings are processed.

---

## Part B: OpenTelemetry Instrumentation

### Files

| File | Purpose |
|---|---|
| `config/telemetry.py` | OTel tracer setup, span helpers |

### Tracer Setup Contract

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def setup_telemetry(service_name: str) -> trace.Tracer:
    """
    Configure OTel tracer:
      - Service name per component (orchestrator, mcp-ehr, etc.)
      - OTLP gRPC exporter → localhost:4317
      - BatchSpanProcessor
      - W3C trace context propagation
    
    Returns: configured tracer for the service
    """

def get_tracer(service_name: str) -> trace.Tracer:
    """Lazy init — returns existing tracer or creates one."""
```

### Span Instrumentation Plan

Each component adds named spans at critical points:

**Intake Chain:**
```python
with tracer.start_as_current_span("intake.extract") as span:
    span.set_attribute("input_length", len(raw_text))
    # ... extraction logic
    span.set_attribute("entity_count", len(result.symptoms))
    span.set_attribute("confidence", result.extraction_confidence)
```

**Triage Agent:**
```python
with tracer.start_as_current_span("triage.retrieve") as parent_span:
    # 3 child spans — one per source
    with tracer.start_as_current_span("triage.retrieve.ehr"):
        ...
    with tracer.start_as_current_span("triage.retrieve.guidelines"):
        ...
    with tracer.start_as_current_span("triage.retrieve.drug_effects"):
        ...
```

**Diagnostics (Self-RAG):**
```python
# Per node: "diagnostics.retrieve", "diagnostics.reflect_relevance", etc.
# Attributes: iteration number, reflection pass/fail, doc count
```

**Treatment (ReAct):**
```python
# Per iteration: "treatment.react_iteration.{n}"
# Attributes: tool_name, input_summary (truncated), output_summary (truncated)
```

**HITL:**
```python
# "hitl.submit" — task_id, task_type
# "hitl.await" — started waiting
# "hitl.resume" — outcome (approved/rejected), wait_duration_seconds
```

**Discharge Scheduler:**
```python
# "discharge.scheduler_run" — active_plans, scores_updated, escalations
# "discharge.query.{name}" — query_name, execution_time_ms, result_count
```

**MCP Servers:**
```python
# "mcp.ehr.query", "mcp.lab.orders", etc.
# Attributes: patient_id, status_code, response_time_ms
```

### PHI Redaction

Update `config/otel-collector-config.yaml` to redact PHI fields:

```yaml
processors:
  attributes:
    actions:
      - key: patient_name
        action: update
        value: "[REDACTED]"
      - key: dob
        action: update
        value: "[REDACTED]"
      - key: free_text
        action: update
        value: "[REDACTED]"
```

Traces reference `episode_id` and `patient_uuid` only — never patient names or dates of birth.

### W3C Trace Context Propagation

All inter-service HTTP calls (agent → MCP server) include `traceparent` and `tracestate` headers. Use `opentelemetry-instrumentation-httpx` or manual context injection in httpx/requests calls.

A single root trace spans the entire patient episode from API request through all agents, MCP calls, HITL, and discharge scheduling.

### Verification

```bash
# After running a full episode (Phase 5 verification)
# Check OTel collector output
docker logs pcc-platform-otel-collector-1 | tail -20

# Or if exporting to file:
cat data/otel-traces/*.json | python -m json.tool | head -50
```

Expected: Complete trace with spans covering intake → triage (with 3 retrieval children) → diagnostics (6 nodes) → treatment (ReAct iterations) → HITL → discharge.

```bash
# Verify PHI redaction
# Search for any patient names in trace output
grep -ri "patient_name" data/otel-traces/ | grep -v "REDACTED"
# Expected: no results (all redacted)
```

---

## Phase 6 Checkpoint

- [ ] All 5 SQL analytics queries return correct results in < 2s
- [ ] Composite risk score calculated with correct weights (0.4/0.3/0.2/0.1)
- [ ] Scheduler runs every 15 min, processes all active plans
- [ ] Anomaly detection identifies seeded patients by Day 20-22
- [ ] Escalation triggers when risk_score crosses 65 threshold
- [ ] discharge_plans.risk_score and risk_score_updated_at get updated
- [ ] OTel tracer configured for all components
- [ ] Named spans present for every critical operation
- [ ] W3C trace context propagated across service boundaries
- [ ] PHI redacted in all exported traces
- [ ] Complete end-to-end trace visible for full patient episode
