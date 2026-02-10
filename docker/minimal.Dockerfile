# Minimal Runtime
# Used for: Text processing, simple logic, utilities
FROM python:3.12-slim-bookworm

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install standard utilities if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pre-install common lightweight libs
RUN pip install --no-cache-dir \
    requests \
    python-dotenv \
    pydantic

CMD ["python"]
