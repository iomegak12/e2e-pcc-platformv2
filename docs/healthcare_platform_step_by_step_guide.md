# AI-Powered Patient Care Coordination Platform
## Step-by-Step Implementation Guide

**Stack:** Python · OpenAI API · LangChain · LangGraph · PostgreSQL · Redis · ChromaDB · FastAPI · Docker · AWS EC2 + Managed Services
**Dataset:** Synthea FHIR + Custom Tabular SQL (Faker)
**Compliance:** HIPAA
**Deployment:** AWS EC2 with managed services
**Format:** Phase-separated — no code, no scripts, no notebooks

---

## How to Use This Guide

Each phase is self-contained. Read the entire phase before starting any step within it. Complete every verification step before moving to the next action. Do not start a new phase until the phase checklist at the end is fully satisfied.

When a step says "verify," stop and confirm the stated condition is true before proceeding. A verification failure is information — it tells you exactly where a problem exists. Proceeding past a failed verification embeds the problem deeper and makes it harder to diagnose later.

---

## Table of Contents

- [Phase 0 — Foundations and Accounts](#phase-0--foundations-and-accounts)
- [Phase 1 — Data Synthesis and Preparation](#phase-1--data-synthesis-and-preparation)
- [Phase 2 — Local Environment and Infrastructure](#phase-2--local-environment-and-infrastructure)
- [Phase 3 — MCP Tool Servers](#phase-3--mcp-tool-servers)
- [Phase 4 — LangChain Intake Chain](#phase-4--langchain-intake-chain)
- [Phase 5 — Symptom Triage Agent](#phase-5--symptom-triage-agent)
- [Phase 6 — Diagnostics Agent](#phase-6--diagnostics-agent)
- [Phase 7 — Treatment Planning Agent](#phase-7--treatment-planning-agent)
- [Phase 8 — Human-in-the-Loop Mechanism](#phase-8--human-in-the-loop-mechanism)
- [Phase 9 — Post-Discharge Agent](#phase-9--post-discharge-agent)
- [Phase 10 — Orchestrator REST API](#phase-10--orchestrator-rest-api)
- [Phase 11 — Observability Layer](#phase-11--observability-layer)
- [Phase 12 — AWS Infrastructure](#phase-12--aws-infrastructure)
- [Phase 13 — Production Deployment](#phase-13--production-deployment)
- [Phase 14 — CI/CD Pipeline](#phase-14--cicd-pipeline)
- [Phase 15 — Monitoring and Operations](#phase-15--monitoring-and-operations)

---

## Phase 0 — Foundations and Accounts

### Purpose
Establish all accounts, credentials, and local tooling before any application work begins. Every gap discovered here costs less to fix now than when discovered mid-build.

---

### Step 0.1 — Create and Secure the OpenAI Account

Go to the OpenAI platform website and create an account if you do not have one. Navigate to the API keys section and generate a new secret key. Copy the key immediately — it is shown only once.

In the OpenAI dashboard, set a hard monthly spend limit. Choose a value that represents a comfortable ceiling for development use. This prevents a runaway agent loop from generating unexpected charges.

Store the API key temporarily in a plain text file on your local machine that is outside any project directory. You will move it to a proper secrets store in Step 0.6.

**Verify:** Make a manual API call to the OpenAI completions endpoint using a tool such as Postman or curl, passing the key in the Authorization header. Confirm you receive a valid response. If the call fails, the key was not copied correctly — regenerate it.

---

### Step 0.2 — Create and Secure the AWS Account

Go to the AWS website and create an account. During signup, provide a billing method. Once the account is active, immediately navigate to the IAM section and enable multi-factor authentication on the root account. Do not use the root account for any operational task after this point.

In the IAM console, create a new IAM user named after the project. Attach the following AWS-managed policies to this user: AmazonEC2FullAccess, AmazonS3FullAccess, SecretsManagerReadWrite, AmazonOpenSearchServiceFullAccess, CloudWatchFullAccess, AmazonECR-FullAccess. Generate programmatic access credentials for this user and store them temporarily alongside your OpenAI key.

Navigate to AWS Budgets and create a monthly cost budget. Set the alert threshold at a value that will notify you before costs become a concern. Provide your email address for notifications.

**Verify:** In the AWS console, confirm the IAM user appears with the correct policies attached. Confirm the budget appears in AWS Budgets with an active status.

---

### Step 0.3 — Create the GitHub Repository

Log in to GitHub and create a new private repository for the project. Do not initialise it with a README yet.

Enable branch protection on the main branch. In the branch protection settings, require pull request reviews before merging and require status checks to pass before merging. Even as a solo developer, this discipline prevents accidental direct pushes to main.

Clone the empty repository to your local machine.

**Verify:** Confirm the repository exists on GitHub, the main branch is protected, and the local clone is connected to the remote by pushing an empty initial commit.

---

### Step 0.4 — Install Local Tooling

Install the following tools in this order. Verify each one after installation before installing the next.

Install Python 3.11 or later. Verify by checking the version in your terminal — the output must show version 3.11 or above.

Install Docker Desktop. After installation, start Docker Desktop and wait for it to report that the Docker engine is running. Verify by running a hello-world container from the terminal.

Install Git if it is not already present. Verify by checking the version in your terminal.

Install the AWS CLI version 2. After installation, configure it by running the AWS configure command and providing the IAM user credentials from Step 0.2, your chosen AWS region, and JSON as the default output format. Verify by running a simple AWS CLI command — for example, listing S3 buckets — and confirming it returns a valid response.

Install a code editor. VS Code with the Python extension is the recommended choice.

Install jq, a command-line JSON processor. You will use this throughout the guide to inspect API responses.

**Verify:** Open a fresh terminal window and confirm each tool — Python, Docker, Git, AWS CLI, jq — is accessible by name without specifying a full path.

---

### Step 0.5 — Establish the Project Directory Structure

Inside the cloned repository directory, create the following folder structure. Do not add any files yet — only create the folders.

Create a top-level folder named `agents` with four subfolders: `triage`, `diagnostics`, `treatment`, and `discharge`.

Create a top-level folder named `orchestrator`.

Create a top-level folder named `mcp_servers` with four subfolders: `ehr`, `lab`, `pharmacy`, and `appointments`.

Create a top-level folder named `data` with two subfolders: `schemas` and `seeds`.

Create a top-level folder named `vector_store`.

Create a top-level folder named `config`.

Create a top-level folder named `tests` with two subfolders: `unit` and `integration`.

Create a top-level folder named `docker`.

Create a top-level folder named `docs` with a subfolder named `runbooks`.

Create a top-level folder named `infra`.

At the repository root, create a file named `.env.example`. In this file, write one line per environment variable the system will need, using the variable name only with no values. The variables to list are: `OPENAI_API_KEY`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `REDIS_HOST`, `REDIS_PORT`, `CHROMADB_HOST`, `CHROMADB_PORT`, `JWT_SECRET`, `AWS_REGION`, `S3_BUCKET_NAME`, `OPENSEARCH_ENDPOINT`.

Create a file named `.gitignore` at the repository root. Add entries for: `.env`, `__pycache__`, `.pytest_cache`, `*.pyc`, `node_modules`, `.DS_Store`, and any IDE-specific folders.

Commit this structure to the repository.

**Verify:** Confirm all folders exist in the correct hierarchy. Confirm `.env.example` is committed and visible on GitHub. Confirm `.env` does not appear in the repository.

---

### Step 0.6 — Set Up Secrets Management

Create a file named `.env` at the root of the project directory. This file is gitignored and will never be committed. Place the actual values for all variables listed in `.env.example`. Set `OPENAI_API_KEY` to the key from Step 0.1. Leave database and service variables as placeholders for now.

Delete the temporary files where you stored credentials in Steps 0.1 and 0.2.

**Verify:** Confirm `.env` is not tracked by Git by checking the git status output.

---

### Phase 0 Checklist

- [ ] OpenAI API key is active and a test call returns a valid response
- [ ] AWS account has MFA on root and a dedicated IAM user with programmatic credentials
- [ ] AWS Cost Budget is active with an email alert configured
- [ ] GitHub repository is created, main branch is protected, and the local clone is connected
- [ ] Python 3.11+, Docker, Git, AWS CLI, and jq are all accessible from a fresh terminal
- [ ] Project directory structure is committed to the repository
- [ ] `.env` file exists locally with the OpenAI key populated and is not tracked by Git

---

## Phase 1 — Data Synthesis and Preparation

### Purpose
Generate a realistic synthetic healthcare dataset covering all clinical scenarios the platform agents will reason over. This phase produces: a populated PostgreSQL database, a loaded vector store, and FHIR patient files in S3.

---

### Step 1.1 — Install Java for Synthea

Synthea is a Java application. Install Java Development Kit version 11 or later on your local machine. After installation, verify the Java version in your terminal. The output must confirm version 11 or above.

**Verify:** Running the Java version check command in a fresh terminal returns the correct version without errors.

---

### Step 1.2 — Download and Configure Synthea

Go to the Synthea GitHub repository and download the latest stable release JAR file. Save it to a folder outside your project directory — for example, a folder named `synthea-tool` in your home directory.

In the same folder, create a Synthea configuration file. Set the export format to FHIR R4. Enable the conditions relevant to the platform's clinical scenarios: iron deficiency anaemia, chronic kidney disease, type 2 diabetes, hypertension, and COPD. Set the population age range to 30 through 75. Set the target population size to 500 patients.

**Verify:** The configuration file is in place alongside the JAR file. Confirm the JAR file size is reasonable — a truncated download will fail silently.

---

### Step 1.3 — Generate the Synthetic Population

Run Synthea from the command line, pointing it at the configuration file and specifying an output directory inside your project under `data/synthea-output`. Do not interrupt the process.

When Synthea completes, open three patient files at random in your text editor. In each file, confirm the presence of the following FHIR resource types within the Bundle entries: Patient, Encounter, Condition, Observation, MedicationRequest. If any resource type is missing across all three sample files, the configuration did not enable it correctly — adjust and regenerate.

**Verify:** The output directory contains approximately 500 JSON files plus one index file. Three randomly sampled files each contain Patient, Encounter, Condition, Observation, and MedicationRequest resources.

---

### Step 1.4 — Design the Relational Database Schema

Before transforming any Synthea data, design the relational schema the application will use. Document the decisions in `docs/schema-design.md`.

The schema consists of the following 13 tables. For each, define column names, data types, primary keys, foreign keys, and indexes.

The `patients` table holds one row per patient with: UUID primary key (from Synthea), date of birth, gender, site identifier, registration timestamp, and active status.

The `clinicians` table holds one row per care provider with: UUID primary key, full name, specialty, ward assignment, and site identifier. Populated by Faker.

The `admissions` table holds one row per hospital visit with: UUID primary key, patient UUID (foreign key), encounter start and end timestamps, encounter type, primary diagnosis ICD-10 code, ward identifier, attending clinician UUID (foreign key), and discharge status.

The `diagnoses` table holds one row per confirmed diagnosis per encounter with: UUID primary key, patient UUID, encounter UUID, ICD-10 code, diagnosis name, confidence score (0 to 1 decimal), source (which agent or clinician), and diagnosis timestamp.

The `lab_results` table holds one row per lab test result with: UUID primary key, patient UUID, encounter UUID, LOINC code, test name, numeric value, unit, reference range low, reference range high, result status, and collection timestamp.

The `medications` table holds one row per medication order with: UUID primary key, patient UUID, encounter UUID, drug name, dose, unit, route, frequency, start date, end date, prescribing clinician UUID, and status.

The `vitals` table holds one row per vital sign measurement with: UUID primary key, patient UUID, encounter UUID, measurement type, numeric value, unit, and measurement timestamp.

The `pharmacy_events` table holds one row per pharmacy interaction with: UUID primary key, patient UUID, medication UUID (foreign key), event type (dispensed, refilled, missed), scheduled date, actual date, and gap in days. Fully Faker-generated.

The `discharge_plans` table holds one row per active care plan with: UUID primary key, patient UUID, admission UUID (foreign key), plan type, start date, target end date, assigned agent identifier, risk score, risk score updated timestamp, status, and completion percentage.

The `wearable_readings` table holds one row per daily wearable data point with: UUID primary key, patient UUID, discharge plan UUID (foreign key), reading date, heart rate, SpO2, blood pressure systolic and diastolic, steps, and an anomaly flag. Fully Faker-generated.

The `approval_events` table holds one row per Human-in-the-Loop decision with: UUID primary key, care episode UUID, approval task type, status, clinician UUID, submitted timestamp, decided timestamp, clinician notes, and the full plan payload as JSON.

The `audit_log` table holds one row per PHI access event with: UUID primary key, actor type, actor identifier, action type, resource type, resource identifier, timestamp, and requester source.

The `schema_migrations` table holds one row per applied database migration with: migration ID, migration name, and applied timestamp.

Define indexes on the following column combinations which correspond directly to the SQL analytics queries:

- `admissions(patient_id, discharge_date)` for cohort readmission queries
- `admissions(primary_diagnosis_code, discharge_date)` for diagnosis-specific cohort scoring
- `lab_results(patient_id, test_name, collected_at)` for time-series lab lookups
- `vitals(patient_id, measurement_type, measurement_timestamp)` for baseline calculations
- `wearable_readings(patient_id, reading_date)` for anomaly detection
- `pharmacy_events(patient_id, scheduled_date)` for adherence gap queries
- `discharge_plans(status, risk_score_updated_at)` for active plan monitoring

**Verify:** The schema design document exists in `docs/schema-design.md`, covers all 13 tables, and specifies indexes for all seven analytics query patterns.

---

### Step 1.5 — Stand Up Local PostgreSQL

In the `docker` folder, create a Docker Compose file for infrastructure services only — PostgreSQL, Redis, ChromaDB, and the OpenTelemetry Collector.

In this file, define a PostgreSQL service using the official PostgreSQL 15 image. Set the database name, user, and password using values from your `.env` file. Mount a named Docker volume as the data directory. Start only the PostgreSQL service.

Connect to the running PostgreSQL container using a database administration tool such as DBeaver or psql. Create the database schema: go table by table following the design document, creating all columns, constraints, foreign keys, and indexes. After all tables are created, insert one row in `schema_migrations` recording this as migration version 1.

**Verify:** Connect to the database and list all tables — confirm all 13 exist. Query `schema_migrations` and confirm one row exists. Run an explain plan on one of the indexed analytics queries to confirm the planner uses the indexes.

---

### Step 1.6 — Transform Synthea FHIR Data into the Relational Schema

Transform the Synthea FHIR JSON output into the relational tables. Process tables in dependency order: patients first, then admissions, diagnoses, lab_results, medications, and vitals.

For `patients`: read the Patient resource from each bundle. Extract the UUID, birthDate, and gender. Assign all patients to site identifier "hospital-a".

For `admissions`: read Encounter resources. Extract the encounter UUID, patient reference, start and end timestamps, encounter class code (map IMP to inpatient, AMB to outpatient, EMER to emergency), and reasonCode as the primary diagnosis code where present.

For `diagnoses`: read Condition resources. Extract Condition UUID, patient reference, encounter reference, and ICD-10 code from the coding array. Set confidence score to 1.0 and source to "synthea".

For `lab_results`: read Observation resources where category is "laboratory". Extract LOINC code, value from valueQuantity, unit, and effectiveDateTime. Map the following LOINC codes to human-readable names: haemoglobin (718-7), ferritin (2276-4), serum iron (2498-4), TIBC (2500-7), HbA1c (4548-4), eGFR (33914-3), creatinine (2160-0), B12 (2132-9), folate (2284-8).

For `vitals`: read Observation resources where category is "vital-signs". Extract heart rate (8867-4), blood pressure systolic (8480-6), blood pressure diastolic (8462-4), SpO2 (2708-6), and body weight (29463-7).

For `medications`: read MedicationRequest resources. Extract drug name from medicationCodeableConcept display, dosageInstruction fields, and authoredOn as start date.

For `clinicians`: generate 50 records using Faker. Assign specialties evenly across: general medicine, haematology, nephrology, endocrinology, and cardiology. Then update the admissions table to assign a randomly selected clinician UUID to each admission.

**Verify:** Run row count queries on each table. Expected approximate counts for 500 patients: 500 patients, 50 clinicians, 3,000–8,000 admissions, 5,000–15,000 diagnoses, 20,000–60,000 lab results, 10,000–30,000 medications, 30,000–80,000 vitals. If any table is empty, the FHIR resource type was not found — check the Synthea configuration.

---

### Step 1.7 — Generate Faker Extension Tables

With core Synthea data loaded, generate the operational tables Synthea does not produce.

For `discharge_plans`: identify all inpatient admissions where the encounter has ended. For each, create one discharge plan row. Set the plan type based on the primary diagnosis code — IDA gets "anaemia-followup", CKD gets "renal-followup", diabetes gets "diabetes-management", others get "general-followup". Set start date to the discharge date, target end date to 90 days later, status to "active", and initial risk score to a random value between 20 and 45.

For `pharmacy_events`: for each active medication, generate a dispensed event on the start date and monthly refill events. For 18% of medications, introduce one missed refill event where the actual date is 4–12 days later than scheduled. For 5% of medications, introduce a complete gap with no actual date.

For `wearable_readings`: for each active discharge plan, generate one row per day from the plan start date to today. Use the patient's most recent vitals as the baseline mean. Add small random variance (within plus or minus 5% of the mean) to simulate normal daily fluctuation.

For 10% of discharge plans selected randomly, introduce an anomaly trend starting at day 18: progressively increase heart rate by 1–2 beats per day and decrease SpO2 by 0.2–0.4 percentage points per day. Set the anomaly flag to true for these rows from day 18 onward. These patients must be identifiable by the Post-Discharge Agent's anomaly detection query.

**Verify:** Query discharge_plans — all should have status "active". Query pharmacy_events grouped by event_type and confirm dispensed, refilled, and missed events all exist. Query wearable_readings where anomaly flag is true and confirm results for approximately 10% of patients who have discharge plans.

---

### Step 1.8 — Validate the SQL Analytics Queries

Manually run all five SQL analytics query patterns against the loaded data. If any query exceeds 2 seconds, use the explain plan to identify the slow step and add or adjust an index before proceeding.

The readmission cohort query: given a primary diagnosis ICD-10 code and patient age range, returns the fraction of historical patients with that diagnosis who were readmitted within 30 days. A second admission row for the same patient with a start date within 30 days of the first discharge defines readmission. Confirm it returns a decimal between 0 and 1 for the IDA code.

The medication adherence drop-off query: given a patient UUID, returns all medications where the gap between scheduled and actual refill exceeds 3 days, or where a scheduled refill has no actual date. Confirm it returns results for patients in the Faker-introduced missed refill group.

The vital sign anomaly detection query: for a given patient UUID, calculates the mean and standard deviation of each vital sign type over the first 14 days of their discharge plan, then identifies readings after day 14 that fall more than 2 standard deviations from that baseline. Confirm it identifies the anomaly-flagged patients by approximately day 20–22.

The outcome KPI query: returns the 30-day readmission rate grouped by primary diagnosis code. Confirm it returns one row per distinct diagnosis code with a readmission rate decimal.

The population segmentation query: computes a composite risk score for all active discharge plans. The composite weights cohort readmission rate at 40%, pharmacy adherence gap normalised at 30%, proportion of anomaly-flagged wearable readings at 20%, and days since last wearable reading at 10%. Returns all active plans ordered by composite score descending. Confirm the anomaly-seeded patients appear in the top 15% of results.

**Verify:** All five queries return results. All five complete in under 2 seconds. The anomaly detection query identifies the correct seeded patients. The segmentation query ranks seeded anomaly patients in the top 15%.

---

### Step 1.9 — Upload FHIR Files to S3

In the AWS console, create an S3 bucket in your target region with: block all public access, versioning enabled, server-side encryption SSE-S3, and no static website hosting.

After the bucket is created, add a bucket policy that denies any request that does not use HTTPS.

Using the AWS CLI, upload the entire Synthea output directory to the bucket under the prefix `synthea-fhir/patients/`. After upload, list the objects under that prefix and confirm the count matches the number of generated patient files.

**Verify:** The S3 bucket exists with versioning and encryption enabled. Public access is blocked. The bucket policy requires HTTPS. The CLI list command shows the correct file count.

---

### Step 1.10 — Prepare the Clinical Guidelines Corpus

Download the following publicly available clinical guideline documents as PDF files. Save them to `data/guidelines/`.

Download: NICE guideline NG203 (iron deficiency anaemia), NICE guideline NG28 (type 2 diabetes), NICE guideline CG182 (chronic kidney disease), British Society for Haematology guideline on iron deficiency, WHO primary care guidelines for anaemia, and BNF drug monographs for iron sucrose, ferrous sulphate, metformin, lisinopril, and amlodipine.

For each downloaded document, confirm it is a readable PDF — text must be selectable. Scanned image-only PDFs cannot be text-extracted.

Create a document registry file at `data/guidelines/registry.md`. For each document, record: document title, issuing organisation, publication year, version number, local filename, and clinical topics covered.

**Verify:** All PDF files are readable with selectable text. The registry documents all files with publication details.

---

### Step 1.11 — Load the Vector Store

Add a ChromaDB service to the infrastructure Docker Compose file using the ChromaDB server image with a persistent volume mount. Start the ChromaDB container.

For each guideline document, follow this loading sequence:

Extract text from the PDF page by page, preserving page numbers for metadata.

Chunk the text at 600 tokens with 60-token overlap between adjacent chunks. Clinical guidelines are dense — this size balances context depth with retrieval precision.

Embed each chunk using the OpenAI `text-embedding-3-small` model. This must be the same model used at query time — using different models for indexing and querying makes similarity scores meaningless.

Store each chunk with its embedding and metadata: source document name, page number, chunk index, topic tags from the registry, and publication year.

Load documents in this order: NICE NG203, BNF iron sucrose, BNF ferrous sulphate, BSH iron guideline, NICE NG28, BNF metformin, NICE CG182, BNF lisinopril, BNF amlodipine, WHO anaemia guidelines.

After loading all documents, run three retrieval test queries via the ChromaDB HTTP API and inspect the top 5 returned chunks for each:

Query 1: "iron deficiency anaemia treatment oral versus intravenous." Returned chunks should be from iron deficiency guidelines or BNF iron monographs addressing treatment route selection.

Query 2: "chronic kidney disease stage 3 iron absorption." Returned chunks should include content from the CKD guideline or iron guidelines discussing renal implications.

Query 3: "metformin contraindications renal impairment eGFR." Returned chunks should include the BNF metformin monograph and ideally diabetes or CKD guidelines.

**Verify:** ChromaDB returns a non-zero collection count. All three test queries return 5 chunks each. The returned chunks are clinically relevant — reading them confirms they address the query topic directly.

---

### Phase 1 Checklist

- [ ] Synthea generated 500 patients with target conditions present in FHIR bundles
- [ ] All 13 database tables are created with correct columns, keys, and indexes
- [ ] Row counts match expected ranges for a 500-patient dataset
- [ ] All five SQL analytics queries return correct results in under 2 seconds
- [ ] Faker-seeded anomaly patients appear in the top 15% of the population segmentation query
- [ ] FHIR files are in S3 with encryption and HTTPS-only access
- [ ] All guideline PDFs are readable and in the registry
- [ ] ChromaDB is running with all documents loaded
- [ ] All three vector store test queries return clinically relevant results

---

## Phase 2 — Local Environment and Infrastructure

### Purpose
Define and validate the complete local Docker Compose stack. Establishing the full service topology before writing agent code prevents integration surprises later.

---

### Step 2.1 — Add Redis to the Infrastructure Stack

In the infrastructure Docker Compose file, add a Redis 7 service with append-only file persistence enabled. Mount a named volume for the Redis data directory. Start Redis alongside PostgreSQL and ChromaDB.

Connect to the Redis container using redis-cli inside the container. Run the ping command and confirm it returns PONG. Run a set followed by a get to confirm read and write operations work.

**Verify:** Redis is running and responds to ping. A value written with set is correctly returned by get. The AOF persistence file exists in the mounted volume directory.

---

### Step 2.2 — Add the OpenTelemetry Collector

In the infrastructure Docker Compose file, add an OpenTelemetry Collector service. For local development, configure the collector to receive OTLP traces over gRPC and write them to a JSON file in a mounted volume directory.

Create a collector configuration file in the `config` folder defining: a receiver accepting OTLP gRPC on port 4317, a batching processor, and a file exporter writing to the mounted volume.

**Verify:** The collector container starts without errors. The JSON output file is created in the mounted volume directory.

---

### Step 2.3 — Create the Application Docker Compose File

Create `docker-compose.app.yml` at the project root. This file defines all nine application services — the orchestrator, four agents, and four MCP servers — on the same Docker network as the infrastructure compose file.

For each service, define: a name, a build context pointing to the relevant folder, a health check, and environment variables sourced from the `.env` file. The nine services are: orchestrator (port 8000), agent-triage, agent-diagnostics, agent-treatment, agent-discharge, mcp-ehr (port 8001), mcp-lab (port 8002), mcp-pharmacy (port 8003), mcp-appointments (port 8004).

Configure `depends_on` with `condition: service_healthy` so the orchestrator does not start until all four MCP servers are healthy.

**Verify:** The Docker Compose file parses without errors. The dependency chain is correct — confirm by running docker compose config and reviewing the resolved configuration.

---

### Step 2.4 — Create Base Dockerfiles

In each of the nine application service folders, create a Dockerfile. All use the same base structure: Python 3.11 slim image, working directory, copy requirements file, install dependencies, specify run command. The requirements files are empty and commands are placeholders for now.

Confirm that `docker compose build` runs without errors against both compose files.

**Verify:** All service images appear in the local Docker image list after the build.

---

### Step 2.5 — Confirm Full Stack Startup

Start the infrastructure stack. Confirm all four infrastructure services — PostgreSQL, Redis, ChromaDB, OpenTelemetry Collector — are running and healthy. Connect to each one to confirm accessibility.

**Verify:** All infrastructure services report healthy status. The Docker network is created and all services are attached to it.

---

### Phase 2 Checklist

- [ ] Redis is running with AOF persistence and responds to read/write commands
- [ ] OTel Collector is running and the JSON output file exists
- [ ] Application Docker Compose defines all nine services with correct dependencies
- [ ] Base Dockerfiles exist in all nine service folders
- [ ] `docker compose build` succeeds without errors
- [ ] All infrastructure services are healthy and accessible from within the Docker network

---

## Phase 3 — MCP Tool Servers

### Purpose
Build the four MCP servers before any agent. Agents are only as reliable as the tools they call. Each server must be independently functional and testable before being connected to an agent.

---

### Step 3.1 — Define the MCP Server Contract

Document the API contract for all four servers in `docs/mcp-contracts.md`. For each server, specify every endpoint: path, HTTP method, request body fields with types, response body fields with types, and error codes for invalid input, unauthorised access, and not-found conditions.

This document is the specification you build against and test against. If the contract changes, all dependent agents must be updated.

**Verify:** The contracts document covers all four servers, all endpoints per server, and specifies request and response field types precisely.

---

### Step 3.2 — Build the EHR MCP Server

In the `mcp_servers/ehr` folder, build a FastAPI application implementing the EHR access contract.

The server exposes one primary endpoint: a POST endpoint accepting a patient UUID and a list of requested resource types (demographics, conditions, lab_results, medications, vitals, encounters). For each requested type, it queries the corresponding database table and assembles the results into a structured JSON response.

Before any database query, the server validates: the patient UUID must be valid UUID format, and all requested resource types must be from the allowed list. A missing or invalid Authorization header returns 401. An unknown patient UUID returns 404. Invalid resource types return 400.

Update the Dockerfile, rebuild the image, and start the EHR server in isolation.

**Verify:** A valid request returns correct patient data. A request for an unknown patient returns 404. A request without Authorization returns 401. A request with malformed UUID returns 400.

---

### Step 3.3 — Build the Lab MCP Server

In the `mcp_servers/lab` folder, build a FastAPI application implementing the lab contract.

The server exposes two endpoints.

The order submission endpoint accepts a patient UUID, encounter UUID, and list of test names. It inserts a pending lab result row with status "pending", a `result_available_at` timestamp 30 minutes in the future, and null result values. It returns the order UUID and estimated availability timestamp.

The result retrieval endpoint accepts a patient UUID and test name. It queries for the most recent result. If status is "pending" and the `result_available_at` has not passed, it returns 202 with the estimated time. If `result_available_at` has passed and status is still "pending", it updates the row with a simulated result value generated randomly within the reference range and returns the completed result.

**Verify:** A lab order inserts a pending row and returns the order UUID. A retrieval within the 30-minute window returns 202. A retrieval after 30 minutes returns a completed result with a value.

---

### Step 3.4 — Build the Pharmacy MCP Server

In the `mcp_servers/pharmacy` folder, build a FastAPI application implementing the pharmacy contract.

The server exposes three endpoints.

The interaction check endpoint accepts a list of drug names and queries a pre-loaded interaction table. Return any interactions found, each with the two drug names and severity level.

The formulary check endpoint accepts a drug name and site identifier and queries a formulary table. Return availability, formulations, and any restrictions.

The prescription submission endpoint accepts a patient UUID, drug name, dose, route, frequency, and clinician UUID. Insert a new row in the medications table and return the medication UUID.

Before building the server, create and populate the interaction and formulary tables in PostgreSQL. The interaction table needs at minimum: iron sucrose with ACE inhibitor (low severity), metformin with iodinated contrast (high severity), warfarin with NSAIDs (high severity). The formulary table needs entries for all drugs used in platform scenarios at site "hospital-a".

**Verify:** The interaction check returns known interactions and an empty list for unknown combinations. The formulary check returns availability for in-table drugs and not-found for others. A prescription submission inserts a row in medications.

---

### Step 3.5 — Build the Appointments MCP Server

In the `mcp_servers/appointments` folder, build a FastAPI application implementing the appointments contract.

The server exposes two endpoints.

The appointment creation endpoint accepts a patient UUID, clinician UUID, appointment type, and requested date range. It finds the first available slot by checking an appointments table for conflicts, creates the appointment, and returns the confirmed UUID and date.

The retrieval endpoint accepts a patient UUID and returns all upcoming appointments.

Create an `appointments` table in PostgreSQL: UUID primary key, patient UUID, clinician UUID, appointment type, scheduled datetime, status, and creation timestamp.

**Verify:** Appointment creation inserts a row and returns a confirmed date. Retrieval returns correct appointments per patient. Appointments for one patient do not appear in results for another.

---

### Step 3.6 — Integration Test All MCP Servers Together

Start all four MCP servers simultaneously via the application Docker Compose file with the infrastructure stack also running.

Execute a sequence simulating a clinical workflow: retrieve patient EHR data, submit a lab order, check order status (expect 202), wait for the lab delay to pass, check status again (expect a result), check drug interactions for a treatment option, check formulary availability, submit a prescription, and book a follow-up appointment.

Confirm all calls succeed with expected responses and that write operations create correct database rows.

**Verify:** The full sequence completes without errors. All write operations create correct rows. No MCP server returns an error when called in a realistic order.

---

### Phase 3 Checklist

- [ ] MCP contract document covers all four servers with field-level specifications
- [ ] EHR server returns correct data, enforces authentication, and handles invalid input correctly
- [ ] Lab server correctly simulates the pending/available lifecycle
- [ ] Pharmacy server checks interactions, formulary, and submits prescriptions correctly
- [ ] Appointments server creates and retrieves appointments correctly
- [ ] All four servers run simultaneously without conflicts
- [ ] The integration sequence across all four servers completes without errors

---

## Phase 4 — LangChain Intake Chain

### Purpose
Build the structured text processing pipeline that transforms free-text patient symptom input into a normalised clinical entity object.

---

### Step 4.1 — Define the Clinical Entity Schema

Document the output schema in `docs/intake-schema.md`. The output object must always contain all of the following fields — none are optional:

A `symptoms` array where each element has: `name` (normalised clinical term), `duration_days` (integer), and `severity` (one of mild, moderate, severe).

A `reported_negatives` array of strings — symptoms the patient explicitly denies.

A `reported_medications` array where each element has: `name` and `indication`.

A `free_text_summary` field containing the original patient input for audit purposes.

An `extraction_confidence` field — a decimal between 0 and 1.

**Verify:** The schema document is clear, all field types are specified, and every field must always be present even if some arrays are empty.

---

### Step 4.2 — Build the Entity Extraction Chain

In the `orchestrator` folder, build a three-step LangChain chain.

Step one — extraction: send the raw symptom text to the OpenAI API with a system prompt instructing the model to extract all schema fields. The prompt must specify: use clinical terminology for symptom names (dyspnoea not "shortness of breath", fatigue not "tiredness"), estimate duration in days (convert "about three weeks" to 21), list only explicitly stated negatives not inferred ones.

Step two — normalisation: map symptom names to SNOMED-CT preferred terms using a lookup dictionary of the 50 most common symptom descriptions. Preserve extractions not in the dictionary.

Step three — validation: verify the output conforms to the schema. If any required field is missing, return a validation error rather than a malformed output. Calculate `extraction_confidence`: a full object from a detailed description scores 1.0; a minimal extraction from brief input scores proportionally lower.

**Verify:** Run the chain against five test inputs of varying quality: a detailed multi-symptom description, a one-sentence description, a description with medication mentions, a description with explicit negatives, and casual non-clinical language. Confirm the output is correctly structured for all five and that confidence is lower for the brief description.

---

### Step 4.3 — Test Edge Cases

Run the chain against the following and confirm correct behaviour:

An empty string — the chain should return a validation error, not crash.

An input not about symptoms (asking about appointments) — the chain should return a low-confidence extraction with empty symptom arrays.

A description of an emergency (severe chest pain radiating to the left arm, feeling of impending doom) — severity should be "severe" for chest pain.

An input mentioning a known medication (taking lisinopril for two years and feeling tired) — the medication appears in `reported_medications` and fatigue appears in `symptoms`.

**Verify:** All four edge cases produce the expected output structure without errors or crashes.

---

### Phase 4 Checklist

- [ ] Intake schema is documented with all required fields and types
- [ ] The chain correctly extracts and normalises symptoms from five varied test inputs
- [ ] Confidence scores are lower for lower-quality inputs
- [ ] All four edge cases produce correct structured output without crashes

---

## Phase 5 — Symptom Triage Agent

### Purpose
Build the first full clinical agent, which receives the intake chain output and produces an urgency score, supporting clinical context, and a routing decision.

---

### Step 5.1 — Define the Triage Agent Output Schema

Document the output schema in `docs/triage-schema.md`. The output must contain:

An `urgency_level` field — one of: emergency, urgent, routine, self-care.

An `urgency_rationale` field — a plain-language explanation citing specific symptoms and retrieved evidence.

A `retrieved_context` object with: `patient_history_summary`, `guideline_references` array, and `medication_risks` array.

A `routing_decision` field — one of: "diagnostics-agent", "treatment-agent", or "human-in-the-loop".

A `triage_timestamp` field.

---

### Step 5.2 — Implement Enterprise RAG Retrieval

In the `agents/triage` folder, build the retrieval component that performs the multi-source fan-out.

The component accepts the normalised intake object and the patient UUID. It executes three retrieval operations concurrently:

First, calls the EHR MCP server requesting conditions, medications, lab_results, and encounters. Summarises key clinical findings: active diagnoses, current medications, most recent relevant lab values, and the date of the most recent encounter.

Second, queries the ChromaDB vector store using symptom names from the intake object. Requests the top 8 results and filters to those with similarity score above 0.75.

Third, queries ChromaDB again with a query constructed from the `reported_medications` list to retrieve drug side effect information. Requests the top 5 results with threshold 0.70.

The component merges the three result sets and re-ranks them. The re-ranking logic scores each piece of evidence on: recency (more recent EHR data scores higher), source authority (NICE guidelines score higher than WHO, which score higher than BNF for clinical recommendations), and raw similarity score for vector store results.

Apply the RBAC scope filter at the start of the EHR retrieval call: the patient UUID in the request must match the patient UUID in the service token scope. If they do not match, return an empty patient history and log an access control event to the audit_log table.

**Verify:** Given a patient UUID and symptom terms appearing in the loaded guidelines, the component returns a merged result set containing EHR data, guideline chunks, and medication information in re-ranked order. An RBAC mismatch logs an audit event and returns an empty EHR result.

---

### Step 5.3 — Implement the Urgency Scoring Prompt

Build the LangChain chain that takes the retrieved context and produces the triage output.

The system prompt must specify: the agent's role as a clinical triage specialist, urgency level definitions with clinical examples for each, the requirement to cite specific retrieved evidence in the rationale, the instruction to prefer caution when evidence supports either of two levels, and the instruction to flag any retrieved medication side effect that could explain the primary symptom.

The chain's output parser validates the response against the triage schema. If required fields are missing or the urgency level is invalid, the chain retries once. If the retry also fails, the chain returns a fallback triage object with urgency "urgent" and a note that automated triage failed — ensuring a human reviews the case.

Write the urgency score and rationale to the `audit_log` table for every triage event including failed attempts.

**Verify:** Run the chain with retrieved context for a test patient with IDA symptoms. Confirm the output matches the schema, urgency is routine or urgent, and the rationale cites specific retrieved guideline content.

---

### Step 5.4 — Build the Triage Agent Test Suite

Create 10 test cases in `tests/integration/triage_test_cases.json` covering the urgency spectrum: two emergency cases, three urgent cases, three routine cases, and two self-care cases. Each test case specifies the intake object, the patient UUID to use, the expected urgency level, and the clinical reasoning.

Run all 10 test cases and record the outputs. For any case where the agent assigns a different level than expected, analyse the rationale. If the rationale is clinically defensible, accept it and update the expected level. If the rationale is clinically incorrect, revise the system prompt and re-run.

**Verify:** All 10 test cases produce urgency levels that a clinical reviewer would consider appropriate. No emergency case scores below urgent. No self-care case scores above routine.

---

### Phase 5 Checklist

- [ ] Triage output schema is documented
- [ ] Enterprise RAG retrieval fans out to EHR, guideline vector store, and medication vector store concurrently
- [ ] Re-ranking is applied to the merged retrieval results
- [ ] RBAC scope check logs an audit event on mismatch
- [ ] All 10 test cases produce clinically appropriate urgency scores
- [ ] Triage events are written to the audit_log table

---

## Phase 6 — Diagnostics Agent

### Purpose
Build the agent that takes a triage packet and applies Self-RAG reasoning to produce a confirmed differential diagnosis with a confidence score.

---

### Step 6.1 — Define the Diagnostics Agent Output Schema

Document the output schema in `docs/diagnostics-schema.md`. The output must contain:

A `primary_diagnosis` object with: `icd10_code`, `name`, `confidence_score` (0–100), and `evidence_citations` array.

A `differential_diagnoses` array (maximum 3), each with the same fields as primary_diagnosis.

A `pending_lab_orders` array with test name and order UUID for any labs ordered.

A `self_rag_iterations` integer — the number of retrieval cycles run.

An `escalate_to_human` boolean — true if confidence is below 70.

A `diagnostics_timestamp` field.

---

### Step 6.2 — Build the LangGraph Self-RAG Subgraph

In the `agents/diagnostics` folder, build the Self-RAG loop as a LangGraph StateGraph.

The state object holds: the triage packet, the current list of retrieved documents, the current draft hypothesis, the current reflection scores, the number of iterations completed, the list of lab orders placed, and the final output object (initially null).

Define the following nodes:

The `retrieve` node queries the vector store using symptom names and any diagnosis terms from the draft hypothesis. It also queries the EHR MCP server for recent relevant lab results. It appends new results to the state's retrieved documents list, filtering out duplicates by chunk ID.

The `reflect_relevance` node sends each retrieved document to the OpenAI API with a prompt asking for a 0–1 relevance score given the patient's symptom profile. Documents scoring below 0.6 are removed. If more than 60% of documents are removed, set a flag to reformulate the retrieval query.

The `generate_draft` node sends the filtered documents and the triage packet to the OpenAI API with a prompt to produce a preliminary differential diagnosis list. It updates the draft hypothesis in state.

The `reflect_support` node checks whether each claim in the draft is directly supported by retrieved evidence. Flags unsupported claims and softens them in the draft.

The `reflect_utility` node assesses whether sufficient evidence exists to produce a clinically actionable diagnosis. If not, specifies exactly what additional tests are needed.

The `request_labs` node, reached when utility reflection indicates insufficient evidence, calls the Lab MCP server to submit the requested orders. It updates the state's pending_lab_orders list, sets a `waiting_for_labs` flag, and persists state to Redis.

The `generate_final` node, reached when utility reflection confirms sufficient evidence or the maximum iteration count of 3 is reached, assembles the final output. Calculates confidence score as: mean relevance score of accepted documents multiplied by 80, plus 20 if utility reflection confirmed sufficiency. Sets `escalate_to_human` to true if confidence is below 70.

Define edges: retrieve to reflect_relevance to generate_draft to reflect_support to reflect_utility. From reflect_utility: a conditional edge routes to request_labs if insufficient, to generate_final if sufficient, or back to retrieve if reformulation is needed and iterations are below 3. The request_labs node transitions to a waiting state. generate_final is the terminal node.

**Verify:** Manually trace the state transitions for a simple single-iteration scenario: a patient with clear IDA symptoms, existing lab results confirming low Hb and ferritin, and relevant guidelines loaded. The graph should traverse retrieve, reflect_relevance, generate_draft, reflect_support, reflect_utility, and generate_final in one iteration without ordering labs.

---

### Step 6.3 — Implement Lab Result Waiting and Resume

Implement a polling background task within the diagnostics agent service running every 5 minutes. On each run, the task checks the lab MCP server for the status of all pending orders recorded in LangGraph state. When a result is available (200 response with a value instead of 202), the task loads the LangGraph checkpoint from Redis, updates the state with the new result, and resumes the graph from the retrieve node.

**Verify:** Run a full diagnostics session requiring a lab order. Confirm the graph enters the waiting state with a checkpoint in Redis. After the lab delay passes, confirm the background task detects the available result and resumes the graph. Confirm the final output reflects the lab result in its evidence citations.

---

### Step 6.4 — Build the Diagnostics Agent Test Suite

Create test cases in `tests/integration/diagnostics_test_cases.json` covering:

A case with clear supporting evidence in one iteration (IDA with Hb 9.2 and ferritin 6 — expect confidence above 85 in one iteration).

A case requiring two iterations because the first retrieval returns overly broad results (fatigue with no lab data — expect the relevance reflection to reject broad results and reformulate).

A case requiring a lab order (fatigue with no recent lab results — expect lab orders to be placed).

A case producing `escalate_to_human: true` because confidence stays below 70 (ambiguous symptoms with conflicting evidence).

**Verify:** All four test cases produce the expected Self-RAG behaviour and schema-conformant outputs.

---

### Phase 6 Checklist

- [ ] Diagnostics output schema is documented
- [ ] The LangGraph Self-RAG subgraph has all six nodes with correct edges
- [ ] State persists to Redis correctly at each node transition
- [ ] The lab waiting and resume mechanism works without manual intervention
- [ ] All four test cases produce the expected behaviour
- [ ] Confidence is below 70 for the ambiguous test case, triggering escalation

---

## Phase 7 — Treatment Planning Agent

### Purpose
Build the agent that takes a confirmed diagnosis and autonomously plans a multi-step evidence retrieval sequence to produce a personalised treatment plan.

---

### Step 7.1 — Define the Treatment Plan Output Schema

Document the output schema in `docs/treatment-schema.md`. The output must contain:

A `primary_recommendation` object with: `treatment_name`, `dose`, `route`, `frequency`, `duration`, `guideline_citation`, and `rationale`.

A `contraindications_checked` array, each element with: `check_name`, `result` (clear or flagged), and `source`.

A `cause_investigation` array, each element with: `investigation_name`, `rationale`, and `urgency`.

An `alternatives_rejected` array, each element with: `treatment_name`, `reason_rejected`, and `guideline_citation`.

A `monitoring_schedule` array, each element with: `action`, `timing`, and `responsible_party`.

A `confidence_score` field (0–100).

A `tool_call_count` field — the number of MCP calls made during reasoning.

An `awaiting_human_approval` boolean — always true.

---

### Step 7.2 — Build the Agentic RAG ReAct Loop

In the `agents/treatment` folder, build the Treatment Planning Agent as a LangGraph node implementing a ReAct loop.

The state holds: the confirmed diagnosis, the patient UUID, the current knowledge state (accumulating findings from each tool call), the current tool call count, the list of tool calls and their results, and the final output object.

Define the five available tools:

`search_clinical_guidelines` — queries ChromaDB with a search string, returns top 6 matching chunks with metadata.

`get_patient_comorbidities` — calls the EHR MCP server requesting conditions and medications, returns a structured summary.

`check_drug_interactions` — calls the Pharmacy MCP server's interaction endpoint.

`check_formulary` — calls the Pharmacy MCP server's formulary endpoint.

`request_investigation` — records an investigation recommendation in the agent state without calling an external server.

On each loop iteration, the agent sends its current knowledge state, the available tool descriptions, and the confirmed diagnosis to the OpenAI API. The prompt instructs the model to reason about what it knows and what it still needs to know, then select the next tool or decide to conclude.

If the model selects a tool, execute the call, append the result to the knowledge state, increment the tool call count, and begin the next iteration.

If the model decides it has sufficient information, exit the loop and call the synthesis step.

Set a hard limit of 8 tool call iterations. If reached without concluding, force an exit and set the confidence score proportionally lower.

**Verify:** Run the agent for the IDA + CKD scenario. Confirm the agent calls `get_patient_comorbidities` early, discovers CKD stage 3, and subsequently calls `search_clinical_guidelines` with an IV iron-related query rather than an oral iron query. This mid-reasoning pivot from oral to IV iron is the key behaviour to validate.

---

### Step 7.3 — Build the Treatment Plan Synthesis Step

After the ReAct loop concludes, a synthesis step assembles the final output from the accumulated knowledge state.

The synthesis prompt sends all tool call results to the OpenAI API and instructs it to: identify the primary recommendation with full dosing details, list all contraindications checked and their results, identify any cause investigations required by applicable guidelines, list all treatment alternatives considered and the reason each was rejected, and define the monitoring schedule.

Validate the output against the treatment plan schema. If any required field is missing, retry once. If the retry also fails, flag the plan as incomplete — the clinician must complete missing sections.

**Verify:** The synthesised plan for IDA + CKD contains: IV iron sucrose as the primary recommendation, a contraindication check showing no iron allergy, a cause investigation for GI bleeding, oral iron in the alternatives rejected list with CKD malabsorption as the reason, and a monitoring schedule including repeat ferritin at 6 weeks.

---

### Step 7.4 — Build the Treatment Agent Test Suite

Create four test cases in `tests/integration/treatment_test_cases.json`:

The IDA + CKD scenario (validates the oral-to-IV pivot).

A straightforward type 2 diabetes case with no comorbidities (validates simple 2–3 tool call completion).

A case with a drug interaction that changes the first-choice recommendation.

A case where formulary check shows the first-choice drug is unavailable at the site.

**Verify:** All four test cases produce schema-conformant treatment plans. The IDA + CKD pivot is observed. Drug interaction and formulary findings are reflected in recommendations.

---

### Phase 7 Checklist

- [ ] Treatment plan output schema is documented
- [ ] The ReAct loop iterates, calls tools, and accumulates knowledge correctly
- [ ] The mid-reasoning pivot from oral to IV iron is observed for IDA + CKD
- [ ] The hard limit of 8 tool calls is respected
- [ ] The synthesis step produces a schema-conformant output
- [ ] All four test cases produce correct and schema-conformant treatment plans

---

## Phase 8 — Human-in-the-Loop Mechanism

### Purpose
Implement the approval gate that pauses every treatment plan at the clinician boundary and resumes only when an explicit approval decision is recorded.

---

### Step 8.1 — Define the Approval Task Schema

Document the approval task schema in `docs/hitl-schema.md`. An approval task record in `approval_events` contains: UUID task ID, care episode UUID, task type (treatment-plan-approval, lab-order-approval, emergency-escalation), the full treatment plan as a JSON payload, status (pending, approved, rejected, escalated), clinician UUID (null until decided), submitted timestamp, decided timestamp (null until decided), and clinician notes.

---

### Step 8.2 — Implement the LangGraph Interrupt Node

In the `orchestrator` folder, add a LangGraph HITL node between the Treatment Planning Agent output and the Post-Discharge Agent activation.

When the HITL node is reached, it executes four actions in sequence:

First, writes an approval task record to `approval_events` with status "pending" and the full treatment plan as the JSON payload.

Second, writes the complete LangGraph workflow state to Redis under a key composed from the care episode UUID and the task ID.

Third, publishes a notification event to a Redis pub/sub channel named "hitl-notifications" containing the task ID, care episode UUID, urgency level, and primary diagnosis.

Fourth, calls `graph.interrupt()` to pause the workflow. No further computation occurs until an external resume event arrives.

**Verify:** Submit a treatment plan through the full pipeline. After the Treatment Planning Agent completes, confirm an approval task row exists in `approval_events` with status "pending". Confirm the workflow state is visible in Redis. Confirm the Post-Discharge Agent has not activated.

---

### Step 8.3 — Implement the Approval Endpoint

Create a POST endpoint at `/api/v1/approvals/{task_id}` in the orchestrator.

The endpoint accepts: the clinician's JWT token in the Authorization header, an action field (approved or rejected), and an optional notes field.

Execution steps in order: validate the JWT and extract the clinician UUID; retrieve the approval task — return 404 if not found, 409 if status is not "pending"; update the approval task with the action, clinician UUID, decided timestamp, and notes; write the approval event to `audit_log`; load the LangGraph workflow state from Redis; if approved, resume the workflow from the persisted state; if rejected, mark the episode as requiring manual intervention.

Return 200 confirming the action was recorded.

**Verify:** With a pending approval task in the database, call the endpoint with a valid clinician JWT and action "approved". Confirm the approval_events row is updated. Confirm the LangGraph workflow resumes and the Post-Discharge Agent is activated.

---

### Step 8.4 — Implement Approval Timeout Escalation

Add a background task to the orchestrator running every hour. The task queries `approval_events` for rows with status "pending" and submitted timestamp more than 24 hours ago. For each overdue task, it updates the status to "escalated" and publishes an escalation notification to the Redis pub/sub channel.

**Verify:** Manually insert an approval task with a submitted timestamp 25 hours in the past. Run the timeout task. Confirm the task status changes to "escalated" and an escalation notification appears in the Redis pub/sub channel.

---

### Phase 8 Checklist

- [ ] Approval task schema is documented
- [ ] The HITL LangGraph node pauses the workflow and persists state to Redis
- [ ] The approval_events row exists with "pending" status after the node executes
- [ ] The approval endpoint correctly resumes the workflow on approval
- [ ] The approval endpoint correctly handles rejection without resuming
- [ ] Timeout escalation changes overdue tasks to "escalated" status

---

## Phase 9 — Post-Discharge Agent

### Purpose
Build the agent that activates after clinician approval and monitors patients continuously through the duration of their care plan.

---

### Step 9.1 — Define the Post-Discharge Agent Outputs

Document the output actions in `docs/discharge-outputs.md`:

Risk score update — writes a new risk score and updated timestamp to `discharge_plans` for each active plan on each run.

Escalation event — writes a row to `approval_events` with task type "post-discharge-escalation" and status "pending" when a patient's risk score crosses the threshold.

Check-in notification — writes a record to a `notifications` table. Create this table: UUID primary key, patient UUID, notification type, message, scheduled_at, sent_at, and status.

---

### Step 9.2 — Implement the Scheduler

In the `agents/discharge` folder, implement a scheduler using APScheduler. Configure it to trigger the main agent loop every 15 minutes in development.

On each trigger, the loop:

Queries `discharge_plans` for all rows with status "active".

For each active plan, runs all five SQL analytics queries for that patient.

Calculates the composite risk score: cohort readmission rate (weight 0.4), adherence gap normalised to 0–1 by dividing by 30 (weight 0.3), proportion of anomaly-flagged wearable readings (weight 0.2), days since last wearable reading normalised to 0–1 by dividing by 7 (weight 0.1).

Updates `discharge_plans` with the new risk score and updated timestamp.

If the new risk score exceeds the threshold (65 for IDA plans) and the previous score was below the threshold, creates an escalation approval task in `approval_events` and publishes a notification to the Redis pub/sub channel.

Checks the check-in schedule and creates notification records for patients whose check-in is due today.

Writes a summary span to the OpenTelemetry collector.

**Verify:** Start the scheduler and let it run for two cycles. Confirm `discharge_plans` shows updated risk scores and timestamps after each cycle. Confirm the anomaly-seeded patients receive increasing risk scores on successive runs.

---

### Step 9.3 — Validate Anomaly Detection

Using the seeded anomaly patients from Phase 1 Step 1.7, advance their wearable reading dates manually in the database to simulate Day 22 of their discharge plan. Run the scheduler. Confirm the anomaly detection query identifies these patients, their risk scores cross the threshold, and escalation approval tasks are created.

**Verify:** After advancing the dates, at least 80% of the seeded anomaly patients have escalation tasks created. No non-anomaly patients have escalation tasks created.

---

### Phase 9 Checklist

- [ ] Discharge agent output actions are documented
- [ ] The scheduler runs every 15 minutes and processes all active discharge plans
- [ ] Risk scores are updated in discharge_plans after each scheduler run
- [ ] The composite risk score produces higher scores for anomaly patients
- [ ] Escalation tasks are created when the risk score crosses the threshold
- [ ] The anomaly-seeded patients from Phase 1 are correctly identified by Day 22

---

## Phase 10 — Orchestrator REST API

### Purpose
Expose the platform through a secure REST API that the web UI and mobile app call.

---

### Step 10.1 — Implement All Endpoints

In the `orchestrator` folder, build a FastAPI application exposing the following endpoints.

`GET /api/v1/health` — returns 200 with the status of all services. Used by the load balancer health check and the CI/CD smoke test.

`POST /api/v1/symptoms` — accepts a patient UUID from JWT claims, a free-text symptom description, and optional structured fields. Runs the intake chain and invokes the Triage Agent. Returns the triage reference ID and urgency level. For emergency cases, also publishes an immediate notification to the Redis pub/sub channel.

`GET /api/v1/cases/{case_id}` — returns the current state of a care episode: triage output, diagnostics output if available, treatment plan if available, approval task status if applicable, and active discharge plan summary.

`GET /api/v1/approvals/pending` — returns all pending approval tasks for the authenticated clinician's scope. Ward-assigned clinicians see only tasks for patients in their ward, determined by JWT claims.

`POST /api/v1/approvals/{task_id}` — the approval endpoint from Phase 8.

`GET /api/v1/patients/{patient_id}/discharge-plan` — returns the active discharge plan, current risk score, check-in completion rate, and recent wearable readings summary.

`GET /api/v1/analytics/kpis` — returns 30/60/90-day readmission rates by diagnosis, approval queue depth, mean time to approval, and total active discharge plans. Accessible only to users with the "administrator" role in their JWT claims.

---

### Step 10.2 — Implement JWT Authentication

Implement JWT-based authentication. On startup, the orchestrator loads the JWT signing secret from the `JWT_SECRET` environment variable.

Create a token issuance endpoint at `POST /api/v1/auth/token` that accepts a user identifier and role, validates them against the `clinicians` table, and returns a signed JWT with 8-hour expiry. Token claims include: user UUID, role (patient, nurse, physician, specialist, or administrator), site identifier, and ward identifier.

Every other endpoint validates the JWT before processing. A missing or expired token returns 401. A valid token with insufficient role returns 403. Log all 401 and 403 responses to the `audit_log` table.

**Verify:** Obtain a token via the auth endpoint. Use it on a protected endpoint — confirm 200. Call the same endpoint without a token — confirm 401. Call the KPI analytics endpoint with a clinician (non-administrator) token — confirm 403.

---

### Step 10.3 — End-to-End Integration Test

Run a complete end-to-end test from symptom submission to post-discharge monitoring:

Submit a symptom report via REST API for a patient with IDA symptoms. Verify "urgent" urgency is assigned. Retrieve the case status and verify the diagnostics workflow has started. Wait for the Self-RAG loop to complete (including any lab simulation delay). Retrieve the case status again and verify a diagnosis is present. Verify an approval task exists. Submit an approval. Verify the discharge plan is created and the scheduler begins updating the risk score. Advance the patient's wearable reading dates to Day 22 with the anomaly trend. Run the scheduler manually. Verify an escalation task is created.

**Verify:** Each step produces the expected state. The complete journey from symptom submission to escalation completes without errors.

---

### Phase 10 Checklist

- [ ] All seven API endpoints are implemented and return correct responses
- [ ] JWT authentication is enforced on all protected endpoints
- [ ] Role-based access returns 403 for insufficient-role requests
- [ ] All 401 and 403 responses are logged to the audit_log table
- [ ] The complete end-to-end test passes

---

## Phase 11 — Observability Layer

### Purpose
Instrument every agent and service with OpenTelemetry tracing so the complete reasoning chain for every patient episode is traceable in a single distributed trace.

---

### Step 11.1 — Instrument All Services

In each of the nine application services, add OpenTelemetry instrumentation. Configure each to send traces to the OTel Collector on port 4317.

For each service, define a tracer using the service name. Wrap the following operations as named spans:

In the orchestrator: the intake chain execution, the triage agent invocation, and the HITL node entry and exit.

In the Triage Agent: the Enterprise RAG retrieval as one parent span with three child spans (EHR retrieval, guideline retrieval, medication retrieval), and the urgency scoring prompt call.

In the Diagnostics Agent: each Self-RAG node as a separate span — retrieve, reflect_relevance, generate_draft, reflect_support, reflect_utility, and request_labs — with reflection decisions recorded as span attributes.

In the Treatment Planning Agent: each ReAct iteration as a span with the selected tool name and result summary as span attributes.

In the Post-Discharge Agent: each scheduler run as a span with the number of plans processed and escalations as span attributes.

In each MCP server: each endpoint handler as a span with the patient UUID and resource type as span attributes.

All spans within a single patient episode must share the same root trace ID. Pass the trace context between services using the OpenTelemetry W3C Trace Context propagation format (the `traceparent` HTTP header).

**Verify:** Run a complete end-to-end episode and open the OTel Collector JSON output file. Confirm a single root trace contains nested child spans from all services. Confirm the spans are nested correctly to reflect the actual call hierarchy.

---

### Step 11.2 — Add PHI Redaction to Trace Attributes

In the OTel Collector configuration file, add a transform processor that removes or replaces the following span attribute keys before export: `patient_name`, `date_of_birth`, `free_text_summary`, `symptom_description`. Replace each with a redacted placeholder value.

Span attributes may contain patient episode UUIDs — these are acceptable as they are not directly identifying without database access.

**Verify:** Run an episode that sets the `free_text_summary` attribute on an intake span. Open the OTel output file and confirm the attribute is absent or contains the placeholder. Confirm the patient episode UUID attribute is still present.

---

### Phase 11 Checklist

- [ ] All nine application services emit OpenTelemetry spans
- [ ] A complete episode produces a single distributed trace in the OTel output file
- [ ] Spans are correctly nested to reflect the call hierarchy
- [ ] Trace context is propagated via the traceparent header between all services
- [ ] PHI redaction removes patient names and free-text fields from span attributes
- [ ] Patient episode UUIDs are present in span attributes

---

## Phase 12 — AWS Infrastructure

### Purpose
Provision all AWS resources needed to run the platform in a HIPAA-aware configuration with no public access to application or data services.

---

### Step 12.1 — Create the VPC and Network

In the AWS VPC console, create a new VPC with a /16 CIDR block. Do not use the default VPC.

Create four subnets: two public (one per availability zone) and two private (one per availability zone). All use /24 CIDR blocks within the VPC range.

Create an Internet Gateway and attach it to the VPC. Update the public subnets' route table to route 0.0.0.0/0 to the Internet Gateway.

Create a NAT Gateway in one public subnet. Allocate an Elastic IP for it. Update the private subnets' route table to route 0.0.0.0/0 to the NAT Gateway.

Create three security groups:

The ALB security group: inbound TCP 443 from 0.0.0.0/0, inbound TCP 80 from 0.0.0.0/0 (for redirect), outbound TCP 8000 to the application server security group only.

The application server security group: inbound TCP 8000 from the ALB security group only, all inbound from the data server security group, all outbound.

The data server security group: inbound TCP 5432 and 6379 from the application server security group only, no inbound from any other source, outbound HTTPS to AWS service endpoints only.

**Verify:** In the VPC console, confirm the VPC, four subnets, Internet Gateway, NAT Gateway, and three security groups all exist. Confirm public subnets route to the Internet Gateway. Confirm private subnets route to the NAT Gateway.

---

### Step 12.2 — Create the IAM Instance Role

In the IAM console, create a new role with the EC2 trusted entity type. Attach these policies (scope each to the project's specific resources via conditions): AmazonS3ReadOnlyAccess, SecretsManagerReadWrite, CloudWatchAgentServerPolicy, AmazonOpenSearchServiceFullAccess, and AmazonSSMManagedInstanceCore.

**Verify:** The role appears with all five policies attached. The trusted entity is ec2.amazonaws.com.

---

### Step 12.3 — Launch the Data Server EC2 Instance

In the EC2 console, launch an instance: Amazon Linux 2023 AMI, t3.medium, placed in one private subnet, with the data server security group, the IAM instance role, no public IP, and detailed CloudWatch monitoring enabled.

Add two EBS volumes: a 20 GB gp3 root volume and a 50 GB gp3 data volume with encryption enabled.

After the instance launches, connect via Systems Manager Session Manager. Mount the data volume, format it, and add the mount to /etc/fstab. Install Docker and Docker Compose v2.

**Verify:** Systems Manager Session Manager opens a terminal successfully. The data volume is mounted and accessible. Docker runs successfully.

---

### Step 12.4 — Launch the Application Server EC2 Instance

Launch a second instance: Amazon Linux 2023 AMI, t3.large, one private subnet, application server security group, the IAM instance role, no public IP, detailed CloudWatch monitoring, and only a 30 GB gp3 root volume.

Connect via Systems Manager Session Manager. Install Docker, Docker Compose v2, Python 3.11, Git, and the AWS CLI. Configure the AWS CLI using the instance IAM role — run a test command such as listing S3 bucket contents to confirm role credentials work without manually provided access keys.

**Verify:** Systems Manager Session Manager opens a terminal. Docker, Python, Git, and the AWS CLI are accessible. An AWS CLI command using the instance role succeeds.

---

### Step 12.5 — Create AWS Secrets Manager Secrets

In Secrets Manager, create six secrets using the "Other type of secret" type:

`healthcare-platform/openai` — key `api_key` with your OpenAI API key.

`healthcare-platform/postgres` — keys for `host` (data server private IP), `port` (5432), `db`, `user`, and `password`.

`healthcare-platform/redis` — keys for `host` (data server private IP) and `port` (6379).

`healthcare-platform/chromadb` — keys for `host` and `port`.

`healthcare-platform/opensearch` — keys for `endpoint` (added after Step 12.6) and `region`.

`healthcare-platform/jwt` — key `secret` with a randomly generated 256-bit hex string.

After creating all secrets, verify that the application server EC2 instance can retrieve each secret using the AWS CLI with the instance role credentials.

**Verify:** All six secrets are in Secrets Manager. The AWS CLI on the application server retrieves each secret's value by ARN without additional credentials.

---

### Step 12.6 — Create Amazon OpenSearch Serverless

In the OpenSearch Service console, navigate to Serverless and create a new "Vector search" collection named after the project.

Configure with: encryption using an AWS KMS key (create a new key in KMS first), a VPC endpoint in the private subnets using the application server security group, a data access policy granting full access to the IAM instance role ARN only, and a network policy allowing access only via the VPC endpoint.

After the collection is active, create an index with vector dimensions matching the OpenAI embedding model (1536 for text-embedding-3-small) and cosine similarity metric.

Update the `healthcare-platform/opensearch` secret with the collection endpoint URL.

Rerun the vector store loading process from Phase 1 Step 1.11 targeting OpenSearch instead of ChromaDB. Run the same three test queries and confirm they return the same clinically relevant results.

**Verify:** The OpenSearch collection is active. The VPC endpoint is in place. The three test queries return the same results as ChromaDB. The collection is not reachable from outside the VPC.

---

### Step 12.7 — Create the ECR Repositories

In the ECR console, create nine repositories — one per application service: orchestrator, agent-triage, agent-diagnostics, agent-treatment, agent-discharge, mcp-ehr, mcp-lab, mcp-pharmacy, mcp-appointments.

For each repository, enable image scanning on push and set a lifecycle policy retaining the 10 most recent images.

**Verify:** All nine repositories are visible with scanning and lifecycle policies enabled.

---

### Step 12.8 — Create the TLS Certificate

In AWS Certificate Manager in your target region, request a public certificate for your domain name. Follow the DNS validation process. Wait for the status to show "Issued".

**Verify:** The certificate status is "Issued" in ACM.

---

### Step 12.9 — Create the Application Load Balancer

In the EC2 console, create an internet-facing Application Load Balancer in the two public subnets with the ALB security group.

Create a target group: Instances type, HTTP protocol, port 8000, health check on `GET /api/v1/health` expecting 200. Register the application server instance.

Create an HTTPS listener on port 443 with the ACM certificate forwarding to the target group.

Create an HTTP listener on port 80 with a redirect action to HTTPS.

**Verify:** The ALB is active and its DNS name resolves. The target group shows the application server as "unhealthy" (expected — the application is not deployed yet). The HTTP-to-HTTPS redirect functions.

---

### Phase 12 Checklist

- [ ] VPC has four subnets, Internet Gateway, and NAT Gateway
- [ ] All three security groups have correct inbound and outbound rules
- [ ] Both EC2 instances are in private subnets with no public IP addresses
- [ ] Systems Manager Session Manager opens a terminal to both instances
- [ ] Docker is installed and running on both instances
- [ ] All six Secrets Manager secrets are created and retrievable by the application server role
- [ ] OpenSearch Serverless collection is active and accessible only via the VPC endpoint
- [ ] All nine ECR repositories are created with scanning and lifecycle policies
- [ ] TLS certificate is issued in ACM
- [ ] Application Load Balancer is active with HTTPS listener and HTTP redirect

---

## Phase 13 — Production Deployment

### Purpose
Deploy the working local application to AWS and validate it against the production infrastructure.

---

### Step 13.1 — Update Application Configuration for AWS

Update all application services to retrieve credentials from Secrets Manager at startup using the AWS SDK. Pass secret ARNs as environment variables — the ARNs are not sensitive and can be set directly.

Update all three RAG agents to use OpenSearch instead of ChromaDB when an `APP_ENV` environment variable is set to "production". When set to "local", ChromaDB is used.

Update the OTel Collector configuration to export traces to AWS X-Ray instead of the local JSON file when in production.

Create a production Docker Compose file named `docker-compose.prod.yml` defining only the nine application services with `APP_ENV=production` and secret ARNs as environment variables.

**Verify:** Set `APP_ENV=production` locally and confirm the application fails to connect to OpenSearch (expected — you are outside the VPC). Set `APP_ENV=local` and confirm ChromaDB is used again.

---

### Step 13.2 — Deploy the Data Server Services

Connect to the data server via Systems Manager Session Manager. Clone the project repository. Navigate to the `docker` directory.

Set the environment variables for PostgreSQL and Redis from the Secrets Manager values. Start PostgreSQL and Redis using Docker Compose.

Run the schema creation SQL, the FHIR-to-relational transformation, and the Faker extension processes against the production database to populate it with the synthetic data.

**Verify:** Connect to production PostgreSQL and confirm all 13 tables exist with correct row counts. Confirm Redis is running and responds to ping.

---

### Step 13.3 — Build and Push Docker Images to ECR

On your local machine, authenticate Docker with ECR using the AWS CLI. Build all nine application service images. Tag each with the ECR repository URI and the current Git commit hash.

Push all nine images to their respective ECR repositories.

**Verify:** All nine images appear in ECR with the correct tag. Image scan results show no critical vulnerabilities.

---

### Step 13.4 — Deploy the Application Server Services

Connect to the application server via Systems Manager Session Manager. Clone the project repository. Authenticate Docker with ECR. Pull all nine images.

Set the environment variables for all secret ARNs. Start the application stack using the production Docker Compose file.

Watch the container logs for each service as it starts. Confirm each reports a successful startup and all health checks pass.

**Verify:** All nine containers are running and healthy. The orchestrator logs show successful connections to PostgreSQL, Redis, and OpenSearch. MCP servers log successful database connections.

---

### Step 13.5 — Verify End-to-End on AWS

From your local machine, call the ALB's HTTPS URL to submit a symptom report for a synthetic test patient. Confirm the request is accepted.

Poll the case status endpoint until triage and diagnostics are complete. Confirm a treatment plan is generated and an approval task exists.

Submit an approval. Confirm the workflow resumes and a discharge plan is created.

Open the AWS X-Ray console and confirm a distributed trace exists for the episode covering all services.

**Verify:** The complete end-to-end workflow completes on AWS. The X-Ray trace covers all agent spans. The approval_events table shows the approval record.

---

### Phase 13 Checklist

- [ ] All services use Secrets Manager — no credentials in environment files on EC2
- [ ] OpenSearch is used for vector retrieval in production
- [ ] All nine Docker images are in ECR with no critical vulnerabilities
- [ ] All nine application services are running and healthy
- [ ] The complete end-to-end workflow succeeds via the production HTTPS URL
- [ ] A distributed trace for the episode is visible in AWS X-Ray

---

## Phase 14 — CI/CD Pipeline

### Purpose
Automate build, test, and deployment so every merge to main produces a validated deployment to AWS without manual steps.

---

### Step 14.1 — Create the GitHub Actions Workflow

Create `.github/workflows/deploy.yml`. Configure it to trigger on push to main and on pull request creation.

The workflow has four jobs: test, build, deploy, and verify. The build, deploy, and verify jobs run only on push to main — not on pull requests.

**Verify:** Commit the workflow file. Create a test pull request and confirm only the test job runs.

---

### Step 14.2 — Configure the Test Job

The test job runs on Ubuntu, sets up Python 3.11, installs dependencies, starts temporary PostgreSQL and Redis service containers, and runs the full test suite.

Configure the job to publish test results as a GitHub Actions artifact. Configure it to fail if test coverage drops below 60%.

**Verify:** Intentionally break one unit test and push. Confirm the test job fails and subsequent jobs do not run. Fix the test and confirm all jobs proceed.

---

### Step 14.3 — Configure the Build Job

The build job authenticates Docker with ECR, builds all nine images, tags them with the Git commit hash and "latest", and pushes them to ECR.

Add a step that runs ECR image scanning on the pushed images and fails the job if any image has a CRITICAL vulnerability.

Pass the commit hash as a job output so the deploy job can reference the exact image tags.

**Verify:** A push to main triggers the build job and all nine images appear in ECR tagged with the commit hash.

---

### Step 14.4 — Configure the Deploy Job

The deploy job uses AWS Systems Manager Run Command to send a deployment script to the application server EC2 instance. The script: pulls new images from ECR using the commit hash tag, restarts the application stack using the production Docker Compose file, and waits up to 5 minutes for all health checks to pass before declaring the deployment failed.

Store the EC2 instance ID as a GitHub Actions secret. No SSH keys are needed.

**Verify:** A push to main triggers the build and deploy jobs in sequence. After deployment, the application server runs the new image version.

---

### Step 14.5 — Configure the Verify Job

The verify job calls the health endpoint and confirms a 200 response. It then submits a symptom report for a designated smoke test patient UUID and confirms a triage reference ID is returned.

If the verify job fails, it triggers a rollback: a Systems Manager Run Command restarts the application stack using the previous image tag. After rollback, the smoke test runs again.

**Verify:** Deploy a version with a deliberate bug in the health endpoint. Confirm the verify job fails and the rollback executes. Confirm the production URL is restored.

---

### Phase 14 Checklist

- [ ] The workflow triggers correctly on push to main and on pull requests
- [ ] A failing test blocks all subsequent jobs
- [ ] All nine images are built and pushed to ECR with commit hash tags
- [ ] ECR scanning fails the build on critical vulnerabilities
- [ ] The deploy job uses Systems Manager Run Command — no SSH keys
- [ ] The verify job runs a smoke test after every deployment
- [ ] A failed smoke test triggers automatic rollback

---

## Phase 15 — Monitoring and Operations

### Purpose
Establish observability, alerting, backup procedures, and operational runbooks required to maintain the platform after go-live.

---

### Step 15.1 — Create CloudWatch Log Groups

In the CloudWatch console, create three log groups:

`/healthcare-platform/application` — all agent and orchestrator logs. Retention: 90 days.

`/healthcare-platform/audit` — all HIPAA audit events shipped from the `audit_log` table by a background process in the orchestrator. Retention: 2555 days (7 years).

`/healthcare-platform/infrastructure` — Docker daemon and system logs from both EC2 instances. Retention: 30 days.

For the audit log group, add a resource policy explicitly denying `logs:DeleteLogGroup` and `logs:DeleteLogStream` for all principals including root. This makes the audit log immutable.

Configure the CloudWatch agent on both EC2 instances to ship Docker container logs and system logs to the appropriate log groups.

**Verify:** Start the application and confirm log events appear in the application log group within 2 minutes. Confirm the audit log group has the delete-deny resource policy.

---

### Step 15.2 — Create the CloudWatch Dashboard

Create a CloudWatch dashboard with three sections:

System health: EC2 CPU utilisation for both instances, ALB request count, ALB 5xx error rate, ALB p99 latency, and EBS read/write IOPS for the data server.

Agent performance: mean invocation latency per agent (custom metrics from OTel collector), Self-RAG mean iteration count per episode, and Agentic RAG mean tool call count per episode.

Business outcomes: HITL approval queue depth, mean time to approval, active discharge plans count, and 30-day readmission rate trend.

Add the custom metrics by configuring the OTel Collector to export specific metrics to CloudWatch Embedded Metrics Format in addition to X-Ray trace export.

**Verify:** After running a complete episode, open the dashboard and confirm all widgets show data points.

---

### Step 15.3 — Create CloudWatch Alarms

Create and subscribe your email to an SNS topic. Create alarms sending notifications to this topic:

Critical alarms: ALB 5xx error rate above 5% for 5 consecutive minutes; application server CPU above 90% for 10 consecutive minutes; data server CPU above 85% for 10 consecutive minutes; audit log write failure count above 0; HITL approval queue depth above 20.

Warning alarms: ALB p99 latency above 10 seconds for 15 consecutive minutes; post-discharge escalation rate above 25% of active plans; agent evaluation score below threshold.

**Verify:** Trigger the HITL queue depth alarm by manually inserting 25 pending approval tasks. Confirm the SNS notification arrives within 5 minutes.

---

### Step 15.4 — Configure Automated Backups

In AWS Backup, create a backup plan with two rules:

Daily: runs at 2 AM UTC, backs up the data server EBS data volume and the S3 bucket. Retains 35 days.

Monthly: runs on the first day of each month, backs up the same resources. Retains 365 days.

Test the restore procedure: create a restore from the most recent daily backup, mount the volume on a temporary instance, confirm PostgreSQL data is accessible, then terminate the temporary instance and delete the restored volume.

Document the restore procedure as `docs/runbooks/database-restore.md`.

**Verify:** The backup plan is active with the next scheduled backup time shown. The test restore successfully accesses PostgreSQL data. The runbook is committed.

---

### Step 15.5 — Set Up the Nightly Evaluation Run

Create an EventBridge rule triggering a Systems Manager Run Command on the application server every night at 3 AM UTC. The command runs the agent evaluation suite against production using the smoke test patient UUID.

The evaluation run submits all test cases from Phase 4 through Phase 9, compares outputs against reference answers, calculates a score per agent, and emits the scores as CloudWatch custom metrics.

If any agent's score drops below its threshold — 85 for triage, 80 for diagnostics, 80 for treatment — the critical alarm fires.

**Verify:** Trigger the evaluation run manually via Systems Manager. Confirm custom metric data points appear in CloudWatch. Confirm the dashboard shows evaluation scores.

---

### Step 15.6 — Write the Operational Runbooks

Write and commit the following runbooks to `docs/runbooks/`. Each runbook must specify: purpose, when to use it, pre-conditions, step-by-step procedure, and verification steps.

`database-restore.md` — written in Step 15.4.

`adding-guidelines.md` — download the new PDF, add to the registry, upload to S3, run the vector store loader against OpenSearch, run test retrieval queries, verify clinical relevance.

`rotating-openai-key.md` — generate new key in OpenAI dashboard, update the Secrets Manager secret, restart the application stack via Systems Manager, run the smoke test, revoke the old key.

`scaling-application-server.md` — stop the Docker Compose stack via Systems Manager, stop the EC2 instance, change the instance type, start the instance, start the stack, run the smoke test.

`deployment-rollback.md` — identify the previous image tag from GitHub Actions history, send a Systems Manager Run Command to restart the stack with the previous tag, run the smoke test.

`responding-to-audit-log-failure.md` — check CloudWatch Logs for the error, verify IAM role has CloudWatch Logs write permissions, verify the log group exists, determine if the failure is transient or persistent, document the incident regardless of outcome.

**Verify:** All six runbooks are committed. Each has been reviewed once to confirm the steps are complete and actionable.

---

### Phase 15 Checklist

- [ ] All three CloudWatch log groups are created with correct retention and the audit group has the delete-deny policy
- [ ] CloudWatch agent ships logs from both EC2 instances to the correct log groups
- [ ] The CloudWatch dashboard displays live data across all three sections
- [ ] All critical and warning alarms are active and at least one has been tested end-to-end
- [ ] AWS Backup is configured with daily and monthly rules
- [ ] A test restore from backup has been verified and documented
- [ ] The nightly evaluation run fires via EventBridge and emits scores to CloudWatch
- [ ] All six operational runbooks are written and committed

---

## Final Production-Readiness Checklist

Complete this checklist before using the platform with any audience beyond internal testing.

**Security**
- [ ] No credentials on any EC2 instance — all retrieved from Secrets Manager at runtime
- [ ] No public IP addresses on application or data servers
- [ ] Port 22 is not open on any security group
- [ ] All EBS volumes are encrypted
- [ ] S3 bucket has public access blocked and requires HTTPS
- [ ] OpenSearch collection is accessible only via VPC endpoint
- [ ] JWT tokens expire after 8 hours
- [ ] RBAC scope checks are in place at the API and RAG retrieval layers

**HIPAA**
- [ ] All PHI access is logged to the audit_log table
- [ ] All approval decisions are logged with clinician identity and timestamp
- [ ] Audit CloudWatch log group has the immutability policy applied
- [ ] Audit logs are retained for 7 years
- [ ] PHI redaction is applied in the OTel Collector before export
- [ ] Data in transit is encrypted via TLS on all paths
- [ ] Data at rest is encrypted on EBS and S3

**Reliability**
- [ ] Automated backups are running and a test restore has been verified
- [ ] The nightly evaluation run has completed at least once successfully
- [ ] All six operational runbooks are written and accessible
- [ ] The CI/CD pipeline successfully deploys and auto-rolls back on smoke test failure

**Observability**
- [ ] A complete end-to-end episode produces a distributed trace in X-Ray
- [ ] All CloudWatch alarms have been tested by triggering them
- [ ] The CloudWatch dashboard shows live data from all three sections

---

*Follow the phase checklists rigorously. Each checklist item represents a failure mode that, if unaddressed, will surface as a harder-to-diagnose problem in a later phase. The most common failure mode is skipping local validation in Phase 10 and discovering integration issues on AWS in Phase 12. The local environment must be fully verified before any AWS resource is provisioned.*
