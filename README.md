# Real-Time Bilingual Speech Transcription System

Automatic speech-to-text with live translation for English ↔ Portuguese. Transform your voice into text in real-time with automatic translation, perfect for meetings, dictation, and multilingual conversations.

**Tested on WSL2** (fake Linux, I know) but should work on any proper Linux distribution or even macOS with minor adjustments.

## Features

- **Real-time transcription** using OpenAI Whisper (GPU accelerated)
- **Automatic translation** between English and Portuguese  
- **Firefox integration** for inserting transcriptions into web meetings
- **Smart speech detection** with configurable silence thresholds
- **Complete session recording** with timestamped transcripts

## Quick Start

```bash
# Install everything
./install.sh
```

## Project Structure

```
├── terminal/               # Personal recording tools
│   ├── wsl_audio_recorder.py               # Complete sentences (best accuracy)
│   ├── continuous_parallel_recorder.py    # Real-time streaming
│   └── wsl_audio_recorder_cpu.py           # CPU-only version
├── meetings/               # Meeting transcription with browser integration
│   ├── system_audio_recorder.py           # Records ALL meeting audio
│   ├── websocket_transcriber.py           # WebSocket server for browser
│   └── firefox-extension/                 # Browser extension
└── install.sh             # One-click setup
```

## Tool Selection Guide

| Use Case | Tool | Best For |
|----------|------|----------|
| **Reading text aloud** | `terminal/wsl_audio_recorder.py` | Complete sentences, high accuracy |
| **Live conversations** | `terminal/continuous_parallel_recorder.py` | Real-time feedback, minimal delay |
| **CPU-only systems** | `terminal/wsl_audio_recorder_cpu.py` | No GPU available |
| **Online meetings** | `meetings/system_audio_recorder.py` | Capture all participants + browser integration |

## Installation

### Prerequisites
- Windows 10/11 with WSL2
- Conda or Miniconda
- NVIDIA GPU (optional, but recommended)

### One-Command Install
```bash
chmod +x install.sh
./install.sh
```

This installs system dependencies, Python environment with GPU support, all required models and libraries, and launcher scripts.

### Manual Installation
```bash
# Create environment
conda create -n audio python=3.10
conda activate audio

# Install system packages
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio alsa-utils ffmpeg pulseaudio-utils

# Install Python packages (GPU version)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install nvidia-cudnn-cu12==9.1.0.70
pip install numpy silero-vad faster-whisper pydub googletrans==4.0.0-rc1
conda install -c conda-forge python-sounddevice
```

## Usage Examples

### Personal Dictation
```bash
conda activate audio
./run_transcriber.sh

# Results saved to:
# - transcripts/transcript_1.txt
# - translations/translation_1.txt
```

### Online Meetings
```bash
# Start meeting recorder (captures ALL audio)
cd meetings
./start_meeting_recorder.sh

# Install Firefox extension (one-time setup)
# Firefox → about:debugging → Load Temporary Add-on → select firefox-extension/manifest.json
# Join your meeting - floating widget appears automatically
```

### Example Output
```
Speech detected!
Language: Portuguese (98% confidence)
Original: A revolução começa nos pequenos atos de desobediência civil.
Translation (English): The revolution begins with small acts of civil disobedience.
```

## Browser Integration

The Firefox extension provides:
- **Floating widget** on meeting pages (Google Meet, Zoom, Teams)
- **Auto-insert mode** - transcriptions sent directly to chat
- **Copy/paste controls** for manual text insertion
- **Real-time display** of transcriptions and translations

## Configuration

### Adjust Speech Detection
```python
# In any recorder script
self.silence_threshold = 1.5  # seconds (increase for longer sentences)
```

### Change Models
```python
# For better accuracy (requires more GPU memory)
model_name = "large-v3"  # Options: tiny, base, small, medium, large-v3

# For faster processing
model_name = "base"
```

### Language Pairs
```python
# Currently supports English ↔ Portuguese
# Modify in transcriber for other languages:
target_lang = 'es' if lang == 'en' else 'en'  # English ↔ Spanish
```

## Performance

| Mode | Model | Speed (GPU) | Speed (CPU) | Accuracy |
|------|-------|-------------|-------------|----------|
| GPU | large-v3 | ~3s per segment | N/A | Highest |
| GPU | base | ~2s per segment | N/A | High |
| CPU | base | N/A | ~8s per segment | Good |

## Troubleshooting

### Audio Not Working
```bash
# Test microphone
arecord -d 3 test.wav && aplay test.wav

# Check PulseAudio
pactl list short sources
```

### GPU Issues
```bash
# Check CUDA
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"

# If GPU issues, use CPU version:
python terminal/wsl_audio_recorder_cpu.py
```

### Browser Extension Not Connecting
```bash
# Check if WebSocket server is running
lsof -i :8765

# Restart the meeting recorder
cd meetings && ./start_meeting_recorder.sh
```

## Advanced Features

### Meeting Audio Capture
The meeting recorder captures:
- Your microphone (when unmuted)
- All other participants
- System sounds and screen shares
- Sends live transcriptions to browser extension

### WebSocket Integration
Real-time communication between recorder and browser:
```python
# In your own scripts
from websocket_transcriber import TranscriptionWebSocketServer
ws_server = TranscriptionWebSocketServer()
ws_server.broadcast_transcription(text, language, translation)
```

## Contributing

Really scratching my own itch here, for having meetings between Portuguese and English sepoakers at https://capacity.eco/, but maybe...

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Acknowledgments

- **OpenAI Whisper** for state-of-the-art speech recognition
- **Silero Team** for excellent voice activity detection
- **Google Translate** for translation services
- **WSL Team** for making Linux audio work on Windows