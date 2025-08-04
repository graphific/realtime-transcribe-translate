# Usage Guide

A practical guide for using technology to break down language barriers in organizing and solidarity work.

## Table of Contents
- [Quick Start](#quick-start)
- [Understanding the System](#understanding-the-system)
- [Web Interface](#web-interface)
- [Audio Capture Methods](#audio-capture-methods)
- [Browser Extension](#browser-extension)
- [Meeting Platforms](#meeting-platforms)
- [Real-World Scenarios](#real-world-scenarios)
- [Advanced Features](#advanced-features)
- [Privacy & Security](#privacy--security)
- [Tips from the Field](#tips-from-the-field)

## Quick Start

### Three Steps to Freedom from Corporate Transcription

1. **Start the system**:
```bash
docker-compose -f docker/docker-compose.yml up -d
```

2. **Open the interface**: http://localhost:8080

3. **Click "Start Recording"** - that's it. Your words stay on your computer.

### What You'll See

When someone speaks in Portuguese:
```
[PT] A luta continua, e vamos vencer
[EN] The struggle continues, and we will win
```

When someone responds in English:
```
[EN] Solidarity across borders is our strength
[PT] A solidariedade além-fronteiras é nossa força
```

Both languages, equal footing. No corporate intermediary.

## Understanding the System

### How It Works (Simply)

1. **Audio Capture** - Your microphone or system audio
2. **Local Processing** - Whisper AI runs on YOUR computer
3. **Local Translation** - LibreTranslate on YOUR computer
4. **Display** - In your browser, on YOUR computer

No cloud. No surveillance. No corporate control.

### System Architecture for Transparency

```
Your Audio → Local Capture → Local AI → Local Translation → Your Screen
     ↓                                                           ↓
 (stays here)                                              (stays here)
```

Compare to corporate services:
```
Your Audio → Their Servers → Their AI → Their Analytics → Their Profit
     ↓                                                           ↓
 (extracted)                                                (exploited)
```

### Important Privacy Note

While our transcription stays local, **your meeting platform choice matters**:
- Google Meet, Zoom, Teams already have your audio/video
- They can (and do) analyze, record, and monetize your conversations
- When you share transcriptions back to chat, they get that text too

**For actual privacy, use self-hosted alternatives**:
- **Jitsi Meet** - Open source, can self-host, no account needed
- **BigBlueButton** - Open source, designed for privacy
- **Element (Matrix)** - Encrypted, decentralized communication
- **Nextcloud Talk** - Self-hosted video calls
- **Jami** - Peer-to-peer, no servers required

Our tool gives you local transcription, but can't protect you from the meeting platform itself.

## Web Interface

### The Control Center

The web interface at http://localhost:8080 is designed for simplicity:

```
┌─────────────────────────────────────┐
│  Meeting Transcriber                │
│  Local Processing | Privacy First   │
├─────────────────────────────────────┤
│                                     │
│  Audio Sources:                     │
│  ┌─────────────┐ ┌─────────────┐   │
│  │ Test Mode   │ │Windows Audio│   │
│  │   Ready     │ │   Ready     │   │
│  └─────────────┘ └─────────────┘   │
│                                     │
│  [Start Recording]                  │
│                                     │
│  Transcriptions appear here...      │
│                                     │
└─────────────────────────────────────┘
```

### Configuration Options

Click the gear icon for settings:

- **Target Language**: Where to translate to
- **Model Size**: 
  - `tiny/base` - Fast, good enough for most
  - `small/medium` - Better accuracy, slight delay
  - `large-v3` - Best accuracy, needs good GPU
- **Save Locally**: Keep recordings (your choice)
- **Privacy Mode**: Strict local-only processing

## Audio Capture Methods

### Method 1: Test Mode

Perfect for:
- Testing the system
- Demo to communities
- No audio setup needed

How: Just click "Test Mode" and start.

### Method 2: System Audio (Windows)

Captures everything you hear - perfect for online meetings.

```bash
cd src/clients
python windows_audio_client.py
```

What it captures:
- Meeting participants
- Shared videos
- System sounds
- Your microphone (if unmuted)

### Method 3: Microphone Only

For in-person meetings or when you only want your voice:

```bash
python windows_microphone_client.py
```

Features:
- Auto-gain control (boosts quiet voices)
- Noise suppression
- Works with any microphone

### Method 4: Professional Audio (VoiceMeeter)

For important sessions needing quality:

1. Install VoiceMeeter (free)
2. Route your audio through it
3. Enable VBAN
4. System auto-detects

Benefits:
- Multiple audio sources
- EQ and compression
- Recording backup

### Method 5: Network Audio (PulseAudio)

For Linux users and advanced setups:

```bash
# Enable network audio
pactl load-module module-native-protocol-tcp port=4713 auth-anonymous=1
```

Use cases:
- Multiple computers
- Remote participants
- Isolated audio processing

## Browser Extension

### Installation (One Time)

1. Open Firefox
2. Go to `about:debugging`
3. Click "This Firefox"
4. Click "Load Temporary Add-on"
5. Select `manifest.json` from `src/extensions/firefox/`

### The Floating Assistant

When you join a meeting, a small widget appears:

```
┌─────────────────────┐
│ Live Transcription  │
├─────────────────────┤
│ [EN] We need to... │
│ [PT] Precisamos...  │
├─────────────────────┤
│ Copy Insert Auto X  │
└─────────────────────┘
```

Controls:
- **Copy**: Copy last transcription
- **Insert**: Put into meeting chat
- **Auto**: Automatically share translations
- **X**: Clear display

### Privacy-Conscious Features

- All processing stays local
- No data sent to meeting platforms
- You control what gets shared
- Drag anywhere on screen

## Meeting Platforms

### Google Meet

**Setup**: 
1. Join meeting in browser
2. Extension activates automatically
3. Open chat panel
4. Enable "Auto" mode

**What happens**: Translations appear in chat for all participants

### Microsoft Teams

**Browser Version**:
- Works like Google Meet
- Auto-detects chat input

**Desktop App**:
- Use copy/paste mode
- Or share screen with web interface

### Zoom

**Web Client** (Recommended):
1. Join via browser
2. Extension works automatically

**Desktop App**:
- Run web interface
- Share screen to show transcriptions

### Jitsi Meet

**Coming Soon** - Full integration planned
**Current**: Use screen share method

### Signal/WhatsApp/Telegram Calls

For encrypted calls:
1. Use system audio capture
2. View transcriptions locally
3. Never goes through their servers

## Real-World Scenarios

### Scenario 1: Multilingual Team Meeting

**Setup**: International team with diverse accents

**Configuration**:
```env
WHISPER_MODEL=large-v3          # Best accuracy for accents
LIBRETRANSLATE_LANGS=pt,en,es   # Portuguese, English, Spanish
VAD_THRESHOLD=0.4               # Sensitive for soft speakers
```

**In Practice**:
- Team members speak in their preferred language
- Real-time translation for all participants
- Accents handled accurately by larger model
- Meeting recording saved for minutes

### Scenario 2: Technical Support Session

**Setup**: Fast-paced troubleshooting call

**Configuration**:
```env
WHISPER_MODEL=base              # Fast response time
CHUNK_DURATION=5.0              # Quick processing
AUTO_INSERT=true                # Share immediately
```

**In Practice**:
- Quick back-and-forth conversation
- Minimal delay in transcription
- Technical terms captured accurately
- Works on standard hardware

### Scenario 3: Confidential Discussion

**Setup**: Private meeting requiring security

**Configuration**:
```env
PRIVACY_MODE=strict             # No external connections
SAVE_AUDIO=false               # Nothing saved to disk
USE_MEMORY_ONLY=true           # RAM only
```

**In Practice**:
- All processing in memory
- No records kept
- Close window = data gone
- Complete privacy protection

### Scenario 4: Educational Webinar

**Setup**: Multilingual online workshop

**Configuration**:
```env
WHISPER_MODEL=medium           # Balance speed/accuracy
SAVE_TRANSCRIPTS=true          # Keep transcript for attendees
LIBRETRANSLATE_LANGS=en,pt,es  # Support multiple languages
```

**In Practice**:
- Multiple languages supported
- Participants see live transcriptions
- Smooth performance for extended sessions
- Exportable transcript for attendees

## Advanced Features

### Custom Vocabulary

Teach the system your terminology:

```env
# In .env file
WHISPER_PROMPT="Participants discuss: quilombos, MST, ocupação, grilagem, INCRA"
```

### Multi-Language Sessions

System auto-detects and translates between:
- English ↔ Portuguese
- Spanish ↔ English  
- French ↔ Portuguese
- And more...

### Speaker Identification

Enable speaker tracking:
```env
ENABLE_DIARIZATION=true
```

Shows as:
```
[Speaker 1 - PT]: Precisamos organizar...
[Speaker 2 - EN]: I agree, we should...
```

### Export Options

After your meeting:

1. **Text Export**:
```
Click Export → Choose TXT
Includes timestamps and translations
```

2. **Structured Data**:
```
Export → JSON
For analysis or archiving
```

3. **Subtitles**:
```
Export → SRT
For video recordings
```

### Collaborative Sessions

Multiple people can connect:

1. Share your IP address (local network only)
2. Others configure extension: `ws://YOUR-IP:8765`
3. Everyone sees same transcriptions
4. No central server needed

## Privacy & Security

### Current Security Configuration

**Good news!** As of the latest update, all services are secured to localhost only:

```bash
# Verify with:
netstat -an | grep -E "8765|8766|8000|8080|5000"

# You should see:
tcp  0  0  127.0.0.1:8765  0.0.0.0:*  LISTEN  # WebSocket - localhost only ✅
tcp  0  0  127.0.0.1:8766  0.0.0.0:*  LISTEN  # Audio input - localhost only ✅
tcp  0  0  127.0.0.1:8000  0.0.0.0:*  LISTEN  # API - localhost only ✅
tcp  0  0  127.0.0.1:8080  0.0.0.0:*  LISTEN  # Web UI - localhost only ✅
tcp  0  0  127.0.0.1:5000  0.0.0.0:*  LISTEN  # LibreTranslate - localhost only ✅
```

### What This Means

**Protected by default:**
- No one on your network can access your transcriptions
- No external connections possible without explicit configuration
- Your meeting transcriptions stay on your computer

**Still works normally:**
- Browser extension connects fine
- Web UI fully functional
- All audio clients work as expected

### What Stays Private

**Always Local**:
- Audio processing
- Speech recognition  
- Translation (with LibreTranslate)
- Storage (if enabled)

**Never Uploaded**:
- Your conversations
- Meeting participants
- Organization details
- Strategic discussions

### For Team/Network Deployment

If you need network access (understand the risks first):

1. **Recommended: SSH Tunneling**
   ```bash
   # Access from remote machine securely
   ssh -L 8080:localhost:8080 -L 8765:localhost:8765 user@your-server
   ```

2. **Alternative: Modify docker-compose.yml**
   - Remove `127.0.0.1:` from port bindings (reduces security)
   - Add authentication (WebSocket auth coming soon - see TODO.md)
   - Configure firewall rules

3. **Best Practice: VPN Access**
   - Keep localhost binding
   - Use VPN for remote team members
   - Maintains security while allowing access

### Security Best Practices

**For Sensitive Meetings**:

1. **Use memory-only mode**:
```env
SAVE_AUDIO=false
SAVE_TRANSCRIPTS=false
USE_MEMORY_ONLY=true
```

2. **Verify localhost binding**:
```bash
# Should show 127.0.0.1 not 0.0.0.0
netstat -an | grep 8765
```

3. **Clear data after meetings**:
```bash
# Linux/Mac
rm -rf data/recordings/* data/transcripts/*

# Windows
del /S data\recordings\* data\transcripts\*
```

4. **Use encrypted storage** (optional):
```bash
# Linux example
sudo cryptsetup luksFormat /dev/sdX
sudo cryptsetup open /dev/sdX meeting-data
# Mount and use for data directory
```

### Verification

Check privacy status:
```bash
curl http://localhost:8000/api/status

# Look for:
# "privacy_mode": "local_only"
# "external_connections": 0
```

## Tips from the Field

### For Accuracy

1. **Speak clearly** but naturally
2. **Minimize background noise**
3. **Use headphones** in online meetings
4. **Pause between speakers**

### For Performance

1. **Start with smaller models** - upgrade if needed
2. **Close other programs** to free resources
3. **Use GPU if available** - much faster
4. **Adjust chunk size** for responsiveness

### For Organizing

1. **Test before important meetings**
2. **Have backup plan** - technology fails
3. **Explain the system** - builds trust
4. **Share the tool** - community ownership

### Common Solutions

**"Transcription is slow"**
- Use smaller model
- Check CPU/GPU usage
- Reduce chunk duration

**"Missing words"**
- Increase model size
- Check audio levels
- Reduce background noise

**"Wrong language detected"**
- Set primary language in config
- Speak first sentence clearly
- System learns and improves

## Command Reference

### Quick Commands

```bash
# Start system
docker-compose -f docker/docker-compose.yml up -d

# Stop system
docker-compose -f docker/docker-compose.yml down

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Restart service
docker-compose -f docker/docker-compose.yml restart api
```

### Audio Clients

```bash
# List audio devices
python src/clients/windows_audio_client.py --list-devices

# Use specific device
python src/clients/windows_audio_client.py --device 2

# Test mode
python src/clients/windows_audio_client.py --test

# Debug mode
python src/clients/windows_audio_client.py --debug
```

### Direct API Control

```bash
# Start recording
curl -X POST http://localhost:8000/api/audio/start \
  -H "Content-Type: application/json" \
  -d '{"module": "windows_capture"}'

# Check status
curl http://localhost:8000/api/status

# Stop recording  
curl -X POST http://localhost:8000/api/audio/stop

# Export session
curl -X POST http://localhost:8000/api/export \
  -H "Content-Type: application/json" \
  -d '{"format": "txt", "include_translations": true}'
```

### Contributing

This tool belongs to the community:
- Report bugs
- Suggest features
- Improve translations
- Share with others

## Next Steps

- Explore [API documentation](API.md) for integration
- Read [troubleshooting guide](TROUBLESHOOTING.md) for issues
- Check [examples](../examples/) for automation scripts