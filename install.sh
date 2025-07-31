#!/bin/bash

# WSL Audio Transcription Setup Script
# This script sets up the complete environment for bilingual speech transcription on WSL2

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

echo "================================================"
echo "WSL Audio Transcription Setup"
echo "================================================"
echo ""

# Check if running on WSL
if ! grep -q Microsoft /proc/version; then
    print_error "This script is designed for WSL2. Exiting."
    exit 1
fi

# Check for conda
if ! command -v conda &> /dev/null; then
    print_error "Conda not found! Please install Miniconda or Anaconda first."
    echo "Visit: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Update system packages
print_status "Updating system packages..."
sudo apt-get update

# Install system dependencies
print_status "Installing system dependencies..."
sudo apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    alsa-utils \
    ffmpeg \
    pulseaudio-utils

# Check audio setup
print_status "Checking audio configuration..."
if pactl info &> /dev/null; then
    print_status "PulseAudio is working"
else
    print_warning "PulseAudio might not be configured. Audio recording may not work."
fi

# Create conda environment
print_status "Creating conda environment 'audio'..."
conda create -n audio python=3.10 -y

# Activate environment
print_status "Activating conda environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate audio

# Check for NVIDIA GPU
if nvidia-smi &> /dev/null; then
    print_status "NVIDIA GPU detected. Installing CUDA version..."
    GPU_AVAILABLE=true
    
    # Install PyTorch with CUDA
    print_status "Installing PyTorch with CUDA support..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    
    # Install cuDNN 9
    print_status "Installing cuDNN 9 for GPU acceleration..."
    pip install nvidia-cudnn-cu12==9.1.0.70
    
else
    print_warning "No NVIDIA GPU detected. Installing CPU version..."
    GPU_AVAILABLE=false
    
    # Install PyTorch CPU version
    print_status "Installing PyTorch (CPU only)..."
    pip install torch torchvision torchaudio
fi

# Install Python packages
print_status "Installing required Python packages..."
pip install \
    numpy \
    silero-vad \
    faster-whisper \
    pydub \
    googletrans==4.0.0-rc1

# Install sounddevice through conda-forge
print_status "Installing sounddevice..."
conda install -c conda-forge python-sounddevice -y

# Fix potential ALSA conflicts
print_status "Checking for ALSA conflicts..."
if [ -d "$CONDA_PREFIX/lib/alsa-lib" ]; then
    print_warning "Removing conda's ALSA to prevent conflicts..."
    rm -rf "$CONDA_PREFIX/lib/alsa-lib"
fi

# Test audio recording
print_status "Testing audio recording..."
if arecord -d 1 -f cd test_audio.wav &> /dev/null; then
    print_status "Audio recording test successful"
    rm -f test_audio.wav
else
    print_warning "Audio recording test failed. Please check your microphone setup."
fi

# Create launcher scripts
print_status "Creating launcher scripts..."

# Main transcriber launcher
cat > run_transcriber.sh << 'EOF'
#!/bin/bash
# Launcher for WSL Audio Transcriber

# Activate conda environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate audio

# Set library path for cuDNN
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH

# Run the transcriber
echo "Starting WSL Audio Transcriber..."
echo "Options:"
echo "  1) wsl_audio_recorder.py - Complete sentences (1.5s silence)"
echo "  2) continuous_parallel_recorder.py - Real-time continuous"
echo "  3) wsl_audio_recorder_cpu.py - CPU-only version"
echo ""
read -p "Select option (1-3): " choice

case $choice in
    1)
        python wsl_audio_recorder.py
        ;;
    2)
        python continuous_parallel_recorder.py
        ;;
    3)
        python wsl_audio_recorder_cpu.py
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac
EOF

chmod +x run_transcriber.sh

# Quick start launcher for GPU version
cat > start_gpu.sh << 'EOF'
#!/bin/bash
source $(conda info --base)/etc/profile.d/conda.sh
conda activate audio
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH
python wsl_audio_recorder.py
EOF

chmod +x start_gpu.sh

# Quick start launcher for continuous version
cat > start_continuous.sh << 'EOF'
#!/bin/bash
source $(conda info --base)/etc/profile.d/conda.sh
conda activate audio
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH
python continuous_parallel_recorder.py
EOF

chmod +x start_continuous.sh

# Create test script
print_status "Creating audio test script..."
cat > test_audio.py << 'EOF'
import subprocess
import numpy as np
from silero_vad import load_silero_vad, get_speech_timestamps
import torch

print("Testing audio setup...")
print("Recording 3 seconds - please speak...")

# Record audio
process = subprocess.Popen(
    ['arecord', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'raw', '-q', '-d', '3'],
    stdout=subprocess.PIPE
)
audio_data, _ = process.communicate()
audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

print(f"Recorded {len(audio_array)} samples")
print(f"Max amplitude: {np.max(np.abs(audio_array)):.4f}")

# Test VAD
model = load_silero_vad()
audio_tensor = torch.tensor(audio_array, dtype=torch.float32)
speech_timestamps = get_speech_timestamps(audio_tensor, model, threshold=0.5)

if speech_timestamps:
    print(f"✓ Speech detected! {len(speech_timestamps)} segments")
else:
    print("✗ No speech detected")

print(f"CUDA available: {torch.cuda.is_available()}")
EOF

# Final setup summary
echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
print_status "Environment: audio"
if [ "$GPU_AVAILABLE" = true ]; then
    print_status "GPU support: Enabled"
else
    print_warning "GPU support: Disabled (CPU only)"
fi
print_status "Launcher scripts created:"
echo "  - ./run_transcriber.sh (interactive menu)"
echo "  - ./start_gpu.sh (quick start GPU version)"
echo "  - ./start_continuous.sh (quick start continuous)"
echo ""
echo "To test your setup:"
echo "  conda activate audio"
echo "  python test_audio.py"
echo ""
echo "To start transcribing:"
echo "  ./run_transcriber.sh"
echo ""
print_warning "Note: If using GPU, the first run will download the Whisper model (~1.5GB)"
