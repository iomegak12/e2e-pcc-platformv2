# Phase 4 — Clinical AI Agents

**Status:** Not started
**Depends on:** Phase 3 (all MCP servers running and tested)
**Produces:** Intake chain, Triage agent, Diagnostics agent, Treatment agent

---

## Overview

Build the four clinical AI components in dependency order. Each agent is tested independently before connecting to the next. The intake chain is stateless LangChain; triage uses Enterprise RAG; diagnostics uses Self-RAG (LangGraph subgraph); treatment uses Agentic RAG (ReAct loop).

---

## Step 1: Intake Chain (LangChain)

### Files

| File | Purpose |
|---|---|
| `agents/intake/schemas.py` | ClinicalEntity Pydantic model |
| `agents/intake/chain.py` | 3-step LangChain chain |

### Schema Contract

```python
class Symptom(BaseModel):
    name: str
    duration_days: int | None
    severity: str  # "mild" | "moderate" | "severe"

class ReportedMedication(BaseModel):
    name: str
    indication: str | None

class ClinicalEntity(BaseModel):
    symptoms: list[Symptom]
    reported_negatives: list[str]
    reported_medications: list[ReportedMedication]
    free_text_summary: str
    extraction_confidence: float  # 0.0 - 1.0
```

### Chain Contract

```python
def create_intake_chain() -> RunnableSequence:
    """
    Returns a 3-step chain:
      1. extraction_chain — GPT-4o prompt → raw structured output
      2. normalisation_chain — map symptoms to SNOMED-CT terms (50-term lookup dict)
      3. validation_chain — schema check, confidence scoring, one retry on failure
    """

def run_intake(raw_text: str) -> ClinicalEntity:
    """Convenience: creates chain and invokes with raw symptom text."""
```

### SNOMED-CT Lookup

Hardcoded dict of 50 common symptom terms → SNOMED preferred terms. Examples:
- `"tired"` → `"fatigue"`
- `"short of breath"` → `"dyspnoea"`
- `"dizzy"` → `"dizziness"`

### Test Cases (5 edge cases)

| # | Input | Expected Output |
|---|---|---|
| 1 | "Tired for 3 weeks, breathless on stairs, dizzy sometimes" | 3 symptoms, duration_days=21, moderate severity |
| 2 | Empty string | Low confidence, empty symptoms list |
| 3 | "No chest pain, no fever, just mild headache" | 1 symptom + 2 reported_negatives |
| 4 | "Taking metformin for diabetes, now having stomach cramps" | 1 symptom + 1 reported_medication |
| 5 | Mixed languages / typos | Best-effort extraction with lower confidence |

### Verification

```bash
python -c "
from agents.intake.chain import run_intake
result = run_intake('Tired for 3 weeks, breathless on stairs, dizzy sometimes')
print(f'Symptoms: {len(result.symptoms)}')
print(f'Confidence: {result.extraction_confidence}')
for s in result.symptoms:
    print(f'  {s.name}: {s.duration_days}d, {s.severity}')
"
```

Expected: 3 symptoms with normalised names, confidence > 0.7.

```bash
python -m pytest tests/unit/test_intake_chain.py -v
```

Expected: 5/5 tests pass.

---

## Step 2: Triage Agent — Enterprise RAG

### Files

| File | Purpose |
|---|---|
| `agents/triage/schemas.py` | TriageOutput model |
| `agents/triage/retrieval.py` | Fan-out retrieval + re-ranking |
| `agents/triage/agent.py` | Urgency scoring agent |

### Schema Contract

```python
class TriageOutput(BaseModel):
    urgency_level: str  # "emergency" | "urgent" | "routine" | "self-care"
    urgency_rationale: str
    retrieved_context: list[dict]
    routing_decision: str  # "diagnostics" | "immediate_hitl" | "self_care_advice"
    triage_timestamp: datetime
```

### Retrieval Contract

```python
async def fan_out_retrieval(
    patient_uuid: UUID,
    clinical_entity: ClinicalEntity
) -> list[dict]:
    """
    Concurrent fan-out to 3 sources:
      1. EHR MCP (POST /query) — patient history
      2. ChromaDB guidelines — symptom-disease associations
      3. Drug side effects — from EHR medications + known side effect data
    
    Returns merged + re-ranked results.
    Re-ranking weights: recency (0.4) + authority (0.3) + similarity (0.3)
    """
```

### Agent Contract

```python
def create_triage_agent() -> Runnable:
    """
    GPT-4o with structured output prompt.
    System prompt includes caution-preference instruction.
    Fallback on error: urgency_level = "urgent".
    """

async def run_triage(
    patient_uuid: UUID,
    clinical_entity: ClinicalEntity
) -> TriageOutput:
    """Full triage: retrieval → scoring → output."""
```

### Audit Logging

Every triage event writes to `audit_log`:
- `actor_type = "agent"`, `actor_id = "triage_agent"`
- `action_type = "triage"`
- `details` JSONB includes urgency_level, patient_uuid, retrieval_source_count

### Test Cases (10)

