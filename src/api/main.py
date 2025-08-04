# api-server/main.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import threading
import time
import importlib
import os
import asyncio
import websockets
import json
from queue import Queue

# Import WebSocket server
from websocket_server import get_websocket_server

app = Flask(__name__)
# Allow all origins for development
CORS(app, resources={r"/api/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Start WebSocket server on startup
ws_server = get_websocket_server()

# Windows audio capture WebSocket server
windows_audio_clients = set()
windows_audio_queue = Queue()

# Global variable to track device requests
device_requests = {}

def auto_start_audio_module():
    """Auto-start audio module if configured"""
    import time
    time.sleep(5)  # Wait for everything to initialize
    
    auto_module = os.environ.get('AUTO_START_MODULE', '')
    if auto_module:
        logger.info(f"🚀 Auto-starting audio module: {auto_module}")
        config = {
            'save_audio': os.environ.get('SAVE_AUDIO', 'true').lower() == 'true'
        }
        
        try:
            # Import and start the module
            if auto_module == 'windows_capture':
                from audio_modules.windows_capture import WindowsCaptureModule
                global audio_manager
                audio_manager = WindowsCaptureModule(ws_server, config, windows_audio_queue)
                
                # Start in thread
                global current_audio_thread
                current_audio_thread = threading.Thread(target=audio_manager.start)
                current_audio_thread.daemon = True
                current_audio_thread.start()
                
                logger.info("✅ Audio module started automatically")
        except Exception as e:
            logger.error(f"Failed to auto-start audio module: {e}")

async def handle_windows_audio(websocket, path):
    """Handle incoming audio from Windows client with device management"""
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}" if websocket.remote_address else "unknown"
    logger.info(f"🎤 Windows audio client connected from {client_id}")
    windows_audio_clients.add(websocket)
    
    bytes_received = 0
    chunks_received = 0
    last_log_time = time.time()
    
    try:
        # Send connection confirmation
        await websocket.send(json.dumps({
            "type": "connection",
            "status": "connected",
            "message": "Connected to Windows audio server"
        }))
        
        async for message in websocket:
            if isinstance(message, bytes):
                # Raw audio data
                windows_audio_queue.put(message)
                bytes_received += len(message)
                chunks_received += 1
                
                # Log progress every 5 seconds
                if time.time() - last_log_time > 5:
                    logger.info(f"📊 Windows audio stats - Client: {client_id}, Chunks: {chunks_received}, Bytes: {bytes_received:,}")
                    last_log_time = time.time()
                    
            else:
                # JSON control message
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    # Handle device list response
                    if msg_type == 'device_list':
                        request_id = data.get('request_id')
                        if request_id in device_requests:
                            device_requests[request_id]['result'] = {
                                'devices': data.get('devices', [])
                            }
                            device_requests[request_id]['completed'] = True
                    
                    # Handle device test response
                    elif msg_type == 'device_test':
                        request_id = data.get('request_id')
                        if request_id in device_requests:
                            device_requests[request_id]['result'] = data.get('result', {})
                            device_requests[request_id]['completed'] = True
                    
                    # Handle client info
                    elif msg_type == 'info':
                        logger.info(f"Client info: Mode: {data.get('mode')}, Client: {data.get('client')}")
                    
                    else:
                        logger.info(f"📨 Control message from {client_id}: {data}")
                        
                except Exception as e:
                    logger.error(f"Failed to parse message: {e}")
                    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"❌ Windows audio client disconnected: {client_id} (received {bytes_received:,} bytes total)")
    except Exception as e:
        logger.error(f"❌ Error in Windows audio handler: {e}")
    finally:
        windows_audio_clients.discard(websocket)
        logger.info(f"🔌 Active Windows clients: {len(windows_audio_clients)}")

def start_windows_audio_server():
    """Start the Windows audio WebSocket server"""
    async def start_server():
        try:
            server = await websockets.serve(
                handle_windows_audio, 
                '0.0.0.0', 
                8766,
                compression=None,
                max_size=10485760
            )
            logger.info("🎧 Windows audio WebSocket server listening on port 8766")
            await asyncio.Future()  # Run forever
        except Exception as e:
            logger.error(f"Failed to start Windows audio server: {e}")
    
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_server())
    except Exception as e:
        logger.error(f"Windows audio server error: {e}")
    finally:
        loop.close()

# Audio module manager
audio_manager = None
current_audio_thread = None

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "websocket": "running" if ws_server and ws_server.running else "stopped",
        "windows_audio_clients": len(windows_audio_clients)
    })

@app.route('/api/status')
def status():
    return jsonify({
        "running": True,
        "websocket": "ws://localhost:8765",
        "websocket_connected_clients": len(ws_server.clients) if ws_server else 0,
        "windows_audio_clients": len(windows_audio_clients)
    })

