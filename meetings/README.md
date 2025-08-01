# Meeting Transcription with Live Browser Integration

Real-time transcription and translation for online meetings with automatic chat insertion. Transform your online meetings with live transcription that appears directly in your browser and can automatically send translations to the meeting chat.

**Privacy-First Design**: This project prioritizes user privacy and open-source solutions. We recommend LibreTranslate for translation to ensure your conversations remain completely private and under your control.

## What This Does

**Audio Capture:**
- Records ALL meeting audio (your voice + participants + screen shares)
- Works with any meeting platform (Teams, Zoom, Google Meet, etc.)
- Mixed audio capture - no complex routing needed

**Real-time Processing (100% Local):**
- **Transcription**: OpenAI Whisper runs entirely on YOUR computer
  - Large-v3 model (~3GB) for GPU systems
  - Base model (~150MB) for CPU systems
  - No audio ever sent to OpenAI or any cloud service
- **Translation**: LibreTranslate (recommended) runs locally on YOUR computer
  - Or falls back to cloud services if you choose
- **WebSocket**: Local server (localhost:8765) for browser communication

**Browser Integration:**
- Floating widget overlays on meeting pages
- One-click insertion into meeting chat
- Auto-mode: translations sent automatically to all participants
- Works on Google Meet, Zoom, Microsoft Teams

**What Stays Local vs Cloud:**

| Component | Local/Cloud | Data Sent | Alternative |
|-----------|------------|-----------|-------------|
| Audio Recording | ✅ Local | Nothing | N/A |
| Whisper Transcription | ✅ Local | Nothing | N/A |
| LibreTranslate | ✅ Local | Nothing | N/A |
| Google Translate | ☁️ Cloud | Text only | Use LibreTranslate |
| WebSocket Server | ✅ Local | Nothing | N/A |
| Browser Extension | ✅ Local | Nothing | N/A |

## Quick Start

```bash
# 1. Start the meeting recorder
cd meetings
./start_meeting_recorder.sh

# 2. Install Firefox extension (one-time setup)
# Firefox → about:debugging → Load Temporary Add-on
# Select: firefox-extension/manifest.json

# 3. Join your meeting in Firefox
# 4. The floating widget appears automatically
```

## Translation Options

### Recommended: LibreTranslate (Self-hosted, Private, Open Source)

