# api-server/audio_modules/test.py
import time
import numpy as np

class TestAudioModule:
    """Test module that generates fake audio"""
    
    def __init__(self, ws_server, config):
        self.ws_server = ws_server
        self.config = config
        self.running = False
        
    def start(self):
        """Generate test transcriptions"""
        self.running = True
        
        test_phrases = [
            ("Hello, this is a test of the audio system", "en"),
            ("The meeting will begin in five minutes", "en"),
            ("Por favor, verifique seu microfone", "pt"),
            ("Thank you for testing the system", "en")
        ]
        
        index = 0
        while self.running:
            text, lang = test_phrases[index % len(test_phrases)]
            
            # Simulate transcription
            self.ws_server.broadcast_transcription(
                text=text,
                lang=lang,
                translation=self._mock_translate(text, lang)
            )
            
            index += 1
            time.sleep(5)
    
    def stop(self):
        self.running = False
    
    def _mock_translate(self, text, lang):
        if lang == 'en':
            return "Tradução simulada para português"
        else:
            return "Simulated translation to English"