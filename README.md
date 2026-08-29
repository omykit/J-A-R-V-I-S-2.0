# 🤖 J.A.R.V.I.S 2.0

> **Just A Rather Very Intelligent System**

JARVIS 2.0 is a modular AI voice assistant built around a microservice architecture. It combines a locally hosted Large Language Model, deterministic command handling, contextual memory, speech interaction, Docker-based service orchestration, and a PostgreSQL-backed memory system.

The project is designed as an evolution from a monolithic assistant architecture toward a scalable, testable, and modular AI system.

---

# 🚀 Current Status

**Current Development Stage:** Core backend architecture complete and functional.

### Verified capabilities

* ✅ Docker-based microservice architecture
* ✅ API Gateway routing
* ✅ Local Ollama LLM integration
* ✅ Custom `jarvis` Ollama model
* ✅ Neon PostgreSQL cloud database
* ✅ Persistent contextual memory
* ✅ AI conversation routing
* ✅ Deterministic command execution
* ✅ Location-aware time queries
* ✅ Docker ↔ Windows host networking
* ✅ SSL/TLS verified database connections
* ✅ Service health monitoring
* ✅ 149 automated tests passing
* ✅ Git version-controlled baseline

The project is currently preparing for **human voice interaction testing and further optimization before Phase 7 development**.

---

# 🧠 Architecture Overview

JARVIS 2.0 follows a microservice architecture where each major responsibility is separated into its own service.

```text
                           ┌─────────────────────┐
                           │   Voice Client      │
                           │  STT / TTS / UI     │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │    API Gateway      │
                           │      :8080          │
                           └──────────┬──────────┘
                                      │
                     ┌────────────────┼────────────────┐
                     │                │                │
                     ▼                ▼                ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ AI Service   │  │ Command      │  │ Memory       │
            │    :8002     │  │ Service      │  │ Service      │
            │              │  │    :8003     │  │    :8001     │
            └──────┬───────┘  └──────────────┘  └──────┬───────┘
                   │                                    │
                   ▼                                    ▼
        ┌─────────────────────┐              ┌─────────────────────┐
        │ Ollama (Host)       │              │ Neon PostgreSQL     │
        │ Custom Jarvis Model │              │ Contextual Memory   │
        └─────────────────────┘              └─────────────────────┘
```

---

# 🏗️ Core Components

## 🌐 API Gateway

The Gateway acts as the central entry point for JARVIS.

Responsibilities include:

* Receiving user requests
* Routing requests to the command service
* Falling back to the AI service when necessary
* Aggregating service health information
* Returning a unified response format

Example routing flow:

```text
User Input
    │
    ▼
Gateway
    │
    ├── Can command-service handle this?
    │         │
    │         ├── Yes → Execute deterministic command
    │         │
    │         └── No
    │
    ▼
AI Service
    │
    ├── Retrieve contextual memory
    │
    ├── Build system context
    │
    ▼
Ollama
    │
    ▼
Response
```

---

# 🧠 AI Service

The AI service manages communication with the locally hosted Ollama instance.

Features include:

* Custom Ollama model support
* Model availability detection
* Configurable model selection
* Fallback model chain
* Contextual memory injection
* Health caching with automatic refresh
* Graceful fallback responses

The currently configured primary model is:

```text
jarvis
```

The model is built using:

```text
qwen2.5:3b-instruct
```

with a custom JARVIS personality defined through:

```text
ollama/jarvis.modelfile
```

---

# 🤖 Ollama Integration

Ollama runs directly on the Windows host rather than inside Docker.

```text
Windows Host
│
├── Ollama
│     └── jarvis model
│
└── Docker Compose
      │
      └── AI Service
             │
             ▼
      host.docker.internal:11434
```

This allows the Dockerized AI service to communicate with the GPU-enabled Ollama instance running on the host machine.

---

# 🧠 Contextual Memory

JARVIS includes a persistent memory service backed by PostgreSQL.

The memory system allows the assistant to retrieve stored information and inject relevant context into AI interactions.

Architecture:

```text
AI Service
     │
     ▼
Memory Service
     │
     ▼
PostgreSQL / Neon
```

The database connection supports TLS verification using Python's SSL context.

Neon-specific connection parameters such as:

```text
sslmode=require
channel_binding=require
```

are safely handled internally for compatibility with SQLAlchemy and `asyncpg`.

---

# ⚡ Command Service

The Command Service handles deterministic operations without unnecessarily invoking the LLM.

Examples include:

* Time queries
* Location-aware time queries
* Date queries
* Weather functionality
* Location detection
* Structured commands

Example:

```text
"What time is it in Tokyo?"
```

The command service resolves:

```text
Tokyo
↓
Asia/Tokyo
↓
Current local time
```

If a location cannot be confidently resolved, JARVIS avoids guessing.

Example:

