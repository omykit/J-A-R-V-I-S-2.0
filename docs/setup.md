# JARVIS Setup Guide

## Prerequisites

- **Python 3.12+** (for the voice client)
- **Docker & Docker Compose** (for the containerized services)
- **Ollama** installed on the host with the `jarvis` model created
- **NeonDB** account with a Postgres database (or any Postgres-compatible database)

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your actual values:
#   DATABASE_URL — your NeonDB connection string
#   WEATHER_API_KEY — optional, for weather commands
#   OPENWEATHER_API_KEY — optional, for weather commands
```

### 2. Create the Ollama model (if not already done)

```bash
ollama create jarvis -f ollama/jarvis.modelfile
```

### 3. Start the services

```bash
docker-compose up -d
```

Verify all services are healthy:
```bash
curl http://localhost:8080/health
```

### 4. Migrate existing data (optional)

If you have existing `memory.json` or `jarvis_config.json` data:
```bash
python scripts/migrate_json_to_postgres.py
```

### 5. Start the voice client

```bash
# Option A: Use the launcher
client\start-jarvis.bat

# Option B: Run directly
cd client && python desktop_app.py
```

## Development Setup

### Install dependencies for local development

```bash
# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install all dev dependencies
pip install -e ".[dev,gateway,ai,command,memory,client]"
```

### Run services individually (without Docker)

```bash
# Terminal 1: Memory service
cd services/memory && uvicorn memory_service.main:app --port 8001

# Terminal 2: AI service
cd services/ai && uvicorn ai_service.main:app --port 8002

# Terminal 3: Command service
cd services/command && uvicorn command_service.main:app --port 8003

# Terminal 4: Gateway
cd services/gateway && uvicorn gateway.main:app --port 8080

# Terminal 5: Voice client
cd client && python desktop_app.py
```

### Run tests

```bash
# Unit tests
pytest services/memory/tests/
pytest services/ai/tests/
pytest services/command/tests/
pytest services/gateway/tests/

# Smoke tests
python test_jarvis_smoke.py
```

## Project Structure

```
J-A-R-V-I-S/
├── docker-compose.yml          # Orchestrates all services
├── .env.example                # Environment variable template
├── pyproject.toml              # Monorepo root config
├── services/
│   ├── gateway/                # API gateway (:8080)
│   ├── ai/                     # AI/LLM service (:8002)
│   ├── command/                # Command routing (:8003)
│   └── memory/                 # Data persistence (:8001)
├── client/                     # Desktop voice client (host)
├── shared/                     # Shared Pydantic schemas
├── scripts/                    # Utility scripts
├── docs/                       # Documentation
├── ollama/                     # Ollama model configuration
├── models/                     # STT/TTS model files (git-ignored)
├── tests/                      # Integration tests
└── legacy/                     # Archived web UI files
```

## Ports

| Service | Port | URL |
|---------|------|-----|
| Gateway | 8080 | http://localhost:8080 |
| Memory Service | 8001 | http://localhost:8001 |
| AI Service | 8002 | http://localhost:8002 |
| Command Service | 8003 | http://localhost:8003 |
| Ollama | 11434 | http://localhost:11434 |
