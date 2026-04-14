# Phase 1 — Data Synthesis & Pipeline

**Status:** ✅ Complete
**Depends on:** Nothing
**Produces:** Populated PostgreSQL (14 tables, 1.7M rows), ChromaDB (14 guideline chunks), verified SQL analytics

---

## Overview

Generate a realistic synthetic healthcare dataset, transform it into relational tables, and load clinical guidelines into the vector store. Every subsequent phase depends on this data existing and being correct.

---

## Step 1: Project Scaffolding

### 1.1 Initialize Project

```bash
mkdir pcc-platform && cd pcc-platform
uv init
uv venv
.venv\Scripts\activate
```

### 1.2 Install Dependencies

```
pyproject.toml dependencies:
  langchain, langgraph, openai, langchain-openai, langchain-community
  chromadb, fastapi, uvicorn, pydantic, sqlalchemy, psycopg2-binary
  redis, pyjwt, apscheduler, opentelemetry-sdk, opentelemetry-api
  opentelemetry-instrumentation-fastapi, httpx, python-dotenv, faker
```

### 1.3 Create .env

Copy `.env.example` → `.env`. Fill in:
- `OPENAI_API_KEY` — real key
- `POSTGRES_PASSWORD` — chosen password
- `JWT_SECRET` — `python -c "import secrets; print(secrets.token_hex(32))"`

### 1.4 Docker Infrastructure

```bash
docker compose -f docker-compose.infra.yml up -d
```

**Verification:**

```bash
docker compose -f docker-compose.infra.yml ps
```

Expected: all 4 services healthy (postgres, redis, chromadb, otel-collector).

```bash
psql -h localhost -U healthcare_app -d healthcare_platform -c "SELECT 1"
redis-cli ping
curl http://localhost:8200/api/v1/heartbeat
```

---

## Step 2: Database Schema

### 2.1 Apply Schema

```bash
psql -h localhost -U healthcare_app -d healthcare_platform -f data/schemas/001_initial_schema.sql
```

### 2.2 Schema Contract

File: `data/schemas/001_initial_schema.sql`

14 tables created:

| Table | PK | Key Foreign Keys | Notable Columns |
|---|---|---|---|
| `patients` | `patient_id` UUID | — | gender CHECK, site_id, active |
| `clinicians` | `clinician_id` UUID | — | specialty, ward_assignment |
| `admissions` | `admission_id` UUID | patients, clinicians | encounter_type CHECK, discharge_status CHECK |
| `diagnoses` | `diagnosis_id` UUID | patients, admissions | icd10_code, confidence_score CHECK 0-1 |
| `lab_results` | `lab_result_id` UUID | patients, admissions | loinc_code, result_status CHECK, result_available_at |
| `medications` | `medication_id` UUID | patients, clinicians | status CHECK (incl 'stopped') |
| `vitals` | `vital_id` UUID | patients, admissions | vital_type, value, unit, recorded_at |
| `pharmacy_events` | `event_id` UUID | patients, medications | gap_days GENERATED ALWAYS |
| `discharge_plans` | `plan_id` UUID | patients, admissions | risk_score, completion_percentage CHECK 0-100 |
| `wearable_readings` | `reading_id` UUID | patients, discharge_plans | anomaly_flag, UNIQUE(patient,plan,date) |
| `appointments` | `appointment_id` UUID | patients, clinicians | status CHECK (scheduled/completed/cancelled/no_show) |
| `approval_events` | `approval_id` UUID | clinicians | plan_payload JSONB, status CHECK |
| `audit_log` | `log_id` UUID | — | actor_type CHECK, details JSONB |
| `schema_migrations` | `migration_id` SERIAL | — | migration_name UNIQUE |

**Verification:**

```bash
psql -h localhost -U healthcare_app -d healthcare_platform -c "\dt"
```

Expected: 14 tables listed.

---

## Step 3: Synthea Data Generation

### 3.1 Run Synthea

```bash
java -jar synthea-with-dependencies.jar -p 500 --exporter.fhir.export true Massachusetts
```

Output: `data/synthea/fhir/` — one JSON bundle per patient.

### 3.2 Verification

```bash
python -c "import os; files = [f for f in os.listdir('data/synthea/fhir') if f.endswith('.json')]; print(f'{len(files)} FHIR bundles')"
```

Expected: ~500-600 FHIR bundles.

---

## Step 4: FHIR-to-Relational Transformation

### 4.1 Transform Script Contract

File: `data/seeds/transform_fhir.py`

```python
def transform_fhir(fhir_dir: str, db_url: str) -> dict[str, int]:
    """
    Parse FHIR bundles and populate:
      patients, admissions, diagnoses, lab_results, medications, vitals
    
    Returns: dict of table_name → row_count
    """
```

**Key decisions:**
- Keep Synthea UUIDs as primary keys
- All dates stored as TIMESTAMPTZ
- Map LOINC codes to human-readable test_name via lookup
- ICD-10 codes extracted from Condition resources

