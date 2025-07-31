# Firefox Extension Setup Guide

## Step 1: Integrate WebSocket into Your Transcriber

Add the WebSocket server to your existing transcriber by modifying your `BilingualTranscriber` class:

```python
# At the top of your file
from websocket_transcriber import TranscriptionWebSocketServer

# In BilingualTranscriber.__init__
self.ws_server = TranscriptionWebSocketServer()
self.ws_server.start()

# In transcribe_audio_file method, after getting transcript:
if transcript.strip():
    # Send to browser extension
    self.ws_server.broadcast_transcription(
        transcript, 
        lang_name,
        translation.text if 'translation' in locals() else None
    )
```

## Step 2: Create Extension Directory

```bash
mkdir firefox-transcription-extension
cd firefox-transcription-extension

# Create the files:
# - manifest.json
# - background.js
# - content.js
# - popup.html (includes popup.js)
# - style.css
# - websocket_transcriber.py
```

## Step 3: Create Simple Icons

Create simple colored squares as placeholder icons:

```python
# create_icons.py
from PIL import Image, ImageDraw

sizes = [16, 48, 128]
color = (33, 150, 243)  # Material Blue

for size in sizes:
    img = Image.new('RGB', (size, size), color)
    draw = ImageDraw.Draw(img)
    # Add a white circle in center
    margin = size // 4
    draw.ellipse([margin, margin, size-margin, size-margin], fill='white')
    img.save(f'icon-{size}.png')
```

Or use any icon you prefer!

## Step 4: Install Extension in Firefox

1. Open Firefox
2. Go to `about:debugging`
3. Click "This Firefox"
4. Click "Load Temporary Add-on"
5. Select the `manifest.json` file

## Step 5: Test the Setup

1. Start your transcriber with WebSocket:
   ```bash
   python wsl_audio_recorder.py  # Make sure it includes WebSocket server
   ```

2. Open a meeting site (Google Meet, Zoom, Teams)

3. Click the extension icon in Firefox toolbar

4. You should see:
   - Connection status (green = connected)
   - Floating widget on the page
   - Transcriptions appearing in real-time

## How to Use

### Floating Widget Controls:
- **📋 Copy**: Copy last transcription to clipboard
- **💬 Insert**: Insert into chat input field
- **🔄 Auto**: Toggle auto-insert mode
- **🗑️ Clear**: Clear the display

### Features:
- Drag widget anywhere on page
- Minimize to save space
- Auto-detects chat input on major platforms
- Shows both original and translation
- Keeps last 10 transcriptions

## Troubleshooting

### Connection Issues:
- Make sure WebSocket server is running (port 8765)
- Check Firefox console for errors (F12)
- Firewall might block localhost connections

### Chat Input Not Found:
- Click directly in chat box first
- Use Copy button then paste manually
- Check console for selector errors

### Extension Not Loading:
- Make sure all files are in same directory
- Check manifest.json for syntax errors
- Reload extension in about:debugging

## Making it Permanent

To install permanently:
1. Get Firefox Developer Edition
2. Sign the extension at addons.mozilla.org
3. Or use `web-ext` tool for development

## Security Note

This extension only connects to localhost:8765. Never expose the WebSocket server to the internet!