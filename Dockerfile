FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev deps)
RUN uv sync --frozen --no-dev

# Copy application source
COPY app/ ./app/
COPY GEMINI.md ./

# MCP server must be co-located
COPY mcp_server/ ./mcp_server/

# Environment variables (injected at runtime, NOT baked in)
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_GENAI_USE_VERTEXAI=True

# Expose ADK web port
EXPOSE 8080

# Run ADK web server
CMD ["uv", "run", "adk", "web", "--host", "0.0.0.0", "--port", "8080", "app"]
