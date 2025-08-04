# web-ui/app.py
from flask import Flask, render_template, jsonify, request, send_file
import requests
import os
from datetime import datetime
import json

app = Flask(__name__)

# Configuration - Use Docker service names for internal communication
# When containers talk to each other, they use service names, not localhost
API_URL = os.environ.get('API_URL', 'http://api:8000')  # This is correct
LIBRETRANSLATE_URL = os.environ.get('LIBRETRANSLATE_URL', 'http://libretranslate:5000')  # This is correct

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/api/status')
def get_status():
    """Get system status"""
    status = {
        'transcriber': check_service_health(f"{API_URL}/health"),
        'libretranslate': check_service_health(f"{LIBRETRANSLATE_URL}/languages"),
        'websocket': False,  # Will be updated via WebSocket
        'recordings': count_files('/data/recordings'),
        'transcripts': count_files('/data/transcripts')
    }
    return jsonify(status)

@app.route('/api/audio/detect')
def detect_audio():
    """Proxy to API server's detect endpoint"""
    try:
        # Use the internal Docker network URL
        response = requests.get(f"{API_URL}/api/audio/detect", timeout=5)
        return jsonify(response.json())
    except Exception as e:
        # Log the actual error for debugging
        app.logger.error(f"Error proxying to {API_URL}/api/audio/detect: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/scan-devices', methods=['POST'])
def scan_devices():
    """Proxy to API server's scan-devices endpoint"""
    try:
        response = requests.post(
            f"{API_URL}/api/audio/scan-devices", 
            json=request.json, 
            headers={'Content-Type': 'application/json'},
            timeout=10  # Increased timeout for device scanning
        )
        return response.json(), response.status_code
    except Exception as e:
        app.logger.error(f"Error proxying scan-devices: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/test-device', methods=['POST'])
def test_device():
    """Proxy to API server's test-device endpoint"""
    try:
        response = requests.post(
            f"{API_URL}/api/audio/test-device", 
            json=request.json,
            headers={'Content-Type': 'application/json'},
            timeout=15  # Device testing can take time
        )
        return response.json(), response.status_code
    except Exception as e:
        app.logger.error(f"Error proxying test-device: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/start', methods=['POST'])
def proxy_start_audio():
    """Proxy to API server"""
    try:
        response = requests.post(
            f"{API_URL}/api/audio/start", 
            json=request.json,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        return response.json(), response.status_code
    except Exception as e:
        app.logger.error(f"Error proxying start audio: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/stop', methods=['POST'])
def proxy_stop_audio():
    """Proxy to API server"""
    try:
        response = requests.post(f"{API_URL}/api/audio/stop", timeout=5)
        return response.json(), response.status_code
    except Exception as e:
        app.logger.error(f"Error proxying stop audio: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/transcripts')
def list_transcripts():
    """List available transcripts"""
    transcripts = []
    transcript_dir = '/data/transcripts'
    
    if os.path.exists(transcript_dir):
        for filename in os.listdir(transcript_dir):
            if filename.endswith('.txt'):
                filepath = os.path.join(transcript_dir, filename)
                stats = os.stat(filepath)
                transcripts.append({
                    'name': filename,
                    'size': stats.st_size,
                    'modified': datetime.fromtimestamp(stats.st_mtime).isoformat()
                })
    
    return jsonify(sorted(transcripts, key=lambda x: x['modified'], reverse=True))

@app.route('/api/transcript/<filename>')
def get_transcript(filename):
    """Get transcript content"""
    try:
        # Sanitize filename
        filename = os.path.basename(filename)
        filepath = os.path.join('/data/transcripts', filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content, 'filename': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 404

def check_service_health(url):
    """Check if a service is healthy"""
    try:
        response = requests.get(url, timeout=2)
        return response.status_code == 200
    except Exception as e:
        app.logger.warning(f"Health check failed for {url}: {str(e)}")
        return False

def count_files(directory):
    """Count files in directory"""
    try:
        if os.path.exists(directory):
            return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
        return 0
    except:
        return 0

if __name__ == '__main__':
    # Enable debug logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    app.run(host='0.0.0.0', port=5000, debug=True)