# Meeting Transcriber

Real-time meeting transcription and translation system with browser integration. Transform your meetings with live transcription that **stays on YOUR machine** - no corporate surveillance, no data mining, just technology serving people.

**Built for activists, organizers, and anyone who believes technology should empower communities, not corporations.**

## 🏴 Why This Project Exists

In a world where Big Tech monetizes every word we speak, this project stands as an act of technological resistance. Your conversations about organizing mutual aid networks, planning direct actions, or discussing radical politics belong to YOU - not to Google, Microsoft, or OpenAI's training datasets.

This tool is developed for/at **capacity.eco** specifically for better conversations across languages between people who normally face barriers communicating with each other. Our primary use case is enabling communication between folks in the Global North with indigenous communities in the Amazon to support them in solidarity - often replacing corporate meeting tools that harvest data and compromise privacy.

Note that this is a work-in-progress and only replaces the part of transcribing and translating the meeting, not where the meeting takes place:
1. Transcription and real-time translation tools just all really suck, even paid ones or integrated ones by Google Meet or others...
2. We couldn't find open alternatives, but the fact that a lot of underlying technologies (models) are open makes this not very hard.

For having safe meetings without (or at least less) corporate surveillance, consider using Jitsi Meet (integration in progress).

Let this be a humble addition to freeing ourselves from capitalist surveillance.

## Solidarity Use Cases

### Amazon-North Solidarity Meetings
```
Indigenous organizer (PT): "As empresas estão invadindo nosso território"
System transcribes: [PT] As empresas estão invadindo nosso território
LibreTranslate: [EN] Companies are invading our territory

Northern ally (EN): "We can coordinate pressure campaigns from here"
System transcribes: [EN] We can coordinate pressure campaigns from here
LibreTranslate: [PT] Podemos coordenar campanhas de pressão daqui
```

### Cross-Border Organizing
- **Direct action coordination** without corporate intermediaries
- **Knowledge sharing** between indigenous communities and solidarity networks
- **Strategy sessions** that respect data sovereignty
- **Emergency response** planning with real-time translation

## Transitional Technology: Working Within the System While Building Alternatives

**Yes, this tool currently works with Google Meet and Microsoft Teams.** We acknowledge this contradiction - using the master's tools while trying to dismantle the master's house. But consider this a form of technological harm reduction.

### Why We Start Here
Many organizations, especially those working across borders, are currently trapped in corporate ecosystems:
- NGOs use Google Workspace because it's "free" (you're the product)
- Universities mandate Microsoft Teams
- International solidarity networks rely on Zoom (somehow)
- Indigenous communities are given corporate "solutions" by well-meaning allies and also just because they're easy to use

**This tool is our first nibble at reclaiming control.** 
**Every meeting transcribed locally is data kept from corporate AI training.**
**Every translation done on your machine is a conversation they can't monetize.**
**Every small act of technological resistance matters.**

## Quick Start

```bash
# Clone the repository
git clone https://github.com/graphific/realtime-transcribe-translate
cd realtime-transcribe-translate

# Copy environment variables
cp .env.example .env

# Start all services (no more version warnings!)
docker-compose -f docker/docker-compose.yml up -d

# For Windows users - capture your voice AND the system audio
python src\clients\enhanced_windows_audio_client.py  # Terminal 1
python src\clients\windows_microphone_client.py      # Terminal 2

# Start transcription service (or setup auto start as env variable)
curl -X POST http://localhost:8000/api/audio/start \
  -H "Content-Type: application/json" \
  -d '{"module": "windows_capture", "config": {}}'

# Open web interface
open http://localhost:8080
```

**Note:** Web UI control for audio input selection is in progress.

## Features That Respect Your Freedom

- **100% Local Processing**: Whisper AI runs on YOUR hardware - your audio never leaves your machine
- **Self-Hosted Translation**: LibreTranslate keeps your multilingual organizing private
- **No Cloud Surveillance**: Everything runs locally - because the revolution won't be uploaded to AWS
- **Multi-Source Audio**: Capture microphone, system audio, or both simultaneously
- **Browser Integration**: Works with corporate meeting platforms while keeping your data free
- **Browser Integration (2)**: Will soon work with privacy-oriented self-hosted meeting tools like Jitsi Meet 
- **Privacy-First Design**: No telemetry, no analytics, no corporate backdoors
- **Indigenous Data Sovereignty**: Your conversations stay under community control (if hosted there)

## What Makes This Different

Unlike corporate transcription services that mine your conversations:

