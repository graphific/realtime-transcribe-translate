# Installation Guide

Setting up technology for community empowerment, not corporate surveillance.

## Table of Contents
- [Before You Begin](#before-you-begin)
- [Windows Installation](#windows-installation)
- [Linux Installation](#linux-installation)
- [macOS Installation](#macos-installation)
- [Docker Configuration](#docker-configuration)
- [GPU Setup](#gpu-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Security Hardening](#security-hardening)

## Before You Begin

### Why Local Installation Matters

Every component runs on YOUR hardware because:
- **Your conversations belong to you**, not tech corporations
- **No cloud services** can mine your organizing discussions  
- **Complete control** over your data and privacy
- **No corporate kill switches** can shut down your tools

### System Requirements

**Minimum** (for basic transcription):
- CPU: 4 cores
- RAM: 8GB
- Disk: 20GB free space
- Internet: Only for initial setup

**Recommended** (for real-time multilingual meetings):
- CPU: 6+ cores
- RAM: 16GB
- GPU: NVIDIA with 4GB+ VRAM
- Disk: 50GB free space

### Software Prerequisites
- Docker Desktop or Docker Engine
- Git
- Modern web browser (Firefox recommended - respects your privacy)

## Windows Installation

### Step 1: Install Docker Desktop

1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. During installation, **enable WSL 2 backend**
3. After installation, open Docker Desktop
4. Go to Settings → Resources and allocate:
   - Memory: 8GB minimum
   - CPU: 4+ cores

### Step 2: Install Git

Download and install [Git for Windows](https://git-scm.com/download/win) with default settings.

### Step 3: Clone the Repository

Open PowerShell as Administrator:

```powershell
# Clone the repository
git clone https://github.com/yourusername/meeting-transcriber
cd meeting-transcriber

# Create necessary directories
mkdir -p data\recordings data\transcripts data\translations
```

### Step 4: Run Windows Setup

```powershell
# Run the setup script
.\scripts\setup-windows.ps1
```

This script:
- Checks your system compatibility
- Downloads required audio tools
- Configures Windows audio capture
- Sets up Docker networks
- Creates configuration files

### Step 5: Configure Audio Capture

Windows offers several audio capture methods:

**Option A: Simple Audio Client** (Recommended)
```powershell
# This captures all system audio
cd src\clients
python windows_audio_client.py
```

**Option B: VoiceMeeter** (Professional)
1. Download [VoiceMeeter](https://vb-audio.com/Voicemeeter/)
2. Set as default audio device
3. Enable VBAN streaming
4. The system auto-detects it

**Option C: Separate Microphone**
```powershell
# For capturing only your microphone
python windows_microphone_client.py
```

## Linux Installation

### Step 1: Install Docker

For Ubuntu/Debian:
```bash
# Remove any old Docker versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add yourself to docker group (avoid sudo)
sudo usermod -aG docker $USER

# Apply group changes
newgrp docker
```

For Fedora:
```bash
sudo dnf install docker docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```

For Arch:
```bash
sudo pacman -S docker docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2: Install Dependencies

```bash
# Install Git and audio tools
# Ubuntu/Debian
sudo apt-get install git pulseaudio-utils

# Fedora  
sudo dnf install git pulseaudio-utils

# Arch
sudo pacman -S git pulseaudio-utils
```

### Step 3: Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/meeting-transcriber
cd meeting-transcriber

# Run Linux setup
./scripts/setup-linux.sh
```

### Step 4: Configure PulseAudio

For network audio streaming:
```bash
# Enable TCP module for Docker
pactl load-module module-native-protocol-tcp port=4713 auth-anonymous=1

# Make permanent (optional)
echo "load-module module-native-protocol-tcp port=4713 auth-anonymous=1" >> ~/.config/pulse/default.pa
```

## macOS Installation

### Step 1: Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Install Docker Desktop

```bash
brew install --cask docker
```

Open Docker Desktop and complete setup.

### Step 3: Install Dependencies

```bash
brew install git
```

### Step 4: Clone and Setup

```bash
git clone https://github.com/yourusername/meeting-transcriber
cd meeting-transcriber
./scripts/setup-macos.sh
```

### Step 5: Audio Configuration

For audio routing on macOS:
```bash
# Install BlackHole for virtual audio
brew install --cask blackhole-2ch

# Configure in System Preferences → Sound
# Set BlackHole as output device
```

## Docker Configuration

### Understanding Our Docker Setup

We use Docker to ensure:
- **Consistent environment** across all systems
- **Isolated processing** - no system contamination
- **Easy updates** without breaking your system
- **Resource limits** to prevent system overload

### Configuration File

Copy and customize the environment file:
```bash
cp .env.example .env
```

Key settings to configure:

```bash
# Privacy Settings
PRIVACY_MODE=strict              # Never attempt cloud connections
ALLOW_CLOUD_FALLBACK=false      # No fallback to cloud services
LOCAL_ONLY=true                 # Enforce local processing

# Model Configuration
WHISPER_MODEL=base              # Options: tiny, base, small, medium, large-v3
WHISPER_DEVICE=cuda             # Use 'cpu' if no GPU

# Language Support
LIBRETRANSLATE_LANGS=en,pt,es,fr,de,it
DEFAULT_TARGET_LANG=pt          # Your primary translation target

# Performance Tuning
CHUNK_DURATION=10.0             # Seconds of audio to process at once
VAD_THRESHOLD=0.5               # Voice detection sensitivity
MIN_SPEECH_DURATION=0.5         # Minimum speech length to transcribe

# Storage Options
SAVE_AUDIO=true                 # Keep audio recordings
SAVE_TRANSCRIPTS=true           # Keep text transcripts
DATA_RETENTION_DAYS=30          # Auto-delete after X days
```

### Building and Starting Services

```bash
# Build all containers
docker-compose -f docker/docker-compose.yml build

# Start services in background
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop services
docker-compose -f docker/docker-compose.yml down
```

## GPU Setup

### Why GPU Matters

With GPU acceleration:
- **Faster transcription** - Real-time processing
- **Larger models** - Better accuracy
- **Lower latency** - Smoother meetings

Without GPU, the system still works but with smaller models and slight delays.

### NVIDIA GPU on Linux

1. Install NVIDIA drivers:
```bash
# Ubuntu/Debian
sudo apt-get install nvidia-driver-530
sudo reboot

# Verify installation
nvidia-smi
```

2. Install NVIDIA Container Toolkit:
```bash
# Add NVIDIA repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install toolkit
sudo apt-get update
sudo apt-get install nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker

# Test GPU in Docker
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

### NVIDIA GPU on Windows (WSL2)

1. Install NVIDIA drivers on Windows (not in WSL)
2. WSL2 automatically exposes GPU to Linux
3. Verify in WSL:
```bash
nvidia-smi
```

### AMD GPU Support

Currently experimental. For AMD GPUs:
```bash
# Set in .env
WHISPER_DEVICE=cpu  # Use CPU for now
# ROCm support coming soon
```

## Verification

### Step 1: Check Services

```bash
# List running services
docker-compose -f docker/docker-compose.yml ps

# Should show:
# meeting-transcriber-api       Up    0.0.0.0:8000->8000/tcp
# meeting-transcriber-web       Up    0.0.0.0:8080->5000/tcp
# meeting-transcriber-libre...  Up    0.0.0.0:5000->5000/tcp
```

### Step 2: Test Web Interface

Open http://localhost:8080 in your browser.

You should see:
- Meeting Transcriber interface
- Available audio sources
- "Start Recording" button

### Step 3: API Health Check

```bash
# Check API health
curl http://localhost:8000/health

# Should return:
# {"status": "healthy", "privacy_mode": "local_only", ...}
```

### Step 4: Test GPU (if applicable)

```bash
# Check GPU in container
docker-compose -f docker/docker-compose.yml exec api \
    python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### Step 5: Test Transcription

1. Click "Test Mode" in web interface
2. Click "Start Recording"
3. You should see sample transcriptions appear

## Troubleshooting

### Common Issues and Solutions

#### "Cannot connect to Docker daemon"

**Linux/Mac:**
```bash
# Start Docker service
sudo systemctl start docker

# Check if you're in docker group
groups | grep docker
```

**Windows:**
- Open Docker Desktop
- Wait for "Docker Desktop is running" notification

#### Port Already in Use

```bash
# Find what's using the port
# Linux/Mac
sudo lsof -i :8080

# Windows
netstat -ano | findstr :8080

# Change port in .env
WEB_UI_PORT=8081
```

#### GPU Not Detected

1. Check GPU is available:
```bash
nvidia-smi  # Should show your GPU
```

2. Check Docker GPU support:
```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

3. If no GPU, system automatically uses CPU

#### Audio Not Capturing

**Windows:**
- Run audio client as Administrator
- Check Windows privacy settings → Microphone
- Disable exclusive mode in audio settings

**Linux:**
```bash
# Check PulseAudio
pactl info

# List audio sources
pactl list sources short

# Test audio capture
parecord -d 3 test.wav && paplay test.wav
```

#### LibreTranslate Not Working

```bash
# Check if service is running
docker-compose -f docker/docker-compose.yml ps libretranslate

# View logs
docker-compose -f docker/docker-compose.yml logs libretranslate

# Restart service
docker-compose -f docker/docker-compose.yml restart libretranslate
```

### Performance Issues

#### High CPU Usage

In `.env`, adjust:
```bash
WHISPER_MODEL=tiny       # Use smaller model
CHUNK_DURATION=5.0       # Smaller chunks
VAD_THRESHOLD=0.6        # Less sensitive
```

#### Out of Memory

```bash
# Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory: 8GB+

# Or use smaller model
WHISPER_MODEL=base
```

#### Slow Transcription

```bash
# Check if using GPU
docker-compose -f docker/docker-compose.yml exec api \
    python -c "import torch; print(torch.cuda.is_available())"

# If False, check GPU setup
# If True but still slow, try smaller model
```

## Security Hardening

### For Activists and Organizers

#### 1. Firewall Configuration

Block external access to services:
```bash
# Linux (UFW)
sudo ufw deny 8000/tcp
sudo ufw deny 8080/tcp
sudo ufw deny 8765/tcp
sudo ufw deny 5000/tcp

# Windows Firewall
netsh advfirewall firewall add rule name="Block Transcriber" \
    dir=in action=block protocol=TCP localport=8000,8080,8765,5000
```

#### 2. Encrypted Storage

Store transcriptions on encrypted volumes:
```bash
# Linux - Create encrypted volume
sudo cryptsetup luksFormat /dev/sdX
sudo cryptsetup open /dev/sdX meeting-data
sudo mkfs.ext4 /dev/mapper/meeting-data
sudo mount /dev/mapper/meeting-data /mnt/secure-meetings

# Update docker-compose.yml volumes
volumes:
  - /mnt/secure-meetings:/app/data
```

#### 3. Memory-Only Mode

For sensitive meetings:
```bash
# In .env
SAVE_AUDIO=false
SAVE_TRANSCRIPTS=false
USE_MEMORY_ONLY=true

# Mount tmpfs for temporary data
docker-compose -f docker/docker-compose.yml up -d \
    --mount type=tmpfs,destination=/app/temp
```

#### 4. Network Isolation

Run on isolated network:
```yaml
# docker-compose.override.yml
services:
  api:
    networks:
      - isolated
  web:
    networks:
      - isolated

networks:
  isolated:
    driver: bridge
    internal: true
```

### Regular Maintenance

1. **Update regularly**:
```bash
git pull
docker-compose -f docker/docker-compose.yml pull
docker-compose -f docker/docker-compose.yml up -d
```

2. **Clean old data**:
```bash
# Remove recordings older than 30 days
find data/recordings -mtime +30 -delete
```

3. **Monitor disk usage**:
```bash
df -h data/
```

## Next Steps

Once installation is complete:

1.  **Test the system** - See [Usage Guide](USAGE.md) for detailed instructions
2.  **Install browser extension** - See [extension README](../src/extensions/firefox/README.md)
3.  **Configure audio capture** - See [audio clients documentation](../src/clients/README.md)
4.  **Adjust language settings** - Configure translation pairs in `.env`
5.  **Review security** - Read security guide for sensitive use cases (TODO)
6.  **Join the community** - Contribute improvements and report issues


---

*Technology should empower communities, not surveil them*