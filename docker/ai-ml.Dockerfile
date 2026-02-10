# AI/ML Runtime (Heavy)
# Used for: Deep Learning, Embeddings, Inference
# Using PyTorch CPU base to keep image size reasonable for non-GPU nodes
# For GPU support, switch to pytorch/pytorch:latest-cuda
FROM python:3.12-slim-bookworm

WORKDIR /app
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch (CPU version for broad compatibility by default)
# In a real heavy-ai container, we might want CUDA
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install Transformers & ecosystem
RUN pip install --no-cache-dir \
    transformers \
    sentence-transformers \
    accelerate \
    huggingface-hub \
    tokenizers

CMD ["python"]
