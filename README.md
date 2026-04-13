# AI-Powered Patient Care Coordination Platform

A multi-agent AI system for healthcare coordination using LangChain, LangGraph, and OpenAI.

## 🏗️ Architecture

- **Stack**: Python 3.12, OpenAI API, LangChain, LangGraph, PostgreSQL, Redis, ChromaDB
- **Deployment**: Docker Compose (local) → AWS EC2 (production)
- **Data**: Synthea FHIR synthetic data + custom operational tables
- **Compliance**: HIPAA-aware design

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker Desktop with WSL2
- Java 11+ (for Synthea)
- AWS CLI v2
- OpenAI API account
- jq (command-line JSON processor)

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd pcc-platform
cp .env.example .env
# Edit .env with your actual credentials
```

### 2. Verify Environment

```bash
python scripts/verify_environment.py
python scripts/test_openai_key.py
```

### 3. Start Infrastructure

```bash
docker compose -f docker-compose.infra.yml up -d
```

### 4. Run Data Pipeline

```bash
# Generate all data (Synthea + SQL + Vector Store)
python scripts/run_data_pipeline.py --all

# Or run stages individually:
python scripts/run_data_pipeline.py --stage synthea
python scripts/run_data_pipeline.py --stage schema
python scripts/run_data_pipeline.py --stage transform
python scripts/run_data_pipeline.py --stage faker
python scripts/run_data_pipeline.py --stage s3
python scripts/run_data_pipeline.py --stage vector
```

### 5. Verify Data Quality

```bash
python tests/integration/test_data_quality.py
```

## 📂 Project Structure

```
pcc-platform/
├── agents/               # AI agents (Triage, Diagnostics, Treatment, Discharge)
├── orchestrator/         # LangGraph workflow orchestration
├── mcp_servers/         # MCP tool servers (EHR, Lab, Pharmacy, Appointments)
├── data/
│   ├── schemas/         # PostgreSQL DDL scripts
│   ├── seeds/           # Data generation scripts
│   ├── synthea/         # Synthea configuration and runner
│   └── guidelines/      # Clinical guideline PDFs
├── vector_store/        # ChromaDB loader and utilities
├── config/              # Configuration files
├── scripts/             # Utility and orchestration scripts
├── tests/               # Test suites
└── docker/              # Dockerfiles for services
```

## 🔧 Development Workflow

### Phase 0: Foundation (Complete)
- ✅ Project structure created
- ✅ Environment configured
- ✅ Docker infrastructure ready

### Phase 1: Data Synthesis (In Progress)
- ⏳ Generate 500 synthetic patients with Synthea
- ⏳ Transform FHIR to SQL
- ⏳ Generate operational tables (pharmacy, wearables, discharge plans)
- ⏳ Load vector store with clinical guidelines

### Phase 2-15: Application Development
See `docs/healthcare_platform_step_by_step_guide.md` for complete roadmap.

## 📊 Database Schema

13 tables covering:
- Core patient data (patients, admissions, diagnoses, lab_results, medications, vitals)
- Operational data (pharmacy_events, discharge_plans, wearable_readings)
- System data (clinicians, appointments, approval_events, audit_log, schema_migrations)

## 🧪 Testing

```bash
# Data quality tests
pytest tests/integration/test_data_quality.py -v

# Environment validation
python scripts/verify_environment.py

# SQL analytics queries validation
python tests/integration/test_sql_queries.py
```

## 📖 Documentation

- `docs/healthcare_platform_step_by_step_guide.md` - Complete implementation guide
- `docs/healthcare_platform_implementation_plan.md` - Architecture and design
- `docs/schema-design.md` - Database schema documentation (generated)

## 🔐 Security Notes

- Never commit `.env` file
- All credentials in environment variables or AWS Secrets Manager
- S3 bucket blocks public access
- PostgreSQL uses app-specific user (not superuser)
- HIPAA compliance considerations documented

## 📝 License

[Your License Here]
