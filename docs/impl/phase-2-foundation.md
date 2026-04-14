# Phase 2 — Foundation Layer

**Status:** Not started
**Depends on:** Phase 1 (data pipeline complete)
**Produces:** Shared config module, database utilities, Redis client, ChromaDB client, directory structure

---

## Overview

Create the shared foundation that all MCP servers, agents, and the orchestrator depend on. This phase produces no user-facing functionality — it builds the plumbing.

---

## Step 1: Directory Structure

Create all directories and `__init__.py` files:

```
agents/
  intake/__init__.py
  triage/__init__.py
  diagnostics/__init__.py
  treatment/__init__.py
  discharge/__init__.py
mcp_servers/
  ehr/__init__.py
  lab/__init__.py
  pharmacy/__init__.py
  appointments/__init__.py
orchestrator/__init__.py
config/__init__.py
docker/
tests/
  unit/__init__.py
  integration/__init__.py
```

**Verification:**

```bash
python -c "import agents.intake; import agents.triage; import agents.diagnostics; import agents.treatment; import agents.discharge; import mcp_servers.ehr; import mcp_servers.lab; import mcp_servers.pharmacy; import mcp_servers.appointments; import orchestrator; print('All packages importable')"
```

---

## Step 2: Shared Config (Pydantic BaseSettings)

File: `config/settings.py`

### Contract

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str
    
    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "healthcare_platform"
    postgres_user: str = "healthcare_app"
    postgres_password: str
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    
    # ChromaDB
    chromadb_host: str = "localhost"
    chromadb_port: int = 8200
    
    # JWT
    jwt_secret: str
    jwt_expiry_hours: int = 8
    
    # App
    environment: str = "development"
    log_level: str = "INFO"
    
    # Vector Store
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 600
    chunk_overlap: int = 60

    @property
    def database_url(self) -> str: ...
    
    @property
    def async_database_url(self) -> str: ...

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings() -> Settings: ...
```

**Verification:**

```bash
python -c "from config.settings import get_settings; s = get_settings(); print(f'DB: {s.postgres_host}:{s.postgres_port}/{s.postgres_db}')"
```

Expected: `DB: localhost:5432/healthcare_platform`

---

## Step 3: Database Utility

File: `config/database.py`

### Contract

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

engine: Engine  # Lazy init from settings.database_url
SessionLocal: sessionmaker[Session]

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a session, auto-closes."""

def get_engine() -> Engine:
    """Returns the SQLAlchemy engine (creates on first call)."""
```

Connection pool defaults: `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`.

**Verification:**

```bash
python -c "
from config.database import get_engine
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(text('SELECT count(*) FROM patients'))
    print(f'Patients: {result.scalar()}')
"
```

Expected: `Patients: 573`

---

## Step 4: Redis Client

File: `config/redis_client.py`

### Contract

```python
import redis

def get_redis_client() -> redis.Redis:
    """Returns a Redis client from settings. Connection pool reused."""

def get_redis_pubsub() -> redis.client.PubSub:
    """Returns a pub/sub instance for HITL notifications."""
```

**Verification:**

```bash
python -c "
from config.redis_client import get_redis_client
r = get_redis_client()
r.set('test_key', 'ok')
print(r.get('test_key'))
r.delete('test_key')
"
```

Expected: `b'ok'`

---

## Step 5: ChromaDB Client

File: `config/chromadb_client.py`

### Contract

```python
import chromadb
from openai import OpenAI

def get_chromadb_collection() -> chromadb.Collection:
    """
    Returns the 'clinical_guidelines' collection from PersistentClient.
    Persist directory: data/chromadb
    Suppresses telemetry warnings.
    """

def query_guidelines(query_text: str, n_results: int = 5) -> list[dict]:
    """
    Embed query using text-embedding-3-small via OpenAI, then query ChromaDB
    using query_embeddings (NOT query_texts).
    
    Returns: [{document, metadata, distance}]
    """

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using OpenAI text-embedding-3-small."""
```

**Critical:** Must use `query_embeddings=` to match the 1536-dim OpenAI embeddings stored in ChromaDB. Using `query_texts=` would invoke ChromaDB's default 384-dim model and fail.

**Verification:**

```bash
python -c "
from config.chromadb_client import query_guidelines
results = query_guidelines('iron deficiency anaemia treatment')
print(f'Results: {len(results)}, Top: {results[0][\"document\"][:80]}...')
"
```

Expected: Returns relevant clinical guideline chunks about IDA.

---

## Phase 2 Checkpoint

- [ ] All package directories exist with `__init__.py`
- [ ] `config/settings.py` loads all env vars from `.env`
- [ ] `config/database.py` connects to PostgreSQL, can query patients table
- [ ] `config/redis_client.py` can set/get/delete keys
- [ ] `config/chromadb_client.py` queries guidelines using OpenAI embeddings
- [ ] All 4 utilities are importable from any agent or MCP server module