```text
"What time is it in Wakanda?"
```

Response behavior:

> I couldn't work out which timezone Wakanda is in, so I'd rather not guess.

This prevents the AI system from confidently returning incorrect deterministic information.

---

# 🎙️ Voice Interaction

The JARVIS client is responsible for the user interaction layer.

The broader voice pipeline is designed around:

```text
Microphone
    │
    ▼
Speech-to-Text
    │
    ▼
Gateway
    │
    ├── Command Service
    │
    └── AI Service
          │
          ▼
        Ollama
    │
    ▼
Response
    │
    ▼
Text-to-Speech
    │
    ▼
Speaker
```

Voice interaction testing is one of the next major validation stages.

---

# 🐳 Docker Architecture

The backend services are containerized using Docker Compose.

Current services:

```text
memory-service
ai-service
command-service
gateway
```

Ollama intentionally runs outside Docker on the Windows host.

Start the backend services with:

```bash
docker compose up --build
```

Check service status:

```bash
docker compose ps
```

Gateway health:

```bash
curl http://localhost:8080/health
```

Expected structure:

```json
{
  "status": "ok",
  "services": {
    "memory": {
      "status": "ok"
    },
    "ai": {
      "status": "ok"
    },
    "command": {
      "status": "ok"
    }
  }
}
```

---

# 🔐 Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Important configuration groups:

```text
JARVIS_MEMORY_
JARVIS_AI_
JARVIS_CMD_
JARVIS_GW_
```

The project intentionally keeps real credentials out of version control.

The following files should never be committed:

```text
.env
.env.local
.neon
memory.json
*.log
```

See `.env.example` for the complete configuration reference.

---

# 🗄️ Database

JARVIS uses PostgreSQL-compatible storage for persistent memory.

The project currently supports:

* Neon PostgreSQL
* Local PostgreSQL
* Other PostgreSQL-compatible providers

Database communication is handled by:

```text
SQLAlchemy
+
asyncpg
```

TLS certificate verification remains enabled when database SSL is configured.

---

# 🧪 Testing

The project currently includes automated tests covering:

* Service configuration
* Database connectivity
* Memory functionality
* AI service behavior
* Command routing
* Timezone resolution
* Gateway routing
* HTTP endpoints
* Ollama health caching
* Unknown location safety

Run the full test suite:

```bash
pytest services/ -q
```

Current verified result:

```text
149 passed
```

Tests are designed to avoid unnecessary live network dependencies where deterministic testing is possible.

---

# 📁 Project Structure

```text
J-A-R-V-I-S-2.0/
│
├── client/
│   └── Voice client and desktop interaction
│
├── services/
│   │
│   ├── ai/
│   │   └── Ollama and AI response service
│   │
│   ├── command/
│   │   └── Deterministic command processing
│   │
│   ├── gateway/
│   │   └── Central API routing layer
│   │
│   └── memory/
│       └── Persistent memory service
│
├── shared/
│   └── Shared schemas and utilities
│
├── ollama/
│   └── jarvis.modelfile
│
├── scripts/
│   └── Development and utility scripts
│
├── docs/
│   ├── architecture.md
│   └── setup.md
│
├── legacy/
│   └── Previous architecture retained for reference
│
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

---

# ⚙️ Running JARVIS Locally

## 1. Clone the repository

```bash
git clone https://github.com/omykit/J-A-R-V-I-S-2.0.git
cd J-A-R-V-I-S-2.0
```

---

## 2. Create a Python environment

```bash
python -m venv .venv
```

Activate it:

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 3. Install dependencies

Install the required dependencies for the project.

Refer to the individual service requirements and project setup documentation:

```text
docs/setup.md
```

---

## 4. Configure environment variables

```powershell
Copy-Item .env.example .env
```

Update `.env` with your local configuration.

Do not commit this file.

---

## 5. Start Ollama

Ollama must run on the Windows host.

```powershell
ollama serve
```

Check available models:

```powershell
ollama list
```

---

## 6. Create the custom Jarvis model

From the repository root:

```powershell
ollama create jarvis -f ollama/jarvis.modelfile
```

Test it:

```powershell
ollama run jarvis "Hello Jarvis, who are you?"
```

---

## 7. Start Docker services

```powershell
docker compose up --build
```

Check service status:

```powershell
docker compose ps
```

---

## 8. Verify system health

Memory service:

```text
http://localhost:8001/health
```

AI service:

```text
http://localhost:8002/health
```

Command service:

```text
http://localhost:8003/health
```

Gateway:

```text
http://localhost:8080/health
```

---

# 💬 Example Requests

## AI Conversation

```http
POST /chat
```

Example:

```json
{
  "text": "Hello Jarvis, who are you?",
  "chat_history": [],
  "selected_action": "chrome",
  "last_action": "chrome",
  "owner_name": "Omair"
}
```

Example response:

```json
{
  "source": "ai",
  "spoken_text": "I'm Jarvis, your personal assistant.",
  "full_text": "I'm Jarvis, your personal AI assistant. How can I help you?",
  "model_used": "jarvis"
}
```

---

## Deterministic Command

```text
What time is it in Tokyo?
```

The request is routed to the Command Service rather than unnecessarily consuming LLM resources.

Example:

```json
{
  "source": "command",
  "spoken_text": "The time in Tokyo is 7:16 AM.",
  "model_used": null
}
```

---

# 🧩 Technology Stack

### Backend

* Python
* FastAPI
* Uvicorn
* Pydantic

### AI

* Ollama
* Qwen 2.5
* Custom JARVIS model

### Database

* PostgreSQL
* Neon
* SQLAlchemy
* asyncpg

### Infrastructure

* Docker
* Docker Compose

### Voice

* Speech-to-Text pipeline
* Text-to-Speech pipeline
* Local voice interaction components

### Testing

* Pytest

### Version Control

* Git
* GitHub

---

# 🛣️ Development Roadmap

## Phase 1–6

Core architecture and foundational systems.

* Microservice architecture
* Docker infrastructure
* AI service
* Command service
* Memory service
* API Gateway
* Neon database integration
* Ollama integration
* Custom Jarvis model
* Contextual memory
* Location-aware commands

**Status: Core functionality implemented and verified.**

---

## Current Priority

### 1. CLI Launcher

Build a reliable launcher that can automate:

```text
Check Ollama
        ↓
