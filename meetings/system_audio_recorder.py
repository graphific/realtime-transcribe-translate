#!/usr/bin/env python3
"""
System Audio Recorder - Captures all system audio including meeting participants
Works with PulseAudio monitor devices
"""

import os
import subprocess
import numpy as np
import wave
import threading
import time
from silero_vad import load_silero_vad, get_speech_timestamps
import torch
from faster_whisper import WhisperModel
from googletrans import Translator
from pydub import AudioSegment
import signal
from collections import deque
import queue
from datetime import datetime
import concurrent.futures

# Import WebSocket server if available
try:
    from websocket_transcriber import TranscriptionWebSocketServer
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("⚠️  WebSocket server not found - browser extension integration disabled")

# Set environment variable to handle cuDNN issues
os.environ['CUDNN_FRONTEND_ENABLED'] = '0'

class SystemAudioRecorder:
    """Records system audio using PulseAudio monitor"""
    
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.recording = True
        
        # Setup mixed audio if needed
        self.mixer_modules = []
        self.setup_mixed_audio()
        
        # Find monitor device
        self.monitor_source = self.find_monitor_source()
        if not self.monitor_source:
            raise Exception("No monitor source found! Make sure PulseAudio is running.")
            
        print(f"🎧 Using monitor source: {self.monitor_source}")
        
        # Thread-safe queues
        self.audio_queue = queue.Queue(maxsize=1000)
        self.vad_queue = queue.Queue(maxsize=100)
        
        # Stats
        self.stats = {
            'chunks_recorded': 0,
            'chunks_processed': 0,
            'segments_detected': 0,
            'segments_transcribed': 0
        }
        
        # Thread pool for transcription
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Initialize models once
        print("📥 Loading models...")
        self.vad_model = load_silero_vad()
        
        # Whisper model
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            self.whisper_model = WhisperModel("large-v3", device="cuda", compute_type="float16")
            print("✅ Whisper model loaded on GPU")
        else:
            self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            print("✅ Whisper model loaded on CPU")
            
        self.translator = Translator()
        
        # WebSocket server for browser extension
        self.ws_server = None
        if WEBSOCKET_AVAILABLE:
            self.ws_server = TranscriptionWebSocketServer()
            self.ws_server.start()
            print("🌐 WebSocket server started for browser extension")
        
        # Create directories
        self.create_directories()
        
    def setup_mixed_audio(self):
        """Setup mixed audio capture (microphone + system audio)"""
        print("🎙️ Setting up mixed audio capture...")
        
        try:
            # Check if meeting_mixer already exists
            result = subprocess.run(
                ['pactl', 'list', 'short', 'sinks'],
                capture_output=True, text=True
            )
            
            if 'meeting_mixer' in result.stdout:
                print("✅ Mixed audio already configured")
                return
            
            # Create null sink for mixing
            result = subprocess.run(
                ['pactl', 'load-module', 'module-null-sink', 
                 'sink_name=meeting_mixer',
                 'sink_properties=device.description="Meeting_Mixer"'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                sink_id = result.stdout.strip()
                self.mixer_modules.append(sink_id)
                print(f"✅ Created mixer sink (ID: {sink_id})")
                
                # Find and connect microphone
                mic_source = self.find_microphone_source()
                if mic_source:
                    result = subprocess.run(
                        ['pactl', 'load-module', 'module-loopback',
                         f'source={mic_source}', 'sink=meeting_mixer',
                         'latency_msec=1'],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.mixer_modules.append(result.stdout.strip())
                        print(f"✅ Connected microphone: {mic_source}")
                
                # Find and connect system audio
                system_monitor = self.find_system_monitor()
                if system_monitor:
                    result = subprocess.run(
                        ['pactl', 'load-module', 'module-loopback',
                         f'source={system_monitor}', 'sink=meeting_mixer',
                         'latency_msec=1'],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.mixer_modules.append(result.stdout.strip())
                        print(f"✅ Connected system audio: {system_monitor}")
                
                print("🎯 Mixed audio setup complete!")
                
        except Exception as e:
            print(f"⚠️  Mixed audio setup failed: {e}")
            print("   Falling back to system audio only")
    
    def find_microphone_source(self):
        """Find the microphone source"""
        try:
            result = subprocess.run(
                ['pactl', 'list', 'short', 'sources'],
                capture_output=True, text=True
            )
            
            # Look for RDPSource (WSL microphone)
            for line in result.stdout.strip().split('\n'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    source_name = parts[1]
                    if 'RDPSource' in source_name:
                        return source_name
                    elif 'input' in source_name.lower() and '.monitor' not in source_name:
                        return source_name
            
            return None
            
        except Exception:
            return None
    
    def find_system_monitor(self):
        """Find system audio monitor (excluding our mixer)"""
        try:
            result = subprocess.run(
                ['pactl', 'list', 'short', 'sources'],
                capture_output=True, text=True
            )
            
            for line in result.stdout.strip().split('\n'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    source_name = parts[1]
                    # Get monitor but not our mixer's monitor
                    if '.monitor' in source_name and 'meeting_mixer' not in source_name:
                        return source_name
            
            return None
            
        except Exception:
            return None
    
    def find_monitor_source(self):
        """Find PulseAudio monitor source for system audio"""
        try:
            # First check if we have mixed audio setup
            result = subprocess.run(
                ['pactl', 'list', 'short', 'sources'],
                capture_output=True, text=True
            )
            
            # Look for our mixer monitor first
            for line in result.stdout.strip().split('\n'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    source_name = parts[1]
                    if 'meeting_mixer.monitor' in source_name:
                        print("✅ Using mixed audio (microphone + system)")
                        return source_name
            
            # Otherwise look for any monitor source
            for line in result.stdout.strip().split('\n'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    source_name = parts[1]
                    if '.monitor' in source_name:
                        print("⚠️  Using system audio only (no microphone)")
                        return source_name
                        
            # Fallback to default monitor
            return "alsa_output.pci-0000_00_1f.3.analog-stereo.monitor"
            
        except Exception as e:
            print(f"Error finding monitor source: {e}")
            return None
            
    def create_directories(self):
        """Create necessary directories"""
        dirs = ['recordings', 'transcripts', 'translations', 'temp_audio']
        for d in dirs:
            os.makedirs(d, exist_ok=True)
            
    def setup_audio_loopback(self):
        """Setup audio loopback to capture system audio"""
        print("\n📢 Setting up audio capture...")
        
        instructions = """
For best results, configure audio loopback:

Option 1 - Use PulseAudio Monitor (Automatic):
  ✓ Already configured to use: {monitor}
  ✓ This captures all system audio
  
Option 2 - Create Virtual Sink (Better isolation):
  # Create virtual sink
  pactl load-module module-null-sink sink_name=virtual_speaker sink_properties=device.description=Virtual_Speaker
  
  # Create loopback from your default output
  pactl load-module module-loopback source=virtual_speaker.monitor
  
  # In your meeting app, keep audio output as default
  # This script will capture from the monitor

Option 3 - Use OBS Virtual Audio (Windows):
  1. Install OBS Studio
  2. Add Audio Output Capture
  3. Use OBS Virtual Camera/Audio
        """.format(monitor=self.monitor_source)
        
        print(instructions)
        
    def start(self):
        """Start all threads"""
        print("\n🚀 Starting System Audio Recorder")
        print("🎯 This will capture ALL system audio including:")
        print("   - Your microphone (if enabled in meeting)")
        print("   - Other participants' voices")  
        print("   - System sounds")
        print("\n🛑 Press Ctrl+C to stop\n")
        
        self.setup_audio_loopback()
        
        # Start threads
        self.record_thread = threading.Thread(target=self.recording_loop)
        self.record_thread.start()
        
        self.vad_thread = threading.Thread(target=self.vad_loop)
        self.vad_thread.start()
        
        self.status_thread = threading.Thread(target=self.status_loop)
        self.status_thread.start()
        
        try:
            # Wait for interrupt
            while self.recording:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down...")
            self.stop()
            
    def recording_loop(self):
        """Continuous audio recording from system monitor"""
        chunk_duration = 0.5  # 500ms chunks
        chunk_samples = int(self.sample_rate * chunk_duration)
        chunk_bytes = chunk_samples * 2  # 16-bit
        
        # Use parec (PulseAudio recorder) to capture from monitor
        cmd = [
            'parec',
            '--device=' + self.monitor_source,
            '--rate=' + str(self.sample_rate),
            '--channels=1',
            '--format=s16le',
            '--latency-msec=10'
        ]
        
        print(f"🎤 Starting system audio capture from: {self.monitor_source}")
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Check for errors
        time.sleep(0.5)
        if process.poll() is not None:
            _, error = process.communicate()
            print(f"❌ Failed to start audio capture: {error.decode()}")
            print("\n💡 Try: pactl list short sources")
            print("   Find a .monitor source and update the script")
            self.recording = False
            return
            
        print("✅ System audio capture started successfully")
        
        while self.recording:
            audio_data = process.stdout.read(chunk_bytes)
            if audio_data and len(audio_data) == chunk_bytes:
                # Convert to numpy
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Add to queue
                try:
                    self.audio_queue.put(audio_array, timeout=0.01)
                    self.stats['chunks_recorded'] += 1
                    
                    # Debug every 20 chunks (10 seconds)
                    if self.stats['chunks_recorded'] % 20 == 0:
                        max_amp = np.max(np.abs(audio_array))
                        print(f"🎤 Recording active - chunks: {self.stats['chunks_recorded']}, "
                              f"amplitude: {max_amp:.3f}")
                except queue.Full:
                    pass  # Skip if queue is full
                    
        process.terminate()
        print("🎤 Recording stopped")
        
    def vad_loop(self):
        """Voice Activity Detection loop"""
        print("🔍 VAD started")
        
        # Buffers
        audio_buffer = deque(maxlen=int(self.sample_rate * 10))  # 10 sec
        speech_buffer = []
        pre_buffer = deque(maxlen=int(self.sample_rate * 0.5))  # 0.5 sec
        
        # State
        in_speech = False
        silence_start = None
        silence_threshold = 1.5  # Longer for meetings
        segment_id = 0
        
        while self.recording or not self.audio_queue.empty():
            try:
                # Get audio chunk
                audio_chunk = self.audio_queue.get(timeout=0.5)
                self.stats['chunks_processed'] += 1
                
                # Add to buffers
                audio_buffer.extend(audio_chunk)
                if not in_speech:
                    pre_buffer.extend(audio_chunk)
                
                # Run VAD
                audio_tensor = torch.tensor(audio_chunk, dtype=torch.float32)
                speech_timestamps = get_speech_timestamps(audio_tensor, self.vad_model, 
                                                         threshold=0.5)
                
                if speech_timestamps:
                    if not in_speech:
                        # Speech started
                        in_speech = True
                        silence_start = None
                        speech_buffer = list(pre_buffer)  # Include pre-buffer
                        print(f"\n🔊 Speech detected (segment {segment_id + 1})")
                        self.stats['segments_detected'] += 1
                    
                    speech_buffer.extend(audio_chunk)
                    
                else:  # Silence
                    if in_speech:
                        speech_buffer.extend(audio_chunk)
                        
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > silence_threshold:
                            # Speech ended
                            if len(speech_buffer) > self.sample_rate * 0.5:
                                # Add post-padding
                                post_pad = list(audio_buffer)[-int(self.sample_rate * 0.3):]
                                speech_buffer.extend(post_pad)
                                
                                # Save segment
                                duration = len(speech_buffer) / self.sample_rate
                                filename = self.save_segment(speech_buffer, segment_id)
                                
                                print(f"💾 Saved segment {segment_id} ({duration:.1f}s)")
                                
                                # Submit to thread pool
                                self.executor.submit(self.transcribe_segment, 
                                                   segment_id, filename, duration)
                                
                                segment_id += 1
                            
                            # Reset
                            speech_buffer = []
                            in_speech = False
                            silence_start = None
                            
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ VAD error: {e}")
                import traceback
                traceback.print_exc()
                
        print("🔍 VAD stopped")
        
    def save_segment(self, audio_data, segment_id):
        """Save audio segment"""
        filename = f"temp_audio/segment_{segment_id:04d}.wav"
        
        audio_int16 = (np.array(audio_data) * 32767).astype(np.int16)
        
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
            
        return filename
        
    def transcribe_segment(self, segment_id, filename, duration):
        """Transcribe a segment"""
        try:
            print(f"\n🎧 Transcribing segment {segment_id} ({duration:.1f}s)...")
            
            # Load audio
            with wave.open(filename, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                audio_array = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
            
            # Transcribe
            segments, info = self.whisper_model.transcribe(
                audio_array,
                beam_size=5,
                task="transcribe",
                vad_filter=True
            )
            
            # Get text
            transcript = ""
            for segment in segments:
                transcript += segment.text
                
            if transcript.strip():
                # Language detection
                lang = info.language
                lang_name = {'en': 'English', 'pt': 'Portuguese'}.get(lang, lang)
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                print(f"🌐 [{timestamp}] Language: {lang_name} ({info.language_probability:.0%})")
                print(f"📝 Text: \033[1m{transcript}\033[0m")
                
                # Save transcript
                with open(f"transcripts/meeting_transcript.txt", 'a', encoding='utf-8') as f:
                    f.write(f"[{timestamp}] [{lang_name}] {transcript}\n")
                
                # Translate if English or Portuguese
                translation_text = None
                if lang in ['en', 'pt']:
                    target_lang = 'pt' if lang == 'en' else 'en'
                    target_name = 'Portuguese' if target_lang == 'pt' else 'English'
                    
                    try:
                        translation = self.translator.translate(transcript, 
                                                              src=lang, dest=target_lang)
                        translation_text = translation.text
                        print(f"🔄 Translation ({target_name}): \033[1;36m{translation_text}\033[0m")
                        
                        with open(f"translations/meeting_translation.txt", 'a', encoding='utf-8') as f:
                            f.write(f"[{timestamp}]\n")
                            f.write(f"[{lang_name}] {transcript}\n")
                            f.write(f"[{target_name}] {translation_text}\n\n")
                    except Exception as e:
                        print(f"⚠️ Translation error: {e}")
                
                # Send to browser extension
                if self.ws_server:
                    self.ws_server.broadcast_transcription(
                        transcript, lang, translation_text
                    )
                
                print("-" * 60)
                self.stats['segments_transcribed'] += 1
                
            # Clean up
            try:
                os.remove(filename)
            except:
                pass
                
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            import traceback
            traceback.print_exc()
            
    def status_loop(self):
        """Status monitoring"""
        while self.recording:
            time.sleep(10)
            print(f"\n📊 Status - Recorded: {self.stats['chunks_recorded']} chunks | "
                  f"Processed: {self.stats['chunks_processed']} | "
                  f"Detected: {self.stats['segments_detected']} | "
                  f"Transcribed: {self.stats['segments_transcribed']}")
            
    def stop(self):
        """Stop recording and clean up"""
        self.recording = False
        
        # Wait for threads
        self.record_thread.join(timeout=2)
        self.vad_thread.join(timeout=5)
        
        # Process remaining queue items
        print("⏳ Processing remaining audio...")
        while not self.vad_queue.empty():
            time.sleep(0.1)
            
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        # Combine files
        self.cleanup_and_combine()
        
        # Clean up audio mixer
        self.cleanup_mixer()
        
    def cleanup_mixer(self):
        """Remove the mixed audio setup"""
        if self.mixer_modules:
            print("\n🧹 Cleaning up audio mixer...")
            for module_id in reversed(self.mixer_modules):
                try:
                    subprocess.run(['pactl', 'unload-module', module_id])
                    print(f"✅ Removed module {module_id}")
                except:
                    pass
    
    def cleanup_and_combine(self):
        """Combine audio files"""
        print("\n🔧 Combining audio segments...")
        
        temp_files = sorted([f for f in os.listdir('temp_audio') if f.endswith('.wav')])
        if temp_files:
            try:
                combined = AudioSegment.empty()
                for filename in temp_files:
                    filepath = os.path.join('temp_audio', filename)
                    audio = AudioSegment.from_wav(filepath)
                    combined += audio
                    
                output_file = f"meeting_recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                combined.export(output_file, format="wav")
                print(f"✅ Saved combined recording: {output_file}")
                
                # Clean up
                for filename in temp_files:
                    os.remove(os.path.join('temp_audio', filename))
                    
            except Exception as e:
                print(f"⚠️ Error combining: {e}")
                
        print("✅ Done! Check transcripts and translations folders.")


def main():
    recorder = SystemAudioRecorder()
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        recorder.recording = False
        
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start recording
    recorder.start()


if __name__ == "__main__":
    main()