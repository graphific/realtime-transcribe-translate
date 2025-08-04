# api-server/audio_modules/windows_capture_fixed.py
"""
Fixed Windows audio capture module with improved Whisper handling
"""

import numpy as np
import threading
import time
from queue import Queue, Empty
import logging
import wave
import os
from datetime import datetime
import torch

# Import translation utilities
from .translation_utils import TranslationManager

# Import OpenAI Whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError as e:
    WHISPER_AVAILABLE = False
    print(f"⚠️ Whisper not available: {e}")

# Import Silero VAD
try:
    from silero_vad import load_silero_vad, get_speech_timestamps
    VAD_AVAILABLE = True
except ImportError as e:
    VAD_AVAILABLE = False
    print(f"⚠️ Silero VAD not available: {e}")

logger = logging.getLogger(__name__)


class WindowsCaptureModule:
    """Windows audio capture module with real-time transcription and translation"""
    
    def __init__(self, ws_server, config, audio_queue=None):
        self.ws_server = ws_server
        self.config = config
        self.running = False
        
        # Use the shared audio queue from main.py
        self.audio_queue = audio_queue or Queue()
        
        # Windows capture settings
        self.sample_rate = config.get('sample_rate', 48000)
        self.device_name = config.get('device_name', 'Unknown Device')
        
        # Recording settings
        self.save_audio = config.get('save_audio', True)
        self.recording_dir = '/app/recordings'
        self.session_start = datetime.now()
        self.session_id = self.session_start.strftime('%Y%m%d_%H%M%S')
        
        # Create directories
        os.makedirs(self.recording_dir, exist_ok=True)
        os.makedirs('/app/transcripts', exist_ok=True)
        os.makedirs('/app/translations', exist_ok=True)
        
        # Audio recording files
        self.raw_audio_file = None
        self.processed_audio_file = None
        
        if self.save_audio:
            self._setup_recording_files()
        
        # Stats
        self.total_bytes = 0
        self.total_chunks = 0
        self.start_time = None
        self.transcription_count = 0
        self.segments_processed = 0
        self.failed_transcriptions = 0
        self.hallucination_count = 0
        
        # Audio processing
        self.audio_buffer = b''
        self.raw_audio_buffer = []
        self.last_transcription_time = time.time()
        
        # Whisper specific settings to reduce hallucinations
        self.min_speech_duration = 1.0  # Minimum seconds of speech to transcribe
        self.max_silence_ratio = 0.9    # Maximum ratio of silence in audio
        self.hallucination_threshold = 10  # Max repetitions before considering hallucination
        
        # Initialize models
        self.whisper_model = None
        self.vad_model = None
        self._initialize_models()
        
        # Initialize translation manager
        self.translation_manager = TranslationManager(preferred_service='auto')
        
        # Log initialization status
        self._log_initialization_status()
    
    def _initialize_models(self):
        """Initialize Whisper and VAD models"""
        
        # Check CUDA availability
        logger.info("🔍 Checking GPU availability...")
        logger.info(f"   PyTorch version: {torch.__version__}")
        logger.info(f"   CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            logger.info(f"   CUDA version: {torch.version.cuda}")
            logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")
            device = "cuda"
        else:
            device = "cpu"
            logger.warning("⚠️ CUDA not available - using CPU")
        
        # Initialize Whisper
        if not WHISPER_AVAILABLE:
            logger.error("❌ Whisper not available")
            return
            
        try:
            model_name = os.environ.get('WHISPER_MODEL', 'base')
            logger.info(f"🔄 Loading Whisper model '{model_name}' on {device}...")
            
            self.whisper_model = whisper.load_model(model_name, device=device)
            logger.info(f"✅ Whisper {model_name} model loaded")
                
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            self.whisper_model = None
        
        # Initialize VAD
        if VAD_AVAILABLE:
            try:
                logger.info("🔄 Loading Silero VAD model...")
                self.vad_model = load_silero_vad()
                
                if device == "cuda":
                    self.vad_model = self.vad_model.cuda()
                    
                logger.info(f"✅ Silero VAD model loaded on {device}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to load VAD model: {e}")
                self.vad_model = None
    
    def _setup_recording_files(self):
        """Setup WAV files for recording"""
        try:
            # Raw audio file
            raw_filename = os.path.join(self.recording_dir, f'raw_audio_{self.session_id}.wav')
            self.raw_audio_file = wave.open(raw_filename, 'wb')
            self.raw_audio_file.setnchannels(2)
            self.raw_audio_file.setsampwidth(2)
            self.raw_audio_file.setframerate(self.sample_rate)
            
            # Processed audio file
            proc_filename = os.path.join(self.recording_dir, f'processed_audio_{self.session_id}.wav')
            self.processed_audio_file = wave.open(proc_filename, 'wb')
            self.processed_audio_file.setnchannels(1)
            self.processed_audio_file.setsampwidth(2)
            self.processed_audio_file.setframerate(16000)
            
            logger.info(f"📁 Recording files created")
            
        except Exception as e:
            logger.error(f"Failed to setup recording files: {e}")
            self.save_audio = False
    
    def _log_initialization_status(self):
        """Log the initialization status"""
        logger.info("=" * 60)
        logger.info("🚀 Windows Capture Module Initialized")
        logger.info(f"📅 Session ID: {self.session_id}")
        logger.info(f"🎤 Device: {self.device_name}")
        logger.info(f"🎯 Whisper: {'Ready' if self.whisper_model else 'Not Available'}")
        logger.info(f"🔍 VAD: {'Ready' if self.vad_model else 'Not Available'}")
        
        translation_info = self.translation_manager.get_service_info()
        logger.info(f"🌐 Translation: {translation_info['service_name'] or 'Not Available'}")
        logger.info("=" * 60)
    
    def start(self):
        """Start processing audio from Windows client"""
        self.running = True
        self.start_time = time.time()
        
        logger.info("🎬 Starting Windows capture module...")
        
        # Send startup message
        self.ws_server.broadcast_transcription(
            text=f"Audio capture started - {self.device_name}",
            lang="en",
            translation=None
        )
        
        # Start threads
        threads = []
        
        # Audio processing thread
        process_thread = threading.Thread(target=self._process_audio_realtime, name="AudioProcessor")
        process_thread.start()
        threads.append(process_thread)
        
        # Status monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_status, name="StatusMonitor")
        monitor_thread.start()
        threads.append(monitor_thread)
        
        # Recording thread
        if self.save_audio:
            recording_thread = threading.Thread(target=self._recording_loop, name="AudioRecorder")
            recording_thread.start()
            threads.append(recording_thread)
        
        # Wait for threads
        for thread in threads:
            thread.join()
    
    def _recording_loop(self):
        """Save raw audio to file periodically"""
        while self.running:
            try:
                if self.raw_audio_buffer:
                    audio_to_save = self.raw_audio_buffer.copy()
                    self.raw_audio_buffer.clear()
                    
                    if self.raw_audio_file:
                        for chunk in audio_to_save:
                            self.raw_audio_file.writeframes(chunk)
                        self.raw_audio_file._file.flush()
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Recording error: {e}")
    
    def _process_audio_realtime(self):
        """Process audio in real-time chunks"""
        logger.info("🎵 Audio processing thread started")
        
        # Process in 10-second chunks for better context
        chunk_duration = 10.0
        bytes_per_second = self.sample_rate * 2 * 2  # 16-bit stereo
        chunk_size = int(bytes_per_second * chunk_duration)
        
        while self.running:
            try:
                # Get audio data
                audio_data = self.audio_queue.get(timeout=0.5)
                
                # Ensure it's bytes
                if isinstance(audio_data, bytes):
                    self.audio_buffer += audio_data
                else:
                    continue
                
                self.total_bytes += len(audio_data)
                self.total_chunks += 1
                
                # Save for recording
                if self.save_audio:
                    self.raw_audio_buffer.append(audio_data)
                
                # Process when we have enough audio
                if len(self.audio_buffer) >= chunk_size:
                    chunk = self.audio_buffer[:chunk_size]
                    self.audio_buffer = self.audio_buffer[chunk_size:]
                    self._process_chunk(chunk, chunk_duration)
                    
            except Empty:
                # Process remaining buffer if significant
                if len(self.audio_buffer) > self.sample_rate * 4:  # At least 2 seconds
                    remaining_duration = len(self.audio_buffer) / bytes_per_second
                    chunk = self.audio_buffer
                    self.audio_buffer = b''
                    self._process_chunk(chunk, remaining_duration)
                    
            except Exception as e:
                logger.error(f"❌ Error in audio processing: {e}")
                import traceback
                traceback.print_exc()
    
    def _process_chunk(self, audio_bytes, duration):
        """Process a chunk of audio"""
        try:
            self.segments_processed += 1
            
            # Convert to numpy array
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Convert stereo to mono
            if len(audio_array) % 2 == 0:
                audio_stereo = audio_array.reshape(-1, 2)
                audio_mono = audio_stereo.mean(axis=1).astype(np.int16)
            else:
                audio_mono = audio_array
            
            # Convert to float32
            audio_float = audio_mono.astype(np.float32) / 32768.0
            
            # Resample to 16kHz for Whisper
            if self.sample_rate != 16000:
                downsample_factor = self.sample_rate / 16000
                indices = np.arange(0, len(audio_float), downsample_factor).astype(int)
                indices = indices[indices < len(audio_float)]
                audio_float = audio_float[indices]
            
            # Save processed audio
            if self.save_audio and self.processed_audio_file:
                processed_int16 = (audio_float * 32767).astype(np.int16)
                self.processed_audio_file.writeframes(processed_int16.tobytes())
                self.processed_audio_file._file.flush()
            
            # Calculate audio levels
            max_level = np.max(np.abs(audio_float))
            rms_level = np.sqrt(np.mean(audio_float**2))
            
            # Skip if too quiet
            if max_level < 0.001:
                return
            
            # Check silence ratio
            silence_samples = np.sum(np.abs(audio_float) < 0.01)
            silence_ratio = silence_samples / len(audio_float)
            
            if silence_ratio > self.max_silence_ratio:
                logger.debug(f"Chunk has {silence_ratio:.1%} silence, skipping")
                return
            
            # Log every 10th chunk
            if self.segments_processed % 10 == 1:
                logger.info(f"🔊 Chunk #{self.segments_processed} - Duration: {duration:.1f}s, "
                          f"Max: {max_level:.3f}, RMS: {rms_level:.3f}, "
                          f"Silence: {silence_ratio:.1%}")
            
            # Process with VAD if available
            if self.vad_model and VAD_AVAILABLE:
                self._transcribe_with_vad(audio_float, duration)
            elif self.whisper_model and max_level > 0.01:
                # Direct transcription without VAD
                self._transcribe_audio(audio_float, duration)
                    
        except Exception as e:
            logger.error(f"❌ Error processing chunk: {e}")
            import traceback
            traceback.print_exc()
    
    def _transcribe_with_vad(self, audio_float, duration):
        """Transcribe using VAD to detect speech segments"""
        try:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            audio_tensor = torch.tensor(audio_float, dtype=torch.float32)
            
            if device == 'cuda':
                audio_tensor = audio_tensor.cuda()
            
            # Get speech timestamps with adjusted parameters
            speech_timestamps = get_speech_timestamps(
                audio_tensor,
                self.vad_model,
                threshold=0.5,
                min_speech_duration_ms=500,  # Increased from 250ms
                min_silence_duration_ms=500,  # Increased from 300ms
                return_seconds=False
            )
            
            if not speech_timestamps:
                return
            
            logger.info(f"🎤 VAD detected {len(speech_timestamps)} speech segments")
            
            # Extract speech segments
            speech_segments = []
            total_speech_duration = 0
            
            audio_cpu = audio_float if device == 'cpu' else audio_tensor.cpu().numpy()
            
            for i, ts in enumerate(speech_timestamps):
                start_sample = ts['start']
                end_sample = ts['end']
                segment_duration = (end_sample - start_sample) / 16000
                total_speech_duration += segment_duration
                
                if segment_duration > 0.5:  # Only keep segments > 0.5s
                    speech_segments.append(audio_cpu[start_sample:end_sample])
            
            # Concatenate speech segments
            if speech_segments and total_speech_duration > self.min_speech_duration:
                speech_audio = np.concatenate(speech_segments)
                
                logger.info(f"📊 Total speech: {total_speech_duration:.1f}s "
                          f"({total_speech_duration/duration*100:.0f}% of chunk)")
                
                self._transcribe_audio(speech_audio, total_speech_duration)
                    
        except Exception as e:
            logger.error(f"❌ VAD error: {e}")
            # Fallback to direct transcription
            self._transcribe_audio(audio_float, duration)
    
    def _is_hallucination(self, text):
        """Check if transcription is likely a hallucination using n-gram detection"""
        if not text or len(text) < 10:
            return False
        
        # Clean and split text
        # Remove punctuation and split by both spaces and commas
        import re
        cleaned = re.sub(r'[.!?;]', '', text)
        # Split by comma or space
        words = re.split(r'[,\s]+', cleaned)
        words = [w.strip().lower() for w in words if w.strip()]
        
        if len(words) < 3:
            return False
        
        # Check for repeated n-grams
        # 1-gram (single word repetition)
        for i in range(len(words) - 2):
            if words[i] == words[i+1] == words[i+2]:
                self.hallucination_count += 1
                logger.warning(f"⚠️ Detected hallucination (repeated word '{words[i]}'): {text[:100]}...")
                return True
        
        # 2-gram (bigram repetition)
        if len(words) >= 4:
            for i in range(len(words) - 3):
                bigram1 = (words[i], words[i+1])
                bigram2 = (words[i+2], words[i+3])
                if bigram1 == bigram2:
                    self.hallucination_count += 1
                    logger.warning(f"⚠️ Detected hallucination (repeated bigram '{' '.join(bigram1)}'): {text[:100]}...")
                    return True
        
        # 3-gram (trigram repetition)
        if len(words) >= 6:
            for i in range(len(words) - 5):
                trigram1 = (words[i], words[i+1], words[i+2])
                trigram2 = (words[i+3], words[i+4], words[i+5])
                if trigram1 == trigram2:
                    self.hallucination_count += 1
                    logger.warning(f"⚠️ Detected hallucination (repeated trigram '{' '.join(trigram1)}'): {text[:100]}...")
                    return True
        
        # Check if more than 50% of the text is the same word
        if words:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            max_count = max(word_counts.values())
            if max_count > len(words) * 0.5 and len(words) > 4:
                most_common = [w for w, c in word_counts.items() if c == max_count][0]
                self.hallucination_count += 1
                logger.warning(f"⚠️ Detected hallucination (>{50}% same word '{most_common}'): {text[:100]}...")
                return True
        
        return False
    
    def _transcribe_audio(self, audio_float, duration):
        """Transcribe audio using Whisper with hallucination detection"""
        try:
            if not self.whisper_model:
                return
            
            logger.info(f"🎙️ Starting Whisper transcription of {duration:.1f}s audio...")
            
            # Ensure audio is the right format
            audio_float = np.asarray(audio_float, dtype=np.float32)
            
            # Pad audio if too short
            if len(audio_float) < 16000:  # Less than 1 second
                padding = 16000 - len(audio_float)
                audio_float = np.pad(audio_float, (0, padding), mode='constant')
            
            # Transcribe with adjusted parameters
            start_time = time.time()
            result = self.whisper_model.transcribe(
                audio_float,
                language=None,  # Auto-detect
                task="transcribe",
                temperature=0.0,  # Deterministic
                best_of=1,  # Disable beam search
                beam_size=1,  # Disable beam search
                no_speech_threshold=0.6,
                logprob_threshold=-1.0,
                compression_ratio_threshold=2.4,
                condition_on_previous_text=False,  # Prevent context contamination
                initial_prompt=None  # Don't provide initial prompt
            )
            transcription_time = time.time() - start_time
            
            # Extract results
            text = result.get("text", "").strip()
            language = result.get("language", "unknown")
            no_speech_prob = result.get("no_speech_prob", 0)
            
            # Check if transcription failed or is empty
            if not text or len(text) <= 2:
                self.failed_transcriptions += 1
                logger.warning(f"⚠️ No text from transcription (no_speech_prob: {no_speech_prob:.2f})")
                return
            
            # Skip punctuation only
            if text in [".", ",", "!", "?", "...", "-", "—"]:
                return
            
            # Check for hallucination
            if self._is_hallucination(text):
                self.failed_transcriptions += 1
                return
            
            # Successful transcription!
            self.transcription_count += 1
            timestamp = datetime.now()
            
            logger.info("=" * 60)
            logger.info(f"✅ Transcription #{self.transcription_count}")
            logger.info(f"⏱️ Processing time: {transcription_time:.2f}s "
                      f"({duration/transcription_time:.1f}x realtime)")
            logger.info(f"🌐 Language: {language}")
            logger.info(f"📝 Text: {text}")
            
            # Translation
            translation = None
            if self.translation_manager.translator:
                if language == 'en':
                    translation = self.translation_manager.translate(text, source_lang='en', target_lang='pt')
                    if translation:
                        logger.info(f"🇵🇹 Portuguese: {translation}")
                elif language == 'pt':
                    translation = self.translation_manager.translate(text, source_lang='pt', target_lang='en')
                    if translation:
                        logger.info(f"🇬🇧 English: {translation}")
                else:
                    translation = self.translation_manager.translate(text, source_lang=language, target_lang='en')
                    if translation:
                        logger.info(f"🇬🇧 English: {translation}")
            
            logger.info("=" * 60)
            
            # Broadcast to WebSocket
            self.ws_server.broadcast_transcription(
                text=text,
                lang=language,
                translation=translation
            )
            
            # Save transcript
            self._save_transcript(text, language, translation, timestamp)
            self.last_transcription_time = time.time()
                
        except Exception as e:
            self.failed_transcriptions += 1
            logger.error(f"❌ Transcription error: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_transcript(self, text, language, translation, timestamp):
        """Save transcript to file"""
        try:
            transcript_file = os.path.join('/app/transcripts', f'transcript_{self.session_id}.txt')
            
            with open(transcript_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}]\n")
                f.write(f"Language: {language}\n")
                f.write(f"Original: {text}\n")
                if translation:
                    f.write(f"Translation: {translation}\n")
                f.write("-" * 60 + "\n")
                
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
    
    def _monitor_status(self):
        """Monitor and report status periodically"""
        logger.info("📊 Status monitoring thread started")
        
        while self.running:
            try:
                time.sleep(30)
                
                runtime = time.time() - self.start_time
                success_rate = (self.transcription_count / (self.transcription_count + self.failed_transcriptions) * 100) if (self.transcription_count + self.failed_transcriptions) > 0 else 0
                
                logger.info(f"""
📊 Status Report - Runtime: {runtime/60:.1f} minutes
Audio: {self.total_chunks:,} chunks, {self.total_bytes/1024/1024:.1f} MB
Transcriptions: {self.transcription_count} successful, {self.failed_transcriptions} failed ({success_rate:.1f}% success)
Hallucinations detected: {self.hallucination_count}
Queue: {self.audio_queue.qsize()} items
""")
                    
            except Exception as e:
                logger.error(f"Status monitor error: {e}")
                
        logger.info("📊 Status monitoring thread stopped")
    
    def stop(self):
        """Stop capture and cleanup"""
        logger.info("🛑 Stopping Windows capture module...")
        self.running = False
        
        time.sleep(1)
        
        # Close recording files
        if self.save_audio:
            try:
                if self.raw_audio_file:
                    self.raw_audio_file.close()
                if self.processed_audio_file:
                    self.processed_audio_file.close()
            except Exception as e:
                logger.error(f"Error closing audio files: {e}")
        
        runtime = time.time() - self.start_time if self.start_time else 0
        
        logger.info(f"""
📊 Final Session Statistics
Session ID: {self.session_id}
Total runtime: {runtime/60:.1f} minutes
Successful transcriptions: {self.transcription_count}
Failed transcriptions: {self.failed_transcriptions}
Hallucinations detected: {self.hallucination_count}
""")
        
        logger.info("✅ Windows capture module stopped")