| # | Scenario | Expected Urgency |
|---|---|---|
| 1 | Chest pain radiating to left arm | emergency |
| 2 | Anaphylaxis symptoms (swelling, throat closing) | emergency |
| 3 | Fatigue + breathlessness + dizziness (suspected anaemia) | urgent |
| 4 | Uncontrolled diabetes symptoms (polyuria, polydipsia) | urgent |
| 5 | Acute UTI symptoms (dysuria, frequency) | urgent |
| 6 | Mild fatigue, no other symptoms | routine |
| 7 | Seasonal allergy (sneezing, nasal congestion) | routine |
| 8 | Minor wound, no signs of infection | routine |
| 9 | Common cold (runny nose, mild sore throat) | self-care |
| 10 | Mild muscle soreness after exercise | self-care |

### Verification

```bash
python -c "
import asyncio
from agents.intake.chain import run_intake
from agents.triage.agent import run_triage

entity = run_intake('Tired for 3 weeks, breathless climbing stairs, occasional dizziness')
# Use a known patient_uuid from the DB
result = asyncio.run(run_triage('PATIENT_UUID_HERE', entity))
print(f'Urgency: {result.urgency_level}')
print(f'Rationale: {result.urgency_rationale[:100]}...')
print(f'Routing: {result.routing_decision}')
"
```

Expected: urgency = "urgent", routing = "diagnostics".

```bash
python -m pytest tests/unit/test_triage_agent.py -v
```

Expected: 10/10 tests pass.

---

## Step 3: Diagnostics Agent — Self-RAG

### Files

| File | Purpose |
|---|---|
| `agents/diagnostics/schemas.py` | DiagnosticsOutput, DiagnosticsState |
| `agents/diagnostics/agent.py` | Self-RAG LangGraph subgraph |

### Schema Contract

```python
class DiagnosisCandidate(BaseModel):
    icd10: str
    name: str
    confidence: float
    citations: list[str]

class DiagnosticsOutput(BaseModel):
    primary_diagnosis: DiagnosisCandidate
    differential_diagnoses: list[DiagnosisCandidate]  # max 3
    pending_lab_orders: list[dict]
    self_rag_iterations: int
    escalate_to_human: bool
    timestamp: datetime

class DiagnosticsState(TypedDict):
    triage_packet: TriageOutput
    patient_uuid: str
    retrieved_docs: list[dict]
    draft_hypothesis: str
    reflection_scores: dict  # {relevance: float, support: float, utility: float}
    iterations: int
    lab_orders: list[dict]
    final_output: DiagnosticsOutput | None
```

### LangGraph Subgraph Contract

```python
def build_diagnostics_graph() -> CompiledGraph:
    """
    6-node LangGraph subgraph:
    
    Nodes:
      retrieve         — query ChromaDB + lab history
      reflect_relevance — score each doc 0-1, filter below 0.6
      generate_draft    — draft hypothesis from filtered docs
      reflect_support   — check claims are grounded in evidence
      reflect_utility   — assess if evidence is sufficient
      request_labs      — submit lab orders via Lab MCP, checkpoint to Redis
      generate_final    — produce DiagnosticsOutput with confidence
    
    Edges:
      retrieve → reflect_relevance → generate_draft → reflect_support → reflect_utility
      reflect_utility → generate_final    (if sufficient OR iterations >= 3)
      reflect_utility → request_labs       (if insufficient)
      request_labs → retrieve              (when results available)
    
    Config:
      max_iterations: 3
      confidence_threshold: 70 (below → escalate_to_human = True)
    """

async def run_diagnostics(
    patient_uuid: UUID,
    triage_output: TriageOutput
) -> DiagnosticsOutput:
    """Execute the Self-RAG subgraph. Handles lab waiting via Redis checkpoint."""
```

### Confidence Calculation

```
confidence = (mean_relevance_score * 0.8) + (20 if sufficient_evidence else 0)
```

Where `mean_relevance_score` is calculated from the reflect_relevance node on a 0-100 scale.

### Lab Waiting Mechanism

1. `request_labs` node calls Lab MCP POST /orders
2. State checkpointed to Redis: `episode:{task_id}`
3. Background task polls Lab MCP GET /results every 5 minutes
4. When results available, write resume event to Redis
5. Subgraph resumes at `retrieve` node with new lab data in scope

### Test Cases (4)

| # | Scenario | Expected Behaviour |
|---|---|---|
| 1 | Clear IDA (Hb 9.2, MCV 72, ferritin 6) | 1 iteration, confidence > 85, IDA diagnosis |
| 2 | Broad initial results (fatigue only) | 2+ iterations, query refinement |
| 3 | Insufficient evidence, need labs | request_labs triggered, resumes after results |
| 4 | Ambiguous presentation | 3 iterations, confidence < 70, escalate_to_human = True |

### Verification

```bash
python -c "
import asyncio
from agents.diagnostics.agent import run_diagnostics
# Pass a TriageOutput from Step 2
result = asyncio.run(run_diagnostics('PATIENT_UUID', triage_output))
print(f'Diagnosis: {result.primary_diagnosis.name}')
print(f'Confidence: {result.primary_diagnosis.confidence}')
print(f'Iterations: {result.self_rag_iterations}')
print(f'Escalate: {result.escalate_to_human}')
"
```

