# robust_translator.py
#!/usr/bin/env python3
"""
Robust translation module with multiple fallback options
Provides automatic fallback between translation services
"""

import time
from googletrans import Translator
from deep_translator import GoogleTranslator, MyMemoryTranslator, LibreTranslator
import logging

logger = logging.getLogger(__name__)

class RobustTranslator:
    """Translation with multiple fallback services"""
    
    def __init__(self):
        # Primary translator (googletrans)
        self.googletrans = Translator()
        self.last_googletrans_error_time = 0
        self.googletrans_error_count = 0
        
        # Fallback translators
        self.fallback_translators = [
            ('Google (deep-translator)', self._translate_google_deep),
            ('MyMemory', self._translate_mymemory),
            ('LibreTranslate', self._translate_libre),
        ]
        
        logger.info("Initialized RobustTranslator with fallback services")
        
    def translate(self, text, src='auto', dest='en', timeout=5.0):
        """Translate with automatic fallback"""
        if not text or len(text.strip()) < 2:
            return None
            
        # Clean text
        text = text.strip()
        
        # Skip very short or punctuation-only text
        if len(text) < 3 or text in ['.', '!', '?', ',', '...']:
            return None
        
        # Try primary translator first (googletrans)
        current_time = time.time()
        time_since_error = current_time - self.last_googletrans_error_time
        
        # Use primary if no recent errors or after cooldown
        if self.googletrans_error_count == 0 or time_since_error > 300:  # 5 min cooldown
            try:
                result = self.googletrans.translate(text, src=src, dest=dest)
                if result and hasattr(result, 'text') and result.text:
                    self.googletrans_error_count = 0  # Reset error count
                    logger.debug("Translation successful with primary googletrans")
                    return result.text
            except Exception as e:
                self.last_googletrans_error_time = current_time
                self.googletrans_error_count += 1
                logger.warning(f"Primary googletrans failed (attempt {self.googletrans_error_count}): {str(e)[:100]}")
        
        # Try fallback translators
        for name, translator_func in self.fallback_translators:
            try:
                logger.info(f"Trying fallback: {name}...")
                translation = translator_func(text, src, dest)
                if translation:
                    logger.info(f"✅ {name} succeeded")
                    return translation
            except Exception as e:
                logger.warning(f"{name} failed: {str(e)[:100]}")
                continue
        
        logger.error("All translation services failed")
        return None
    
    def _translate_google_deep(self, text, src, dest):
        """Google Translate via deep-translator"""
        # Handle 'auto' detection
        if src == 'auto':
            src = 'auto-detect'
        translator = GoogleTranslator(source=src, target=dest)
        return translator.translate(text)
    
    def _translate_mymemory(self, text, src, dest):
        """MyMemory translator (no API key required for limited use)"""
        # MyMemory has a 500 chars/request limit for free tier
        if len(text) > 500:
            text = text[:497] + "..."
        
        # MyMemory doesn't support 'auto' - default to 'en' if auto
        if src == 'auto':
            src = 'en'  # You might want to detect language first
            
        translator = MyMemoryTranslator(source=src, target=dest)
        return translator.translate(text)
    
    def _translate_libre(self, text, src, dest):
        """LibreTranslate using direct API (more reliable than deep-translator)"""
        import requests
        
        if src == 'auto':
            # LibreTranslate doesn't support auto-detect
            # You could implement language detection here if needed
            raise Exception("LibreTranslate requires explicit source language")
        
        # Configuration
        base_urls = [
            'http://localhost:5000',
            'http://127.0.0.1:5000'
        ]
        
        # Try each URL
        for base_url in base_urls:
            try:
                # Test connectivity first with a quick timeout
                test_response = requests.get(f"{base_url}/languages", timeout=1)
                if test_response.status_code != 200:
                    continue
                    
                # Translate using the API directly
                translate_url = f"{base_url}/translate"
                
                response = requests.post(
                    translate_url,
                    json={
                        "q": text,
                        "source": src,
                        "target": dest,
                        "format": "text"
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    translated_text = result.get("translatedText")
                    if translated_text:
                        logger.debug(f"LibreTranslate successful via {base_url}")
                        return translated_text
                    else:
                        logger.warning(f"LibreTranslate returned empty translation")
                        continue
                else:
                    logger.warning(f"LibreTranslate API error: {response.status_code}")
                    continue
                    
            except requests.exceptions.ConnectionError:
                logger.debug(f"Cannot connect to LibreTranslate at {base_url}")
                continue
            except requests.exceptions.Timeout:
                logger.debug(f"LibreTranslate timeout at {base_url}")
                continue
            except Exception as e:
                logger.warning(f"LibreTranslate error at {base_url}: {str(e)}")
                continue
        
        # If all local attempts fail, try public instance
        try:
            public_url = "https://translate.argosopentech.com/translate"
            response = requests.post(
                public_url,
                json={
                    "q": text,
                    "source": src,
                    "target": dest,
                    "format": "text"
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                translated_text = result.get("translatedText")
                if translated_text:
                    logger.info("LibreTranslate successful via public instance")
                    return translated_text
        except:
            pass
        
        raise Exception("LibreTranslate not available (tried local and public instances)")