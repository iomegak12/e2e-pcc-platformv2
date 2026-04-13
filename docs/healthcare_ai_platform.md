# AI-Powered Patient Care Coordination Platform
### Enterprise Use Case — Business & Technical Reference Document

**Version:** 1.0  
**Audience:** Business Stakeholders · Solution Architects · Engineering Teams  
**Industry:** Healthcare  
**Status:** Proposal / Pre-Engagement

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Problem We Are Solving](#2-the-problem-we-are-solving)
3. [The Solution — Platform Overview](#3-the-solution--platform-overview)
4. [Patient Journey — End to End](#4-patient-journey--end-to-end)
5. [Platform Architecture — All Layers](#5-platform-architecture--all-layers)
6. [Agent Deep Dives](#6-agent-deep-dives)
   - 6.1 [Symptom Triage Agent — Enterprise RAG](#61-symptom-triage-agent--enterprise-rag)
   - 6.2 [Diagnostics Agent — Self-RAG](#62-diagnostics-agent--self-rag)
   - 6.3 [Treatment Planning Agent — Agentic RAG](#63-treatment-planning-agent--agentic-rag)
   - 6.4 [Post-Discharge Agent — SQL Analytics](#64-post-discharge-agent--sql-analytics)
7. [Technology Stack — Topic Mapping](#7-technology-stack--topic-mapping)
8. [Cross-Cutting Concerns](#8-cross-cutting-concerns)
   - 8.1 [Human-in-the-Loop](#81-human-in-the-loop)
   - 8.2 [Durability and State Management](#82-durability-and-state-management)
   - 8.3 [Authentication and Authorization](#83-authentication-and-authorization)
   - 8.4 [Observability — Logging, Metrics, and Traces](#84-observability--logging-metrics-and-traces)
   - 8.5 [Evaluation and Testing](#85-evaluation-and-testing)
9. [UI Layer](#9-ui-layer)
10. [Business Value and ROI](#10-business-value-and-roi)
11. [Compliance and Risk Considerations](#11-compliance-and-risk-considerations)
12. [Implementation Roadmap](#12-implementation-roadmap)
13. [Key Demo Scenarios](#13-key-demo-scenarios)

---

## 1. Executive Summary

This document describes an **AI-Powered Patient Care Coordination Platform** — an enterprise-grade, multi-agent AI system that manages the complete patient care journey from initial symptom intake through diagnosis support, personalised treatment planning, and post-discharge follow-up monitoring.

The platform is designed to demonstrate, in a single cohesive healthcare use case, how modern AI engineering patterns — including multi-agent orchestration, Retrieval-Augmented Generation (RAG) in three distinct forms, MCP-based tool integration, SQL analytics, and Human-in-the-Loop governance — can be applied to one of the most demanding, regulated, and impactful industries in the world.

**What the platform does in one sentence:** When a patient reports symptoms, AI agents coordinate to investigate, validate, plan, and monitor their care — with clinicians firmly in control of every critical decision.

**Why healthcare is the right demo domain:**
- High stakes naturally justify Human-in-the-Loop — no AI executes without clinical approval
- Complex, multi-step workflows justify multi-agent architecture
- Rich, regulated data (EHR, labs, guidelines) justifies Enterprise RAG
- Long-running care journeys (days to months) justify Durability and State Management
- HIPAA compliance requirements justify Authentication, Authorization, Audit Logging, and OTLP observability
- Measurable outcomes (readmission rates, time-to-diagnosis) justify SQL Analytics and Evaluation

---

## 2. The Problem We Are Solving

### 2.1 Business Problem

Healthcare systems worldwide face a converging set of pressures:

| Problem | Scale |
|---|---|
| Clinician burnout from administrative load | 50%+ of physician time spent on documentation, not patients |
| Preventable hospital readmissions | ~$26B annual cost in the US alone |
| Delayed diagnoses from fragmented data | Patient history spread across EHR, labs, pharmacy, wearables |
| Inconsistent guideline adherence | Treatment variation across clinicians and sites |
| Post-discharge patient drop-off | 40–60% of patients do not complete follow-up care plans |

### 2.2 What Clinicians Actually Need

Clinicians do not want AI to replace their judgment. They want AI to handle the cognitive load of **information gathering, pattern matching, and monitoring** — so that by the time a decision reaches them, the evidence is already synthesised, the options are ranked, and the reasoning is transparent.

The platform is designed around this principle: **the AI does the legwork, the clinician makes the call.**

### 2.3 What the Technology Demonstrates

From an engineering perspective, this use case surfaces real enterprise challenges that any large organisation faces when deploying AI at scale:

- How do you coordinate multiple AI agents without them stepping on each other?
- How do you ensure AI retrieves the right clinical evidence — not just any evidence?
- How do you keep humans in control without creating bottlenecks?
- How do you maintain state across a care journey that spans weeks or months?
- How do you audit every AI decision for regulatory compliance?
- How do you test AI agents that make medical recommendations?

Every one of these challenges maps directly to a technology topic in the stack.

---

## 3. The Solution — Platform Overview

### 3.1 What the Platform Consists Of

The platform is composed of four layers:

**Interface Layer** — Three surfaces where humans interact with the system:
- A React Native mobile app where patients file symptoms and receive follow-up prompts
- A React Web dashboard where clinicians review AI recommendations and approve care decisions
- An Office 365 Copilot Agent embedded in Microsoft Teams where care teams collaborate and receive escalation alerts

**Orchestration Layer** — The coordination engine:
- LangChain chains handle the structured intake pipeline
- LangGraph and Azure AI Foundry coordinate the multi-agent workflow
- A Human-in-the-Loop mechanism gates all critical clinical decisions
- A REST API gateway with OAuth2 and RBAC exposes the orchestrator to external systems

**Specialist Agent Layer** — Four clinical AI agents, each with a distinct reasoning pattern:
- Symptom Triage Agent (Enterprise RAG)
- Diagnostics Agent (Self-RAG)
- Treatment Planning Agent (Agentic RAG)
- Post-Discharge Follow-Up Agent (SQL Analytics)

**Data and Tools Layer** — The knowledge and system foundations:
- Clinical knowledge vector store (guidelines, protocols, drug references)
- EHR and pharmacy REST APIs accessed via MCP servers
- SQL database containing patient records, outcomes, and KPIs
- State store providing durable, resumable workflow persistence

**Cross-Cutting Layer** — Applied to every agent and every interaction:
- OTLP-based observability (logs, metrics, distributed traces)
- Evaluation and safety testing framework
- Durability and state management for long-running workflows

### 3.2 The Core Architectural Principle

Every agent operates on the same pattern: **Retrieve → Reason → Reflect → Act → Await Human Approval**. No agent takes a clinically consequential action autonomously. The AI's role is always to prepare the best possible recommendation, with full reasoning transparency, and present it to a clinician for the final decision.

---

## 4. Patient Journey — End to End

This section describes the complete patient experience and the AI orchestration happening behind it.

### Step 1 — Symptom Intake (Patient, Mobile App)

A 52-year-old female patient opens the mobile app and reports: fatigue for 3 weeks, shortness of breath on exertion, occasional dizziness. She fills in a structured symptom form augmented by free-text description.

The mobile app sends the structured payload to the Orchestration Layer via the REST API gateway. The OAuth2 token in the request carries her patient ID and the requesting clinician's practice ID.

### Step 2 — Triage (Symptom Triage Agent)

The Symptom Triage Agent receives the payload. It runs the LangChain intake chain to normalise and extract clinical entities (symptom names, duration, severity, relevant negatives). It then fires an Enterprise RAG retrieval — pulling the patient's EHR history from the hospital system via MCP, querying the clinical guidelines vector store for symptom-disease associations, and cross-referencing the drug database for any medication side effects that could explain the symptoms.

After retrieval, the agent scores urgency. In this case: fatigue + dyspnoea + dizziness in a post-menopausal female → moderate urgency. Routine emergency fast-track is not triggered. The case is routed to the Diagnostics Agent.

**LangGraph state checkpoint created.** The triage result, retrieved documents, and urgency score are persisted to the state store.

### Step 3 — Diagnostics (Diagnostics Agent, Self-RAG)

The Diagnostics Agent receives the triage output. It begins a Self-RAG loop: retrieve clinical evidence → reflect on relevance → generate a draft hypothesis → reflect on whether the hypothesis is actually supported by the evidence → reflect on whether enough evidence exists to conclude.

Initial retrieval for "fatigue, dyspnoea" returns broad results including cardiac, pulmonary, and haematological differentials. The relevance reflection narrows the query — the patient's demographic and symptom cluster points toward haematological causes. A second retrieval targets anaemia differentials specifically.

The agent requests lab orders via the MCP pharmacy/lab tool: full blood count, metabolic panel, ferritin, B12, folate. The utility reflection determined that without these values, no confident differential is possible.

Lab results return: Hb 9.2 g/dL, MCV 72 fL, ferritin 6 ng/mL. Self-RAG loop reruns with the new data. Confidence rises to 91%. Diagnosis: severe iron deficiency anaemia (IDA).

The Diagnostics Agent hands the confirmed diagnosis, confidence score, full reasoning chain, and cited evidence to the Treatment Planning Agent.

### Step 4 — Treatment Planning (Treatment Planning Agent, Agentic RAG)

The Treatment Planning Agent receives the confirmed diagnosis and begins Agentic RAG — a multi-step autonomous reasoning process that dynamically decides which sources to query, in what order, based on what it learns at each step.

First retrieval: NICE CG39 and BSH iron deficiency anaemia treatment guidelines, plus oral iron dosing options. Second retrieval (triggered after reading the patient's EHR and finding CKD stage 3): IV iron protocols, since oral iron absorption is impaired in renal disease. Third retrieval: drug interaction checker for IV iron against the patient's ACE inhibitor and metformin. Fourth retrieval: hospital formulary confirmation that IV iron sucrose is stocked at the patient's care site.

The agent produces a structured treatment plan:
- IV iron sucrose 200mg, 3 infusions, fortnightly
- Nephrology co-management recommended
- Colonoscopy referral to investigate GI bleeding as underlying cause
- Alternatives considered: oral iron (rejected — CKD), erythropoietin (rejected — threshold not met)
- Full guideline citations, confidence score: 88%

The plan is forwarded to the Human-in-the-Loop mechanism. A notification fires to the responsible clinician via the O365 Copilot Agent in Microsoft Teams.

### Step 5 — Clinical Approval (Human-in-the-Loop, Clinician Web Dashboard)

The clinician opens the React Web dashboard. They see the treatment plan with the full Agentic RAG reasoning chain expanded — every tool call the agent made, every document it retrieved, and why each alternative was rejected. They review, add a note, and click Approve.

The approval event is written to the OTLP audit log with the clinician's identity, timestamp, and the plan version they approved.

LangGraph receives the approval event and transitions the workflow to the Post-Discharge Agent.

### Step 6 — Post-Discharge Monitoring (Post-Discharge Agent, SQL Analytics)

Following the infusions, the patient is discharged. The Post-Discharge Agent activates a 90-day care plan:

- Day 3, 7, 14: Mobile app check-ins asking about energy levels, dizziness, and medication adherence
- Daily: SQL analytics queries running readmission risk cohort scoring against the historical patient population
- Continuous: Wearable data ingested and compared against the patient's own baseline (SQL anomaly detection)
- Week 6: Ferritin recheck reminder issued via MCP appointment booking tool

On Day 22, the SQL anomaly detection query fires — the patient's reported fatigue score has risen, not fallen as expected. The risk rescore crosses the threshold. The Post-Discharge Agent escalates to Human-in-the-Loop. The clinician is alerted in Teams. A phone consultation is booked within 24 hours.

---

## 5. Platform Architecture — All Layers

### 5.1 Layer Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│  INTERFACE LAYER                                                 │
│  React Native Mobile  │  React Web Dashboard  │  O365 Copilot   │
└──────────────────────────────┬───────────────────────────────────┘
                               │ REST API (OAuth2 / RBAC)
┌──────────────────────────────▼───────────────────────────────────┐
│  ORCHESTRATION LAYER                                             │
│  LangChain Chains  │  LangGraph + Azure Foundry  │  HITL Gate   │
└───────┬──────────────────────┬──────────────────────┬────────────┘
        │                      │                      │
┌───────▼──────┐  ┌────────────▼──────┐  ┌───────────▼──────────┐  ┌──────────────────┐
│  Symptom     │  │  Diagnostics      │  │  Treatment Planning  │  │  Post-Discharge  │
│  Triage      │  │  Agent            │  │  Agent               │  │  Agent           │
│  Agent       │  │                   │  │                      │  │                  │
│  Enterprise  │  │  Self-RAG         │  │  Agentic RAG         │  │  SQL Analytics   │
│  RAG         │  │                   │  │                      │  │                  │
└───────┬──────┘  └────────────┬──────┘  └───────────┬──────────┘  └──────┬───────────┘
        └─────────────┬────────┘                      └──────────────┬─────┘
                      │                                              │
┌─────────────────────▼──────────────────────────────────────────── ▼──────┐
│  DATA AND TOOLS LAYER  (MCP Servers)                                      │
│  Clinical Vector Store │ EHR/Lab/Pharmacy APIs │ SQL DB │ State Store     │
└───────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Data Flow Summary

| From | To | Payload |
|---|---|---|
| Mobile app | Orchestrator REST API | Structured symptom payload + OAuth2 token |
| Orchestrator | Symptom Triage Agent | Normalised clinical entities + patient ID |
| Triage Agent | MCP / EHR | Patient record query |
| Triage Agent | Vector Store | Symptom-disease guideline retrieval |
| Triage Agent | Diagnostics Agent | Urgency score + triage summary |
| Diagnostics Agent | MCP / Lab System | Lab order request |
| Diagnostics Agent | Treatment Planning Agent | Confirmed diagnosis + confidence + evidence chain |
| Treatment Planning Agent | MCP / Formulary | Drug availability check |
| Treatment Planning Agent | Human-in-the-Loop | Structured care plan + reasoning |
| Clinician (web UI) | Orchestrator | Approval event + clinician ID |
| Post-Discharge Agent | SQL Database | Risk cohort queries, anomaly detection |
| Post-Discharge Agent | Human-in-the-Loop | Escalation alert when threshold breached |

---

## 6. Agent Deep Dives

### 6.1 Symptom Triage Agent — Enterprise RAG

#### What it does

The Symptom Triage Agent is the platform's entry point. It receives raw patient symptom input and produces a structured triage decision: urgency level, a summary of relevant clinical context, and a routing decision to the appropriate next agent.

#### Why Enterprise RAG

Standard RAG retrieves from a single vector store and generates. Enterprise RAG does significantly more:

| Capability | Standard RAG | Enterprise RAG |
|---|---|---|
| Retrieval sources | One vector store | Multi-source fan-out (EHR + vector store + drug DB) |
| Access control | None | RBAC enforced at query time — pre-LLM |
| Audit trail | None | Every retrieval call logged with query, results, user role |
| Chunking strategy | Generic | Tuned per source type (clinical notes vs guidelines vs drug monographs) |
| Freshness | Static | Freshness-aware — recent labs override older guidelines |

#### Retrieval sources

1. **Patient EHR** — via MCP tool call to the hospital EHR system. Returns: past diagnoses, current medications, allergies, recent visits, lab history.
2. **Clinical guidelines vector store** — WHO protocols, NICE guidelines, hospital-specific pathways, symptom-disease association tables.
3. **Drug and allergy database** — medication side effects that could explain symptoms, contraindication flags.

#### Output

A triage packet containing: normalised symptom list, relevant patient history excerpts, urgency score (emergency / urgent / routine / self-care), and a routing decision with rationale.

---

### 6.2 Diagnostics Agent — Self-RAG

#### What it does

The Diagnostics Agent takes a triage packet and attempts to produce a confirmed differential diagnosis with a confidence score. It orders additional investigations (lab tests, imaging) when the evidence is insufficient to conclude.

#### Why Self-RAG

Self-RAG adds metacognition — the agent evaluates the quality of its own retrieval and generation before proceeding. This is critical in diagnostics, where an underconfident or overconfident output has direct patient safety implications.

#### The three reflection checkpoints

**Checkpoint 1 — Relevance:** "Is what I retrieved actually relevant to this patient's specific presentation?" If the retrieval set is too broad (e.g. returning normocytic anaemia guidelines when MCV = 72 indicates microcytic), the agent reformulates the query with tighter constraints and retries.

**Checkpoint 2 — Support:** "Is my draft hypothesis actually grounded in the retrieved evidence?" If the draft diagnosis is making claims that go beyond what the retrieved documents support, the agent either softens its language or retrieves confirmatory evidence before proceeding.

**Checkpoint 3 — Utility:** "Do I have enough evidence to produce an actionable diagnostic conclusion, or do I need more data?" If the differential cannot be narrowed without additional lab results, the agent explicitly requests those tests via MCP rather than guessing.

#### The clinical significance

Standard RAG would retrieve once, generate a diagnosis, and move on — potentially producing a confident-sounding output based on insufficient evidence. Self-RAG introduces the concept of **earned confidence**: the agent's output confidence score is a meaningful signal because the agent has actively evaluated whether its evidence supports its conclusion.

#### Output

A structured diagnostic report containing: primary diagnosis, confidence score, ranked differentials, evidence citations per differential, any pending lab orders, and a flag to the Treatment Planning Agent or to Human-in-the-Loop if confidence is below a clinical threshold.

---

### 6.3 Treatment Planning Agent — Agentic RAG

#### What it does

The Treatment Planning Agent receives a confirmed diagnosis and produces a personalised, evidence-based treatment plan that accounts for the patient's specific comorbidities, medications, allergies, site formulary, and the latest clinical guidelines — all simultaneously.

#### Why Agentic RAG

Agentic RAG differs from both Enterprise RAG and Self-RAG in one fundamental way: the agent **autonomously plans and replans its own retrieval strategy** based on what it learns at each step. It does not execute a fixed retrieval plan. It reads the results of each tool call and decides what to query next.

| RAG Pattern | Retrieval Strategy | Self-Evaluation | Mid-Reasoning Pivot |
|---|---|---|---|
| Enterprise RAG | Fixed, multi-source fan-out | None | No |
| Self-RAG | Fixed, with retry on failure | Relevance + support + utility | No — retries same strategy |
| Agentic RAG | Dynamically planned per step | Implicit in reasoning | Yes — changes question based on findings |

#### The multi-step tool call sequence

A typical Agentic RAG run for a treatment planning task might execute:

1. **Guideline retrieval** — first-line treatment options for the confirmed diagnosis
2. **EHR re-query** — patient's comorbidities, active medications, relevant history
3. **Replan** — based on what was found (e.g. CKD stage 3 discovered), the agent changes the treatment question from "what oral iron is best?" to "what IV iron protocol applies here?"
4. **Interaction checker** — drug-drug interaction validation for the new treatment option
5. **Formulary check** — pharmacy API to confirm the selected drug is stocked at the patient's care site
6. **Secondary guideline retrieval** — cause investigation protocol (e.g. colonoscopy for GI bleeding as underlying IDA cause)

#### The output structure

The care plan handed to the clinician for Human-in-the-Loop approval contains:

- **Confirmed diagnosis** with confidence score
- **Recommended treatment** with specific drug, dose, route, frequency, and duration — with guideline citation for each choice
- **Contraindications checked** — explicit list of what was verified and the result
- **Cause investigation steps** — autonomously initiated by the agent where guidelines require it
- **Alternatives considered and rejected** — what was evaluated and why it was excluded, with guideline references
- **Monitoring schedule** — follow-up labs, appointments, thresholds for escalation

This structure is critical for clinician trust: the plan is not a black-box recommendation, it is a transparent reasoning artefact that a clinician can review, interrogate, and annotate before approving.

---

### 6.4 Post-Discharge Agent — SQL Analytics

#### What it does

The Post-Discharge Agent activates when a patient is discharged with an active care plan. It runs autonomously for the duration of the care plan (typically 30 to 90 days), continuously monitoring the patient, running population-level analytics to contextualise their risk, and escalating to Human-in-the-Loop when thresholds are breached.

#### Why this agent matters for the business case

Preventable readmissions are one of the highest-cost, highest-volume problems in healthcare. A patient who is discharged with IDA but does not complete their iron infusion course, or whose underlying GI bleed is not detected, is likely to deteriorate and readmit within 30 days. The Post-Discharge Agent is explicitly designed to intercept that trajectory.

#### The SQL analytics patterns

The agent runs five distinct SQL query patterns against the clinical database:

**Pattern 1 — Readmission risk cohort scoring**

Queries the historical patient population to find all patients discharged with the same primary diagnosis in the past 12 months. Calculates the 30-day readmission rate for that cohort, segmented by age band, comorbidity count, and discharge Hb level. Assigns the current patient a risk score based on where their profile sits in the cohort distribution.

```sql
-- Illustrative example
SELECT
  AVG(CASE WHEN readmitted_within_30d = TRUE THEN 1.0 ELSE 0.0 END) AS cohort_readmit_rate,
  AVG(discharge_hb) AS avg_discharge_hb
FROM patient_admissions
WHERE primary_diagnosis_code = 'D50.9'     -- IDA
  AND discharge_date >= DATEADD(month, -12, GETDATE())
  AND age_at_discharge BETWEEN 48 AND 56
  AND comorbidity_count BETWEEN 2 AND 4;
```

**Pattern 2 — Medication adherence drop-off detection**

Compares the patient's last pharmacy refill event against the prescribed medication schedule. If the gap between the expected refill date and the actual refill date exceeds 3 days, a flag is raised and a mobile check-in is triggered.

**Pattern 3 — Vital sign anomaly detection**

Compares incoming wearable data (heart rate, SpO2, blood pressure) against the patient's own 30-day baseline. Uses a standard deviation threshold to identify readings that are statistically unusual for this specific patient — not just outside population reference ranges.

**Pattern 4 — Outcome KPI dashboard**

Aggregates 30, 60, and 90-day readmission rates across the entire post-discharge patient cohort, broken down by ward, primary diagnosis, attending clinician, and insurance payer. This feeds the React Web dashboard for hospital leadership reporting and drives the Evaluation and Testing framework.

**Pattern 5 — Population segmentation for outreach prioritisation**

Scores and ranks all currently active post-discharge patients by a composite risk index (diagnosis severity × adherence score × days since last check-in × cohort readmit rate). The agent uses this ranking to prioritise which patients to contact first each day when outreach capacity is limited.

#### The Durability connection

A 90-day care plan cannot be held in memory. The Post-Discharge Agent checkpoints its state — current risk score, last check-in result, pending lab orders, days remaining on care plan — to the durable state store after every significant event. If the system restarts, the agent resumes from the last checkpoint. If the patient goes offline for two weeks and then responds to a check-in, the agent picks up exactly where the care plan left off.

---

## 7. Technology Stack — Topic Mapping

This section maps every technology topic to its specific role in the healthcare use case.

| Topic | Where It Lives | Healthcare Role |
|---|---|---|
| **LangChain Chains** | Orchestration Layer | Structures the symptom intake pipeline — normalises input, extracts clinical entities, routes to triage agent |
| **Enterprise RAG** | Symptom Triage Agent | Multi-source retrieval across EHR, clinical guidelines vector store, and drug DB — with RBAC access control |
| **Self-RAG** | Diagnostics Agent | Three-checkpoint reflection loop ensures diagnostic hypotheses are grounded in evidence before acting |
| **Agentic RAG** | Treatment Planning Agent | Dynamically plans and replans retrieval strategy based on patient-specific findings discovered mid-reasoning |
| **MCP Servers** | Data and Tools Layer | Exposes EHR, pharmacy, lab system, formulary, and appointment booking as structured tools all agents can call |
| **REST APIs** | Orchestration Layer | OAuth2-secured API gateway through which mobile app, web UI, and external systems interact with the platform |
| **SQL Database Analytics** | Post-Discharge Agent | Readmission risk cohort scoring, adherence monitoring, anomaly detection, KPI dashboards |
| **LangGraph** | Orchestration Layer | Stateful multi-agent graph — manages handoffs between all four agents, state transitions, and checkpoint persistence |
| **Microsoft Agent Framework** | Specialist Agent Layer | Runtime for all four clinical agents — lifecycle, tool binding, error handling |
| **Azure AI Foundry** | Orchestration Layer | Agent hosting, model serving, and orchestration infrastructure |
| **O365 Copilot Agents** | Interface Layer | Clinician-facing Teams integration — receives escalation alerts, surfaces approval tasks, enables care team discussion |
| **Human-in-the-Loop** | Orchestration Layer | Gates all critical clinical decisions — no prescription, referral, or care plan executes without clinician approval |
| **Durability and State Management** | State Store + LangGraph | Persists care plan state across days and weeks — agent workflows survive restarts and long pauses |
| **Auth and Authorization** | REST API Gateway | OAuth2 tokens, RBAC role enforcement, HIPAA-grade access control — filtering applied before any data reaches the LLM |
| **OTLP Observability** | Cross-Cutting | Distributed traces of every agent reasoning chain, metrics on retrieval quality and latency, audit logs for HIPAA |
| **Evaluation and Testing** | Cross-Cutting | Clinical red-teaming, RAG retrieval quality evals, regression testing on agent outputs, safety threshold testing |
| **React Web UI** | Interface Layer | Clinician dashboard — shows AI reasoning chains, pending approvals, patient timelines, population KPIs |
| **React Native Mobile UI** | Interface Layer | Patient-facing app — symptom intake, medication reminders, daily check-ins, care plan progress |

---

## 8. Cross-Cutting Concerns

These capabilities apply to every agent, every interaction, and every data flow in the platform.

### 8.1 Human-in-the-Loop

#### Business rationale

No AI agent takes a clinically consequential action without clinician approval. This is not a technical limitation — it is a deliberate design principle. The platform is built to augment clinical judgment, not replace it.

#### What requires approval

| Action | Approval Required | Who Approves |
|---|---|---|
| Lab order requested by Diagnostics Agent | Yes — low urgency | Responsible physician (async, web UI) |
| Treatment plan produced by Planning Agent | Yes — always | Responsible physician (async, web UI) |
| Emergency triage routing | Yes — immediate | On-call clinician (Teams alert) |
| Post-discharge escalation | Yes — within 4 hours | Care team (Teams alert) |
| Routine check-in follow-up | No — automated | — |

#### Technical implementation

The Human-in-the-Loop mechanism is implemented as a LangGraph interrupt node. When the orchestrator reaches a decision point that requires human approval, it:

1. Serialises the full agent state (reasoning chain, retrieved documents, proposed action) to the state store
2. Creates an approval task in the web UI and fires a notification via the O365 Copilot Agent
3. Pauses the workflow — the LangGraph node blocks until an approval event arrives
4. On approval, resumes from the exact serialised state, appending the clinician's identity, timestamp, and any notes to the OTLP audit trace

The workflow can pause for minutes or days. Durability ensures the state is never lost.

#### Demo moment

Show a treatment plan sitting in the clinician's dashboard with the full Agentic RAG reasoning chain visible. The clinician reads the agent's rationale, sees that oral iron was rejected because of CKD stage 3, and approves. The system resumes instantly. The OTLP trace shows the full approval chain. This is the moment that lands with healthcare CIOs and CMOs — they recognise immediately that this is what safe AI looks like.

---

### 8.2 Durability and State Management

#### The problem it solves

A post-discharge care plan runs for 90 days. A treatment approval might wait 8 hours for a busy clinician. A diagnostic workflow pauses while lab results are processed overnight. These are not edge cases — they are the normal operational pattern of healthcare.

Without durable state management, every pause is a potential failure point. The agent would need to restart from scratch every time.

#### How it works

Every meaningful state transition in every agent is checkpointed to the state store. The checkpoint includes:

- Current agent step in the LangGraph workflow
- All retrieved documents and their retrieval metadata
- All tool call results from MCP servers
- The current reasoning draft (for Agentic RAG and Self-RAG)
- Pending actions (lab orders, approval tasks)
- The care plan timeline and completion state

When a workflow resumes — whether after a 10-minute Human-in-the-Loop pause or a 3-day wait for lab results — it loads the checkpoint and continues from the exact state it left, with full context intact.

#### Infrastructure

- LangGraph's native checkpoint system for agent-level state
- Azure Durable Functions for long-running workflow orchestration with guaranteed delivery
- Redis or Azure Table Storage as the backing state store depending on latency requirements
- State store access is RBAC-controlled and every state read/write is included in the OTLP audit trail

---

### 8.3 Authentication and Authorization

#### The regulatory context

HIPAA requires that access to protected health information (PHI) is: role-appropriate, audited, revocable, and enforced at the system level — not the application level.

#### Implementation

The platform's REST API gateway enforces a multi-layer authentication and authorization model:

**Authentication** — All requests to the orchestrator carry an OAuth2 Bearer token issued by the hospital's identity provider (Azure AD / Entra ID). Tokens include the user's identity, their clinical role, their site affiliation, and their scope of access.

**Authorization** — The gateway validates the token and enforces role-based access control (RBAC) before the request reaches any agent. Roles map to data access scopes:

| Role | Data Access |
|---|---|
| Patient | Own records only |
| Nurse | Assigned ward patients |
| Physician | Own panel + referred patients |
| Specialist | Referred cases within specialty |
| Administrator | Aggregate KPIs only — no individual PHI |
| AI Agent (service principal) | Scoped to the current care episode only |

**RAG-level filtering** — The access control does not stop at the API gateway. The Enterprise RAG retrieval layer receives the user's role and patient scope as query-time filters. A nurse retrieving context on a patient gets a different result set than a specialist — even if they query the same vector store with the same query. The filter is applied before any document is returned to the LLM context window.

**Token scoping for MCP tools** — When an agent calls an MCP server (e.g. the EHR), it presents a service principal token scoped to the current care episode. The MCP server validates the token and returns only data within that scope. Agents cannot query arbitrary patient records.

---

### 8.4 Observability — Logging, Metrics, and Traces

#### Why OTLP specifically

OpenTelemetry (OTLP) is the industry-standard protocol for producing and transmitting telemetry data. It enables vendor-neutral observability across every layer of the platform — agents, orchestrator, MCP servers, UI — into a single unified view.

In a HIPAA-regulated environment, observability is not optional. Every AI decision must be auditable.

#### Three signal types

**Distributed Traces** capture the complete execution path of every patient workflow — from the mobile app symptom submission, through every agent step, every tool call, every retrieval, every Human-in-the-Loop pause, to the final care plan approval. A single trace for a complex diagnostic workflow might span 15–20 spans across 4 agents and 8 MCP tool calls.

The trace is the primary audit artefact. A compliance officer reviewing a clinical decision can open the trace and see: which agent made the recommendation, what evidence it retrieved, what it decided not to use, when the clinician approved it, and under which credentials.

**Metrics** cover:
- RAG retrieval quality (mean reciprocal rank, retrieval latency, chunk relevance scores)
- Agent reasoning latency (time from input to recommendation)
- Human-in-the-Loop queue depth and average approval time
- SQL analytics query performance
- Post-discharge risk score distributions
- Readmission rate trends (the KPI the business actually cares about)

**Logs** capture structured events at every agent step:
- Retrieval queries and document counts returned
- Self-RAG reflection decisions (relevant / not relevant, supported / not supported)
- Agentic RAG tool call sequences with inputs and outputs
- Every state store checkpoint write with size and timestamp
- Authorization decisions (granted / denied) with the role and scope evaluated

#### Infrastructure

The platform ships OTLP-formatted telemetry to Azure Monitor or any OpenTelemetry-compatible backend (Jaeger, Grafana Tempo, Datadog). Sensitive fields (patient names, PHI) are automatically redacted before telemetry export — the trace references patient episode IDs, not personally identifiable information.

---

### 8.5 Evaluation and Testing

#### Why AI agents are hard to test

Traditional software tests verify that given input X, the system produces output Y. AI agents do not work this way. Given the same input, an LLM-based agent might produce slightly different outputs on different runs — and both might be clinically valid. Traditional unit testing is necessary but not sufficient.

#### Testing layers

**Unit tests** — Tool call integrations, MCP server connectors, SQL query correctness, RBAC enforcement, state store read/write. These are conventional tests.

**RAG evaluation** — Measures whether the retrieval layer is returning the right documents. Key metrics:
- *Retrieval precision* — what fraction of returned documents are actually relevant?
- *Retrieval recall* — what fraction of relevant documents were actually returned?
- *Answer faithfulness* — does the agent's generated output actually reflect what the retrieved documents say, or is it hallucinating?
- *Context relevance* — is the retrieved context sufficient to answer the question?

These are run continuously as the guideline document corpus is updated, to detect retrieval degradation.

**Agent behaviour evals** — A curated set of clinical test cases (synthetic patient scenarios with known correct triage decisions, diagnoses, and treatment plans) are run against each agent after every deployment. Outputs are compared against clinician-validated reference answers using an LLM-as-judge evaluation framework.

**Clinical red-teaming** — Adversarial testing specifically designed to find dangerous failure modes:
- Edge-case symptoms that could be serious conditions presenting atypically
- Contradictory lab results (e.g. high MCV and low ferritin simultaneously)
- Patients with multiple rare comorbidities with conflicting treatment implications
- Attempts to extract PHI through prompt injection via the patient-facing mobile app

**Human-in-the-Loop quality tracking** — Every clinician approval or rejection is a labelled data point. When a clinician significantly modifies an AI-generated treatment plan before approving it, that modification is flagged for review. Patterns of consistent clinician corrections on a specific recommendation type feed back into the evaluation framework, triggering a targeted red-team and potentially a retrieval corpus update.

**Regression testing** — Before every deployment, the full agent eval suite runs against the candidate build. If any agent's performance on the reference test set drops below the clinical safety threshold, the deployment is blocked.

---

## 9. UI Layer

### 9.1 React Native Mobile App (Patient-Facing)

The patient app is the entry point for symptom reporting and the ongoing channel for post-discharge care plan engagement.

**Symptom intake flow:**
- Structured symptom form with progressive disclosure — starts simple, adds detail based on responses
- Free-text description field (processed by the LangChain intake chain for entity extraction)
- Photo/document upload for paper records or prescription photos
- Secure OAuth2 login — patient authenticates with their NHS/hospital patient portal credentials

**Post-discharge engagement:**
- Daily or weekly check-in prompts pushed by the Post-Discharge Agent
- Medication adherence tracking — patient confirms or skips each dose
- Wearable integration — Apple Health / Google Fit data ingested passively
- Care plan timeline — patient sees their upcoming appointments, lab due dates, and progress milestones

### 9.2 React Web Dashboard (Clinician-Facing)

The web dashboard is the primary clinical interface — where clinicians review AI recommendations and maintain oversight of their patient panel.

**Approval workflow:**
- Pending approval queue — all AI-generated plans awaiting clinician review, ranked by urgency
- Full reasoning chain expansion — every Agentic RAG tool call, every retrieved document, every Self-RAG reflection decision is accessible with one click
- Inline annotation — clinicians can add notes to any section of the plan before approving
- Modification mode — clinicians can edit the plan and the system records what was changed relative to the AI recommendation (feeds into the evaluation framework)

**Patient panel view:**
- Live post-discharge risk scores for all monitored patients
- Anomaly alerts surfaced from the SQL anomaly detection queries
- Trend charts for key vitals and lab values over the care episode

**Population KPI dashboard:**
- 30 / 60 / 90-day readmission rates by ward, diagnosis, and clinician
- Average time from symptom intake to treatment plan approval
- Human-in-the-Loop queue metrics — average approval time, longest pending items
- Post-discharge care plan completion rates

### 9.3 Office 365 Copilot Agent (Care Team Collaboration)

The O365 Copilot Agent embeds the platform into the environment where clinical teams already work — Microsoft Teams.

**Capabilities:**
- Receives escalation alerts from the orchestrator and posts them as structured cards in the relevant Teams channel
- Surfaces pending approval tasks directly in Teams — clinician can approve or request more information without leaving Teams
- Answers care team questions about a specific patient's AI-generated plan ("What was the reason IV iron was recommended over oral iron for patient episode 7823?")
- Posts daily summary of the post-discharge cohort risk scores to the ward's Teams channel

---

## 10. Business Value and ROI

### 10.1 Measurable Outcomes

| Metric | Baseline (Industry Average) | Target with Platform |
|---|---|---|
| Time from symptom intake to diagnosis | 2–5 days (EHR + manual) | 4–8 hours (AI-assisted) |
| Time from diagnosis to treatment plan | 1–3 days | Same day |
| 30-day readmission rate (IDA cohort) | 12–18% | Target 6–9% |
| Clinician time on documentation per patient | 45–60 min | 10–15 min (AI prepares, clinician reviews) |
| Post-discharge care plan completion rate | 40–60% | Target 75–85% |
| Treatment guideline adherence | 60–75% | Target 90%+ (AI always checks guidelines) |

### 10.2 Why These Numbers Are Defensible

The readmission reduction target is grounded in existing literature on structured discharge follow-up programmes. The documented effect of systematic adherence monitoring and timely escalation on 30-day readmission rates is a 30–50% relative reduction in high-risk cohorts. The platform automates and scales what previously required dedicated care coordination teams.

The documentation time reduction is grounded in similar AI-assisted clinical documentation pilots at large health systems. The AI produces the structured artefact; the clinician reviews and approves, rather than creating from scratch.

### 10.3 Revenue and Cost Implications

For a hospital network processing 10,000 discharges per month, a 6-percentage-point reduction in 30-day readmission rate represents approximately 600 fewer readmissions per month. At an average readmission cost of $15,000, that is $9M per month in avoided cost — not including the CMS readmission penalty reductions.

The platform also enables the hospital to move toward value-based care contracting with payers — where reimbursement is tied to outcomes rather than volume — with the data infrastructure and outcome tracking to support those contracts.

---

## 11. Compliance and Risk Considerations

### 11.1 HIPAA

| Requirement | Platform Implementation |
|---|---|
| Access controls | OAuth2 + RBAC enforced at API gateway and RAG retrieval layer |
| Audit controls | Full OTLP distributed trace per care episode — tamper-evident |
| Integrity controls | State store writes are append-only with version history |
| Transmission security | All traffic TLS 1.3 — including MCP server calls |
| PHI minimisation | Telemetry export redacts PHI — traces use episode IDs not patient names |

### 11.2 AI Clinical Decision Support

In most jurisdictions, AI systems that provide clinical decision support but require human review before action are not classified as medical devices and do not require FDA clearance or CE marking. The platform's Human-in-the-Loop architecture is specifically designed to keep every AI output in the category of decision support, not autonomous decision-making.

Legal review is recommended before deployment to confirm classification under the applicable jurisdiction's regulatory framework.

### 11.3 Model Risk

AI models can produce incorrect outputs. The platform's risk mitigation strategy is multi-layered:

- Self-RAG and Agentic RAG produce confidence scores — low-confidence outputs trigger automatic Human-in-the-Loop escalation regardless of clinical urgency classification
- Every AI output includes explicit citations — clinicians can verify claims against source documents
- The evaluation framework runs continuous regression testing — model degradation is detected before it reaches production
- All clinician modifications to AI plans are logged — patterns of corrections indicate model failures before they become patient safety events

---

## 12. Implementation Roadmap

### Phase 1 — Foundation (Months 1–3)

**Goal:** Core infrastructure operational. Basic triage and diagnostic flow end-to-end.

- Set up Azure AI Foundry environment, LangGraph orchestration, state store
- Implement REST API gateway with OAuth2 and basic RBAC
- Build MCP server connectors for EHR (read-only) and clinical guidelines vector store
- Implement Symptom Triage Agent with Enterprise RAG (single pilot department)
- Implement Diagnostics Agent with Self-RAG
- Build React Native mobile app (symptom intake only)
- Set up OTLP telemetry pipeline

**Milestone:** First patient symptom intake to triage decision, end-to-end, with full OTLP trace.

### Phase 2 — Clinical Workflow (Months 4–6)

**Goal:** Full care episode from intake to treatment plan approval.

- Implement Treatment Planning Agent with Agentic RAG
- Add MCP connectors for pharmacy, formulary, drug interaction checker
- Build Human-in-the-Loop approval mechanism
- Build React Web dashboard (approval queue + reasoning chain viewer)
- Implement O365 Copilot Agent for Teams escalation alerts
- Expand RBAC to full clinical role taxonomy
- Run first clinical red-team exercise

**Milestone:** First clinician-approved AI-generated treatment plan on real patient data (pilot cohort).

### Phase 3 — Post-Discharge and Analytics (Months 7–9)

**Goal:** Full care journey including post-discharge monitoring.

- Implement Post-Discharge Agent with SQL analytics
- Build wearable data ingestion pipeline
- Implement readmission risk cohort scoring queries
- Implement anomaly detection and escalation threshold system
- Add population KPI dashboard to React Web UI
- Add medication adherence tracking to mobile app
- Full evaluation and testing framework operational

**Milestone:** First post-discharge cohort completing full 90-day monitored care plan.

### Phase 4 — Scale and Optimisation (Months 10–12)

**Goal:** Multi-department rollout with performance and safety validation.

- Expand from pilot department to full hospital network
- RAG corpus expansion — additional specialty guidelines
- Performance optimisation — retrieval latency, SQL query optimisation
- Full clinical safety validation against evaluation framework thresholds
- HIPAA compliance audit
- Staff training programme for clinicians and administrators

**Milestone:** Platform in production across 3+ departments with validated outcome metrics.

---

## 13. Key Demo Scenarios

These are the specific moments to show in a business or technical demonstration:

### Demo 1 — The Triage to Diagnosis Loop (10 minutes)

Show a patient submitting symptoms on the mobile app. Walk through the Enterprise RAG retrieval in the triage agent — show the three sources being queried simultaneously. Show the urgency score being assigned and the case routed to the Diagnostics Agent. Open the OTLP trace and show the full retrieval chain.

**What it demonstrates:** LangChain chains, Enterprise RAG, MCP tool calls, REST API, OTLP.

### Demo 2 — Self-RAG Catching Overconfidence (10 minutes)

Use the anaemia case. Show the first retrieval returning broad results. Show the relevance reflection rejecting them. Show the reformulated query. Show the support reflection catching the fact that the draft diagnosis is overclaiming. Show the utility reflection ordering additional labs. Show the diagnostic report arrive when results return.

**What it demonstrates:** Self-RAG, Diagnostics Agent, MCP lab tool, Durability (workflow pauses for lab results and resumes).

### Demo 3 — Agentic RAG Treatment Plan with Human Approval (15 minutes)

Show the Treatment Planning Agent receiving the confirmed diagnosis. Walk through the multi-step tool call sequence — show the agent changing its retrieval question mid-reasoning when it discovers CKD. Show the care plan arriving in the clinician's Teams via O365 Copilot. Open the React Web dashboard and show the full reasoning chain expanded. Have the clinician approve. Show the OTLP trace update with the approval event.

**What it demonstrates:** Agentic RAG, MCP tools, O365 Copilot Agents, Human-in-the-Loop, React Web UI, Auth/RBAC, OTLP.

### Demo 4 — Post-Discharge Risk Escalation (10 minutes)

Skip forward to Day 22 of the care plan. Show the SQL anomaly detection query firing. Show the risk score crossing the threshold. Show the escalation alert appearing in Teams. Show the clinician approving an urgent call. Show the OTLP audit trace for the full escalation chain.

**What it demonstrates:** Post-Discharge Agent, SQL analytics, Durability (90-day state preserved), Human-in-the-Loop, O365 Copilot, OTLP.

### Demo 5 — Evaluation Dashboard (5 minutes)

Show the evaluation framework running the reference test case suite. Show a retrieval quality metric. Show a clinician modification being logged and flagged for review. Show the regression test gate blocking a hypothetical bad deployment.

**What it demonstrates:** Evaluation and Testing, OTLP metrics.

---

*Document prepared for internal use and meeting presentations. Clinical statistics cited are indicative and should be validated against specific deployment context and target patient population before use in external proposals.*

*All patient scenarios used in this document are synthetic and do not represent real individuals.*
