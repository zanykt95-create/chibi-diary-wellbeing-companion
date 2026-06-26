# Chibi Diary & Wellbeing Companion — Project Spec

## 1. Project Overview

**Name:** Chibi Diary & Wellbeing Companion
**Description:** A personal diary concierge agent that accepts daily text entries, analyzes emotional tone, summarizes content, generates chibi-style artwork to illustrate each entry, and produces weekly/monthly recap digests.
**Goal:** Make journaling delightful by combining LLM-powered emotional intelligence with cute, personalized chibi-art — creating a private, reflective space that feels alive and encouraging.

---

## 2. Architecture Overview

The system is built as a **multi-agent pipeline** using Google ADK. A root orchestrator accepts user input and sequentially fans out to four specialist agents, each with a single clear responsibility.

```
User Input (diary entry text)
        │
        ▼
┌──────────────────────────┐
│  chibi_diary_orchestrator │  ← Root agent (SequentialAgent)
│  chibi_diary/orchestrator.py │
└──────────────────────────┘
        │
        ├──① capture_agent        → validates & cleans raw entry text
        ├──② mood_analysis_agent  → detects primary emotion + intensity score
        ├──③ chibi_illustrator_agent → generates chibi art prompt + image URL
        └──④ memory_agent         → saves summary + metadata to SQLite
```

### Agent Roles

| # | Agent | File | Responsibility |
|---|-------|------|----------------|
| 0 | `chibi_diary_orchestrator` | `chibi_diary/orchestrator.py` | Root; routes input sequentially to all sub-agents; assembles final response |
| 1 | `capture_agent` | `chibi_diary/agents/capture_agent.py` | Receives raw diary text, validates it is non-empty, strips excess whitespace, returns cleaned string |
| 2 | `mood_analysis_agent` | `chibi_diary/agents/mood_analysis_agent.py` | Classifies primary emotion (happy/sad/anxious/grateful/excited/neutral), returns mood + intensity 0.0-1.0 + keywords |
| 3 | `chibi_illustrator_agent` | `chibi_diary/agents/chibi_illustrator_agent.py` | Builds a chibi-art prompt from mood + themes; calls MCP image tool via McpToolset; returns image path |
| 4 | `memory_agent` | `chibi_diary/agents/memory_agent.py` | Summarises entry in ≤50 words; persists to SQLite with date, mood, chibi URL; can retrieve past entries |

### Inter-Agent Communication

Agents communicate via **ADK session state** (`output_key`). Each agent writes its result to a named key; the next agent reads from state via `{key}` placeholders in its instruction. No direct function calls between agents — the orchestrator wires them together deterministically using `SequentialAgent`.

---

## 3. Coding Conventions

### Language & Style
- **Python 3.11+** only
- **Type hints** on every function signature (parameters AND return type)
- **Docstrings** on every class and public function (Google-style: `Args:`, `Returns:`, `Raises:`)
- `snake_case` for functions and variables; `PascalCase` for classes
- Max line length: **100 characters**
- Use `from __future__ import annotations` at the top of files that need forward references

### Imports
- Standard library first, then third-party, then local — separated by blank lines
- Never use wildcard imports (`from module import *`)

### ADK Patterns
- Always import `Agent` from `google.adk.agents`
- Always import `SequentialAgent` from `google.adk.agents` for pipeline orchestration
- Tool functions must have clear Google-style docstrings — ADK sends the docstring to the LLM
- Tool return type must be `dict` (JSON-serializable)
- Type hints are **required** on all tool parameters; omit default values that aren't essential
- Use `output_key` to pass data between sequential agents via session state

### Security
- **NEVER hardcode API keys, passwords, or secrets in source code**
- Always load credentials via `python-dotenv` and `os.environ`
- The `.env` file is gitignored; only `.env.example` is committed
- All database paths must be configurable via environment variables

---

## 4. Critical Instructions for AI Assistants

1. **Always use `google.adk.agents.Agent`** (or `SequentialAgent`/`ParallelAgent`) — never custom HTTP calls to the Gemini API directly.
2. **Never hardcode API keys.** All credentials come from `.env` via `python-dotenv`:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   api_key = os.environ["GOOGLE_API_KEY"]
   ```
3. **Always read `.env` for credentials** — do not accept credentials as function arguments.
4. **Stub tools must return realistic data** so the pipeline can be tested end-to-end before real integrations are wired up.
5. **Log each agent invocation** with `print(f"[orchestrator] → routing to {agent_name}")` so the pipeline is observable.
6. **SQLite writes are synchronous** in this prototype; upgrade to `aiosqlite` when moving to async FastAPI.
7. **The `root_agent` variable** must be defined at module level in `chibi_diary/orchestrator.py` — ADK's CLI discovers it by name.

---

## 5. Agent Routing Rules

The orchestrator applies the following routing logic **in fixed sequential order**:

```
User sends diary entry
  └─ ALWAYS → capture_agent      (validation is mandatory)
       └─ ALWAYS → mood_analysis_agent   (mood is required for art generation)
            └─ ALWAYS → chibi_illustrator_agent  (art is core product value)
                 └─ ALWAYS → memory_agent         (persistence is non-negotiable)
                      └─ Return structured response to user