### 4.2 Run

```bash
python data/seeds/transform_fhir.py
```

### 4.3 Verification

```sql
SELECT 'patients' as t, count(*) FROM patients
UNION ALL SELECT 'admissions', count(*) FROM admissions
UNION ALL SELECT 'lab_results', count(*) FROM lab_results
UNION ALL SELECT 'medications', count(*) FROM medications
UNION ALL SELECT 'vitals', count(*) FROM vitals
UNION ALL SELECT 'diagnoses', count(*) FROM diagnoses;
```

Expected (approximate for 500 patients):
- patients: ~573
- admissions: ~42,000
- lab_results: ~223,000
- medications: ~variable
- vitals: ~variable

---

## Step 5: Faker Data Generation

### 5.1 Clinicians

File: `data/seeds/generate_clinicians.py`

```python
def generate_clinicians(count: int, db_url: str) -> int:
    """Generate fake clinicians with specialties and ward assignments. Returns row count."""
```

Expected: 250 clinicians.

### 5.2 Pharmacy Events

File: `data/seeds/generate_pharmacy.py`

```python
def generate_pharmacy_events(db_url: str) -> int:
    """
    For each active medication, generate dispensed/refilled/missed events.
    15-20% of refills are late or missed (adherence gaps).
    Returns row count.
    """
```

Expected: ~1.2M pharmacy events.

### 5.3 Discharge Plans

File: `data/seeds/generate_discharge.py`

```python
def generate_discharge_plans(db_url: str) -> int:
    """
    Generate discharge plans for recent admissions.
    plan_type: anaemia-followup, renal-followup, diabetes-management, general-followup
    Returns row count.
    """
```

Expected: ~559 plans.

### 5.4 Wearable Readings

File: `data/seeds/generate_wearables.py`

```python
def generate_wearable_readings(db_url: str) -> int:
    """
    Daily readings per discharge plan patient.
    10% of patients get seeded anomalies starting from day 18.
    anomaly_flag = TRUE for seeded anomaly readings.
    Returns row count.
    """
```

Expected: ~50,000 readings.

### 5.5 Verification

```bash
python data/seeds/verify_data_quality.py
```

Expected: 20+ of 23 tests passing.

---

## Step 6: SQL Analytics Validation

Run the 5 analytics patterns that the Post-Discharge Agent will use:

```bash
python data/seeds/verify_analytics.py
```

### Analytics Contract

| # | Query | Target |
|---|---|---|
| 1 | Readmission cohort scoring | < 2s, returns cohort_readmit_rate |
| 2 | Adherence drop-off detection | < 2s, identifies gap > 3 days |
| 3 | Vital anomaly detection | < 2s, catches seeded anomalies |
| 4 | Outcome KPIs (30/60/90 day) | < 2s, returns readmission rates |
| 5 | Population segmentation | < 2s, ranked risk scores |

**Verification:**

```
All 5 queries pass, all < 400ms
```

---

## Step 7: Vector Store Loading

### 7.1 Clinical Guidelines

Place guideline files in `data/guidelines/`:
- `NICE_NG203_Anaemia.txt`
- `NICE_NG28_Diabetes.txt`
- `WHO_Anaemia_Protocol.txt`

### 7.2 Load to ChromaDB

File: `vector_store/load_chromadb.py`

```python
def load_guidelines(guidelines_dir: str, persist_dir: str) -> int:
    """
    Extract text → chunk (600 tokens, 60 overlap) → embed (text-embedding-3-small) → store.
    Uses PersistentClient. Suppresses ChromaDB telemetry warnings.
    Returns chunk count.
    """
```

```bash
python vector_store/load_chromadb.py
```

### 7.3 Verification

```bash
python vector_store/verify_guidelines.py
```

Expected: 3 guideline files found.

```python
# In load_chromadb.py test_retrieval():
# Uses query_embeddings (NOT query_texts) to match 1536-dim OpenAI embeddings
```

Expected: 14 chunks loaded, retrieval returns relevant results for "iron deficiency anaemia".

---

## Phase 1 Checkpoint

All conditions must be true before proceeding to Phase 2:

- [ ] PostgreSQL running with 14 tables populated
- [ ] Row counts: ~573 patients, ~42K admissions, ~223K lab_results, ~1.2M pharmacy_events, ~559 discharge_plans, ~50K wearable_readings, 250 clinicians
- [ ] 20+ of 23 data quality tests passing
- [ ] All 5 SQL analytics queries return correct results in < 400ms
- [ ] ChromaDB has 14 chunks in `clinical_guidelines` collection
- [ ] Vector retrieval returns relevant results (OpenAI embeddings, not default)
- [ ] `.env` contains all secrets; `.gitignore` ignores `data/`, `.env`, `.venv/`
- [ ] Docker infrastructure healthy: postgres, redis, chromadb, otel-collector