Expected (clear IDA case): IDA diagnosis, confidence > 85, 1-2 iterations, escalate = False.

---

## Step 4: Treatment Agent — Agentic RAG (ReAct)

### Files

| File | Purpose |
|---|---|
| `agents/treatment/schemas.py` | TreatmentPlan model |
| `agents/treatment/tools.py` | 5 tool definitions |
| `agents/treatment/agent.py` | ReAct loop |

### Schema Contract

```python
class TreatmentRecommendation(BaseModel):
    treatment: str
    dose: str
    route: str
    frequency: str
    duration: str
    citation: str
    rationale: str

class RejectedAlternative(BaseModel):
    name: str
    reason: str

class TreatmentPlan(BaseModel):
    primary_recommendation: TreatmentRecommendation
    contraindications_checked: list[str]
    cause_investigation: list[str]
    alternatives_rejected: list[RejectedAlternative]
    monitoring_schedule: list[dict]
    confidence_score: float
    tool_call_count: int
    awaiting_human_approval: bool  # always True
```

### Tools Contract

```python
# tools.py — 5 tools available to the ReAct agent

def search_clinical_guidelines(query: str) -> list[dict]:
    """ChromaDB query — returns top 6 chunks."""

def get_patient_comorbidities(patient_uuid: str) -> list[dict]:
    """EHR MCP call — returns conditions list."""

def check_drug_interactions(drug_list: list[str]) -> list[dict]:
    """Pharmacy MCP POST /interactions."""

def check_formulary(drug_name: str, site_id: str) -> dict:
    """Pharmacy MCP POST /formulary."""

def request_investigation(investigation_name: str) -> dict:
    """Records investigation in agent state (e.g., colonoscopy referral)."""
```

### Agent Contract

```python
def build_treatment_agent() -> CompiledGraph:
    """
    ReAct loop implemented as LangGraph:
    
    Loop:
      1. reason — assess current knowledge vs patient context
      2. select_tool — choose next tool from 5 available
      3. execute — call tool via MCP server
      4. update — incorporate result into knowledge state
      5. decide — continue (loop) or conclude (exit)
    
    Config:
      max_tool_calls: 8
      Force-exit at max with lower confidence flag
    
    Exit produces synthesis step → TreatmentPlan
    """

async def run_treatment(
    patient_uuid: UUID,
    diagnostics_output: DiagnosticsOutput
) -> TreatmentPlan:
    """Execute the ReAct treatment planning loop."""
```

### Key Behaviour: Mid-Reasoning Pivot

The critical test is IDA + CKD:
1. Agent retrieves oral iron guidelines (tool 1: search_clinical_guidelines)
2. Agent discovers CKD stage 3 via EHR (tool 2: get_patient_comorbidities)
3. Agent **pivots** — queries IV iron protocols instead of continuing oral iron
4. Agent checks IV iron interactions (tool 3)
5. Agent checks IV iron formulary (tool 4)
6. Agent requests colonoscopy investigation (tool 5)
7. Synthesis: IV iron sucrose treatment plan with CKD rationale

If the agent does NOT pivot after discovering CKD, revise the system prompt to emphasize comorbidity-driven replanning.

### Test Cases (4)

| # | Scenario | Expected Behaviour |
|---|---|---|
| 1 | IDA + CKD | Oral→IV iron pivot, 5-7 tool calls, colonoscopy referral |
| 2 | Simple diabetes | Metformin recommendation, 3-4 tool calls |
| 3 | Drug interaction detected | Alternative drug selected, interaction documented |
| 4 | Drug not in formulary | Alternative formulation or drug, formulary check documented |

### Verification

```bash
python -c "
import asyncio
from agents.treatment.agent import run_treatment
# Pass DiagnosticsOutput with IDA diagnosis for a patient with CKD
result = asyncio.run(run_treatment('PATIENT_UUID', diagnostics_output))
print(f'Treatment: {result.primary_recommendation.treatment}')
print(f'Route: {result.primary_recommendation.route}')
print(f'Tool calls: {result.tool_call_count}')
print(f'Alternatives rejected:')
for alt in result.alternatives_rejected:
    print(f'  {alt.name}: {alt.reason}')
"
```

Expected (IDA+CKD): Treatment = "iron sucrose", route = "IV", oral iron in rejected alternatives with CKD reason.

---

## Phase 4 Checkpoint

- [ ] Intake chain produces valid ClinicalEntity for all 5 edge cases
- [ ] Triage agent scores 10 test cases with clinically appropriate urgency
- [ ] Diagnostics Self-RAG completes in ≤ 3 iterations for clear IDA case
- [ ] Diagnostics requests labs when evidence is insufficient
- [ ] Diagnostics escalates (escalate_to_human=True) when confidence < 70
- [ ] Treatment ReAct demonstrates oral→IV iron pivot for IDA+CKD
- [ ] Treatment max 8 tool calls enforced
- [ ] All agents use shared config/database/chromadb from Phase 2
- [ ] All agents write to audit_log
