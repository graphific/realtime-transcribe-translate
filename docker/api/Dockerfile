# GPU-enabled version with OpenAI Whisper
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# Set environment variables for NVIDIA
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility
ENV CUDA_VISIBLE_DEVICES 0

# Install system dependencies including FFmpeg for audio
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-dev \
    ffmpeg \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create python symlinks
RUN ln -sf /usr/bin/python3.10 /usr/bin/python
RUN ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

# Create necessary directories
RUN mkdir -p /data/{recordings,transcripts,translations} \
    /models/{whisper,huggingface,torch} \
    /app/audio_modules

# Upgrade pip and install setuptools-rust for tiktoken
RUN python -m pip install --upgrade pip setuptools-rust

# Install PyTorch with CUDA 12.1 support
RUN pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121

# Verify CUDA installation
RUN python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"

# Install OpenAI Whisper
RUN pip install -U openai-whisper

# Install Silero VAD with proper dependencies
RUN pip install silero-vad

# Install audio backend for torchaudio
RUN pip install soundfile

# Install core dependencies
RUN pip install --no-cache-dir \
    flask==3.0.3 \
    flask-cors==4.0.0 \
    websockets==12.0 \
    aiohttp==3.9.1 \
    numpy==1.24.3 \
    requests==2.31.0 \
    scipy==1.11.4 \
    pydub==0.25.1

# Install translation libraries
RUN pip install --no-cache-dir \
    googletrans==4.0.0-rc1 \
    deep-translator==1.11.4

# Install additional utilities
RUN pip install --no-cache-dir \
    python-dotenv==1.0.0 \
    psutil==5.9.6

# Pre-download models during build (CPU only during build)
# Models will be moved to GPU at runtime if available
ARG WHISPER_MODEL=base
RUN python -c "import whisper; print('Pre-downloading Whisper model...'); whisper.load_model('${WHISPER_MODEL}', device='cpu')" || true
RUN python -c "from silero_vad import load_silero_vad; print('Pre-downloading VAD model...'); load_silero_vad()" || true

# Copy application code
COPY src/api /app
COPY src/api/audio_modules /app/audio_modules

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV WHISPER_MODEL=${WHISPER_MODEL}
ENV TORCH_HOME=/models/torch
ENV HF_HOME=/models/huggingface
ENV CUDA_LAUNCH_BLOCKING=1

EXPOSE 8000 8765 8766

# Add a healthcheck that includes GPU status
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import torch; assert torch.cuda.is_available(), 'GPU not available'" || exit 1

CMD ["python", "main.py"]