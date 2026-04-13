# AI-Powered Patient Care Coordination Platform
## Phase-by-Phase Implementation & Deployment Guide

**Stack:** OpenAI API · LangChain + LangGraph · Python · PostgreSQL on EC2 · AWS EC2 + Managed Services  
**Dataset:** Synthea FHIR + Custom Tabular SQL (Python / Faker)  
**Compliance:** HIPAA  
**Team:** Solo Developer  
**Version:** 1.0

---

## Table of Contents

1. [Guide Overview & Principles](#1-guide-overview--principles)
2. [Prerequisites & Accounts Setup](#2-prerequisites--accounts-setup)
3. [Phase 1 — Data Synthesis & Preparation](#3-phase-1--data-synthesis--preparation)
4. [Phase 2 — Local Development & Agent Building](#4-phase-2--local-development--agent-building)
5. [Phase 3 — AWS Infrastructure Setup](#5-phase-3--aws-infrastructure-setup)
6. [Phase 4 — CI/CD & Deployment Pipeline](#6-phase-4--cicd--deployment-pipeline)
7. [Phase 5 — Post-Deployment Monitoring & Ops](#7-phase-5--post-deployment-monitoring--ops)
8. [HIPAA Compliance Checklist](#8-hipaa-compliance-checklist)
9. [AWS Services Reference Map](#9-aws-services-reference-map)
10. [Solo Developer Day-by-Day Schedule](#10-solo-developer-day-by-day-schedule)
11. [Risk Register & Mitigations](#11-risk-register--mitigations)

---

## 1. Guide Overview & Principles

### 1.1 What This Guide Covers

This guide walks a solo developer through the complete journey of building and deploying the AI-Powered Patient Care Coordination Platform — from generating a realistic synthetic healthcare dataset through to a live, HIPAA-aware deployment on AWS using EC2 and managed services.

Each phase is designed to be independently completable and testable before the next phase begins. You should never move to the next phase with a broken or unvalidated previous phase. This discipline is especially important when working solo — there is no team member to catch integration failures at a later stage.

### 1.2 Core Principles for Solo Development

**Local first, cloud second.** Every component is built and fully validated locally before any AWS resource is provisioned. AWS costs money from the moment infrastructure is created. Local development is free.

**One working slice before expanding.** Build the narrowest possible end-to-end path first — one agent, one tool call, one database query, one human approval — and verify it works completely before adding agents or capabilities. A thin working slice is worth more than a wide half-built system.

**Environment parity.** The local development environment should mirror the AWS environment as closely as possible using Docker Compose. This eliminates the most common class of deployment failure — code that works locally but breaks in production.

**Secrets never in code.** From day one, all credentials, API keys, and connection strings live in environment variables or AWS Secrets Manager. No exceptions. For a HIPAA workload, a credential leak is a reportable breach.

**Checkpoints and rollback.** Every phase ends with a defined checkpoint — a set of tests or verifiable states that confirm the phase is complete. If a checkpoint is not met, the phase is not complete, regardless of how much time was spent.

### 1.3 Technology Decisions Summary

| Decision | Choice | Rationale |
|---|---|---|
| LLM provider | OpenAI API (GPT-4o) | Strongest reasoning for clinical text; no GPU infrastructure to manage |
| Orchestration | LangChain + LangGraph | LangChain for chains, LangGraph for stateful multi-agent coordination |
| Vector store | OpenSearch Serverless (AWS) / ChromaDB (local) | ChromaDB locally for simplicity; OpenSearch in production for scale and AWS-native access control |
| SQL database | PostgreSQL in Docker on EC2 | Full control, no RDS cost, containerised for portability |
| State store | Redis on EC2 (Docker) | LangGraph checkpoint persistence; fast key-value for workflow state |
| MCP servers | Custom Python FastAPI services | Lightweight, Python-native, easy to deploy alongside agents on EC2 |
| Compute | EC2 t3.large (dev) / t3.xlarge (prod) | Right-sized for a demo platform; easily resized |
| Object storage | S3 | Synthea FHIR files, document chunks, model artefacts, logs |
| Secrets | AWS Secrets Manager | HIPAA-required; all credentials retrieved at runtime |
| Observability | CloudWatch + OpenTelemetry collector on EC2 | OTLP traces and metrics shipped to CloudWatch |
| CI/CD | GitHub Actions | Free tier, sufficient for solo; deploys to EC2 via SSH |

---

## 2. Prerequisites & Accounts Setup

### 2.1 Accounts You Need Before Starting

Before writing a single line of application code, the following accounts and access must be in place. Missing any of these will block a later phase.

**OpenAI**
Create an OpenAI platform account and generate an API key with sufficient quota for development use. Verify the key works by making a test completion call before proceeding. Set a monthly spend limit in the OpenAI dashboard — without a limit, a runaway agent loop can generate unexpected charges.

**AWS**
Create an AWS account if you do not already have one. Immediately enable MFA on the root account and create an IAM user for all day-to-day work — never use root credentials operationally. Enable AWS Cost Budgets with an alert at a sensible monthly threshold before provisioning any resources. Request a service quota increase for EC2 t3.xlarge instances in your target region if you are on a new account.

**GitHub**
A GitHub account is required for the CI/CD pipeline. Create a new repository for the project. Enable branch protection on the main branch — even as a solo developer, this prevents accidental direct pushes to the production branch.

**Docker Hub (optional)**
If you plan to push custom Docker images to a registry, create a Docker Hub account or use AWS ECR (Elastic Container Registry), which is the preferred choice for AWS deployments as it avoids public registry rate limits.

### 2.2 Local Machine Requirements

Your development machine should have the following installed and verified before Phase 2 begins:

- Python 3.11 or later
- Docker Desktop (with Docker Compose v2)
- Git
- AWS CLI v2 — configured with your IAM user credentials and default region
- A code editor with Python language support (VS Code recommended)
- `curl` and `jq` for API testing from the terminal

Verify each tool is installed and accessible from your terminal before proceeding. A setup issue discovered mid-phase is more disruptive than one caught at the start.

### 2.3 AWS IAM Setup

Create a dedicated IAM user for the project with programmatic access. Attach the following managed policies as a starting point, then tighten permissions in Phase 3 when you know exactly which services you are using:

- `AmazonEC2FullAccess`
- `AmazonS3FullAccess`
- `SecretsManagerReadWrite`
- `AmazonOpenSearchServiceFullAccess`
- `CloudWatchFullAccess`
- `AmazonECR-FullAccess`

Create an IAM role for the EC2 instances themselves — the instances will use this role to access S3, Secrets Manager, OpenSearch, and CloudWatch without any credentials stored on the machine. This is mandatory for HIPAA compliance.

---

## 3. Phase 1 — Data Synthesis & Preparation

**Goal:** Produce a realistic, schema-correct synthetic healthcare dataset that exercises every agent in the platform — triage, diagnostics, treatment planning, and post-discharge monitoring.  
**Duration:** 3–4 days  
**Output:** Populated PostgreSQL database + FHIR JSON files in S3 + vector store loaded with clinical guidelines

---

### 3.1 Why This Phase Comes First

You cannot meaningfully build or test agents without data. The Symptom Triage Agent needs patient records to retrieve. The Diagnostics Agent needs lab result histories to reason over. The Post-Discharge Agent needs a historical admissions cohort to run risk scoring queries against. Building agents against empty or stub data produces agents that appear to work but fail immediately when real data is introduced.

Investing 3–4 days in a high-quality synthetic dataset at the start pays dividends across every subsequent phase.

### 3.2 Dataset Design — What You Need

The platform requires three categories of data, each serving different agents and system components.

**Category 1 — FHIR Patient Records (Synthea)**

Synthea generates medically realistic patient populations as FHIR R4 JSON bundles. Each patient bundle contains: demographics, conditions, observations (lab results, vital signs), medications, procedures, encounters (hospital visits), and care plans.

For this platform, generate a population with the following characteristics:
- 500 patients minimum (provides enough cohort depth for the SQL analytics queries)
- Focus conditions: iron deficiency anaemia, type 2 diabetes, chronic kidney disease, hypertension, COPD — these are the conditions the clinical agents are designed to reason about
- Age range: 30–75 (most representative of the target clinical population)
- Include patients with multiple comorbidities — the Treatment Planning Agent's Agentic RAG is specifically tested by patients with conflicting treatment implications

Synthea is run locally as a Java application. It takes configuration parameters for population size, age distribution, and condition prevalence. The output is a directory of FHIR JSON bundles — one file per patient.

**Category 2 — Custom Relational Tables (Python / Faker)**

Synthea does not generate the flat operational tables that the SQL analytics layer needs. These are built by parsing the Synthea FHIR bundles and transforming them into a relational schema, then supplementing with Faker-generated data for fields Synthea does not cover.

The tables required are:

| Table | Contents | Source |
|---|---|---|
| `patients` | Demographics, identifiers, registration date | Synthea FHIR Patient resource |
| `admissions` | Hospital visit records with admission/discharge dates, primary diagnosis, ward, attending clinician | Synthea FHIR Encounter resource |
| `diagnoses` | Diagnosis codes (ICD-10), confidence scores, diagnosing agent or clinician | Synthea FHIR Condition resource |
| `lab_results` | Test name, value, unit, reference range, collection timestamp, patient ID, encounter ID | Synthea FHIR Observation resource |
| `medications` | Drug name, dose, route, start date, end date, prescribing clinician | Synthea FHIR MedicationRequest resource |
| `vitals` | Heart rate, SpO2, blood pressure, weight — timestamped series | Synthea FHIR Observation resource |
| `pharmacy_events` | Prescription fill date, refill date, gap in days — used by adherence monitoring | Faker-generated, linked to medications |
| `discharge_plans` | Care plan ID, patient ID, start date, end date, assigned agent, completion status | Faker-generated, linked to admissions |
| `wearable_readings` | Simulated daily wearable data per post-discharge patient | Faker-generated with realistic variance |
| `readmissions` | Patients who were readmitted within 30/60/90 days — labelled for cohort queries | Derived from admissions table |
| `clinicians` | Clinician IDs, names, specialties, ward assignments | Faker-generated |
| `approval_events` | Human-in-the-Loop approval records — clinician ID, timestamp, plan version, action | Faker-generated (seeded for testing) |

**Category 3 — Clinical Guidelines Document Corpus**

The vector store used by all three RAG agents requires a corpus of clinical guideline documents. These are publicly available and do not need to be synthesised. The following sources cover all conditions used in the demo:

- NICE guidelines: anaemia (NG203), type 2 diabetes (NG28), CKD (NG203), chest pain (CG95)
- WHO clinical protocols for primary care
- British National Formulary (BNF) drug monographs for iron sucrose, metformin, ACE inhibitors
- Hospital discharge protocol templates (generic, publicly available)

Download these as PDF documents. They will be chunked, embedded, and loaded into the vector store in Step 3.5.

### 3.3 Synthea Installation and Population Generation

Synthea is distributed as a compiled JAR file. Download the latest release from the Synthea GitHub repository. It requires Java 11 or later to run.

Run Synthea with parameters targeting your desired population characteristics. Key configuration options to set before running:

- Population size: 500 patients
- State/region: set to a US state (Synthea uses US clinical prevalence data)
- Condition prevalence: enable the specific conditions listed in 3.2 via the Synthea configuration file
- Export format: FHIR R4 JSON (the default)
- Output directory: a local folder you will reference throughout Phase 1

Synthea will generate one JSON file per patient plus a master index file. On a modern laptop, 500 patients takes approximately 2–3 minutes to generate.

Inspect a sample of the output files before proceeding. Verify that the bundles contain the resource types you expect: Patient, Encounter, Condition, Observation, MedicationRequest. If a resource type is missing, check the Synthea configuration and regenerate.

### 3.4 FHIR-to-Relational Transformation

Once the Synthea output is generated, transform it into the relational tables defined in 3.2.

The transformation process for each table follows the same pattern:
1. Parse all FHIR bundle JSON files
2. Extract the relevant FHIR resource type (e.g. Observation for lab results)
3. Map FHIR fields to relational columns
4. Apply any derived calculations (e.g. compute readmission flag from encounter dates)
5. Write to the target table

Key transformation decisions to make before starting:

**IDs:** Synthea generates UUID-format patient and encounter IDs. Keep these as the primary keys in your relational tables — they link back to the FHIR bundles and simplify debugging.

**Dates:** Synthea generates ISO 8601 timestamps. Store all dates as `TIMESTAMPTZ` in PostgreSQL to avoid timezone ambiguity — important when simulating a multi-site healthcare deployment.

**Lab result normalisation:** Synthea generates Observation resources with LOINC codes. Map the LOINC codes you need (haemoglobin, ferritin, serum iron, HbA1c, creatinine, eGFR) to human-readable names in a lookup table. This is what the Diagnostics Agent will query by name.

**Faker extensions:** For tables that have no Synthea equivalent (pharmacy_events, wearable_readings, discharge_plans), use Python Faker to generate realistic data linked to the Synthea patient IDs. For pharmacy events, generate refill timestamps that are mostly on schedule with a configurable percentage (15–20%) of late or missed refills — this is what triggers the Post-Discharge Agent's adherence detection.

For wearable readings, generate daily heart rate, SpO2, and blood pressure values using the patient's Synthea baseline vitals as the mean, with small random variance. For 10% of post-discharge patients, introduce a gradual anomaly trend in the last two weeks of their care plan — this is what the SQL anomaly detection query will catch.

### 3.5 Database Initialisation

Stand up a local PostgreSQL instance using Docker before loading data. This is the same container configuration you will use on EC2 in Phase 3 — environment parity from day one.

The database setup sequence:
1. Start the PostgreSQL container via Docker Compose
2. Create the database and a dedicated application user with limited permissions — do not use the postgres superuser for application connections
3. Run the schema creation SQL — define all tables, indexes, foreign keys, and constraints
4. Run the FHIR transformation to populate the core patient tables
5. Run the Faker extension scripts to populate the operational tables
6. Verify row counts in each table match expectations

**Indexes to create at this stage** — the SQL analytics queries the Post-Discharge Agent runs are expensive without indexes:
- `admissions(patient_id, discharge_date)` — for cohort readmission queries
- `admissions(primary_diagnosis_code, discharge_date)` — for diagnosis-specific cohort scoring
- `lab_results(patient_id, test_name, collected_at)` — for time-series lab lookups
- `wearable_readings(patient_id, reading_date)` — for anomaly detection queries
- `pharmacy_events(patient_id, expected_refill_date)` — for adherence gap queries

Run the five SQL analytics query patterns from the platform design (readmission cohort, adherence drop-off, anomaly detection, KPI aggregation, population segmentation) manually against the loaded data. If any query takes more than 2 seconds on 500 patients locally, add or adjust indexes before moving on.

### 3.6 FHIR Files Upload to S3

Create an S3 bucket for the project with the following configuration:
- Versioning enabled
- Server-side encryption with SSE-S3 (minimum) or SSE-KMS (preferred for HIPAA)
- Block all public access — no exceptions
- Bucket policy restricting access to your IAM role only

Upload the Synthea FHIR JSON bundles to S3 under a structured prefix: `synthea-fhir/patients/`. This serves two purposes: it mirrors the production data lake pattern you would use with real EHR data, and it gives the EHR MCP server a realistic source to query from during development.

### 3.7 Vector Store Loading

The clinical guidelines corpus (PDF documents downloaded in 3.2) must be processed into embeddings and loaded into the vector store before the RAG agents can be tested.

The loading sequence for each document:
1. Extract text from the PDF — preserve section structure where possible
2. Chunk the text — clinical guidelines chunk well at 512–768 tokens with a 10% overlap between chunks
3. Embed each chunk using the OpenAI `text-embedding-3-small` model — this is the same model the retrieval queries will use, which is required for cosine similarity to be meaningful
4. Store each chunk with its embedding, source document name, section heading, and page number as metadata

For local development, use ChromaDB running as a local persistent store (also via Docker Compose). In production (Phase 3), this will be replaced by Amazon OpenSearch Serverless — the vector store loading process is identical, only the destination client changes.

Load the documents in this order and verify chunk counts after each:
1. NICE guidelines (largest, most referenced — load first to catch any chunking issues early)
2. WHO protocols
3. BNF drug monographs
4. Hospital discharge templates

After loading, run three test retrieval queries that cover the main clinical scenarios — an IDA symptom query, a CKD treatment query, and a drug interaction query — and manually inspect the top 5 returned chunks for each. The results should be clinically coherent and clearly relevant. If they are not, the issue is either in the chunking strategy, the embedding model, or the query formulation. Resolve before Phase 2.

### 3.8 Phase 1 Checkpoint

Phase 1 is complete when all of the following are true:

- PostgreSQL container is running locally with all tables populated and row counts verified
- All five SQL analytics query patterns return results in under 2 seconds
- S3 bucket exists, FHIR files are uploaded, and access is verified via the AWS CLI
- ChromaDB vector store is loaded and three test retrieval queries return clinically coherent results
- No credentials or connection strings appear anywhere in code or configuration files — all are in `.env` (gitignored) locally

---

## 4. Phase 2 — Local Development & Agent Building

**Goal:** Build all four clinical agents and the orchestration layer, fully functional and tested against the Phase 1 dataset, running entirely on your local machine.  
**Duration:** 10–14 days  
**Output:** A working multi-agent system runnable via Docker Compose that passes all local integration tests

---

### 4.1 Project Structure

Before writing any application code, establish the project directory structure. A well-organised structure is especially important for a solo developer — six weeks from now you will need to find files quickly without a team member to ask.

The recommended structure separates concerns cleanly:

```
project-root/
├── agents/
│   ├── triage/          — Symptom Triage Agent
│   ├── diagnostics/     — Diagnostics Agent
│   ├── treatment/       — Treatment Planning Agent
│   └── discharge/       — Post-Discharge Agent
├── orchestrator/        — LangGraph workflow, HITL mechanism, REST API
├── mcp_servers/         — MCP tool server implementations
│   ├── ehr/             — EHR query tool
│   ├── lab/             — Lab order and result tool
│   ├── pharmacy/        — Formulary and drug interaction tool
│   └── appointments/    — Appointment booking tool
├── data/
│   ├── schemas/         — SQL DDL files
│   └── seeds/           — Transformation and Faker scripts
├── vector_store/        — ChromaDB loader and retrieval utilities
├── config/              — Environment config, logging config
├── tests/               — Unit tests, integration tests, eval suite
├── docker/              — Dockerfiles for each service
├── docker-compose.yml   — Full local stack definition
└── .env.example         — Template for environment variables (no real values)
```

Create this structure before writing any agent code. Populate the `.env.example` file with all the environment variable names the system will need (but not the values) so you have a reference as you build.

### 4.2 Docker Compose Local Stack

Define the full local stack in `docker-compose.yml` before building agents. This forces you to think through service dependencies and networking upfront rather than discovering them when you try to connect services together.

The local stack should include the following services:

**Infrastructure services (always running):**
- PostgreSQL — the relational database from Phase 1
- Redis — LangGraph state store and session cache
- ChromaDB — vector store (persistent volume mount)
- OpenTelemetry Collector — receives OTLP traces from all agents and writes to local files for inspection

**Application services (the platform itself):**
- Orchestrator API — the LangGraph workflow and REST API gateway
- Triage Agent service
- Diagnostics Agent service
- Treatment Planning Agent service
- Post-Discharge Agent service
- EHR MCP server
- Lab MCP server
- Pharmacy MCP server
- Appointments MCP server

All application services share a Docker network. Services communicate by service name (e.g. the orchestrator calls `http://ehr-mcp:8001/query`). This mirrors how they will communicate on EC2 in production.

Define health checks for every service — the orchestrator should not start until all MCP servers and infrastructure services report healthy. Docker Compose `depends_on` with `condition: service_healthy` enforces this.

### 4.3 MCP Server Implementation

Build the MCP servers before the agents — the agents depend on the tools being available and testable. Each MCP server is a lightweight Python FastAPI application that exposes a small set of typed endpoints.

**EHR MCP Server**

Exposes patient record retrieval. Accepts a patient ID and a list of requested resource types (demographics, conditions, medications, lab results, encounters). Queries the PostgreSQL database and returns a structured JSON response. Enforces a scope check — the requesting agent's service token must include the patient ID in its scope.

**Lab MCP Server**

Exposes two operations: submitting a lab order (writes a pending order record to the database) and retrieving lab results for a patient and test name. When a lab order is submitted, it writes immediately with a `pending` status and a simulated `result_available_at` timestamp 30 minutes in the future — this simulates the real-world delay and allows you to test the LangGraph workflow pausing and resuming when results arrive.

**Pharmacy MCP Server**

Exposes drug interaction checking (accepts a list of drug names, returns known interactions from a pre-loaded interaction table), formulary checking (accepts a drug name and site ID, returns availability), and prescription submission (writes to the medications table).

**Appointments MCP Server**

Exposes appointment creation and retrieval. For local development this simply writes to and reads from a PostgreSQL appointments table.

Test each MCP server independently via curl before connecting agents to them. Every endpoint should return a predictable response for known inputs before you write a single agent that depends on it.

### 4.4 LangChain Intake Chain

The intake chain is the simplest component to build and the right starting point for the application layer. It is a pure LangChain chain — no agents, no tools, no state — just a structured prompt pipeline that takes raw patient symptom text and produces a normalised clinical entity object.

The chain has three steps:
1. Entity extraction — prompt the LLM to extract structured fields (symptom list, duration, severity, relevant negatives, patient-reported medications) from free text
2. Normalisation — map extracted symptom names to standard clinical terminology (SNOMED-CT preferred terms where possible)
3. Validation — verify the extracted object has all required fields; if not, prompt for clarification

Build this chain and test it against 10–15 synthetic symptom descriptions manually before connecting it to the Triage Agent. The output schema must be stable and consistent — the Triage Agent depends on it.

### 4.5 Symptom Triage Agent — Enterprise RAG

The Triage Agent is the first full agent to build. It receives the intake chain output and produces an urgency score and routing decision.

**Agent structure:**

The agent is built as a LangChain agent with a defined set of tools. The tools it has access to are: the EHR MCP server (to retrieve patient history), the ChromaDB retrieval utility (to query the clinical guidelines vector store), and the drug database retrieval utility (to check medication side effects).

**Enterprise RAG implementation:**

The retrieval logic fans out simultaneously to all three sources when the agent invokes the retrieval tool. The results are merged and re-ranked by a scoring function that weights recency (recent EHR data scores higher than older data) and source type (guideline documents score higher than general references for clinical decisions). The top-ranked results are assembled into the agent's context window.

The RBAC filter is applied before any retrieval — the agent's service token carries the patient episode scope, and the retrieval utility filters results to only documents and records within that scope.

**Urgency scoring:**

After retrieval, the agent follows a structured reasoning prompt that asks it to score urgency on a four-level scale (emergency, urgent, routine, self-care) with a required rationale for each score. The prompt includes explicit instructions to prefer caution over certainty — if any retrieved evidence suggests a potentially serious condition, the score should be elevated rather than averaged down.

**Testing the Triage Agent:**

Create 10 test cases covering the urgency spectrum:
- 2 emergency cases (chest pain with radiation, anaphylaxis symptoms)
- 3 urgent cases (suspected anaemia, uncontrolled diabetes symptoms, acute UTI)
- 3 routine cases (mild fatigue, seasonal allergy, minor wound)
- 2 self-care cases (common cold, mild muscle soreness)

Run each test case and verify the urgency scores are clinically appropriate. Document any cases where the agent scores incorrectly — these become your evaluation suite for Phase 5.

### 4.6 Diagnostics Agent — Self-RAG

The Diagnostics Agent receives a triage packet and runs the Self-RAG reasoning loop to produce a confirmed differential diagnosis.

**Self-RAG loop implementation:**

The Self-RAG loop is implemented as a LangGraph subgraph with the following nodes:

- `retrieve` — executes a retrieval query against the vector store and lab result history
- `reflect_relevance` — prompts the LLM to score each retrieved document's relevance to the current patient presentation on a 0–1 scale; documents below 0.6 are filtered out
- `generate_draft` — produces a draft diagnostic hypothesis from the filtered retrieved documents
- `reflect_support` — prompts the LLM to identify any claims in the draft that are not directly supported by retrieved evidence; unsupported claims are flagged for removal or softening
- `reflect_utility` — prompts the LLM to assess whether the evidence is sufficient to produce a clinically actionable conclusion; if not, the agent identifies what additional data is needed
- `request_labs` — if utility reflection identifies missing data, calls the Lab MCP server to submit orders and sets a `pending_labs` flag on the workflow state
- `generate_final` — produces the final diagnostic report with confidence score and evidence citations

The loop exits to `generate_final` when the utility reflection returns sufficient, or when a maximum iteration count (3) is reached — this prevents infinite loops on genuinely ambiguous presentations.

**Confidence score calibration:**

The confidence score is not a raw LLM output — it is calculated from the reflection scores. A formula combining retrieval relevance scores, support coverage, and utility completeness produces a 0–100 confidence value. Values below 70 automatically trigger Human-in-the-Loop escalation regardless of urgency level.

**Lab result waiting:**

When the agent submits a lab order and enters the `pending_labs` state, the LangGraph workflow checkpoints to Redis and the node blocks. A background polling process checks the lab MCP server every 5 minutes. When results are available, the polling process writes a resume event to Redis and the workflow resumes at the `retrieve` node with the new data in scope.

This is the first place you test Durability end-to-end — verify that the workflow survives a Redis restart between submitting a lab order and receiving the result.

### 4.7 Treatment Planning Agent — Agentic RAG

The Treatment Planning Agent is the most complex agent in the platform. It implements Agentic RAG — a ReAct-style reasoning loop where the agent plans its own sequence of retrieval tool calls based on what it learns at each step.

**Agentic RAG implementation:**

The agent is implemented as a LangGraph node that runs a ReAct loop. In each iteration of the loop:
1. The agent reasons over its current knowledge state and the patient context
2. It selects the next tool to call from its available tools (guideline search, EHR query, interaction checker, formulary check)
3. It executes the tool call via the appropriate MCP server
4. It receives the result and updates its knowledge state
5. It decides whether to continue reasoning (call another tool) or conclude (produce the treatment plan)

The agent has a maximum of 8 tool call iterations per reasoning session. If it reaches 8 without concluding, it produces a partial plan with explicit flags indicating what it was unable to verify — these flags automatically trigger Human-in-the-Loop review.

**Mid-reasoning replanning:**

The key behaviour to verify is that the agent genuinely changes its retrieval strategy based on what it discovers. Test this with the CKD + IDA scenario: the agent should start with oral iron guidelines, discover CKD stage 3 in the EHR query, then pivot to IV iron protocols without being explicitly instructed to do so. If the agent continues retrieving oral iron guidelines after discovering CKD, the system prompt needs to be revised to place stronger emphasis on comorbidity-driven replanning.

**Care plan output schema:**

The treatment plan output is a structured JSON object with explicit fields for: primary recommendation, guideline citations, contraindications checked, cause investigation steps, alternatives rejected (each with a reason), and monitoring schedule. This schema is validated before the plan is forwarded to the Human-in-the-Loop mechanism — a malformed plan is rejected and the agent is asked to regenerate.

### 4.8 Human-in-the-Loop Mechanism

The HITL mechanism is a LangGraph interrupt node that sits between the Treatment Planning Agent output and the Post-Discharge Agent activation.

**Implementation:**

When the orchestrator reaches the HITL node:
1. The full workflow state is serialised to Redis under a unique approval task ID
2. An approval task record is written to the PostgreSQL `approval_events` table with status `pending`
3. The LangGraph workflow pauses — the node blocks waiting for a resume signal
4. A notification payload is written to a Redis pub/sub channel (the web UI polls this channel)
5. When the clinician approves via the web UI, the approval endpoint writes the approval record to PostgreSQL, writes a resume signal to Redis, and the workflow resumes

**Timeout handling:**

Approval tasks that have been pending for more than 24 hours are escalated — a higher-urgency notification is sent and the task is flagged in the dashboard. Tasks pending for more than 72 hours are automatically escalated to the department head (simulated in the demo by a second notification).

**Testing HITL:**

Create an approval task, verify it appears in the PostgreSQL table with `pending` status, verify the workflow is genuinely blocked (the Post-Discharge Agent has not activated), submit an approval via the API, and verify the workflow resumes and the Post-Discharge Agent activates. This test must pass reliably before moving to Phase 3.

### 4.9 Post-Discharge Agent — SQL Analytics

The Post-Discharge Agent is unique among the four agents in that it is time-driven rather than event-driven. It does not wait for a trigger — it runs on a schedule and evaluates all active care plans.

**Scheduler implementation:**

A lightweight scheduler (APScheduler) runs inside the Post-Discharge Agent service. It triggers the agent loop every 15 minutes in development (every 6 hours in production). On each trigger, the agent:
1. Queries the `discharge_plans` table for all active care plans
2. For each active plan, runs the five SQL analytics patterns
3. Updates the risk score for each patient
4. Triggers escalation for any patient whose risk score has crossed the threshold since the last check
5. Sends mobile check-in prompts for patients whose check-in schedule is due
6. Writes a summary event to the OTLP collector

**Risk score threshold:**

The escalation threshold is configurable per care plan type. For IDA post-discharge plans, set the initial threshold at 65 (on a 0–100 scale). The risk score is a weighted composite of: cohort readmission rate for the patient's diagnosis and demographic (weight 0.4), medication adherence gap in days (weight 0.3), vital sign anomaly score (weight 0.2), and days since last completed check-in (weight 0.1).

**Testing the analytics queries:**

Use the Faker-generated anomaly data from Phase 1 (the 10% of patients with introduced vital sign trends) to verify the anomaly detection query catches them. The query should identify these patients by Day 20–22 of their care plan. If it does not, inspect the anomaly threshold values and the query logic.

### 4.10 REST API Gateway

The orchestrator exposes a REST API that the web UI and mobile app call. For local development this is a FastAPI application running in the Docker Compose stack.

**Endpoints to implement:**

- `POST /api/v1/symptoms` — accepts a symptom payload, triggers the intake chain and Triage Agent, returns a triage reference ID
- `GET /api/v1/cases/{case_id}` — returns the current state of a care episode
- `POST /api/v1/approvals/{task_id}` — accepts a clinician approval with credentials
- `GET /api/v1/approvals/pending` — returns all pending approval tasks for the authenticated clinician
- `GET /api/v1/patients/{patient_id}/discharge-plan` — returns the active discharge plan and current risk score
- `GET /api/v1/analytics/kpis` — returns the population KPI dashboard data

**Authentication (local):**

For local development, implement JWT-based authentication with a simple token issuance endpoint. The token payload carries the user's role and patient scope. All endpoints validate the token and enforce role-based access — even locally. This is not optional: HIPAA requires access controls to be implemented at the application layer, not just the infrastructure layer.

### 4.11 OTLP Observability (Local)

Every agent emits OpenTelemetry traces. For local development, the OTel collector is configured to write traces to a local JSON file that you can inspect after test runs.

Each agent should instrument the following as named spans:
- The top-level agent invocation (one span per patient episode)
- Each retrieval tool call (span includes query text, number of results, top result score)
- Each Self-RAG reflection decision (span includes the reflection type and the pass/fail outcome)
- Each Agentic RAG tool call iteration (span includes tool name, input summary, output summary)
- Each HITL event (span includes task ID, timestamp, and outcome when it arrives)
- Each SQL analytics query (span includes query name and execution time)

After running a full end-to-end test (symptom intake through post-discharge escalation), open the trace output file and verify you can trace the complete patient journey from a single root span. This is your manual proof that the OTLP implementation is working before deploying to AWS.

### 4.12 Phase 2 Checkpoint

Phase 2 is complete when all of the following are true:

- `docker-compose up` starts the full stack with all services healthy
- A symptom submission triggers the full chain through triage, diagnostics, treatment planning, HITL pause, HITL approval, and post-discharge agent activation — end-to-end without manual intervention (except the HITL approval itself)
- All 10 triage test cases produce clinically appropriate urgency scores
- The CKD + IDA scenario demonstrates the Agentic RAG mid-reasoning pivot from oral to IV iron
- The Self-RAG loop correctly requests additional labs when the utility reflection returns insufficient
- The Post-Discharge Agent's anomaly detection identifies the 10% of Faker-seeded anomaly patients by Day 20–22
- A complete end-to-end OTLP trace is visible in the local trace output covering all agent steps
- All five SQL analytics queries return in under 2 seconds

---

## 5. Phase 3 — AWS Infrastructure Setup

**Goal:** Provision all AWS resources required to run the platform in a HIPAA-aware configuration, and migrate the working local stack to AWS.  
**Duration:** 5–7 days  
**Output:** A running platform on AWS, accessible via HTTPS, with all data encrypted and access controlled

---

### 5.1 AWS Architecture Overview

The production architecture on AWS uses the following resource topology:

**VPC and Networking:**
- A dedicated VPC for the project (do not use the default VPC for HIPAA workloads)
- Two availability zones minimum for any resource that supports multi-AZ
- Public subnets: Application Load Balancer only
- Private subnets: all EC2 instances, databases, and internal services
- No direct internet access from private subnets — all outbound traffic via NAT Gateway
- Security groups as the primary access control layer — principle of least privilege

**EC2 Instances:**
- One `t3.large` instance for the orchestrator and agent services (can be upgraded to `t3.xlarge` if memory pressure is observed)
- One `t3.medium` instance for PostgreSQL and Redis containers
- Both instances in private subnets
- No SSH access via public IP — all SSH via AWS Systems Manager Session Manager (HIPAA-aligned, no open port 22)

**Load Balancer:**
- Application Load Balancer in the public subnet
- HTTPS listener with an ACM-managed TLS certificate
- Health check on the orchestrator API health endpoint
- HTTP to HTTPS redirect on port 80

**Storage and Data Services:**
- S3 bucket (from Phase 1) — add a bucket policy requiring HTTPS access only
- Amazon OpenSearch Serverless — replaces ChromaDB for the production vector store
- AWS Secrets Manager — all credentials and API keys

**Observability:**
- CloudWatch Log Groups for application logs
- CloudWatch Metrics for custom business metrics
- AWS X-Ray for distributed tracing (OpenTelemetry collector on EC2 ships to X-Ray via the OTLP/gRPC exporter)

### 5.2 VPC and Network Provisioning

Create the VPC with a /16 CIDR block. Create four subnets: two public (one per AZ) and two private (one per AZ). Attach an Internet Gateway to the VPC for the public subnets. Create a NAT Gateway in one public subnet for outbound internet access from the private subnets.

Create the following security groups before provisioning any instances:

**ALB security group:** Inbound HTTPS (443) from 0.0.0.0/0. Inbound HTTP (80) from 0.0.0.0/0 (for redirect). Outbound to the application server security group on port 8000.

**Application server security group:** Inbound on port 8000 from the ALB security group only. Inbound from the data server security group on all ports (for agent-to-database communication). Outbound HTTPS to 0.0.0.0/0 (for OpenAI API calls and AWS service calls via HTTPS).

**Data server security group:** Inbound on PostgreSQL port (5432) and Redis port (6379) from the application server security group only. No inbound from the internet. Outbound HTTPS to 0.0.0.0/0 for AWS service calls.

### 5.3 EC2 Instance Provisioning

Launch both EC2 instances using the Amazon Linux 2023 AMI. Attach the IAM role created in Phase 2 prerequisites. Enable detailed CloudWatch monitoring. Attach an encrypted EBS volume for application data (in addition to the root volume).

**Do not assign public IP addresses to either instance.** All access is via the ALB (for the application) or Systems Manager Session Manager (for SSH-equivalent access).

On the application server, install: Docker, Docker Compose v2, Python 3.11, Git, the AWS CLI, and the CloudWatch agent.

On the data server, install: Docker and Docker Compose v2 only.

Verify Systems Manager Session Manager connectivity to both instances before proceeding. You should be able to open a terminal session to each instance from the AWS console without any SSH key.

### 5.4 PostgreSQL and Redis on EC2

On the data server, deploy the PostgreSQL and Redis containers using Docker Compose. The configuration is identical to the local development setup with the following changes:

- PostgreSQL data directory mounted to the encrypted EBS volume (not the root volume)
- Redis configured with persistence (AOF) to the encrypted EBS volume
- Both containers configured to accept connections only from the application server's private IP range
- PostgreSQL configured with SSL required for all connections
- A daily automated backup of the PostgreSQL data volume to S3 using an AWS Backup plan

After deploying, connect from your local machine via a Systems Manager port-forwarding session and run the Phase 1 schema creation and data loading process against the production database. Verify row counts match the local environment.

### 5.5 Amazon OpenSearch Serverless

Create an OpenSearch Serverless collection for the production vector store. OpenSearch Serverless handles capacity automatically — you do not need to size or manage nodes.

Configure the collection with:
- Encryption with an AWS KMS key (required for HIPAA)
- VPC endpoint — the collection should only be accessible from within your VPC, not from the public internet
- Data access policy restricting access to the EC2 instance IAM role only
- Network policy allowing access from the VPC only

After the collection is created, rerun the vector store loading process from Phase 1 targeting the OpenSearch collection instead of ChromaDB. The loading logic is identical — only the vector store client is swapped. Verify the same three test retrieval queries from Phase 1 return the same clinically coherent results against OpenSearch.

### 5.6 AWS Secrets Manager

Migrate all credentials from local `.env` files to AWS Secrets Manager. Create one secret per logical credential group:

- `healthcare-platform/openai` — OpenAI API key
- `healthcare-platform/postgres` — PostgreSQL connection string with credentials
- `healthcare-platform/redis` — Redis connection string
- `healthcare-platform/opensearch` — OpenSearch endpoint and access credentials
- `healthcare-platform/jwt` — JWT signing secret for the API gateway authentication

Update all application services to retrieve their credentials from Secrets Manager at startup using the AWS SDK. The EC2 instance IAM role grants read access to these secrets — no credentials are stored on the instance or in environment files.

Enable automatic secret rotation for the PostgreSQL credentials (Secrets Manager has a built-in rotation Lambda for RDS — for a Docker PostgreSQL, you will implement a simple custom rotation Lambda).

### 5.7 Application Deployment to EC2

On the application server, clone the project repository and build the Docker images for all application services. The build process is identical to local development — `docker compose build` — but targeting the production Docker Compose file which replaces ChromaDB with OpenSearch, local env vars with Secrets Manager calls, and local OTel collector with the CloudWatch exporter.

Start the application stack with `docker compose up -d`. Verify all service health checks pass. Verify the orchestrator API is accessible from within the VPC on port 8000.

### 5.8 Application Load Balancer and TLS

Create the Application Load Balancer in the public subnets. Request a TLS certificate from AWS Certificate Manager for your domain. Create an HTTPS listener targeting the application server on port 8000. Configure the health check to hit `GET /api/v1/health` and expect a 200 response.

After the ALB is configured, verify the platform is accessible via HTTPS from your local browser. Run the same end-to-end test from Phase 2 checkpoint against the production URL. The full journey — symptom submission through post-discharge agent activation — should complete successfully against the AWS-hosted stack.

### 5.9 Phase 3 Checkpoint

Phase 3 is complete when all of the following are true:

- Both EC2 instances are running with no public IP addresses
- The application is accessible via HTTPS through the ALB only
- All credentials are in Secrets Manager — no credentials on instances or in code
- PostgreSQL and Redis data is on the encrypted EBS volume
- OpenSearch vector store returns the same test retrieval results as ChromaDB locally
- A full end-to-end test against the production URL completes successfully
- Systems Manager Session Manager is the only way to access the instances (port 22 is not open)
- AWS Cost Budget alert is configured

---

## 6. Phase 4 — CI/CD & Deployment Pipeline

**Goal:** Automate the build, test, and deployment process so that every code change on the main branch triggers a validated deployment to AWS with zero manual steps.  
**Duration:** 3–4 days  
**Output:** GitHub Actions pipeline that tests, builds, and deploys automatically on merge to main

---

### 6.1 Pipeline Design

As a solo developer, a CI/CD pipeline serves two purposes beyond automation. First, it enforces discipline — code that breaks tests cannot be deployed, even if you are in a hurry. Second, it creates a deployment audit trail — every deployment is recorded in GitHub Actions with a timestamp, commit hash, and test results. For a HIPAA workload, this is part of your change management record.

The pipeline has four stages that run sequentially:

**Stage 1 — Test:** Run the full test suite against a temporary local environment spun up in the GitHub Actions runner. This includes unit tests, integration tests against mock MCP servers, and the agent evaluation suite. If any test fails, the pipeline stops and the deployment does not proceed.

**Stage 2 — Build:** Build Docker images for all application services and push them to Amazon ECR. Tag each image with the Git commit hash. This tag is used in the deployment stage to ensure the exact code that passed tests is what gets deployed.

**Stage 3 — Deploy:** Connect to the EC2 application server via Systems Manager Session Manager (no SSH key required), pull the new images from ECR, and restart the application stack with `docker compose up -d --pull always`. The deployment is a rolling restart — services are restarted one at a time so the platform remains available during deployment.

**Stage 4 — Verify:** After deployment, run a smoke test against the production URL — a health check call and a simple end-to-end symptom submission with a known test patient. If the smoke test fails, the pipeline triggers an automatic rollback to the previous image tag.

### 6.2 GitHub Actions Configuration

Create a `.github/workflows/deploy.yml` file in the repository. The workflow triggers on push to the `main` branch and on pull request creation (test stage only for PRs — no deployment on PR).

The workflow requires the following secrets configured in GitHub:
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` — IAM credentials for the CI/CD pipeline user
- `AWS_REGION` — the deployment region
- `EC2_INSTANCE_ID` — the application server instance ID (for Systems Manager commands)
- `ECR_REGISTRY` — the ECR registry URL

Create a dedicated IAM user for the GitHub Actions pipeline with minimal permissions: ECR push access, Systems Manager send-command access to the specific EC2 instance, and read access to Secrets Manager for smoke test credentials. Do not reuse your development IAM user for the pipeline.

### 6.3 ECR Repository Setup

Create an ECR repository for each application service. ECR repositories support image scanning on push — enable this. Any image with a `CRITICAL` vulnerability should block the deployment stage.

Configure a lifecycle policy on each ECR repository to retain only the last 10 images. Without a lifecycle policy, old images accumulate and ECR storage costs grow unboundedly.

### 6.4 Database Migration Strategy

Schema changes require a migration strategy that does not break the running application during deployment. For a solo developer on a demo platform, a simple sequential migration approach is appropriate:

1. All schema changes are written as numbered migration SQL files in `data/schemas/migrations/`
2. The orchestrator service runs pending migrations at startup before accepting traffic
3. Migrations are additive only — new columns, new tables, new indexes. Destructive changes (dropping columns, changing types) require a two-step migration with a deprecation window
4. A `schema_migrations` table in PostgreSQL tracks which migrations have been applied

### 6.5 Rollback Procedure

The rollback procedure should be documented and tested before it is needed — not discovered during an outage.

To roll back to a previous version:
1. Identify the ECR image tag of the last known good deployment from the GitHub Actions deployment history
2. Update the Docker Compose production file to reference that image tag
3. Restart the stack via Systems Manager — `docker compose up -d` will pull and restart with the previous images
4. If the rollback requires a database migration rollback, run the down migration from the `data/schemas/migrations/` directory

Test this procedure before deploying the first production release.

### 6.6 Phase 4 Checkpoint

Phase 4 is complete when all of the following are true:

- A push to the `main` branch triggers the pipeline automatically
- The pipeline deploys to AWS only when all tests pass
- A failing test blocks deployment — verify this by intentionally breaking a unit test and confirming the pipeline stops
- A failed smoke test triggers automatic rollback — verify by deploying a version with a broken health endpoint
- Deployment history is visible in GitHub Actions with commit hashes and test results
- No deployment credentials are stored on the EC2 instance

---

## 7. Phase 5 — Post-Deployment Monitoring & Ops

**Goal:** Establish observability, alerting, and operational runbooks so the platform can be monitored and maintained reliably after go-live.  
**Duration:** 3–4 days (initial setup) + ongoing  
**Output:** CloudWatch dashboards, alert policies, and documented operational runbooks

---

### 7.1 CloudWatch Dashboard

Create a CloudWatch dashboard that provides a single-pane view of platform health. Organise the dashboard into three sections:

**System health:**
- EC2 CPU and memory utilisation for both instances
- ALB request count, error rate (4xx and 5xx), and latency (p50, p95, p99)
- EBS volume read/write IOPS
- PostgreSQL connection count and query latency (via CloudWatch custom metrics from the application)

**Agent performance:**
- Triage agent: requests per hour, average latency, error rate
- Diagnostics agent: average Self-RAG iterations per episode, lab order rate, confidence score distribution
- Treatment Planning agent: average Agentic RAG tool call count, plan generation latency
- Post-Discharge agent: active care plans, escalations per day, risk score distribution

**Business outcomes:**
- Care episodes completed per day
- Human-in-the-Loop approval queue depth and average approval time
- Post-discharge escalation rate
- 30-day readmission rate trend (updated daily from the SQL analytics layer)

### 7.2 Alerting Policy

Create CloudWatch Alarms for the following conditions. Each alarm should trigger an SNS notification to your email address.

**Critical alerts (require immediate response):**
- ALB 5xx error rate above 5% for more than 5 minutes
- EC2 CPU above 90% for more than 10 minutes
- PostgreSQL connection count above 80% of maximum
- Any HIPAA audit log write failure (custom metric from the application)
- OpenAI API error rate above 10% for more than 5 minutes (custom metric)

**Warning alerts (review within 1 business day):**
- ALB p99 latency above 10 seconds
- Post-discharge escalation rate above 20% of active care plans (indicates a potential data quality issue)
- Agent evaluation score below threshold (from the automated eval suite that runs nightly)
- ECR image scan finding a `HIGH` or `CRITICAL` vulnerability in a deployed image

### 7.3 OTLP Traces in CloudWatch

The OpenTelemetry collector running on the application EC2 instance is configured to export traces to AWS X-Ray. X-Ray provides a service map view showing the connections between the orchestrator, all four agents, and all MCP servers — with latency and error rate for each connection.

For each patient care episode, the full distributed trace is available in X-Ray for 30 days. This is the primary tool for investigating any episode where the agent produced an unexpected recommendation — you can open the trace and inspect every retrieval call, every reflection decision, and every tool call in sequence.

Configure X-Ray groups to separate traces by agent type. This makes it possible to analyse all Diagnostics Agent traces independently from Treatment Planning Agent traces when investigating performance issues.

### 7.4 Log Management and Retention

CloudWatch Log Groups are created automatically when the CloudWatch agent starts shipping logs from the EC2 instances. Configure the following retention policies:

- Application logs (agent reasoning, API requests): 90 days
- HIPAA audit logs (all PHI access events, approval events, authentication events): 7 years (HIPAA requires 6 years minimum — 7 is a sensible margin)
- Infrastructure logs (EC2 system logs, Docker daemon logs): 30 days

The HIPAA audit logs must be stored in a separate log group with a resource policy that prevents deletion. Create an S3 export for audit logs older than 90 days — S3 Glacier is the appropriate storage class for long-term HIPAA audit log archival.

### 7.5 Agent Evaluation — Nightly Run

The agent evaluation suite from Phase 2 should run automatically every night against the production environment using a dedicated synthetic test patient that is permanently present in the database.

The nightly eval run:
1. Submits 5 synthetic symptom scenarios (one per urgency level, covering the main clinical conditions)
2. Evaluates the triage urgency scores against the reference answers
3. Evaluates the diagnostic confidence scores and differential rankings
4. Evaluates the treatment plan structure and guideline citations
5. Writes evaluation scores as custom CloudWatch metrics

If any evaluation score drops below the acceptable threshold, the critical alert policy fires. This is the automated equivalent of a daily sanity check — it catches model drift, retrieval degradation, and subtle bugs introduced by code changes before they affect real (demo) patients.

### 7.6 Backup and Recovery

**PostgreSQL backups:**
- AWS Backup runs a daily snapshot of the EBS volume containing PostgreSQL data
- Snapshots are retained for 35 days
- Monthly snapshots are retained for 12 months
- Snapshots are copied to a second AWS region for disaster recovery

**Recovery procedure:**
- If the data server fails, launch a new EC2 instance from the latest EBS snapshot, attach the volume, and start the Docker containers
- Target recovery time: under 2 hours from failure detection to service restoration
- Target recovery point: under 24 hours of data loss maximum (daily snapshot cadence)

**Vector store backups:**
- The clinical guidelines corpus in OpenSearch Serverless is backed up via automated daily snapshots to S3
- Since the corpus is loaded from source documents stored in S3, a full rebuild from source is also a valid recovery option

### 7.7 Operational Runbooks

Document the following runbooks before go-live. A runbook is a step-by-step procedure for a specific operational task — written for yourself-in-six-months who may have forgotten the details.

**Runbook 1 — Adding new clinical guidelines to the vector store**
Steps: download new guideline PDF → upload to S3 → run the vector store loader script targeting the new file → run test retrieval queries → verify results are clinically coherent → update the document metadata registry.

**Runbook 2 — Scaling up the application server**
Steps: stop the Docker Compose stack → change the EC2 instance type via the AWS console (requires a stop/start) → restart the stack → verify all services healthy → run the smoke test.

**Runbook 3 — Responding to a HIPAA audit log write failure alert**
Steps: check CloudWatch Logs for the specific error → verify IAM role permissions for CloudWatch Logs → verify the log group exists and is not full → if the application is still running, investigate the error without restarting (to avoid losing in-memory state) → document the incident in the incident log regardless of severity.

**Runbook 4 — Rolling back a deployment**
Steps: identify the previous good image tag in GitHub Actions → update the Docker Compose production file → restart the stack via Systems Manager → run the smoke test → notify of rollback in the GitHub Actions run comments.

**Runbook 5 — Rotating the OpenAI API key**
Steps: generate a new API key in the OpenAI dashboard → update the secret in AWS Secrets Manager → restart the application stack (secrets are retrieved at startup) → verify the API is functioning via the smoke test → revoke the old API key in the OpenAI dashboard.

### 7.8 Phase 5 Checkpoint

Phase 5 is complete when all of the following are true:

- CloudWatch dashboard is populated with live data from all three sections
- All critical and warning alerts are configured and have been tested by triggering them manually
- Nightly evaluation run has completed at least once and written scores to CloudWatch Metrics
- HIPAA audit log retention policy is active and export to S3 Glacier is configured
- PostgreSQL daily backup has run and a test restore has been verified
- All five operational runbooks are written and stored in the project repository under `docs/runbooks/`

---

## 8. HIPAA Compliance Checklist

This checklist maps HIPAA Technical Safeguard requirements to specific platform implementation decisions. Use this as a verification list before going live with any real patient data.

### 8.1 Access Control

| Requirement | Implementation | Verified |
|---|---|---|
| Unique user identification | Each clinician has a unique JWT identity; each agent has a unique service principal | [ ] |
| Automatic logoff | JWT tokens expire after 8 hours; refresh requires re-authentication | [ ] |
| Encryption and decryption | All PHI accessed via the API layer — raw database access requires IAM role, not passwords | [ ] |
| Role-based access | RBAC enforced at API gateway and RAG retrieval layer | [ ] |

### 8.2 Audit Controls

| Requirement | Implementation | Verified |
|---|---|---|
| All PHI access logged | Every MCP server call that accesses patient data writes an audit event to CloudWatch Logs | [ ] |
| All approval events logged | HITL approval events written to PostgreSQL `approval_events` table and CloudWatch | [ ] |
| Log integrity | CloudWatch Log Groups configured to prevent deletion; logs are immutable after write | [ ] |
| 6-year retention | Audit logs retained for 7 years in CloudWatch + S3 Glacier | [ ] |

### 8.3 Integrity Controls

| Requirement | Implementation | Verified |
|---|---|---|
| PHI not improperly altered | PostgreSQL application user has INSERT and SELECT only — no UPDATE or DELETE on patient tables | [ ] |
| Audit log cannot be altered | CloudWatch log groups have resource policy preventing deletion or modification | [ ] |
| State store integrity | Redis persistence (AOF) ensures workflow state is not lost on restart | [ ] |

### 8.4 Transmission Security

| Requirement | Implementation | Verified |
|---|---|---|
| All external traffic encrypted | ALB enforces HTTPS; HTTP redirected to HTTPS | [ ] |
| All internal traffic encrypted | MCP server calls use HTTPS within the VPC; PostgreSQL SSL required | [ ] |
| OpenAI API calls encrypted | HTTPS enforced by the OpenAI client library | [ ] |
| S3 access encrypted | Bucket policy requires `aws:SecureTransport` condition | [ ] |

### 8.5 PHI Minimisation

| Requirement | Implementation | Verified |
|---|---|---|
| LLM context minimisation | Agent prompts receive structured patient data (diagnosis codes, lab values) not free-text notes containing names | [ ] |
| Telemetry PHI scrubbing | OTel collector configured with a PHI redaction processor before export to CloudWatch | [ ] |
| Logging PHI exclusion | Application logs use patient episode IDs, not patient names or identifiers | [ ] |

---

## 9. AWS Services Reference Map

| AWS Service | Role in Platform | Tier |
|---|---|---|
| EC2 t3.large | Application server — runs orchestrator, agents, MCP servers as Docker containers | Core |
| EC2 t3.medium | Data server — runs PostgreSQL and Redis as Docker containers | Core |
| Application Load Balancer | HTTPS termination, health checking, routing to application server | Core |
| S3 | FHIR file storage, audit log archival, document corpus, deployment artefacts | Core |
| AWS Secrets Manager | All credentials and API keys — retrieved at runtime | Core |
| Amazon OpenSearch Serverless | Production vector store for clinical guidelines corpus | Core |
| Amazon ECR | Docker image registry for all application services | Core |
| AWS Certificate Manager | TLS certificate for the ALB HTTPS listener | Core |
| Amazon CloudWatch | Logs, metrics, dashboards, alarms | Observability |
| AWS X-Ray | Distributed tracing from OTLP collector | Observability |
| AWS Backup | Daily EBS snapshots for PostgreSQL data volume | Resilience |
| AWS Systems Manager | Session Manager for instance access (replaces SSH) | Operations |
| Amazon SNS | Alert notifications from CloudWatch Alarms | Operations |
| Amazon VPC | Network isolation — all resources in private subnets except ALB | Security |
| AWS KMS | Encryption key management for EBS, S3, OpenSearch | Security |
| AWS IAM | Instance roles, CI/CD pipeline user, least-privilege policies | Security |

---

## 10. Solo Developer Day-by-Day Schedule

This schedule assumes 6–8 focused hours per day. Adjust for part-time availability by stretching each phase proportionally.

| Week | Days | Phase | Focus |
|---|---|---|---|
| Week 1 | Days 1–2 | Phase 1 | Install Synthea, generate population, inspect output |
| Week 1 | Days 3–4 | Phase 1 | FHIR-to-relational transformation, PostgreSQL loading |
| Week 1 | Day 5 | Phase 1 | Faker extensions, vector store loading, Phase 1 checkpoint |
| Week 2 | Days 6–7 | Phase 2 | Project structure, Docker Compose, MCP servers |
| Week 2 | Days 8–9 | Phase 2 | Intake chain, Triage Agent, Enterprise RAG |
| Week 2 | Days 10–11 | Phase 2 | Diagnostics Agent, Self-RAG loop, lab waiting |
| Week 3 | Days 12–14 | Phase 2 | Treatment Planning Agent, Agentic RAG, care plan schema |
| Week 3 | Days 15–16 | Phase 2 | HITL mechanism, Post-Discharge Agent, SQL analytics |
| Week 3 | Day 17 | Phase 2 | REST API gateway, OTLP wiring, Phase 2 checkpoint |
| Week 4 | Days 18–19 | Phase 3 | VPC, subnets, security groups, IAM roles |
| Week 4 | Days 20–21 | Phase 3 | EC2 instances, PostgreSQL + Redis on data server |
| Week 4 | Days 22–23 | Phase 3 | OpenSearch, Secrets Manager, application deployment |
| Week 4 | Day 24 | Phase 3 | ALB, TLS, end-to-end test on AWS, Phase 3 checkpoint |
| Week 5 | Days 25–26 | Phase 4 | ECR repositories, GitHub Actions pipeline skeleton |
| Week 5 | Days 27–28 | Phase 4 | Test stage, build stage, deploy stage, rollback |
| Week 5 | Day 29 | Phase 4 | Pipeline verification, Phase 4 checkpoint |
| Week 6 | Days 30–31 | Phase 5 | CloudWatch dashboard, alerting policy |
| Week 6 | Days 32–33 | Phase 5 | Nightly eval run, backup configuration |
| Week 6 | Day 34 | Phase 5 | Runbooks, HIPAA checklist verification, Phase 5 checkpoint |
| Week 6 | Day 35 | Buffer | Catch-up, documentation, final end-to-end demo run |

---

## 11. Risk Register & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OpenAI API rate limits during agent testing | Medium | High | Implement exponential backoff in all OpenAI calls; set per-agent rate limit budgets; use GPT-3.5 for development, GPT-4o for evaluation |
| LangGraph state corruption during development | Medium | Medium | Always test checkpoint persistence explicitly; keep a clean database snapshot to restore from |
| PostgreSQL container data loss on EC2 restart | Low | High | EBS volume persistence; daily AWS Backup snapshots; test restore procedure before go-live |
| OpenAI API key exposure in logs | Medium | Critical | PHI + secrets redaction in OTel collector; structured logging that never serialises the full request headers |
| Synthea FHIR schema changes between versions | Low | Medium | Pin the Synthea version in the project documentation; do not upgrade mid-project |
| Agent reasoning loop running indefinitely | Medium | Medium | Maximum iteration counts on all loops; timeout on all MCP server calls; circuit breaker on OpenAI calls |
| AWS costs exceeding budget | Medium | Low | Cost Budget alert set before any infrastructure is provisioned; use t3 instances not t3a; stop instances when not in use |
| HIPAA audit log gap during deployment | Low | High | Deployment pipeline includes a pre-deployment checkpoint confirming audit logging is active; rolling restart ensures no gap |
| Vector store retrieval degradation after guideline updates | Medium | Medium | Nightly evaluation suite includes retrieval quality checks; alert fires if scores drop |
| Solo developer knowledge bus factor | High | High | All runbooks written; architecture decisions documented in ADRs (Architecture Decision Records) in the repository |

---

*This guide covers the complete implementation journey for a solo developer. Each phase checkpoint is a hard gate — do not advance until it is met. The schedule is aggressive but achievable with focused daily effort. The most common failure mode is skipping local validation in Phase 2 and discovering integration issues on AWS in Phase 3 — resist that temptation.*

*All synthetic patient data used throughout this guide is generated by Synthea and Python Faker. No real patient data should be used at any stage of development or testing.*
