#wsl_audio_recorder_cpu.py 
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
import tempfile
import signal

class WSLAudioRecorder:
    """Audio recorder that uses arecord command for WSL compatibility"""
    
    def __init__(self, transcriber, sample_rate=16000, chunk_duration=0.5):
        self.model = load_silero_vad()
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.transcriber = transcriber
        self.recording = True
        self.audio_buffer = []
        self.speech_buffer = []
        self.recording_speech = False
        self.silence_start = None
        self.silence_threshold = 0.5  # seconds
        self.file_count = 1
        
    def create_directories(self):
        """Creates necessary directories"""
        directories = ['recordings', 'transcripts', 'translations']
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"✔ Directory '{directory}' created.")
                
    def start_recording(self):
        """Start continuous recording using arecord"""
        self.create_directories()
        print("\nRecording... Speak in English or Portuguese!")
        print("The system will automatically detect your language and translate.")
        print("English → Portuguese | Portuguese → English")
        print("Press Ctrl+C to stop\n")
        
        # Start the recording process
        record_thread = threading.Thread(target=self._record_loop)
        record_thread.daemon = True
        record_thread.start()
        
        # Process audio in main thread
        try:
            while self.recording:
                if len(self.audio_buffer) > int(self.sample_rate * self.chunk_duration):
                    self._process_chunk()
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.recording = False
            print("\nStopping recording...")
            
    def _record_loop(self):
        """Continuous recording loop using arecord"""
        chunk_samples = int(self.sample_rate * self.chunk_duration)
        chunk_bytes = chunk_samples * 2  # 16-bit audio
        
        # Start arecord process
        cmd = [
            'arecord',
            '-f', 'S16_LE',  # 16-bit signed little-endian
            '-r', str(self.sample_rate),  # Sample rate
            '-c', '1',  # Mono
            '-t', 'raw',  # Raw format
            '-q'  # Quiet mode
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        while self.recording:
            # Read chunk of audio data
            audio_data = process.stdout.read(chunk_bytes)
            if audio_data:
                # Convert bytes to numpy array
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                self.audio_buffer.extend(audio_array)
                
        process.terminate()
        
    def _process_chunk(self):
        """Process audio chunk for speech detection"""
        # Get chunk from buffer
        chunk_size = int(self.sample_rate * self.chunk_duration)
        if len(self.audio_buffer) < chunk_size:
            return
            
        chunk = self.audio_buffer[:chunk_size]
        self.audio_buffer = self.audio_buffer[chunk_size:]
        
        # Detect speech
        audio_tensor = torch.tensor(chunk, dtype=torch.float32)
        speech_timestamps = get_speech_timestamps(audio_tensor, self.model, threshold=0.5)
        
        if speech_timestamps:
            if not self.recording_speech:
                print("\nSpeech detected!")
                self.recording_speech = True
            self.silence_start = None
            self.speech_buffer.extend(chunk)
        else:
            if self.recording_speech:
                if self.silence_start is None:
                    self.silence_start = time.time()
                elif time.time() - self.silence_start > self.silence_threshold:
                    # End of speech detected
                    self._save_and_transcribe()
                    self.speech_buffer = []
                    self.recording_speech = False
                    self.silence_start = None
                else:
                    # Still in silence period, keep adding to buffer
                    self.speech_buffer.extend(chunk)
                    
    def _save_and_transcribe(self):
        """Save speech buffer and trigger transcription"""
        if not self.speech_buffer:
            return
            
        # Convert to int16
        audio_int16 = (np.array(self.speech_buffer) * 32767).astype(np.int16)
        
        # Save to file
        filename = f"recordings/sentence_{self.file_count}.wav"
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
            
        print(f"Saved: {filename}")
        
        # Start transcription in separate thread
        transcribe_thread = threading.Thread(
            target=self.transcriber.transcribe_audio_file,
            args=(filename,)
        )
        transcribe_thread.daemon = True
        transcribe_thread.start()
        
        self.file_count += 1


class BilingualTranscriber:
    def __init__(self, model_name="base", sample_rate=16000):  # Changed to base model for CPU
        print("Loading Whisper model (CPU mode)...")
        # Use CPU mode with int8 for better performance
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")
        self.sample_rate = sample_rate
        self.translator = Translator()
        self.transcript_file = self._create_file("transcripts", "transcript")
        self.translation_file = self._create_file("translations", "translation")
        self.supported_languages = {'en': 'English', 'pt': 'Portuguese'}
        print("Model loaded successfully!")
        
    def _create_file(self, directory, prefix):
        """Create a new numbered file"""
        os.makedirs(directory, exist_ok=True)
        count = 1
        while os.path.exists(f"{directory}/{prefix}_{count}.txt"):
            count += 1
        filepath = f"{directory}/{prefix}_{count}.txt"
        print(f"Created: {filepath}")
        return filepath
        
    def transcribe_audio_file(self, audio_file):
        """Transcribe and translate an audio file"""
        try:
            print(f"Processing {audio_file}...")
            # Load audio
            audio_array, _ = self._load_audio(audio_file)
            
            # Transcribe
            segments, info = self.model.transcribe(
                audio_array,
                beam_size=3,  # Reduced for CPU
                task="transcribe"
            )
            
            # Get transcription
            transcript = ""
            for segment in segments:
                transcript += segment.text
                
            if not transcript.strip():
                print("No speech detected in audio")
                return
                
            # Detect language
            lang = info.language
            lang_name = self.supported_languages.get(lang, lang)
            
            print(f"\nLanguage: {lang_name} ({info.language_probability:.0%} confidence)")
            print(f"Original: \033[1m{transcript}\033[0m")
            
            # Save original
            self._append_to_file(self.transcript_file, f"[{lang_name}] {transcript}\n")
            
            # Translate if English or Portuguese
            if lang in ['en', 'pt']:
                target_lang = 'pt' if lang == 'en' else 'en'
                target_name = self.supported_languages[target_lang]
                
                try:
                    translation = self.translator.translate(
                        transcript,
                        src=lang,
                        dest=target_lang
                    )
                    print(f"Translation ({target_name}): \033[1;36m{translation.text}\033[0m")
                    
                    # Save translation
                    self._append_to_file(
                        self.translation_file,
                        f"[{lang_name}] {transcript}\n[{target_name}] {translation.text}\n\n"
                    )
                except Exception as e:
                    print(f"Translation error: {e}")
                    
            print("-" * 60)
            
        except Exception as e:
            print(f"Transcription error: {e}")
            import traceback
            traceback.print_exc()
            
    def _load_audio(self, audio_file):
        """Load audio from file"""
        with wave.open(audio_file, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            audio_array = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
            return audio_array, wf.getframerate()
            
    def _append_to_file(self, filepath, text):
        """Append text to file"""
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(text)
            
    def combine_recordings(self):
        """Combine all recordings into one file"""
        recordings_dir = "recordings"
        if not os.path.exists(recordings_dir):
            return
            
        files = sorted([f for f in os.listdir(recordings_dir) if f.endswith('.wav')])
        if not files:
            print("No recordings to combine")
            return
            
        print(f"\nCombining {len(files)} recordings...")
        
        # Install ffmpeg if needed
        try:
            combined = AudioSegment.empty()
            for filename in files:
                filepath = os.path.join(recordings_dir, filename)
                audio = AudioSegment.from_wav(filepath)
                combined += audio
                
            output_file = f"combined_recording_{int(time.time())}.wav"
            combined.export(output_file, format="wav")
            print(f"Saved combined recording: {output_file}")
            
            # Clean up individual files
            for filename in files:
                os.remove(os.path.join(recordings_dir, filename))
            print(f"Cleaned up {len(files)} individual recordings")
        except Exception as e:
            print(f"Could not combine recordings (ffmpeg not found): {e}")
            print("Individual recordings are preserved in the recordings folder")


def main():
    # Initialize components
    print("Starting WSL Audio Recorder (CPU Mode)")
    print("Using smaller model for CPU compatibility")
    
    transcriber = BilingualTranscriber()
    recorder = WSLAudioRecorder(transcriber)
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\nShutting down...")
        recorder.recording = False
        time.sleep(0.5)
        transcriber.combine_recordings()
        print("Done! Check your transcripts and translations folders.")
        exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start recording
    try:
        recorder.start_recording()
    except Exception as e:
        print(f"Error: {e}")
        recorder.recording = False


if __name__ == "__main__":
    main()
