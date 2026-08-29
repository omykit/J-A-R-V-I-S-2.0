# JARVIS Architecture

## Overview

JARVIS is a personal AI voice assistant built with a microservices architecture. The system consists of containerized backend services communicating over HTTP, with a host-native voice client for audio I/O.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    HOST (bare metal)                        │
│                                                             │
│  ┌──────────────┐         ┌──────────────────┐              │
│  │ 🎤 Microphone │────────▶│  Voice Client    │              │
│  │ 🔊 Speaker    │◀────────│  (Vosk/Piper/    │              │
│  └──────────────┘         │   Tkinter GUI)   │              │
│                           └────────┬─────────┘              │
│                                    │ HTTP                    │
│  ┌─────────────┐                   │                        │
│  │ Ollama (GPU) │◀─────────┐       │                        │
│  └─────────────┘           │       │                        │
│                            │       │                        │
│  ┌─────────────────────────┼───────┼────────────────────┐   │
│  │ Docker Compose          │       │                    │   │
│  │                         │       ▼                    │   │
│  │  ┌──────────────────────┴───────────────┐            │   │
│  │  │         Gateway (:8080)              │            │   │
│  │  │    Routes: command → ai fallback     │            │   │
│  │  └────────┬──────────┬─────────┬────────┘            │   │
│  │           │          │         │                     │   │
│  │           ▼          ▼         ▼                     │   │
│  │  ┌────────────┐ ┌─────────┐ ┌──────────────┐        │   │
│  │  │ Command    │ │   AI    │ │   Memory     │        │   │
│  │  │ Service    │ │ Service │ │   Service    │        │   │
│  │  │ (:8003)    │ │ (:8002) │ │   (:8001)    │        │   │
│  │  └──────┬─────┘ └────┬────┘ └──────┬───────┘        │   │
│  │         │            │             │                │   │
│  │         └────────────┼─────────────┘                │   │
│  │                      │                              │   │
│  └──────────────────────┼──────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│                   ┌──────────┐                               │
│                   │ NeonDB   │ (cloud Postgres)              │
│                   └──────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

## Services

### Gateway (`:8080`)
- **Location**: `services/gateway/`
- **Purpose**: Central API entry point for all clients
- **Routes**: `POST /chat` — routes text to command-service first, falls back to ai-service
- **Health**: `GET /health` — aggregates health from all downstream services

### AI Service (`:8002`)
- **Location**: `services/ai/`
- **Purpose**: LLM orchestration via Ollama
- **Routes**: `POST /chat` — returns one JSON response (`spoken_text`/`full_text`); the request to Ollama/OpenAI is streamed internally to build that response but nothing is streamed back to the caller yet — client-facing streaming (SSE/WebSocket) is a Jarvis 2.0 item. `GET /health` — Ollama status
- **Dependencies**: Ollama (host), Memory Service (memories context)

### Command Service (`:8003`)
- **Location**: `services/command/`
- **Purpose**: Deterministic command matching (time, weather, reminders, app launch intents)
- **Routes**: `POST /execute` — returns `CommandResult` with action intents
- **Dependencies**: Memory Service (for memory/reminder CRUD)

### Memory Service (`:8001`)
- **Location**: `services/memory/`
- **Purpose**: Persistent storage for memories, reminders, config, conversations
- **Routes**: Full CRUD on `/memories`, `/reminders`, `/config`, `/conversations`
- **Database**: NeonDB (cloud Postgres) via SQLAlchemy async

### Voice Client (host)
- **Location**: `client/`
- **Purpose**: Speech-to-text (Vosk), text-to-speech (Piper), Tkinter desktop GUI
- **Runs on**: Host machine (not containerized — needs mic/speaker access)
- **Communicates via**: HTTP to Gateway

## Data Flow

1. User speaks → **Voice Client** captures audio via Vosk STT
2. Recognized text → HTTP POST to **Gateway** `/chat`
3. Gateway → **Command Service** `/execute` (deterministic matching)
4. If matched → returns response directly
5. If unmatched → Gateway → **AI Service** `/chat` (LLM completion)
6. AI Service fetches memory context from **Memory Service**
7. Response returned to **Voice Client** → Piper TTS → speaker

## Configuration

All services use `pydantic-settings` with environment variables:

| Env Var | Service | Default |
|---------|---------|---------|
| `JARVIS_MEMORY_DATABASE_URL` | memory | `postgresql+asyncpg://...` |
| `JARVIS_AI_OLLAMA_BASE_URL` | ai | `http://localhost:11434` |
| `JARVIS_AI_MODEL` | ai | `jarvis` |
| `JARVIS_CMD_WEATHER_API_KEY` | command | *(empty)* |
| `JARVIS_GW_ALLOWED_ORIGINS` | gateway | `http://localhost:3000,http://localhost:19006,http://127.0.0.1:3000` |
| `GATEWAY_URL` | client (unprefixed) | `http://localhost:8080` |

See [`.env.example`](../.env.example) for the complete list.

## Running

```bash
# Start all containerized services
docker-compose up -d

# Start the voice client on the host
cd client && python desktop_app.py
```