Check Docker
        ↓
Start required services
        ↓
Wait for health checks
        ↓
Launch JARVIS client
```

This will replace error-prone manual startup sequences.

---

### 2. Human Voice Testing

The next major validation stage will test the complete real-world interaction pipeline:

```text
Voice Input
     ↓
Speech Recognition
     ↓
Gateway
     ↓
Command / AI Routing
     ↓
Memory Retrieval
     ↓
AI Response
     ↓
Text-to-Speech
     ↓
User
```

This testing phase will identify practical issues that automated tests cannot detect.

---

### 3. Performance Optimization

Following human testing:

* Reduce response latency
* Improve STT accuracy
* Improve contextual memory relevance
* Optimize model performance
* Improve command routing
* Reduce unnecessary service calls

---

### 4. Phase 7

Phase 7 planning will begin after the current system has completed real-world testing and optimization.

Future development decisions will be based on actual system behavior rather than assumptions.

---

# 🎯 Design Philosophy

JARVIS 2.0 follows several core engineering principles:

### Modular over monolithic

Each major responsibility belongs to an independent service.

### Deterministic when possible

Simple factual operations should not consume LLM resources unnecessarily.

### AI when necessary

Natural conversation and reasoning are delegated to the language model.

### Context-aware responses

Relevant memory should improve conversations without overwhelming the model.

### Local-first intelligence

Core AI capabilities can run locally through Ollama.

### Safety over confident guessing

If deterministic information cannot be resolved reliably, JARVIS should avoid inventing an answer.

### Test before optimizing

Architecture changes should be driven by real evidence and testing.

---

# 🔒 Security Notes

This repository intentionally excludes:

* API keys
* Database credentials
* Neon connection strings
* Local environment files
* Personal memory data
* Logs
* Local AI models
* Voice models

Use `.env.example` as the configuration template.

**Never commit your real `.env` file.**

---

# 🤝 Contributing

JARVIS 2.0 is currently an actively evolving personal engineering project.

Before making architectural changes:

1. Inspect the current architecture.
2. Understand service dependencies.
3. Avoid unnecessary rewrites.
4. Preserve working functionality.
5. Add regression tests when fixing bugs.
6. Avoid committing secrets.
7. Prefer evidence-driven changes.

---

# 📌 Current Known-Good Baseline

The current Git baseline represents a verified working architecture including:

* Docker services operational
* Neon database connectivity
* TLS database verification
* Ollama connectivity
* Custom Jarvis model
* Gateway routing
* Command routing
* Contextual memory
* Location-aware time queries
* Automated test suite passing

This baseline serves as a recoverable checkpoint before further development.

---

# 🧑‍💻 Author

**Omair Kittur**

JARVIS 2.0 is a personal AI engineering project focused on building a modular, locally integrated intelligent assistant using modern AI infrastructure.

---

# ⚠️ Project Status

JARVIS 2.0 is under active development.

The backend architecture is operational, but the project is still undergoing validation and real-world voice interaction testing.

Future development will focus on:

```text
Reliability
↓
Human Testing
↓
Optimization
↓
New Capabilities
```

---

> *"Sometimes you gotta run before you can walk."*

**J.A.R.V.I.S 2.0 — Building an intelligent assistant, one system at a time.** 🤖
