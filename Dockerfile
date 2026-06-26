FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project metadata AND source before syncing.
# pyproject.toml declares readme="README.md" and the chibi_diary/mcp_server
# packages, so all of them must exist when `uv sync` builds the local project —
# otherwise the build fails. README.md and the source are therefore copied first.
COPY pyproject.toml uv.lock README.md ./
COPY chibi_diary/ ./chibi_diary/
COPY mcp_server/ ./mcp_server/
COPY GEMINI.md ./

# Install dependencies + the local project (no dev deps)
RUN uv sync --frozen --no-dev

# Environment variables (injected at runtime, NOT baked in)
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_GENAI_USE_VERTEXAI=True
ENV GOOGLE_CLOUD_LOCATION=us-central1

# Expose ADK web port
EXPOSE 8080

# Run ADK web server
CMD ["uv", "run", "adk", "web", "--host", "0.0.0.0", "--port", "8080", "chibi_diary"]