@app.route('/api/audio/modules')
def get_modules():
    """Get available audio modules"""
    return jsonify({
        'modules': {
            'test': {
                'name': 'Test Mode',
                'description': 'Test without real audio - generates sample transcriptions',
                'status': 'available',
                'badge': '✅ Ready',
                'badge_color': 'success'
            },
            'windows_capture': {
                'name': 'Windows Audio Bridge',
                'description': 'Direct Windows audio capture (requires Windows client)',
                'status': 'available',
                'badge': '✅ Ready',
                'badge_color': 'success',
                'config_fields': [
                    {
                        'name': 'capture_mode',
                        'type': 'select',
                        'options': ['loopback', 'microphone', 'both'],
                        'default': 'loopback',
                        'description': 'What audio to capture'
                    }
                ]
            },
            'pulseaudio': {
                'name': 'PulseAudio',
                'description': 'Capture audio from PulseAudio server (Linux/WSL)',
                'status': 'available',
                'badge': '✅ Ready',
                'badge_color': 'success',
                'config_fields': [
                    {
                        'name': 'server',
                        'type': 'text',
                        'default': 'tcp:host.docker.internal:4713',
                        'description': 'PulseAudio server address'
                    }
                ]
            },
            'voicemeeter': {
                'name': 'VoiceMeeter',
                'description': 'Capture from VoiceMeeter via VBAN protocol (Windows)',
                'status': 'needs_setup',
                'badge': '⚙️ Setup Required',
                'badge_color': 'warning',
                'config_fields': [
                    {
                        'name': 'connection_type',
                        'type': 'select',
                        'options': ['vban', 'tcp'],
                        'default': 'vban',
                        'description': 'Connection protocol'
                    },
                    {
                        'name': 'port',
                        'type': 'number',
                        'default': 6980,
                        'description': 'Port number (6980 for VBAN)'
                    }
                ]
            }
        }
    })

@app.route('/api/audio/detect')
def detect_audio():
    """Auto-detect available audio modules"""
    return jsonify({
        'modules': {
            'test': {
                'name': 'Test Mode',
                'description': 'Test without real audio',
                'status': 'available',
                'badge': '✅ Ready',
                'badge_color': 'success',
                'auto_score': 10
            },
            'windows_capture': {
                'name': 'Windows Audio Bridge',
                'description': 'Direct Windows audio capture',
                'status': 'available',
                'badge': '✅ Ready',
                'badge_color': 'success',
                'auto_score': 80
            }
        },
        'recommended': 'windows_capture'
    })

# Replace the scan-devices endpoint in main.py with this fixed version:

@app.route('/api/audio/scan-devices', methods=['POST'])
def scan_devices():
    """Request device list from Windows client"""
    if not windows_audio_clients:
        # Return mock data for testing if no client connected
        return jsonify({
            'devices': [
                {
                    "index": 0,
                    "name": "Microphone (Realtek Audio)",
                    "channels": 2,
                    "sample_rate": 48000,
                    "is_input": True,
                    "loopback": False
                },
                {
                    "index": 1,
                    "name": "Speakers (Realtek Audio) - Loopback",
                    "channels": 2,
                    "sample_rate": 48000,
                    "is_input": False,
                    "loopback": True
                }
            ],
            'message': 'No Windows client connected - showing mock data. Run windows_audio_client_enhanced.py for real devices.'
        })
    
    # Create a simple synchronous version
    import uuid
    request_id = str(uuid.uuid4())
    device_requests[request_id] = {'type': 'list', 'result': None, 'completed': False}
    
    # Send command to Windows clients
    command = json.dumps({
        'command': 'list_devices',
        'request_id': request_id
    })
    
    # Send to connected clients synchronously
    disconnected_clients = []
    for client in windows_audio_clients:
        try:
            # Use asyncio.run to execute the async send
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(client.send(command))
            loop.close()
        except Exception as e:
            logger.error(f"Failed to send to client: {e}")
            disconnected_clients.append(client)
    
    # Remove disconnected clients
    for client in disconnected_clients:
        windows_audio_clients.discard(client)
    
    # Wait for response (max 5 seconds)
    start_time = time.time()
    while time.time() - start_time < 5:
        if request_id in device_requests and device_requests[request_id]['completed']:
            result = device_requests[request_id]['result']
            del device_requests[request_id]
            return jsonify(result)
        time.sleep(0.1)
    
    # Cleanup on timeout
    if request_id in device_requests:
        del device_requests[request_id]
    
    return jsonify({
        'devices': [],
        'error': 'Timeout waiting for device list. Make sure windows_audio_client_enhanced.py is running.'
    })

