# Install PyTorch with CUDA 12.1 support
Write-Host "Installing PyTorch with CUDA 12.1..."
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# Install other dependencies
Write-Host "Installing other dependencies..."
uv pip install sentence-transformers nvidia-ml-py

Write-Host "Done. Please restart the Function Store MCP."
