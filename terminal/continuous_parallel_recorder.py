#continuous_parallel_recorder.py
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

# Set environment variable to handle cuDNN issues
os.environ['CUDNN_FRONTEND_ENABLED'] = '0'

class ThreadedContinuousRecorder:
    """Continuous recording with threaded processing"""
    
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.recording = True
        
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
        print("Loading models...")
        self.vad_model = load_silero_vad()
        
        # Whisper model
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            self.whisper_model = WhisperModel("large-v3", device="cuda", compute_type="float16")
            print("Whisper model loaded on GPU")
        else:
            self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            print("Whisper model loaded on CPU")
            
        self.translator = Translator()
        
        # Create directories
        self.create_directories()
        
    def create_directories(self):
        """Create necessary directories"""
        dirs = ['recordings', 'transcripts', 'translations', 'temp_audio']
        for d in dirs:
            os.makedirs(d, exist_ok=True)
            
    def start(self):
        """Start all threads"""
        print("\n Starting Threaded Continuous Recording System")
        print(" Recording... Speak in English or Portuguese!")
        print("Press Ctrl+C to stop\n")
        
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
            print("\n\nShutting down...")
            self.stop()
            
    def stop(self):
        """Stop recording and clean up"""
        self.recording = False
        
        # Wait for threads
        self.record_thread.join(timeout=2)
        self.vad_thread.join(timeout=5)
        
        # Process remaining queue items
        print("Processing remaining audio...")
        while not self.vad_queue.empty():
            time.sleep(0.1)
            
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        # Combine files
        self.cleanup_and_combine()
        
    def recording_loop(self):
        """Continuous audio recording"""
        chunk_duration = 0.5  # 500ms chunks
        chunk_samples = int(self.sample_rate * chunk_duration)
        chunk_bytes = chunk_samples * 2  # 16-bit
        
        cmd = ['arecord', '-f', 'S16_LE', '-r', str(self.sample_rate), 
               '-c', '1', '-t', 'raw', '-q']
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Recording started")
        
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
                        print(f"Recording active - chunks: {self.stats['chunks_recorded']}, "
                              f"amplitude: {max_amp:.3f}")
                except queue.Full:
                    pass  # Skip if queue is full
                    
        process.terminate()
        print("Recording stopped")
        
    def vad_loop(self):
        """Voice Activity Detection loop"""
        print("VAD started")
        
        # Buffers
        audio_buffer = deque(maxlen=int(self.sample_rate * 10))  # 10 sec
        speech_buffer = []
        pre_buffer = deque(maxlen=int(self.sample_rate * 0.5))  # 0.5 sec
        
        # State
        in_speech = False
        silence_start = None
        silence_threshold = 1.2  # seconds
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
                        print(f"\nSpeech detected (segment {segment_id + 1})")
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
                                
                                print(f"Saved segment {segment_id} ({duration:.1f}s)")
                                
                                # Queue for transcription
                                self.vad_queue.put({
                                    'id': segment_id,
                                    'filename': filename,
                                    'duration': duration
                                })
                                
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
                print(f"VAD error: {e}")
                import traceback
                traceback.print_exc()
                
        print("VAD stopped")
        
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
            print(f"\nTranscribing segment {segment_id} ({duration:.1f}s)...")
            
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
                
                print(f"Language: {lang_name} ({info.language_probability:.0%})")
                print(f"Text: \033[1m{transcript}\033[0m")
                
                # Save transcript
                with open(f"transcripts/transcript.txt", 'a', encoding='utf-8') as f:
                    f.write(f"[Segment {segment_id}] [{lang_name}] {transcript}\n")
                
                # Translate if English or Portuguese
                if lang in ['en', 'pt']:
                    target_lang = 'pt' if lang == 'en' else 'en'
                    target_name = 'Portuguese' if target_lang == 'pt' else 'English'
                    
                    try:
                        translation = self.translator.translate(transcript, 
                                                              src=lang, dest=target_lang)
                        print(f"Translation ({target_name}): \033[1;36m{translation.text}\033[0m")
                        
                        with open(f"translations/translation.txt", 'a', encoding='utf-8') as f:
                            f.write(f"[Segment {segment_id}]\n")
                            f.write(f"[{lang_name}] {transcript}\n")
                            f.write(f"[{target_name}] {translation.text}\n\n")
                    except Exception as e:
                        print(f"Translation error: {e}")
                
                print("-" * 60)
                self.stats['segments_transcribed'] += 1
                
            # Clean up
            try:
                os.remove(filename)
            except:
                pass
                
        except Exception as e:
            print(f"Transcription error: {e}")
            import traceback
            traceback.print_exc()
            
    def status_loop(self):
        """Status monitoring"""
        while self.recording:
            time.sleep(5)
            print(f"\nStatus - Recorded: {self.stats['chunks_recorded']} chunks | "
                  f"Processed: {self.stats['chunks_processed']} | "
                  f"Detected: {self.stats['segments_detected']} | "
                  f"Transcribed: {self.stats['segments_transcribed']}")
            
    def cleanup_and_combine(self):
        """Combine audio files"""
        print("\nCombining audio segments...")
        
        temp_files = sorted([f for f in os.listdir('temp_audio') if f.endswith('.wav')])
        if temp_files:
            try:
                combined = AudioSegment.empty()
                for filename in temp_files:
                    filepath = os.path.join('temp_audio', filename)
                    audio = AudioSegment.from_wav(filepath)
                    combined += audio
                    
                output_file = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                combined.export(output_file, format="wav")
                print(f"Saved combined recording: {output_file}")
                
                # Clean up
                for filename in temp_files:
                    os.remove(os.path.join('temp_audio', filename))
                    
            except Exception as e:
                print(f"Error combining: {e}")
                
        print("Done! Check transcripts and translations folders.")


def main():
    recorder = ThreadedContinuousRecorder()
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        recorder.recording = False
        
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start recording
    recorder.start()


if __name__ == "__main__":
    main()