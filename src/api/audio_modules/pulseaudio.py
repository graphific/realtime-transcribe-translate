# api-server/audio_modules/pulseaudio.py
import subprocess
import numpy as np
import threading
from queue import Queue

class PulseAudioModule:
    """Capture from Windows PulseAudio server"""
    
    def __init__(self, ws_server, config):
        self.ws_server = ws_server
        self.config = config
        self.running = False
        self.audio_queue = Queue()
        
        # PulseAudio settings
        self.server = config.get('server', 'tcp:host.docker.internal:4713')
        self.source = config.get('source', None)
        self.sample_rate = config.get('sample_rate', 16000)
        
    def start(self):
        """Start audio capture from PulseAudio"""
        self.running = True
        
        # Start capture thread
        capture_thread = threading.Thread(target=self._capture_audio)
        capture_thread.start()
        
        # Start processing thread
        process_thread = threading.Thread(target=self._process_audio)
        process_thread.start()
        
        # Wait for threads
        capture_thread.join()
        process_thread.join()
    
    def _capture_audio(self):
        """Capture audio from PulseAudio server"""
        cmd = [
            'parec',
            '--server', self.server,
            '--rate', str(self.sample_rate),
            '--channels=1',
            '--format=s16le'
        ]
        
        if self.source:
            cmd.extend(['--device', self.source])
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            
            chunk_size = int(self.sample_rate * 0.5) * 2  # 0.5 second chunks
            
            while self.running:
                audio_data = process.stdout.read(chunk_size)
                if audio_data:
                    self.audio_queue.put(audio_data)
                    
            process.terminate()
            
        except Exception as e:
            print(f"PulseAudio capture error: {e}")
            self.running = False
    
    def _process_audio(self):
        """Process captured audio"""
        # This would integrate with your existing VAD and Whisper code
        while self.running:
            try:
                audio_data = self.audio_queue.get(timeout=1)
                # Process with VAD, Whisper, etc.
                # For now, just log
                print(f"Processing {len(audio_data)} bytes of audio")
            except:
                continue
    
    def stop(self):
        self.running = False