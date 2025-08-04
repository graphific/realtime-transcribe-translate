# api-server/audio_modules/translation_utils.py
"""
Translation utilities with support for multiple translation services
and comprehensive logging for LibreTranslate
"""

import logging
import requests
import json
import os
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Check available translation libraries
try:
    from googletrans import Translator
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False
    logger.warning("googletrans not available")

try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    DEEP_TRANSLATOR_AVAILABLE = True
except ImportError:
    DEEP_TRANSLATOR_AVAILABLE = False
    logger.warning("deep-translator not available")


class LibreTranslateWrapper:
    """LibreTranslate wrapper with comprehensive logging"""
    
    def __init__(self, url="http://libretranslate:5000", log_translations=True):
        self.url = url
        self.log_translations = log_translations
        self.translation_log_file = '/app/translations/libretranslate_log.json'
        self.translation_count = 0
        self.error_count = 0
        self.session_start = datetime.now()
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test LibreTranslate connection"""
        try:
            response = requests.get(f"{self.url}/languages", timeout=5)
            if response.status_code == 200:
                languages = response.json()
                logger.info(f"✅ LibreTranslate connected at {self.url}")
                logger.info(f"   Available languages: {len(languages)}")
                # Log first few languages
                for lang in languages[:5]:
                    logger.info(f"   - {lang.get('name', 'Unknown')} ({lang.get('code', 'N/A')})")
                if len(languages) > 5:
                    logger.info(f"   ... and {len(languages) - 5} more languages")
            else:
                logger.error(f"❌ LibreTranslate connection failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Cannot connect to LibreTranslate at {self.url}: {e}")
    
    def translate(self, text, source_lang='auto', target_lang='en', log_details=True):
        """Translate text with detailed logging"""
        
        if not text or not text.strip():
            return None
        
        # Clean text
        text = text.strip()
        
        # Skip very short text
        if len(text) < 3:
            logger.debug(f"Text too short to translate: '{text}'")
            return None
        
        # Log the translation request
        request_id = f"{self.session_start.strftime('%Y%m%d_%H%M%S')}_{self.translation_count:04d}"
        self.translation_count += 1
        
        logger.info(f"🔄 LibreTranslate Request #{self.translation_count}")
        logger.info(f"   Request ID: {request_id}")
        logger.info(f"   Source language: {source_lang}")
        logger.info(f"   Target language: {target_lang}")
        logger.info(f"   Text length: {len(text)} characters")
        logger.info(f"   Text preview: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        # Prepare request
        request_data = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text"
        }
        
        # Log full text if enabled
        if log_details and len(text) <= 500:
            logger.info(f"   Full text: {text}")
        
        try:
            # Make translation request
            start_time = time.time()
            response = requests.post(
                f"{self.url}/translate",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            elapsed_time = time.time() - start_time
            
            # Log response details
            logger.info(f"   Response time: {elapsed_time:.2f}s")
            logger.info(f"   Status code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                translated_text = result.get("translatedText", "")
                detected_language = result.get("detectedLanguage", {})
                
                logger.info(f"✅ Translation successful")
                if detected_language and source_lang == 'auto':
                    logger.info(f"   Detected language: {detected_language.get('language', 'N/A')} "
                              f"(confidence: {detected_language.get('confidence', 'N/A')})")
                logger.info(f"   Translated preview: {translated_text[:100]}{'...' if len(translated_text) > 100 else ''}")
                
                # Save to log file
                if self.log_translations:
                    self._save_translation_log({
                        "request_id": request_id,
                        "timestamp": datetime.now().isoformat(),
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                        "text_length": len(text),
                        "original_text": text if len(text) <= 1000 else text[:1000] + "...",
                        "translated_text": translated_text,
                        "detected_language": detected_language,
                        "response_time": elapsed_time,
                        "success": True
                    })
                
                return translated_text
                
            else:
                error_msg = f"LibreTranslate API error: {response.status_code}"
                error_details = response.text
                logger.error(f"❌ {error_msg}")
                logger.error(f"   Error details: {error_details[:200]}")
                
                # Save error to log
                if self.log_translations:
                    self._save_translation_log({
                        "request_id": request_id,
                        "timestamp": datetime.now().isoformat(),
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                        "text_length": len(text),
                        "original_text": text[:200] + "..." if len(text) > 200 else text,
                        "error": error_msg,
                        "error_details": error_details[:500],
                        "response_time": elapsed_time,
                        "success": False
                    })
                
                self.error_count += 1
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Translation timeout after 30s")
            self.error_count += 1
            if self.log_translations:
                self._save_translation_log({
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat(),
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "text_length": len(text),
                    "error": "Timeout",
                    "success": False
                })
            return None
            
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Cannot connect to LibreTranslate at {self.url}")
            self.error_count += 1
            return None
            
        except Exception as e:
            logger.error(f"❌ Translation error: {e}")
            self.error_count += 1
            if self.log_translations:
                self._save_translation_log({
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat(),
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "text_length": len(text),
                    "error": str(e),
                    "success": False
                })
            return None
    
    def _save_translation_log(self, log_entry):
        """Save translation log entry to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.translation_log_file), exist_ok=True)
            
            # Read existing logs
            logs = []
            if os.path.exists(self.translation_log_file):
                try:
                    with open(self.translation_log_file, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                except:
                    logs = []
            
            # Add new entry
            logs.append(log_entry)
            
            # Keep only last 1000 entries
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Write back
            with open(self.translation_log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save translation log: {e}")
    
    def get_stats(self):
        """Get translation statistics"""
        success_rate = (self.translation_count - self.error_count) / self.translation_count * 100 if self.translation_count > 0 else 0
        
        stats = {
            "total_requests": self.translation_count,
            "successful": self.translation_count - self.error_count,
            "errors": self.error_count,
            "success_rate": f"{success_rate:.1f}%",
            "session_start": self.session_start.isoformat()
        }
        
        logger.info(f"📊 LibreTranslate Statistics:")
        logger.info(f"   Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Total requests: {stats['total_requests']}")
        logger.info(f"   Successful: {stats['successful']}")
        logger.info(f"   Errors: {stats['errors']}")
        logger.info(f"   Success rate: {stats['success_rate']}")
        
        return stats


class GoogleTranslateWrapper:
    """Wrapper for Google Translate with logging"""
    
    def __init__(self):
        if not GOOGLETRANS_AVAILABLE:
            raise ImportError("googletrans not available")
        self.translator = Translator()
        self.translation_count = 0
        logger.info("✅ Google Translate wrapper initialized")
    
    def translate(self, text, source_lang='auto', target_lang='en'):
        """Translate text using Google Translate"""
        if not text or len(text.strip()) < 2:
            return None
        
        self.translation_count += 1
        logger.info(f"🔄 Google Translate Request #{self.translation_count}")
        logger.info(f"   Languages: {source_lang} → {target_lang}")
        logger.info(f"   Text: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        try:
            result = self.translator.translate(text, src=source_lang, dest=target_lang)
            translated = result.text if hasattr(result, 'text') else str(result)
            logger.info(f"✅ Translation successful")
            logger.info(f"   Result: {translated[:100]}{'...' if len(translated) > 100 else ''}")
            return translated
        except Exception as e:
            logger.error(f"❌ Google Translate error: {e}")
            return None


class DeepTranslatorWrapper:
    """Wrapper for deep-translator with multiple service fallbacks"""
    
    def __init__(self):
        if not DEEP_TRANSLATOR_AVAILABLE:
            raise ImportError("deep-translator not available")
        
        self.services = []
        
        # Try to initialize available services
        try:
            self.services.append(('Google', GoogleTranslator))
            logger.info("✅ Deep Translator: Google available")
        except:
            pass
        
        try:
            self.services.append(('MyMemory', MyMemoryTranslator))
            logger.info("✅ Deep Translator: MyMemory available")
        except:
            pass
        
        self.translation_count = 0
        logger.info(f"✅ Deep Translator wrapper initialized with {len(self.services)} services")
    
    def translate(self, text, source_lang='auto', target_lang='en'):
        """Translate with fallback between services"""
        if not text or len(text.strip()) < 2:
            return None
        
        self.translation_count += 1
        logger.info(f"🔄 Deep Translator Request #{self.translation_count}")
        
        for service_name, TranslatorClass in self.services:
            try:
                logger.info(f"   Trying {service_name}...")
                
                # Handle 'auto' for different services
                src = source_lang
                if src == 'auto' and service_name == 'Google':
                    src = 'auto-detect'
                elif src == 'auto' and service_name == 'MyMemory':
                    src = 'en'  # MyMemory doesn't support auto
                
                translator = TranslatorClass(source=src, target=target_lang)
                result = translator.translate(text[:500])  # Limit text length
                
                if result:
                    logger.info(f"✅ {service_name} translation successful")
                    return result
                    
            except Exception as e:
                logger.warning(f"   {service_name} failed: {str(e)[:100]}")
                continue
        
        logger.error("❌ All deep-translator services failed")
        return None


class TranslationManager:
    """Main translation manager that handles all translation services"""
    
    def __init__(self, preferred_service='auto'):
        self.preferred_service = preferred_service
        self.translator = None
        self.service_name = None
        
        self._initialize_translator()
    
    def _initialize_translator(self):
        """Initialize the best available translator"""
        
        # Check environment for LibreTranslate preference
        use_libretranslate = os.environ.get('USE_LIBRETRANSLATE', 'true').lower() == 'true'
        libretranslate_url = os.environ.get('LIBRETRANSLATE_URL', 'http://libretranslate:5000')
        preferred = os.environ.get('PREFERRED_TRANSLATOR', 'libretranslate').lower()
        
        # Try LibreTranslate first if preferred
        if use_libretranslate or preferred == 'libretranslate':
            # Try multiple times with longer timeout
            for attempt in range(3):
                try:
                    logger.info(f"🔄 Attempting to connect to LibreTranslate (attempt {attempt + 1}/3)...")
                    response = requests.get(f"{libretranslate_url}/languages", timeout=10)
                    if response.status_code == 200:
                        self.translator = LibreTranslateWrapper(url=libretranslate_url)
                        self.service_name = 'LibreTranslate'
                        logger.info(f"✅ Translation Manager using LibreTranslate at {libretranslate_url}")
                        return
                except Exception as e:
                    logger.warning(f"LibreTranslate connection attempt {attempt + 1} failed: {e}")
                    if attempt < 2:
                        time.sleep(2)  # Wait before retry
        
        # Only fall back to other services if LibreTranslate is not required
        if preferred != 'libretranslate':
            # Try Google Translate
            if GOOGLETRANS_AVAILABLE:
                try:
                    self.translator = GoogleTranslateWrapper()
                    self.service_name = 'Google Translate'
                    logger.info("✅ Translation Manager using Google Translate (fallback)")
                    return
                except Exception as e:
                    logger.warning(f"Google Translate not available: {e}")
            
            # Try Deep Translator
            if DEEP_TRANSLATOR_AVAILABLE:
                try:
                    self.translator = DeepTranslatorWrapper()
                    self.service_name = 'Deep Translator'
                    logger.info("✅ Translation Manager using Deep Translator (fallback)")
                    return
                except Exception as e:
                    logger.warning(f"Deep Translator not available: {e}")
        
        logger.error("❌ No translation service available")
        self.translator = None
        self.service_name = None
    
    def translate(self, text, source_lang='auto', target_lang='en'):
        """Translate text using the configured service"""
        if not self.translator:
            return None
        
        try:
            return self.translator.translate(text, source_lang, target_lang)
        except Exception as e:
            logger.error(f"Translation error with {self.service_name}: {e}")
            return None
    
    def get_service_info(self):
        """Get information about the current translation service"""
        return {
            "service_name": self.service_name,
            "available": self.translator is not None,
            "stats": self.translator.get_stats() if hasattr(self.translator, 'get_stats') else None
        }