@app.route('/api/audio/test-device', methods=['POST'])
def test_device():
    """Test a specific audio device"""
    if not windows_audio_clients:
        return jsonify({
            'success': False,
            'error': 'No Windows client connected'
        }), 503
    
    data = request.get_json()
    device_index = data.get('device_index')
    
    # Create request
    import uuid
    request_id = str(uuid.uuid4())
    device_requests[request_id] = {'type': 'test', 'result': None, 'completed': False}
    
    command = json.dumps({
        'command': 'test_device',
        'device_index': device_index,
        'request_id': request_id
    })
    
    # Send to first available client
    sent = False
    for client in list(windows_audio_clients):
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(client.send(command))
            loop.close()
            sent = True
            break
        except Exception as e:
            logger.error(f"Failed to send test command: {e}")
    
    if not sent:
        return jsonify({
            'success': False,
            'error': 'Failed to send command to Windows client'
        }), 500
    
    # Wait for response
    start_time = time.time()
    while time.time() - start_time < 10:  # 10 seconds for device test
        if request_id in device_requests and device_requests[request_id]['completed']:
            result = device_requests[request_id]['result']
            del device_requests[request_id]
            return jsonify(result)
        time.sleep(0.1)
    
    # Cleanup on timeout
    if request_id in device_requests:
        del device_requests[request_id]
    
    return jsonify({
        'success': False,
        'error': 'Timeout waiting for device test'
    })

@app.route('/api/audio/start', methods=['POST'])
def start_audio():
    global audio_manager, current_audio_thread
    
    data = request.json or {}
    module_name = data.get('module', 'test')
    config = data.get('config', {})
    
    logger.info(f"Starting audio module: {module_name}")
    logger.info(f"Config: {config}")
    
    # Stop any existing audio capture
    if audio_manager:
        try:
            audio_manager.stop()
        except:
            pass
    
    try:
        # Load the appropriate module
        module_map = {
            'test': ('audio_modules.test', 'TestAudioModule'),
            'pulseaudio': ('audio_modules.pulseaudio', 'PulseAudioModule'),
            'voicemeeter': ('audio_modules.voicemeeter', 'VoiceMeeterModule'),
            'windows_capture': ('audio_modules.windows_capture', 'WindowsCaptureModule')
        }
        
        if module_name in module_map:
            module_path, class_name = module_map[module_name]
            module = importlib.import_module(module_path)
            module_class = getattr(module, class_name)
            
            # Create instance with access to the audio queue
            audio_manager = module_class(ws_server, config, windows_audio_queue)
            
            # Start in thread
            current_audio_thread = threading.Thread(target=audio_manager.start)
            current_audio_thread.daemon = True
            current_audio_thread.start()
            
            # Send startup message
            ws_server.broadcast_transcription(
                f"Audio capture started using {module_name}",
                "en",
                f"Captura de áudio iniciada usando {module_name}"
            )
            
            return jsonify({
                "status": "started",
                "module": module_name,
                "websocket": "ws://localhost:8765",
                "windows_audio_port": 8766 if module_name == 'windows_capture' else None
            })
        else:
            raise ValueError(f"Unknown module: {module_name}")
            
    except Exception as e:
        logger.error(f"Failed to start audio module: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/audio/stop', methods=['POST'])
def stop_audio():
    global audio_manager
    
    if audio_manager:
        try:
            audio_manager.stop()
            audio_manager = None
            return jsonify({"status": "stopped"})
        except Exception as e:
            logger.error(f"Error stopping audio: {e}")
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"status": "not_running"})

@app.route('/api/websocket/status')
def websocket_status():
    """Get WebSocket server status"""
    if ws_server:
        return jsonify({
            "running": ws_server.running,
            "clients": len(ws_server.clients),
            "url": f"ws://localhost:{ws_server.port}",
            "windows_audio_clients": len(windows_audio_clients)
        })
    return jsonify({"running": False})

@app.route('/api/test-message', methods=['POST'])
def send_test_message():
    """Send a test message via WebSocket"""
    if ws_server:
        data = request.json or {}
        text = data.get('text', 'Test message from API')
        lang = data.get('lang', 'en')
        translation = data.get('translation', 'Mensagem de teste da API')
        
        ws_server.broadcast_transcription(text, lang, translation)
        return jsonify({"status": "sent", "text": text})
    
    return jsonify({"error": "WebSocket server not available"}), 503

if __name__ == '__main__':
    # Start WebSocket server
    logger.info("Starting WebSocket server...")
    ws_server.start()
    
    # Start Windows audio WebSocket server
    logger.info("Starting Windows audio server on port 8766...")
    windows_thread = threading.Thread(target=start_windows_audio_server)
    windows_thread.daemon = True
    windows_thread.start()
    
    # Give servers time to start
    time.sleep(2)
    
     # Auto-start audio module if configured
    if os.environ.get('AUTO_START_MODULE'):
        auto_start_thread = threading.Thread(target=auto_start_audio_module)
        auto_start_thread.daemon = True
        auto_start_thread.start()

    time.sleep(2)
    
    # Start Flask app
    logger.info("Starting Flask API server...")
    app.run(host='0.0.0.0', port=8000, debug=False)