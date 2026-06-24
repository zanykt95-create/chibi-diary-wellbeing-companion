# 🎀 Chibi Diary & Wellbeing Companion

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-2.x-orange.svg)](https://github.com/google/ai-agent-developer-kit)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Gemini-purple.svg)](https://deepmind.google/technologies/gemini/)
[![License Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](https://opensource.org/licenses/Apache-2.0)

> **Your personal diary concierge — powered by Google ADK & Gemini**

Chibi Diary & Wellbeing Companion is an AI-powered journaling system that transforms daily text entries into beautiful chibi-style illustrations while tracking your emotional journey over time. The application is built using the Google AI Agent Developer Kit (ADK) and orchestrates special-purpose sub-agents in a secure, structured pipeline, persisting memories to an SQLite database, generating real image art via an Imagen 3 MCP server, and rendering Vietnamese wellbeing insights.

---

## 🏗️ Architecture

```
User Input
    │
    ▼
chibi_diary_orchestrator (Workflow)
    ├── 1. capture_agent          → validates & cleans text (InputSanitizer)
    ├── 2. mood_analysis_agent    → detects emotion + intensity
    ├── 3. chibi_illustrator_agent → generates chibi art via MCP (Imagen 3)
    └── 4. memory_agent           → saves entry to SQLite + Vietnamese insight
```

All agents use the **Google ADK** framework and the `gemini-2.5-flash` model. Inter-agent state is passed cleanly via ADK session state using the `output_key` parameter.

---

## ✨ Features

| Feature | Status |
|:---|:---|
| 📝 Diary Entry Capture & Security Sanitization | ✅ Completed (Day 1 + Day 4 Security) |
| 🧠 Mood Analysis & Intensity Score | ✅ Completed (Day 1) |
| 🎨 Chibi Art Generation via Imagen 3 MCP | ✅ Completed (Day 2) |
| 💾 SQLite Long-term Memory | ✅ Completed (Day 1 + Day 3 upgrade) |
| 📊 Mood Trend, Recaps, and Streak Retrieval | ✅ Completed (Day 3) |
| 🇻🇳 Contextual Vietnamese Wellbeing Insights | ✅ Completed (Day 3) |
| 🛡️ Security Audit Logging | ✅ Completed (Day 4) |
| 🧪 Structured Evaluation & Security Testing | ✅ Completed (Day 4) |

---

## 🚀 Quick Start

### Path A: Local Development
1. **Clone the repository and install dependencies:**
   ```bash
   git clone <repo-url>
   cd chibi-diary
   uv sync
   ```

2. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Add your credentials (GOOGLE_API_KEY) in .env
   ```

3. **Start the ADK Web server:**
   ```bash
   uv run adk web app
   ```
   *This starts the web server locally and displays the interactive UI at [http://localhost:8080](http://localhost:8080).*

---

### Path B: Docker Container
1. **Build the Docker image:**
   ```bash
   docker build -t chibi-diary .
   ```

2. **Run the container locally:**
   ```bash
   docker run -p 8080:8080 --env-file .env chibi-diary
   ```
   *Note: Ensure your `.env` contains the required credentials. The MCP server will start up automatically inside the container.*

---

## 🚀 Deploy to Cloud Run

> ⚠️ **Demo Deployment Note:** The deployment scripts use `--allow-unauthenticated` to allow Kaggle competition judges to access the live demo without credentials. For a personal production deployment, remove this flag and restrict access to specific Google accounts via IAM:
> ```bash
> gcloud run services add-iam-policy-binding chibi-diary \
>   --member="user:your@email.com" \
>   --role="roles/run.invoker" \
>   --region=us-central1
> ```

### Option A: Using deploy.sh
A convenience script is provided to automate build, registry push, and Cloud Run deployment.
```bash
# Set GOOGLE_CLOUD_PROJECT to target project, or defaults to chibi-diary-2306
./deploy.sh
```

### Option B: Using gcloud Directly
Submit build directly using the Google Cloud Build configuration:
```bash
gcloud builds submit --config cloudbuild.yaml --project=chibi-diary-2306
```

---

## 🔧 Environment Variables

| Variable | Purpose | Required |
|----------|---------|:---:|
| `GOOGLE_API_KEY` | Gemini API key (AI Studio / Developer Key) | Yes (local) |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID (Vertex AI, Cloud Run) | Yes (deploy) |
| `GOOGLE_GENAI_USE_VERTEXAI`| Set to "True" to route requests through Vertex AI | Yes |
| `DATABASE_PATH` | SQLite DB file path (default: `./chibi_diary.db`) | No |

---

## 🧪 Running Tests

Execute the full testing suite (including smokes, evaluation, and security checks):
```bash
uv run pytest tests/ -v --tb=short
```

---

## 📁 Project Structure

```
chibi-diary/
├── GEMINI.md                    # Detailed spec & agent implementation notes
├── README.md                    # This file
├── pyproject.toml               # Python dependencies
├── .env.example                 # Environment configuration template
├── agents-cli-manifest.yaml     # ADK CLI configuration manifest
├── Dockerfile                   # Docker image definition
├── .dockerignore                # Docker build context exclusions
├── cloudbuild.yaml              # Cloud Build definition for Cloud Run
├── deploy.sh                    # Deployment convenience script
├── app/
│   ├── orchestrator.py          # Root Workflow orchestrator
│   ├── agents/                  # 4 sequential specialist agents
│   │   ├── capture_agent.py     # Captures, sanitizes (InputSanitizer) and validates
│   │   ├── mood_analysis_agent.py # Identifies feelings and intensity scores
│   │   ├── chibi_illustrator_agent.py # Prompts Imagen 3 via MCP for art
│   │   └── memory_agent.py      # Persistence, Vietnamese insights
│   ├── tools/                   # Action tools used by agents
│   └── memory/                  # Session and SQLite long-term storage
├── mcp_server/                  # FastMCP Imagen 3 subprocess server
└── tests/                       # Complete test suite
    ├── test_orchestrator.py     # Component and integration smoke tests
    ├── test_mcp_server.py       # MCP client and server validation tests
    ├── test_evaluation.py       # E2E pipeline and memory quality tests
    └── test_security.py         # Prompt injection and sanitizer test suite
```

---

## 💡 Concepts Demonstrated

*   **Multi-agent system (ADK Workflow)**: Wire specialized single-purpose agents (`capture_agent`, `mood_analysis_agent`, `chibi_illustrator_agent`, `memory_agent`) sequentially using the modern ADK `Workflow` orchestration class.
*   **MCP Server (FastMCP + Imagen 3)**: Implements custom `FastMCP` server connecting to Google's Imagen 3 model via Vertex AI, handling asynchronous image generation and disk persistence.
*   **Security (InputSanitizer + Audit Logs)**: Integrates strict defense-in-depth sanitization, SQL/prompt injection detection, and security audit log tracing.
*   **Google Antigravity**: Developed, tested, and validated dynamically in the Google Antigravity IDE workspace.
*   **Deployability (Docker + Cloud Run)**: Fully containerized environment with configuration rules ready for cloud deployment.

---

## 📄 License

Apache 2.0 — see [LICENSE](LICENSE).