```

**Conditional routing (future):**
- If `mood_score > 0.8` AND `mood == "anxious"`, add a wellness_tip_agent (Day 3).
- If `date == "Sunday"`, trigger weekly_recap_agent after memory_agent (Day 4).
- Voice input will be pre-processed by a transcription agent before capture_agent (Day 5).

---

## 6. File Map

```
chibi-diary/
├── GEMINI.md                        ← You are here
├── README.md                        ← User-facing project overview
├── pyproject.toml                   ← Python dependencies
├── .env.example                     ← Credential template (no real values)
├── agents-cli-manifest.yaml         ← ADK CLI manifest
├── Dockerfile                       ← Container image definition
├── cloudbuild.yaml                  ← Cloud Build + Cloud Run deployment
├── deploy.sh                        ← Deployment convenience script
├── chibi_diary/
│   ├── __init__.py                  ← Package init (re-exports root_agent for ADK)
│   ├── orchestrator.py              ← Root SequentialAgent orchestrator definition
│   ├── eval_set_1.evalset.json      ← ADK eval cases (run with: adk eval chibi_diary eval_set_1)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── capture_agent.py         ← Stage 1: InputSanitizer + validation
│   │   ├── mood_analysis_agent.py   ← Stage 2: emotion detection + intensity
│   │   ├── chibi_illustrator_agent.py ← Stage 3: McpToolset → Imagen 3
│   │   └── memory_agent.py          ← Stage 4: SQLite persistence + insights
│   ├── tools/
│   │   ├── __init__.py
│   │   └── placeholder_tools.py     ← Tool implementations (real SQLite + stub chibi)
│   └── memory/
│       ├── __init__.py
│       ├── session_memory.py        ← In-memory session scratch pad
│       └── long_term_memory.py      ← SQLite-backed diary history
├── mcp_server/
│   ├── __init__.py
│   ├── chibi_mcp_server.py          ← FastMCP server exposing generate_chibi_image
│   └── imagen_client.py             ← Vertex AI Imagen 3 client wrapper
└── tests/
    ├── __init__.py
    ├── test_orchestrator.py         ← Smoke + unit tests
    ├── test_mcp_server.py           ← MCP server + ImagenClient tests
    ├── test_evaluation.py           ← E2E pipeline + memory quality eval
    └── test_security.py             ← Prompt injection + sanitizer tests
```

---

## 7. Day-by-Day Build Plan

| Day | Focus |
|-----|-------|
| 1 | ✅ Scaffold all agents, stubs, memory layer (this file) |
| 2 | ✅ Replace chibi stub with real MCP image-generation server |
| 3 | ✅ Add wellness tips, emotion trend tracking |
| 4 | ✅ Weekly/monthly recap generation |
| 5 | ✅ Final Orchestrator & Deployability (Docker + Cloud Run) |

## 8. Deployment Spec (Day 5)

### Local Development
```bash
uv sync
adk web        # opens http://localhost:8000 — pick `chibi_diary` from the dropdown
```

### Docker
```bash
docker build -t chibi-diary .
docker run -p 8080:8080 --env-file .env chibi-diary
```

### Cloud Run (Production)
```bash
./deploy.sh   # builds → pushes → deploys to Cloud Run
```

### Environment Variables Required at Runtime
| Variable | Source | Required |
|----------|--------|---------|
| GOOGLE_CLOUD_PROJECT | GCP project | Yes |
| GOOGLE_GENAI_USE_VERTEXAI | Set to "True" | Yes |
| DATABASE_PATH | SQLite file path | No (default: ./chibi_diary.db) |

### Security Notes for Deployment
- NEVER bake .env into Docker image — always inject via --env-file or Cloud Run secrets
- Use Google Secret Manager for production credentials
- MCP server runs as subprocess inside the container — no external port needed

## 9. Concepts Demonstrated (≥3/6 requirement)
| Concept | Where | Evidence |
|---------|-------|---------|
| Multi-agent (ADK SequentialAgent) | chibi_diary/orchestrator.py | SequentialAgent + 4 sub-agents |
| MCP Server | mcp_server/ | FastMCP + Imagen 3 real image generation |
| Security | chibi_diary/agents/capture_agent.py | InputSanitizer + SECURITY_AUDIT_LOG |
| Antigravity | — | Built & demoed in Google Antigravity IDE |
| Deployability | Dockerfile + cloudbuild.yaml | Docker + Cloud Run ready |