| Feature | Corporate Services | Our Approach |
|---------|-------------------|--------------|
| Audio Processing | Cloud servers | Your computer |
| Data Ownership | Their databases | Your hard drive |
| Translation | Tracked & logged | Local LibreTranslate |
| Cost | Subscription fees | Free forever |
| Source Code | Proprietary | Open source |
| Cultural Respect | Algorithmic bias | Community-controlled |

## Installation

### Prerequisites
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- 8GB RAM (16GB for large models)
- 20GB disk space
- Python 3.8+ (for audio clients)
- GPU with CUDA for the larger models to run real-time (optional but recommended)
- A healthy skepticism of corporate surveillance

### Windows Setup

```powershell
# Option 1: Run the setup script
.\scripts\setup-windows.ps1

# Option 2: Manual setup
# 1. Install Docker Desktop
# 2. Clone this repo
# 3. Start services
docker-compose -f docker/docker-compose.yml up -d

# 4. Run BOTH audio clients for complete capture
python src\clients\enhanced_windows_audio_client.py  # System audio
python src\clients\windows_microphone_client.py      # Your microphone
```

### Linux/Mac Setup

```bash
# Run the setup script
./scripts/setup-linux.sh

# The script handles everything including PulseAudio configuration
```

## Audio Capture Explained

### The Multi-Client Approach

We use separate clients for maximum flexibility and privacy:

```
Your Microphone ─────┐
                     ├──→ Server Queue ──→ Whisper ──→ Transcription ──→ LibreTranslate ──→ Translation
System Audio ────────┘                           
```

**Why two clients?**
- **Microphone Client**: Captures your voice with automatic gain control
- **System Audio Client**: Captures meeting participants, videos, screen shares
- **Both Together**: Complete meeting capture without complex audio routing

### Smart Microphone Features

The microphone client includes:
- **Auto-gain control** - amplifies quiet voices automatically
- **Real-time level monitoring** - visual feedback every 5 seconds
- **Smart device selection** - finds your default microphone
- **Zero-configuration** - just run and speak

## Configuration

### Essential Settings (.env file)

```env
# Model selection - bigger = better accuracy, more resources
WHISPER_MODEL=base              # Options: tiny, base, small, medium, large-v3

# GPU acceleration (if you have NVIDIA)
CUDA_VISIBLE_DEVICES=0          # Use -1 for CPU only

# Translation - we recommend LibreTranslate for privacy
LIBRETRANSLATE_LANGS=en,pt,es   # Add indigenous language codes as available
USE_LIBRETRANSLATE=true         # Keep translations local!

# Audio processing
SAMPLE_RATE=48000               # Match your audio device
MIN_SPEECH_DURATION=1.0         # Ignore short sounds

# Privacy settings
SAVE_AUDIO=true                 # Keep recordings locally
ENABLE_HALLUCINATION_FILTER=true # Remove repetitive glitches
```

### Whisper Model Selection

Choose based on your hardware and needs:

| Model | Speed | Accuracy | RAM | Use Case |
|-------|-------|----------|-----|----------|
| tiny | Fastest | Good | 1GB | Quick notes |
| base | Fast | Better | 1.5GB | **Recommended start** |
| small | Moderate | Very Good | 2GB | Daily use |
| medium | Slow | Excellent | 3GB | Important meetings |
| large-v3 | Slowest | Best | 5GB | Critical accuracy |

## Translation Options

### Recommended: LibreTranslate (Self-Hosted)

Keep your translations away from corporate surveillance:

```bash
# Quick setup for English ↔ Portuguese (300MB)
docker run -d --name libretranslate \
  -p 5000:5000 \
  -e LT_LOAD_ONLY="en,pt" \
  libretranslate/libretranslate

# Your translations stay local - as they should!
```

### Why LibreTranslate?

- **Complete Privacy**: Translations never leave your machine
- **No Corporate Control**: Your organizing discussions stay yours
- **No API Limits**: Translate freely without rate limits
- **Open Source**: Inspect and verify the code yourself
- **Growing Language Support**: Community-driven language additions

## Real-World Examples

### Indigenous Rights Meeting

```
Indigenous leader: "Nossos rios estão sendo envenenados pela mineração"
System transcribes: [PT] Nossos rios estão sendo envenenados pela mineração
LibreTranslate: [EN] Our rivers are being poisoned by mining

Solidarity organizer: "We'll coordinate with environmental lawyers here"
System transcribes: [EN] We'll coordinate with environmental lawyers here
LibreTranslate: [PT] Vamos coordenar com advogados ambientais aqui
```

## Privacy & Security

### Your Data Stays Local

**By default, everything runs on YOUR machine:**