[LibreTranslate](https://github.com/LibreTranslate/LibreTranslate) is our **recommended translation solution** for privacy-conscious users. It's a free and open-source machine translation API that runs entirely on your machine.

**Why LibreTranslate?**
- 🔒 **Complete Privacy**: All translations happen locally - no data ever leaves your computer
- 🌍 **Open Source**: Community-driven development aligned with radical technology principles
- 🚫 **No Corporate Surveillance**: Unlike cloud services, your conversations remain yours
- ⚡ **Unlimited Usage**: No API limits, rate limiting, or usage tracking
- 🔧 **Self-Hosted**: You control the infrastructure and data

**Quick Setup (English ↔ Portuguese Only - 200MB):**
```bash
# Start LibreTranslate with bidirectional EN-PT translation
docker run -d --name libretranslate \
  -p 5000:5000 \
  -e LT_LOAD_ONLY="en,pt" \
  libretranslate/libretranslate

# Use with the recorder
python system_audio_recorder.py --translator libretranslate
```

**Full Setup (All 96 Language Pairs - ~8GB):**
```bash
# Only if you need languages beyond English-Portuguese
docker run -d --name libretranslate \
  -p 5000:5000 \
  libretranslate/libretranslate
```

### Alternative: Google Translate (Cloud-based)

If you can't run LibreTranslate locally, the system falls back to Google Translate. However, be aware:
- ⚠️ Your text is sent to Google's servers
- ⚠️ Subject to rate limits and potential blocking
- ⚠️ Google may log and analyze your translations

```bash
# Uses Google Translate with automatic fallback to other services
python system_audio_recorder.py
```

### All Translation Options

```bash
# Automatic selection with fallback (default)
python system_audio_recorder.py --translator auto

# Force specific translator
python system_audio_recorder.py --translator google        # Google Translate
python system_audio_recorder.py --translator google-deep   # Alternative Google
python system_audio_recorder.py --translator mymemory      # MyMemory (5k words/day free)
python system_audio_recorder.py --translator libretranslate # Self-hosted
python system_audio_recorder.py --translator none          # No translation
```

## Firefox Extension Setup

### First-Time Installation

1. Open Firefox and navigate to `about:debugging`
2. Click "This Firefox" in the left sidebar
3. Click "Load Temporary Add-on"
4. Navigate to `meetings/firefox-extension/`
5. Select `manifest.json`
6. Extension installed - look for the microphone icon in your toolbar

### Using the Extension

1. Start the meeting recorder first (creates the WebSocket server)
2. Join your meeting in Firefox
3. The floating widget appears automatically showing:
   - Connection status to transcription server
   - Live transcriptions as they appear
   - Translation results in real-time

### Widget Controls

| Button | Function | Description |
|--------|----------|-------------|
| **Copy** | Copy to clipboard | Copy last transcription |
| **Insert** | Insert into chat | Place text in meeting chat input |
| **Auto** | Toggle auto-mode | Automatically send translations to chat |
| **Clear** | Clear display | Reset the transcription history |
| **−/+** | Minimize/expand | Hide/show widget content |

## Auto-Mode Operation

When **Auto-Mode** is enabled:

1. You speak in your language (English or Portuguese)
2. System transcribes your speech in real-time
3. Automatic translation to the other language
4. Auto-insertion into meeting chat input field
5. Auto-submit sends message to all participants

Perfect for multilingual meetings - speak naturally in your preferred language, and participants receive instant translations.

## Audio Setup

The system automatically creates **mixed audio capture**:

```
Your Microphone (RDPSource) ──┐
                              ├── Mixed Audio → Transcription
System Audio (All sounds) ────┘
```

**What gets captured:**
- Your voice (when you're unmuted in the meeting)
- All other participants speaking
- System sounds and screen share audio
- Meeting platform notifications

## LibreTranslate Setup Guide

[LibreTranslate](https://github.com/LibreTranslate/LibreTranslate) is a free and open-source machine translation API, part of the broader movement for privacy-respecting technology. It's developed by the open-source community and uses the [Argos Translate](https://github.com/argosopentech/argos-translate) library.

### Why LibreTranslate is Our Recommended Choice

**Privacy & Freedom:**
- ✊ **No Corporate Control**: Your translations don't feed big tech surveillance
- 🔓 **Fully Open Source**: Inspect, modify, and improve the code
- 🏠 **Local Processing**: Translations never leave your machine
- 📡 **Offline Capable**: Works without internet once models are downloaded

**Technical Advantages:**
- ✅ No API keys or authentication required
- ✅ No usage limits or throttling
- ✅ REST API compatible with many services
- ✅ Actively maintained by the community

**Complete Local Pipeline with LibreTranslate:**
1. **Audio** → Captured locally via PulseAudio
2. **Transcription** → Processed locally by Whisper (no cloud)
3. **Translation** → Processed locally by LibreTranslate (no cloud)
4. **Browser** → Delivered via local WebSocket

With this setup, your conversations never leave your computer!

### Installation Options

```bash
# 1. Start LibreTranslate with only EN-PT models
docker run -d --name libretranslate \
  -p 5000:5000 \
  -e LT_LOAD_ONLY="en,pt" \
  -e LT_UPDATE_MODELS=true \
  libretranslate/libretranslate

# 2. Wait for models to download (~200MB)
docker logs -f libretranslate

# 3. Test the server
curl http://localhost:5000/languages

# 4. Use with the recorder
python system_audio_recorder.py --translator libretranslate
```

### Persistent Setup (Recommended)

```bash
# Create volume to persist downloaded models
docker volume create libretranslate_models

# Run with persistent storage
docker run -d --name libretranslate \
  -p 5000:5000 \
  -v libretranslate_models:/home/libretranslate/.local \
  -e LT_LOAD_ONLY="en,pt" \
  libretranslate/libretranslate

# Models download once and persist across restarts
```

### Docker Commands

```bash
# Start/stop the container
docker start libretranslate
docker stop libretranslate

# Check logs
docker logs libretranslate

# Remove container (keeps volume)
docker rm libretranslate

# Remove everything including models
docker rm -f libretranslate
docker volume rm libretranslate_models
```

## File Structure

```
meetings/
├── system_audio_recorder.py    # Main audio capture & transcription engine
├── websocket_transcriber.py    # WebSocket server for browser communication
├── robust_translator.py        # Multi-service translation with fallback
├── start_meeting_recorder.sh   # One-click launcher
├── setup_audio_capture.sh      # Audio troubleshooting helper
└── firefox-extension/          # Browser extension
    ├── manifest.json           # Extension configuration
    ├── background.js           # WebSocket client & message handling
    ├── content.js              # Page integration & UI
    ├── popup.html/popup.js     # Extension popup interface
    └── style.css               # Widget styling
```

## Troubleshooting

### No Audio Being Detected

```bash
# Check audio sources
pactl list short sources

# Test microphone
arecord -d 3 test.wav && aplay test.wav

# Run audio setup helper
./setup_audio_capture.sh
```

### WebSocket Connection Issues

```bash
# Check if server is running
lsof -i :8765

# Restart everything
# 1. Stop the recorder (Ctrl+C)
# 2. Restart: ./start_meeting_recorder.sh
# 3. Reload Firefox extension in about:debugging
# 4. Refresh your meeting page
```

### LibreTranslate Issues

```bash
# Check if LibreTranslate is running
curl http://localhost:5000/languages

# View LibreTranslate logs
docker logs libretranslate

# If models fail to download
docker restart libretranslate

# Force re-download of models
docker run --rm -it \
  -e LT_LOAD_ONLY="en,pt" \
  -e LT_UPDATE_MODELS=true \
  libretranslate/libretranslate
```

### Extension Not Working

**Verify installation:**
- Extension icon appears in Firefox toolbar
- Connection status shows green dot when recorder is running

**Check supported sites:**
- Google Meet: meet.google.com
- Zoom: zoom.us  
- Microsoft Teams: teams.microsoft.com
- Other sites: Should work but may need chat selector adjustments

**Manual debugging:**
1. Press F12 in Firefox to open developer tools
2. Check Console tab for error messages
3. Look for WebSocket connection messages

### Chat Input Not Found

**Try these steps:**
1. Click directly in the chat input box first
2. Use Copy button instead, then paste manually (Ctrl+V)
3. Check console for "Could not find chat input" messages

**Platform-specific tips:**
- **Google Meet**: Make sure chat panel is open
- **Zoom**: Chat must be enabled in meeting settings
- **Teams**: Try clicking in the message box first

## Advanced Configuration

### Adjust Silence Detection
```python
# In system_audio_recorder.py
silence_threshold = 1.5  # seconds (increase for longer pauses)
```

### Change WebSocket Port
```python
# In websocket_transcriber.py  
port = 8765  # Change if port conflicts

# In firefox-extension/background.js
ws = new WebSocket('ws://localhost:YOUR_NEW_PORT');
```

### Customize Chat Selectors
```javascript
// In firefox-extension/content.js
const CHAT_SELECTORS = {
  'your-platform.com': [
    'input[placeholder*="message"]',
    'textarea[aria-label*="chat"]'
  ]
};
```

## Output Files

After your meeting ends:

```
meetings/
├── transcripts/
│   └── meeting_transcript.txt      # All transcriptions with timestamps
├── translations/  
│   └── meeting_translation.txt     # Original + translated pairs
└── recordings/
    └── meeting_recording_YYYYMMDD_HHMMSS.wav  # Full audio recording
```

**Example transcript:**
```
[14:32:15] [English] The hierarchical structures are crumbling, comrades.
[14:32:18] [Portuguese] As estruturas hierárquicas estão desmoronando, camaradas.

[14:32:45] [Portuguese] Precisamos organizar uma cooperativa de trabalhadores autônoma.
[14:32:48] [English] We need to organize an autonomous workers' cooperative.
```

## Performance Tips

### For Best Results
- Use GPU mode (automatic if NVIDIA GPU detected)
- Minimize background noise
- Speak clearly with natural pauses
- Test setup before important meetings

### Expected Performance
- **GPU (large-v3)**: ~2-3 seconds transcription delay
- **CPU (base)**: ~5-10 seconds transcription delay  
- **WebSocket latency**: <100ms to browser
- **Auto-insert speed**: Nearly instant

### Translation Service Comparison

| Service | Speed | Quality | Privacy | Limits | Philosophy |
|---------|-------|---------|---------|--------|------------|
| **LibreTranslate** ⭐ | Fast | Good | 🟢 Local/Private | Unlimited | Open Source |
| Google Translate | Fast | Excellent | 🔴 Cloud/Tracked | Rate limited | Proprietary |
| MyMemory | Medium | Good | 🔴 Cloud | 5000 words/day | Proprietary |
| Deep-translator | Fast | Excellent | 🔴 Cloud | Varies | Proprietary |

**Our Recommendation**: Use LibreTranslate for true privacy and alignment with open-source values.

### Meeting Platform Tips
- **Google Meet**: Works best, most reliable chat detection
- **Zoom**: Enable chat in meeting settings
- **Teams**: May need to click in chat box first
- **Others**: Use manual copy/paste if auto-insert fails

## Privacy & Security

**What Runs Locally (No Internet Required):**
- 🎤 **Audio Capture**: PulseAudio records system audio
- 🎧 **Transcription**: Whisper AI model processes audio entirely offline
  - Model downloaded once during setup (3GB for large-v3, 150MB for base)
  - ALL audio processing happens on your CPU/GPU
  - Whisper is open source from OpenAI but runs 100% locally
- 🔄 **Translation** (with LibreTranslate): Argos models run locally
  - Models downloaded once (200MB for EN-PT)
  - Zero network traffic during translation
- 📡 **WebSocket Server**: Localhost only (port 8765)

**What Uses the Cloud (Optional):**
- ☁️ **Google Translate**: If you don't use LibreTranslate
  - Only the transcribed text is sent (never audio)
  - Subject to Google's privacy policy
- ☁️ **Other Translation Services**: MyMemory, etc.
  - Only used as fallbacks if configured

**Meeting Platform Considerations:**
- 💬 **Chat Messages**: When you use auto-insert, translations appear in the meeting chat
  - This is visible to all meeting participants (as intended)
  - The meeting platform (Teams, Google Meet, etc.) stores these chats
  - This is no different than manually typing in the chat
- 🎥 **Your Participation**: You're already trusting the meeting platform with:
  - Your video and audio stream
  - Screen shares and files
  - Chat messages you type
  - Meeting recordings (if enabled by host)

**Important**: This tool doesn't share anything beyond what you're already sharing by being in the meeting. It just helps you communicate across language barriers.

**Complete Privacy Configuration:**
```bash
# 1. Use Whisper locally (automatic - no config needed)
# 2. Use LibreTranslate for translation
docker start libretranslate
python system_audio_recorder.py --translator libretranslate

# Result: 100% local processing - no data leaves your computer
#         (except what you choose to send to meeting chat)
```

**Security Features:**
- WebSocket server binds to localhost only
- No external API endpoints
- No telemetry or analytics
- No automatic updates or phone-home features
- All data stored in local files you control
- Meeting platforms only see what you explicitly send to chat

## Pro Tips

### Before Important Meetings
```bash
# Test your setup
./start_meeting_recorder.sh
# Speak a few sentences and verify transcriptions appear

# Check extension connection
# Look for green dot in floating widget

# Pre-start LibreTranslate if using
docker start libretranslate
```

### During Meetings
- Enable auto-mode for seamless translation sharing
- Monitor the terminal to see all transcriptions in real-time
- Use manual copy if auto-insert has issues
- Minimize widget to reduce screen clutter

### Multilingual Meeting Flow
1. Speak in your preferred language (English or Portuguese)
2. Auto-mode translates and sends to meeting chat
3. Other participants see both original and translation
4. Everyone can follow the conversation regardless of language

## Updates and Maintenance

### Update Extension
1. Make changes to extension files
2. Go to `about:debugging` in Firefox
3. Click "Reload" next to the extension
4. Refresh your meeting page

### Update Python Code
Changes to Python files take effect on next recorder restart. No need to reinstall anything.

### Backup Important Meetings
```bash
# Copy transcripts and recordings to safe location
cp transcripts/meeting_transcript.txt /path/to/backup/
cp translations/meeting_translation.txt /path/to/backup/
cp recordings/meeting_recording_*.wav /path/to/backup/
```

## Use Cases

**Perfect for:**
- Multilingual business meetings
- International conference calls  
- Language learning conversations
- Customer support calls
- Educational webinars
- Remote team collaboration

**Works great when:**
- You need to communicate across language barriers
- Meeting participants speak different languages
- You want automatic meeting transcripts
- Real-time translation would be helpful

## Disk Space Requirements

- **Whisper Models** (downloaded automatically on first run):
  - Large-v3 (GPU): ~3GB - Best accuracy
  - Base (CPU): ~150MB - Good accuracy, faster on CPU
- **LibreTranslate Models** (downloaded when Docker starts):
  - EN-PT only: ~200MB (recommended)
  - All languages: ~8GB (96 language pairs)
- **Audio Recordings**: ~100MB per hour of meeting
- **Transcripts**: Minimal (text files)

**Total Space Needed:**
- Minimum (CPU + EN-PT): ~350MB
- Recommended (GPU + EN-PT): ~3.2GB
- Everything (GPU + all languages): ~11GB

## Quick Reference

```bash
# RECOMMENDED: Private setup with LibreTranslate
docker start libretranslate  # Start if not running
python system_audio_recorder.py --translator libretranslate

# Fallback: Google Translate (sends data to cloud)
python system_audio_recorder.py

# Other options
python system_audio_recorder.py --translator none      # No translation
python system_audio_recorder.py --translator mymemory  # Alternative service

# Show all options
python system_audio_recorder.py --help
```

## About This Project

This project embodies radical technology principles:
- **Privacy First**: Your conversations belong to you, not tech corporations
- **Open Source**: All components are free and open-source software
- **Local Control**: Process everything on your own hardware
- **No Surveillance**: Zero telemetry, analytics, or data collection

Built with ❤️ for the community by developers who believe technology should empower users, not exploit them.

### Contributing

**Contributions welcome!** We especially encourage enhancements that:
- 🔒 Strengthen privacy and security
- 🏠 Improve local-first functionality
- 🚫 Reduce dependence on cloud services
- ♿ Increase accessibility
- 🌍 Add support for more languages
- 📖 Improve documentation

Submit issues and pull requests on our GitHub repository.

### Acknowledgments

This project stands on the shoulders of giants. We're grateful to:

- [OpenAI Whisper](https://github.com/openai/whisper) - For open speech recognition
- [LibreTranslate](https://github.com/LibreTranslate/LibreTranslate) by [Piero Toffanin](https://github.com/pierotofy) - For privacy-respecting translation
- [Argos Translate](https://github.com/argosopentech/argos-translate) by [Argos Open Tech](https://www.argosopentech.com/) - The translation engine powering LibreTranslate
- [Mozilla Firefox](https://www.mozilla.org/firefox/) - For continuing to champion user privacy
- The entire open-source community - For proving that technology can serve people, not profits