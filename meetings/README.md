# Meeting Transcription with Live Browser Integration

Real-time transcription and translation for online meetings with automatic chat insertion. Transform your online meetings with live transcription that appears directly in your browser and can automatically send translations to the meeting chat.

## What This Does

**Audio Capture:**
- Records ALL meeting audio (your voice + participants + screen shares)
- Works with any meeting platform (Teams, Zoom, Google Meet, etc.)
- Mixed audio capture - no complex routing needed

**Real-time Processing:**
- Live transcription using Whisper large-v3 (GPU accelerated)
- Automatic English ↔ Portuguese translation
- WebSocket streaming to browser extension

**Browser Integration:**
- Floating widget overlays on meeting pages
- One-click insertion into meeting chat
- Auto-mode: translations sent automatically to all participants
- Works on Google Meet, Zoom, Microsoft Teams

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

## File Structure

```
meetings/
├── system_audio_recorder.py    # Main audio capture & transcription engine
├── websocket_transcriber.py    # WebSocket server for browser communication
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

### Meeting Platform Tips
- **Google Meet**: Works best, most reliable chat detection
- **Zoom**: Enable chat in meeting settings
- **Teams**: May need to click in chat box first
- **Others**: Use manual copy/paste if auto-insert fails

## Privacy & Security

**Local Processing Only:**
- All transcription happens on your machine
- WebSocket server only accepts localhost connections
- No data sent to external services except Google Translate

**Data Storage:**
- Audio recordings saved locally only
- Transcripts stored in plain text files
- Delete files after meetings if needed

## Pro Tips

### Before Important Meetings
```bash
# Test your setup
./start_meeting_recorder.sh
# Speak a few sentences and verify transcriptions appear

# Check extension connection
# Look for green dot in floating widget
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
cp meeting_recording_*.wav /path/to/backup/
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