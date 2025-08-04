# api-server/audio_modules/voicemeeter.py
import numpy as np
import threading
import socket
import struct
from queue import Queue
import logging

logger = logging.getLogger(__name__)

class VoiceMeeterModule:
    """
    Capture mixed audio from VoiceMeeter via VBAN protocol or TCP stream
    VoiceMeeter can send audio over network using VBAN
    """
    
    def __init__(self, ws_server, config):
        self.ws_server = ws_server
        self.config = config
        self.running = False
        self.audio_queue = Queue()
        
        # VoiceMeeter settings
        self.connection_type = config.get('connection_type', 'vban')  # 'vban' or 'tcp'
        self.host = config.get('host', 'host.docker.internal')
        self.port = config.get('port', 6980)  # VBAN default port
        self.stream_name = config.get('stream_name', 'Stream1')
        self.sample_rate = config.get('sample_rate', 48000)
        
        # For audio processing
        self.transcriber = None  # Would integrate with Whisper
        
    def start(self):
        """Start capturing from VoiceMeeter"""
        self.running = True
        
        if self.connection_type == 'vban':
            capture_thread = threading.Thread(target=self._capture_vban)
        else:
            capture_thread = threading.Thread(target=self._capture_tcp)
            
        process_thread = threading.Thread(target=self._process_audio)
        
        capture_thread.start()
        process_thread.start()
        
        capture_thread.join()
        process_thread.join()
    
    def _capture_vban(self):
        """Capture audio using VBAN protocol"""
        logger.info(f"Starting VBAN capture from {self.host}:{self.port}")
        
        # Create UDP socket for VBAN
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        
        try:
            # For Docker, we need to bind to receive VBAN streams
            sock.bind(('0.0.0.0', self.port))
            logger.info(f"Listening for VBAN on port {self.port}")
            
            while self.running:
                try:
                    # VBAN packet structure
                    data, addr = sock.recvfrom(1436)  # VBAN max packet size
                    
                    if len(data) > 28:  # VBAN header is 28 bytes
                        # Parse VBAN header
                        header = data[:28]
                        audio_data = data[28:]
                        
                        # Check if it's valid VBAN packet
                        if header[:4] == b'VBAN':
                            # Extract stream name (bytes 8-24)
                            stream_name = header[8:24].rstrip(b'\x00').decode('utf-8', errors='ignore')
                            
                            if stream_name == self.stream_name or self.stream_name == '*':
                                self.audio_queue.put(audio_data)
                                
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"VBAN receive error: {e}")
                    
        finally:
            sock.close()
    
    def _capture_tcp(self):
        """Capture audio via TCP stream (alternative method)"""
        logger.info(f"Starting TCP capture from {self.host}:{self.port}")
        
        while self.running:
            try:
                # Connect to VoiceMeeter TCP server
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, self.port))
                logger.info("Connected to VoiceMeeter TCP stream")
                
                while self.running:
                    # Read audio data
                    # Assuming 16-bit stereo at 48kHz
                    chunk_size = 4096
                    data = sock.recv(chunk_size)
                    
                    if not data:
                        break
                        
                    self.audio_queue.put(data)
                    
            except Exception as e:
                logger.error(f"TCP connection error: {e}")
                if self.running:
                    logger.info("Reconnecting in 5 seconds...")
                    threading.Event().wait(5)
            finally:
                sock.close()
    
    def _process_audio(self):
        """Process captured audio"""
        logger.info("Audio processing thread started")
        
        # Buffer for accumulating audio
        audio_buffer = bytearray()
        
        while self.running:
            try:
                audio_data = self.audio_queue.get(timeout=1)
                audio_buffer.extend(audio_data)
                
                # Process in chunks (e.g., 1 second)
                chunk_size = self.sample_rate * 2 * 2  # 16-bit stereo
                
                if len(audio_buffer) >= chunk_size:
                    # Extract chunk
                    chunk = audio_buffer[:chunk_size]
                    audio_buffer = audio_buffer[chunk_size:]
                    
                    # Convert to numpy array
                    audio_array = np.frombuffer(chunk, dtype=np.int16)
                    
                    # Convert stereo to mono if needed
                    if len(audio_array) > 0:
                        audio_mono = audio_array.reshape(-1, 2).mean(axis=1)
                        audio_float = audio_mono.astype(np.float32) / 32768.0
                        
                        # Here you would process with VAD and Whisper
                        # For now, just log
                        logger.debug(f"Processing audio chunk: {len(audio_float)} samples")
                        
                        # Simulate transcription for testing
                        if np.random.random() < 0.1:  # 10% chance
                            self._simulate_transcription()
                            
            except:
                continue
    
    def _simulate_transcription(self):
        """Simulate a transcription for testing"""
        test_phrases = [
            ("Audio captured from VoiceMeeter", "en"),
            ("Testing mixed audio stream", "en"),
            ("All sources are being recorded", "en")
        ]
        
        import random
        text, lang = random.choice(test_phrases)
        
        self.ws_server.broadcast_transcription(
            text=text,
            lang=lang,
            translation="Áudio capturado do VoiceMeeter"
        )
    
    def stop(self):
        """Stop capture"""
        logger.info("Stopping VoiceMeeter capture")
        self.running = False
    
    @staticmethod
    def get_config_fields():
        """Return configuration fields for this module"""
        return [
            {
                'name': 'connection_type',
                'type': 'select',
                'options': ['vban', 'tcp'],
                'default': 'vban',
                'description': 'Connection protocol'
            },
            {
                'name': 'host',
                'type': 'text',
                'default': 'host.docker.internal',
                'description': 'VoiceMeeter host address'
            },
            {
                'name': 'port',
                'type': 'number',
                'default': 6980,
                'description': 'Port number (6980 for VBAN)'
            },
            {
                'name': 'stream_name',
                'type': 'text',
                'default': 'Stream1',
                'description': 'VBAN stream name (* for any)'
            }
        ]