- ✅ **All audio processing** - Whisper AI runs locally on your CPU/GPU
- ✅ **All transcriptions** - Stored only on your hard drive
- ✅ **All translations** - LibreTranslate runs locally (no cloud APIs)
- ✅ **All connections** - Services bound to localhost only:
  - Web UI: `http://localhost:8080`
  - WebSocket: `ws://localhost:8765`
  - Audio input: `localhost:8766`
  - API: `localhost:8000`

**This means:**
- ❌ No external network access
- ❌ No connections from other devices
- ❌ No data leaves your machine
- ✅ Complete privacy by default

### What Could Compromise Privacy

**Only if you choose to:**
- ⚠️ Use Google Translate instead of LibreTranslate (sends text to Google)
- ⚠️ Share transcriptions in meeting chat (platform gets the text)
- ⚠️ Modify Docker config to allow network access

**Remember:** While we keep transcriptions private, meeting platforms (Zoom, Teams, Meet) already have your audio/video. For true privacy, use self-hosted alternatives like Jitsi Meet.

### Network Access (Advanced Users)

Need to access from other devices? Understand the risks first:

1. **Recommended:** Use SSH tunneling
   ```bash
   ssh -L 8080:localhost:8080 -L 8765:localhost:8765 user@your-server
   ```

2. **Alternative:** Modify `docker-compose.yml` (removes security)
   - Remove `127.0.0.1:` prefix from ports
   - Implement authentication (see [TODO.md](TODO.md))
   - Configure firewall rules
   
3. **Best Practice:** Keep localhost binding, use VPN for remote access

### Security Hardening

For sensitive meetings:
```bash
# Use encrypted storage
sudo cryptsetup luksFormat /dev/sdX

# Disable audio saving
SAVE_AUDIO=false

# Use memory-only mode
USE_MEMORY_ONLY=true
```

See [docs/INSTALLATION.md](docs/INSTALLATION.md#security-hardening) for complete hardening guide.

## Known Issues & Solutions

### Hallucination Detection Too Aggressive

Current issue: Legitimate repetitions like "check check check" flagged as hallucinations.

**Temporary fix**: Disable in .env
```env
ENABLE_HALLUCINATION_FILTER=false
```

### Multiple Python Scripts Required

Current: Must run two terminals for complete audio capture.

**Workaround**: Create a batch file (Windows):
```batch
@echo off
start python src\clients\enhanced_windows_audio_client.py
start python src\clients\windows_microphone_client.py
echo Audio capture started!
```

### No Auto-Start

Current: Must manually start transcription after audio clients.

**Solution in progress**: Web UI will handle this automatically.

## Contributing

We especially welcome contributions that:

- **Strengthen privacy** - Make surveillance capitalism harder
- **Improve local-first functionality** - Less cloud, more control
- **Support grassroots organizing** - Features for activists
- **Add language support** - Especially indigenous languages
- **Increase accessibility** - Technology for all
- **Respect indigenous data sovereignty** - Community-controlled tools

### Priority Areas for capacity.eco

1. **Indigenous language support** - Working with communities to add their languages
2. **Low-bandwidth optimization** - For remote areas with limited internet
3. **Offline-first design** - Resilient communication infrastructure
4. **Cultural sensitivity features** - Respecting communication protocols

### Areas Needing Work

See [TODO.md](TODO.md) for the full list, but priorities include:
1. Fix overzealous hallucination detection
2. Single-click startup for all services
3. Linux/Mac audio client support
4. Web UI device management
5. Indigenous language model training support

## Documentation

- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [Usage Guide](docs/USAGE.md) - How to use effectively
- [API Reference](docs/API.md) - For developers
- [TODO/Roadmap](TODO.md) - What needs doing

## Acknowledgments

Standing on the shoulders of giants who believe in technological freedom:

- [OpenAI Whisper](https://github.com/openai/whisper) - For open speech recognition
- [LibreTranslate](https://github.com/LibreTranslate/LibreTranslate) - For privacy-respecting translation
- [Docker](https://www.docker.com/) - For portable deployment
- Indigenous communities fighting for their lands and rights
- Every developer who chooses freedom over profit
- The capacity.eco team for supporting technological sovereignty

## Final Words

This project exists because we believe:
- Technology should serve communities, not extract from them
- Privacy is not about having something to hide, but having something to protect
- The tools of liberation must be in the hands of the people
- Indigenous data sovereignty is non-negotiable
- Solidarity requires secure communication channels

**The revolution will not be uploaded to the cloud - it will be processed locally.**

**From the Amazon to the Arctic, our struggles are connected, and so should be our tools.**

---

*Built with ❤️ and rage against surveillance capitalism*

## 📄 License

MIT License - Because knowledge wants to be free. See [LICENSE](LICENSE) file.