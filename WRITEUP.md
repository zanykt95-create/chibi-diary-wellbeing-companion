# Chibi Diary & Wellbeing Companion

**Track:** Concierge Agents  
**Author:** Z (datlq@mynavitechtus.com)  
**Project:** [GitHub Repo](https://github.com/) | [Video Demo](https://youtube.com/)

---

## The Problem: Journaling is Broken for the Modern Mind

Most people know journaling is good for them. Research consistently links regular reflection with reduced anxiety, better emotional regulation, and improved self-awareness. Yet the habit rarely sticks. The blank page is intimidating. Rereading old entries is tedious. There is no feedback loop — you write into a void and never know if anything is changing.

The root cause is that traditional journaling is a one-way monologue. You pour thoughts onto a page, and nothing responds. Nothing remembers. Nothing connects the dots between how you felt last Tuesday and how you feel today.

What if your journal could actually *listen*?

---

## The Solution: A Concierge Agent That Knows You

**Chibi Diary & Wellbeing Companion** is a personal journaling agent built on Google ADK. You share how your day went — in text or voice — and the agent does the rest: it validates your entry, analyzes your emotional state, generates a personalized chibi-style illustration that captures your mood, and stores everything into a persistent memory layer that grows smarter over time.

Every interaction is a two-way conversation. Over days and weeks, the agent recalls your patterns, surfaces trends ("you've been stressed for 5 days in a row"), and produces weekly and monthly chibi diary recaps — a visual, shareable summary of your emotional journey.

The result is a journaling companion that feels less like writing in a notebook and more like talking to a thoughtful friend who never forgets anything you've said.

---

## Why This Needs Agents (Not Just a Chatbot)

A single LLM prompt cannot do this well. Each task requires different expertise, tools, and memory access:

- **Validating an entry** requires a different mindset than **analyzing emotion**.
- **Generating a chibi image** requires calling an external image model via a tool — not something a single text-completion can do natively.
- **Storing and querying memories** requires database operations that need to be reliable and repeatable, not probabilistic.
- **Coordinating all of this** requires an orchestration layer that ensures each step receives the right input and produces a clean output for the next stage.

This is exactly the problem multi-agent systems solve. By decomposing the task into specialized agents connected in a pipeline, each agent can do one thing well, and the overall system becomes more maintainable, testable, and extensible.

---

## Architecture: Four Agents, One Pipeline

The system uses Google ADK's `Workflow` (with `SequentialAgent` fallback for ADK 2.x compatibility) to orchestrate four specialized sub-agents:

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                          │
│              (ADK Workflow / SequentialAgent)           │
└──────────┬──────────────────────────────────────────────┘
           │  Passes state through output_key chain
           ▼
┌──────────────────┐    ┌───────────────────┐    ┌──────────────────────┐    ┌───────────────────┐
│  Capture Agent   │───▶│ Mood Analysis     │───▶│ Chibi Illustrator    │───▶│  Memory Agent     │
│  Stage 1         │    │ Agent  Stage 2    │    │ Agent  Stage 3       │    │  Stage 4          │
│                  │    │                   │    │                      │    │                   │
│ - Sanitize input │    │ - Emotion detect  │    │ - MCP → Imagen 3     │    │ - Recall trend    │
│ - Security audit │    │ - Score + label   │    │ - Map mood to prompt │    │ - Save to SQLite  │
│ - Output: clean  │    │ - Output: report  │    │ - Output: PNG path   │    │ - Context insight │
│   entry text     │    │   + primary mood  │    │                      │    │ - Streak tracker  │
└──────────────────┘    └───────────────────┘    └──────────────────────┘    └───────────────────┘
                                                          │
                                              ┌───────────┴───────────┐
                                              │    MCP SERVER         │
                                              │  (FastMCP / stdio)    │
                                              │  Imagen 3 via         │
                                              │  google-genai SDK     │
                                              └───────────────────────┘
```

### Agent Responsibilities

**Capture Agent** is the entry point and security gateway. It receives raw user input, strips HTML, truncates to 2,000 characters, detects prompt injection and SQL injection patterns, and writes to a real-time `SECURITY_AUDIT_LOG`. Only a clean, validated string passes to the next stage. The `output_key="captured_entry"` makes this output available to all downstream agents via ADK's shared session state.

**Mood Analysis Agent** receives the clean entry and performs emotion classification using Gemini 2.5 Flash. It outputs a structured `mood_report` containing a primary mood label (e.g., `happy`, `stressed`, `melancholic`), an intensity score, and an explanation. This structured output is what drives the chibi illustration — not raw text.

**Chibi Illustrator Agent** maps the mood report to a detailed image generation prompt (via the `map_mood_to_chibi_prompt` helper, which is fully unit-tested), then calls the MCP Server tool to invoke Imagen 3. The generated PNG is saved locally and its path stored in `chibi_result`. If image generation fails, the agent falls back gracefully with an error note rather than crashing the pipeline.

**Memory Agent** is the most stateful component. Before saving, it recalls the user's recent mood trend and current streak from SQLite. This context is included in the final output as `context_insight` — a short human-readable note in Vietnamese (e.g., "Bạn đang có chuỗi 5 ngày liên tiếp tâm trạng tích cực!"). After generating this insight, it persists the full entry (text, mood, chibi path, tags) to the long-term database.

---

## Key Implementation Details

### MCP Server: Bridging the Agent to Image Generation

The image generation capability is exposed as an MCP (Model Context Protocol) server built with FastMCP, using `stdio` transport. The server exposes a single tool, `generate_chibi_image`, which accepts a `prompt` string and returns the local PNG path.

The Chibi Illustrator Agent connects to this server at runtime using ADK's `McpToolset` with `StdioConnectionParams` (timeout set to 60 seconds to accommodate Imagen 3's latency). The separation of image generation into an MCP server means it can be swapped, upgraded, or replaced without touching any agent code.

```python
# mcp_server/chibi_mcp_server.py (simplified)
from mcp.server.fastmcp import FastMCP
from google import genai

mcp = FastMCP("chibi-image-server")

@mcp.tool()
async def generate_chibi_image(prompt: str) -> str:
    """Generate a chibi-style illustration and return the saved PNG path."""
    client = genai.Client()
    response = client.models.generate_images(
        model="imagen-3.0-generate-001",
        prompt=prompt,
        config={"number_of_images": 1, "safety_filter_level": "BLOCK_ONLY_HIGH"},
    )
    # Save and return path...
```

### Security Features

The `InputSanitizer` class in `capture_agent.py` implements four layers of protection:

1. **HTML stripping** — removes all tags to prevent markup injection.
2. **Length truncation** — caps input at 2,000 characters.
3. **Prompt injection detection** — flags patterns like `ignore previous instructions`, `you are now`, `system:`.
4. **SQL injection detection** — flags classic SQL patterns like `DROP TABLE`, `UNION SELECT`, `; --`.

Every processed entry is logged to `SECURITY_AUDIT_LOG` with timestamp, input hash, and flags raised. This log is in-memory for the demo but is designed to be written to a file or external sink in production.

### Memory Architecture

Long-term memory is stored in a SQLite database (`diary.db`) with a schema that supports full-text search across diary entries, mood trend queries, monthly recaps, and streak calculations. Four async-wrapped methods (`search_entries`, `get_mood_trend`, `get_monthly_recap`, `get_streak`) are exposed as ADK tools to the Memory Agent.

Short-term memory uses ADK's built-in `session.state` dictionary, which passes structured outputs between agents within a single pipeline run via `output_key` chaining.

### Deployability

The project ships with a production-ready `Dockerfile` (based on `python:3.11-slim` with `uv` for fast dependency installation), a `cloudbuild.yaml` for Google Cloud Build, and a `deploy.sh` script that builds and deploys to Cloud Run in a single command. The agent uses Application Default Credentials (ADC) with Vertex AI, making it secure to deploy without hardcoded API keys.

---

## Building in Google Antigravity

The entire project was developed inside Google Antigravity — Google's agentic IDE that uses Gemini 3 or Claude to write, run, test, and iterate on code through natural language prompts. A `GEMINI.md` spec file at the project root defines the architecture, constraints, and expected behaviors for the Antigravity agent.

This approach — spec-driven development with an agentic IDE — is itself a demonstration of the course's core thesis: agents don't just power end-user products; they fundamentally change how software is built. The Antigravity agent wrote hundreds of lines of code, fixed bugs, refactored memory schemas, and generated a full test suite — all from structured natural language specifications.

---

## Testing and Evaluation

The project includes 59 tests across four test files:

| Test File | Count | What It Covers |
|---|---|---|
| `test_orchestrator.py` | 32 | Pipeline E2E, agent outputs, SQLite persistence |
| `test_security.py` | 5 | InputSanitizer: HTML, truncation, injection detection |
| `test_evaluation.py` | 15 | Mood accuracy, chibi prompt quality, memory correctness |
| *(integrated)* | 7 | Memory Agent tools: trend, recap, streak |

All 59 tests pass. The evaluation framework in `test_evaluation.py` generates `eval_report.json` with a `pass_rate: 1.0`, covering mood analysis accuracy, chibi prompt quality scoring, memory retrieval correctness, and end-to-end pipeline integrity.

---

## Concepts Demonstrated

| Concept | Where |
|---|---|
| ✅ Multi-agent system (ADK) | `app/orchestrator.py` — 4-agent SequentialAgent/Workflow pipeline |
| ✅ MCP Server | `mcp_server/chibi_mcp_server.py` — FastMCP stdio, Imagen 3 |
| ✅ Security features | `app/agents/capture_agent.py` — InputSanitizer + SECURITY_AUDIT_LOG |
| ✅ Deployability | `Dockerfile`, `cloudbuild.yaml`, `deploy.sh` — Cloud Run ready |
| ✅ Antigravity | All code built via spec-driven prompts in Google Antigravity IDE |

---

## Value and Impact

**For users**, Chibi Diary solves the journaling adoption problem by removing friction and adding delight. The chibi illustrations give each entry a visual identity — something you actually want to revisit. The trend insights surface patterns you wouldn't notice yourself. The streak tracker provides the motivational nudge to keep going.

**For the field**, this project demonstrates that concierge agents are most powerful when they combine three capabilities that no single LLM prompt can provide: **persistent memory** (you grow with your user), **external tool use** (you can create, not just analyze), and **structured multi-agent coordination** (each concern is handled by the right specialist).

The architecture is deliberately simple enough to understand and extend, yet complete enough to run end-to-end on real data. With 59 passing tests, a working MCP image server, a persistent memory layer, a security-hardened input pipeline, and Cloud Run deployment support, Chibi Diary & Wellbeing Companion is not a prototype — it is a working system built to the standards the course set out to teach.

---

*Built with Google ADK 2.3.0, FastMCP, Imagen 3, Gemini 2.5 Flash, and Google Antigravity.*  
*59/59 tests passing. 5/6 key concepts demonstrated.*
