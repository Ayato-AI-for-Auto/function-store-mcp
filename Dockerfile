# Dockerfile for Function Store MCP (Cloud-Native Edition)
# This allows the server to run in Cloud Run as a managed "Quality Gate" or Shared Hub.

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project files
COPY . .

# Install the project and its dependencies
RUN uv pip install -e .

# Environment setup for local pool
RUN mkdir -p /app/data /app/.mcp_envs

# Use port 8001 for SSE
ENV PORT=8001
EXPOSE 8001

# Run the server using SSE by default for Cloud Run compatibility
CMD ["uv", "run", "python", "-m", "function_store_mcp.server", "--transport", "sse", "--port", "8001"]
