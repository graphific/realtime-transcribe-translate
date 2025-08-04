# API Reference

Complete API documentation for the Meeting Transcriber system.

## Table of Contents
- [Overview](#overview)
- [REST API](#rest-api)
  - [Health & Status](#health--status)
  - [Audio Control](#audio-control)
  - [Transcription Management](#transcription-management)
- [WebSocket API](#websocket-api)
  - [Transcription Stream](#transcription-stream)
  - [Audio Stream](#audio-stream)
- [Client Libraries](#client-libraries)
- [Examples](#examples)
- [Security & Privacy](#security--privacy)

## Overview

The Meeting Transcriber provides both REST and WebSocket APIs designed for local-first operation:

- **REST API** (Port 8000): Control and configuration
- **WebSocket API** (Port 8765): Real-time transcription stream
- **Audio WebSocket** (Port 8766): Raw audio streaming

### Base URLs

```
REST API:       http://localhost:8000/api
WebSocket:      ws://localhost:8765
Audio WS:       ws://localhost:8766
LibreTranslate: http://localhost:5000 (includes Swagger UI)
```

### Core Principles

- **No authentication required for localhost** - your computer, your rules
- **All processing stays local** - no cloud endpoints
- **Open protocol** - build your own clients

## REST API

### Health & Status

#### Check System Health

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "api": true,
    "websocket": true,
    "libretranslate": true
  },
  "version": "1.0.0",
  "uptime": 3600,
  "privacy_mode": "local_only"
}
```

#### Get System Status

```http
GET /api/status
```

**Response:**
```json
{
  "running": true,
  "recording": false,
  "websocket_clients": 2,
  "audio_clients": 1,
  "current_module": "windows_capture",
  "stats": {
    "transcriptions": 45,
    "translations": 42,
    "audio_hours": 1.5,
    "data_sent_to_cloud": 0
  }
}
```

### Audio Control

#### List Available Audio Modules

```http
GET /api/audio/modules
```

**Response:**
```json
{
  "modules": {
    "test": {
      "name": "Test Mode",
      "description": "Generate test transcriptions",
      "status": "available",
      "platforms": ["windows", "linux", "macos"],
      "privacy_level": "local",
      "config_fields": []
    },
    "windows_capture": {
      "name": "Windows Audio Bridge",
      "description": "Capture Windows system audio",
      "status": "available",
      "platforms": ["windows"],
      "privacy_level": "local",
      "config_fields": [
        {
          "name": "device_index",
          "type": "number",
          "description": "Audio device index",
          "required": false
        }
      ]
    }
  }
}
```

#### Start Audio Capture

```http
POST /api/audio/start
Content-Type: application/json

{
  "module": "windows_capture",
  "config": {
    "device_index": 0,
    "sample_rate": 48000,
    "save_locally": true,
    "encrypt_audio": false
  }
}
```

**Response:**
```json
{
  "status": "started",
  "module": "windows_capture",
  "websocket": "ws://localhost:8765",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "data_location": "local",
  "cloud_services": []
}
```

### Transcription Management

#### Get Recent Transcriptions

```http
GET /api/transcriptions?limit=10&offset=0
```

**Response:**
```json
{
  "transcriptions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "timestamp": "2024-01-15T14:30:00Z",
      "text": "Welcome everyone to today's meeting",
      "language": "en",
      "confidence": 0.95,
      "speaker": "local_capture",
      "translation": {
        "text": "Bem-vindo todos à reunião de hoje",
        "target_language": "pt",
        "service": "libretranslate_local"
      }
    }
  ],
  "total": 45,
  "limit": 10,
  "offset": 0,
  "storage": "local_disk"
}
```

#### Export Transcriptions

```http
POST /api/export
Content-Type: application/json

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "txt",
  "include_translations": true,
  "include_timestamps": true,
  "encryption": "none"
}
```

## WebSocket API

### Transcription Stream

Connect to receive real-time transcriptions:

```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
  console.log('Connected to transcription server');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Transcription:', data);
};
```

#### Message Types

##### Connection Confirmation
```json
{
  "type": "connection",
  "status": "connected",
  "message": "Connected to local transcription server",
  "privacy_mode": "local_only",
  "timestamp": "2024-01-15T14:30:00Z"
}
```

##### Transcription Message
```json
{
  "type": "transcription",
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T14:30:00Z",
  "text": "This is the transcribed text",
  "language": "en",
  "confidence": 0.95,
  "processing": "local",
  "translation": {
    "text": "Este é o texto transcrito",
    "language": "pt",
    "service": "local_libretranslate"
  }
}
```

### Audio Stream Protocol

For building your own audio capture tools:

```javascript
const ws = new WebSocket('ws://localhost:8766');

ws.onopen = () => {
  // Send client info
  ws.send(JSON.stringify({
    type: 'info',
    client: 'custom_client',
    sample_rate: 48000,
    channels: 1
  }));
  
  // Send audio data (PCM 16-bit)
  ws.send(audioBuffer);
};
```

## Client Libraries

### Python Client

```python
import asyncio
import websockets
import json

class TranscriptionClient:
    def __init__(self, url='ws://localhost:8765'):
        self.url = url
        
    async def connect(self):
        async with websockets.connect(self.url) as websocket:
            await self.handle_messages(websocket)
    
    async def handle_messages(self, websocket):
        async for message in websocket:
            data = json.loads(message)
            if data['type'] == 'transcription':
                print(f"[{data['language']}] {data['text']}")
                if data.get('translation'):
                    print(f"    → {data['translation']['text']}")

# Usage
client = TranscriptionClient()
asyncio.run(client.connect())
```

### JavaScript Client

```javascript
class TranscriptionClient {
  constructor(url = 'ws://localhost:8765') {
    this.url = url;
    this.ws = null;
  }
  
  connect() {
    this.ws = new WebSocket(this.url);
    
    this.ws.onopen = () => {
      console.log('Connected to transcription server');
      this.onConnect?.();
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'transcription') {
        this.onTranscription?.(data);
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.onError?.(error);
    };
  }
  
  disconnect() {
    this.ws?.close();
  }
}

// Usage
const client = new TranscriptionClient();
client.onTranscription = (data) => {
  console.log(`[${data.language}] ${data.text}`);
};
client.connect();
```

## Examples

### Meeting Recording

```python
import requests
import asyncio
import websockets
import json

class MeetingRecorder:
    def __init__(self, api_url='http://localhost:8000'):
        self.api_url = api_url
        self.session_id = None
        
    def start_recording(self, audio_module='test'):
        response = requests.post(f'{self.api_url}/api/audio/start', 
                               json={'module': audio_module})
        data = response.json()
        self.session_id = data['session_id']
        return data['websocket']
        
    def stop_recording(self):
        response = requests.post(f'{self.api_url}/api/audio/stop')
        return response.json()
        
    async def listen_transcriptions(self, ws_url):
        async with websockets.connect(ws_url) as websocket:
            async for message in websocket:
                data = json.loads(message)
                if data['type'] == 'transcription':
                    yield data
    
    def export_session(self, format='txt'):
        response = requests.post(f'{self.api_url}/api/export',
                               json={
                                   'session_id': self.session_id,
                                   'format': format,
                                   'include_translations': True
                               })
        return response.json()

# Example usage
async def record_meeting():
    recorder = MeetingRecorder()
    
    # Start recording
    ws_url = recorder.start_recording('windows_capture')
    print(f"Recording started. WebSocket: {ws_url}")
    
    # Listen for transcriptions
    try:
        async for transcription in recorder.listen_transcriptions(ws_url):
            print(f"[{transcription['language']}] {transcription['text']}")
            
    except KeyboardInterrupt:
        print("\nStopping recording...")
        
    # Stop and export
    recorder.stop_recording()
    export_data = recorder.export_session()
    print(f"Exported to: {export_data['file_url']}")

# Run
asyncio.run(record_meeting())
```

### Custom Audio Source Integration

```python
import asyncio
import websockets
import numpy as np
import sounddevice as sd

class CustomAudioSource:
    def __init__(self, device_index=None):
        self.device_index = device_index
        self.sample_rate = 16000
        self.channels = 1
        
    async def stream_audio(self):
        uri = 'ws://localhost:8766'
        
        async with websockets.connect(uri) as websocket:
            # Send client info
            await websocket.send(json.dumps({
                'type': 'info',
                'client': 'custom_audio_source',
                'sample_rate': self.sample_rate,
                'channels': self.channels
            }))
            
            # Audio callback
            def audio_callback(indata, frames, time, status):
                if status:
                    print(status)
                # Convert to 16-bit PCM
                audio_int16 = (indata * 32767).astype(np.int16)
                asyncio.create_task(
                    websocket.send(audio_int16.tobytes())
                )
            
            # Start audio stream
            with sd.InputStream(
                device=self.device_index,
                channels=self.channels,
                samplerate=self.sample_rate,
                callback=audio_callback
            ):
                print("Streaming audio... Press Ctrl+C to stop")
                await asyncio.Future()  # Run forever

# Usage
source = CustomAudioSource()
asyncio.run(source.stream_audio())
```

### Webhook Integration

```python
from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def handle_transcription():
    data = request.json
    
    if data['type'] == 'transcription':
        # Process transcription
        text = data['text']
        language = data['language']
        
        # Example: Send to Slack
        slack_webhook = 'https://hooks.slack.com/services/YOUR/WEBHOOK'
        requests.post(slack_webhook, json={
            'text': f"Transcription [{language}]: {text}"
        })
        
    return {'status': 'ok'}
```

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "PRIVACY_VIOLATION",
    "message": "Attempted to use cloud service in local-only mode",
    "details": {
      "attempted_service": "google_translate",
      "alternative": "libretranslate_local"
    }
  }
}
```

### Common Error Codes

- `AUDIO_MODULE_NOT_FOUND`: Requested audio module doesn't exist
- `PRIVACY_VIOLATION`: Attempted cloud service in local mode
- `LOCAL_ONLY`: Feature requires local processing
- `DEVICE_ACCESS_DENIED`: Cannot access audio device
- `TRANSLATION_UNAVAILABLE`: No local translation available

## Security & Privacy

### Local-First Design

All API endpoints default to local processing:

1. **No external connections** without explicit configuration
2. **No telemetry** or usage tracking
3. **No authentication** for localhost (your computer, your rules)

### Production Deployment

For community servers:

1. **VPN or Tor Only**:
```nginx
# Only allow connections from VPN
allow 10.8.0.0/24;
deny all;
```

2. **Client Certificates**:
```nginx
ssl_client_certificate /etc/nginx/client-certs/ca.crt;
ssl_verify_client on;
```

### Data Sovereignty

Your data, your control:

```python
# All data paths are configurable
DATA_PATH=/encrypted/volume/transcriptions
TEMP_PATH=/dev/shm/meeting_temp  # RAM disk
NO_DISK_WRITE=true  # Memory only
```

## Monitoring Without Surveillance

### Local Metrics Only

```http
GET /api/metrics
```

Returns only operational metrics, no user tracking:

```json
{
  "uptime": 3600,
  "memory_usage": {
    "used": 512000000,
    "total": 1024000000
  },
  "models_loaded": ["whisper-base"],
  "privacy_mode": "local_only",
  "external_connections": 0
}
```

## Building Your Own Clients

The API is open for community development:

1. **No API keys** - just connect locally
2. **No rate limits** - it's your computer
3. **Standard protocols** - WebSocket and HTTP
4. **MIT licensed** - fork and modify freely