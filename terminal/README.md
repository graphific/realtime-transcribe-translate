# Personal Recording Tools

Microphone-only transcription tools for dictation, reading, and personal note-taking. High-accuracy speech-to-text tools designed for personal use, perfect for dictating documents, reading text aloud, taking voice notes, and practicing pronunciation.

## Available Tools

| Tool | Best For | Silence Detection | Processing | Accuracy |
|------|----------|-------------------|------------|----------|
| **`wsl_audio_recorder.py`** | Reading, dictation, prepared speeches | 1.5s (complete sentences) | Sequential | Highest |
| **`continuous_parallel_recorder.py`** | Conversations, live interpretation | 1.2s (faster response) | Parallel | High |
| **`wsl_audio_recorder_cpu.py`** | Systems without GPU | 0.5s (very responsive) | Sequential | Good |

## Quick Start

```bash
# Activate environment
conda activate audio

# Choose your tool:
python wsl_audio_recorder.py              # Best for dictation
python continuous_parallel_recorder.py    # Best for conversations  
python wsl_audio_recorder_cpu.py          # Best for CPU-only systems
```

## Detailed Tool Comparison

### 1. Complete Sentences Mode (`wsl_audio_recorder.py`)

**Perfect for:** Reading documents, dictation, prepared content

**Features:**
- **1.5 second silence detection** - waits for natural sentence breaks
- **Pre/post buffering** - captures 0.5s before and after speech
- **GPU/CPU auto-detection** - uses large-v3 on GPU, base on CPU
- **Thread-safe processing** - no data loss during transcription
- **VAD filtering** - removes background noise and breathing

**When to use:**
- Reading a book or document aloud
- Dictating emails or reports  
- Recording prepared presentations
- When you want complete, well-formed sentences

**Example session:**
```bash
$ python wsl_audio_recorder.py

Speech detected!
Processing recordings/sentence_1.wav (12.3s)
Language: English (99% confidence)
Original: Mutual aid networks are more effective than government welfare systems.
Translation (Portuguese): Redes de ajuda mútua são mais eficazes que sistemas de assistência social governamental.

Speech detected!
Processing recordings/sentence_2.wav (8.1s)
Language: Portuguese (97% confidence)  
Original: O Estado é apenas violência organizada em favor da classe dominante.
Translation (English): The State is just organized violence in favor of the ruling class.
```

### 2. Real-time Continuous Mode (`continuous_parallel_recorder.py`)

**Perfect for:** Live conversations, real-time feedback, minimal delay

**Features:**
- **1.2 second silence detection** - faster response time
- **Parallel processing** - multiple segments transcribed simultaneously
- **Thread pool executor** - 2 workers for concurrent transcription
- **Status monitoring** - real-time progress updates every 5 seconds
- **Zero audio gaps** - continuous capture while processing

**When to use:**
- Live conversations or interviews
- Real-time transcription needs
- When you need immediate feedback
- Practicing pronunciation with quick results

**Example session:**
```bash
$ python continuous_parallel_recorder.py

Speech detected (segment 1)
Saved segment 0 (3.2s)
Transcribing segment 0 (3.2s)...

Speech detected (segment 2)  
Saved segment 1 (2.8s)
Language: English (95% confidence)
Text: Direct action gets the goods, not voting.
Translation (Portuguese): A ação direta obtém resultados, não o voto.

Status - Recorded: 23 chunks | Processed: 23 | Detected: 2 | Transcribed: 1
```

### 3. CPU-Only Mode (`wsl_audio_recorder_cpu.py`)

**Perfect for:** Systems without GPU, quick testing, battery saving

**Features:**
- **0.5 second silence detection** - very responsive
- **Forced CPU processing** - even if GPU is available
- **Base model only** - optimized for CPU with int8 quantization
- **Lower memory usage** - good for resource-constrained systems
- **Fast startup** - smaller model loads quickly

**When to use:**
- GPU is not available or having issues
- Quick voice notes or testing
- Battery-powered devices
- When speed is more important than accuracy

## Audio Setup

All tools record from your **default microphone**:
- **WSL**: Usually `RDPSource` (Windows microphone passthrough)
- **Linux**: Usually `alsa_input.*.analog-stereo`

### Test Your Microphone
```bash
# Test recording
arecord -d 3 test.wav && aplay test.wav

# Check available sources
pactl list short sources

# Test with volume monitoring
arecord -vvv -f dat /dev/null
```

## Output Structure

Each tool creates organized output:

```
terminal/
├── recordings/                    # Individual audio segments
│   ├── sentence_1.wav
│   ├── sentence_2.wav
│   └── ...
├── transcripts/
│   └── transcript_1.txt          # Original language text with timestamps
├── translations/  
│   └── translation_1.txt         # Original + translated pairs
└── combined_recording_TIMESTAMP.wav  # Full session (created on exit)
```

### Example Files

**transcript_1.txt:**
```
[English] This is the first sentence I dictated.
[Portuguese] Esta é a segunda frase que eu ditei.
[English] Back to English for the third sentence.
```

**translation_1.txt:**
```
[English] This is the first sentence I dictated.
[Portuguese] Esta é a primeira frase que eu ditei.

[Portuguese] Esta é a segunda frase que eu ditei.
[English] This is the second sentence I dictated.

[English] Back to English for the third sentence.
[Portuguese] De volta ao inglês para a terceira frase.
```

## Configuration Options

### Adjust Silence Detection
```python
# Find this line in any script:
self.silence_threshold = 1.5  # seconds

# Modify for your needs:
self.silence_threshold = 0.8  # Faster response (may cut off sentences)
self.silence_threshold = 2.5  # Slower response (complete thoughts)
```

### Change Audio Buffer Settings
```python
# Pre-speech buffer (audio captured BEFORE speech detected)
self.pre_speech_buffer = deque(maxlen=int(sample_rate * 0.5))  # 0.5 seconds

# Post-speech padding (audio captured AFTER speech ends)  
self.post_speech_padding = 0.5  # seconds
```

### Model Selection
```python
# In GPU-enabled scripts
model_name = "large-v3"     # Highest accuracy, slower
model_name = "medium"       # Good balance
model_name = "base"         # Faster, lower accuracy
model_name = "tiny"         # Fastest, lowest accuracy

# In CPU script
model_name = "base"         # Recommended for CPU
```

### Language Pairs
```python
# Currently supports English ↔ Portuguese
# To add other languages, modify:
self.supported_languages = {
    'en': 'English', 
    'pt': 'Portuguese',
    'es': 'Spanish',     # Add Spanish
    'fr': 'French'       # Add French
}

# And update translation logic:
if lang in ['en', 'pt', 'es', 'fr']:
    # Your translation logic here
```

## Performance Benchmarks

### GPU Performance (NVIDIA RTX 3080)
| Model | Transcription Speed | Memory Usage | Accuracy |
|-------|-------------------|--------------|----------|
| tiny | ~0.5s per segment | 1GB | 85% |
| base | ~1.0s per segment | 1GB | 90% |
| medium | ~2.0s per segment | 2GB | 94% |
| large-v3 | ~3.0s per segment | 4GB | 97% |

### CPU Performance (Intel i7-10700K)
| Model | Transcription Speed | Memory Usage | Accuracy |
|-------|-------------------|--------------|----------|
| tiny | ~2s per segment | 0.5GB | 85% |
| base | ~5s per segment | 1GB | 90% |
| medium | ~15s per segment | 2GB | 94% |

### Real-World Usage
- **Dictation**: Complete sentences mode gives best results
- **Conversations**: Continuous mode provides immediate feedback
- **Note-taking**: CPU mode is fine for quick voice memos
- **Reading practice**: Complete sentences mode with large-v3 for accuracy

## Troubleshooting

### No Speech Detected
```bash
# Check microphone isn't muted
arecord -d 3 test.wav

# Adjust VAD sensitivity in code:
speech_timestamps = get_speech_timestamps(audio_tensor, self.model, threshold=0.3)  # Lower = more sensitive
```

### Sentences Cut Off Too Early
```bash
# Increase silence threshold:
self.silence_threshold = 2.0  # Wait 2 seconds instead of default

# Increase post-speech padding:
self.post_speech_padding = 1.0  # Capture 1 second after speech ends
```

### Slow Transcription
```bash
# Use smaller model:
model_name = "base"  # Instead of large-v3

# Or use CPU mode:
python wsl_audio_recorder_cpu.py

# Check GPU usage:
nvidia-smi  # Should show Python process using GPU
```

### Memory Issues
```bash
# Use smaller model:
model_name = "tiny"  # Uses less memory

# Or use CPU mode with int8:
compute_type="int8"  # Already set in CPU script
```

## Pro Tips

### For Maximum Accuracy
1. Use GPU mode with large-v3 model
2. Speak clearly with minimal background noise
3. Use complete sentences mode for important content
4. Test your setup before long sessions

### For Speed
1. Use continuous parallel mode for real-time feedback
2. Reduce silence threshold for faster response
3. Use smaller models (base instead of large-v3)

## Advanced Usage

### Pipe to Other Programs
```bash
# Watch transcriptions in real-time
python wsl_audio_recorder.py &
tail -f transcripts/transcript_*.txt

# Count words transcribed
python continuous_parallel_recorder.py | grep "Text:" | wc -l
```

### Custom Post-Processing
```python
# Add custom processing in transcribe_audio_file method
def transcribe_audio_file(self, audio_file):
    # ... existing code ...
    
    # Custom processing
    if transcript.strip():
        # Save to custom format
        self.save_to_json(transcript, lang, translation)
        
        # Send to external service
        self.post_to_webhook(transcript)
```

### Integration Examples
```python
# Send transcriptions to Signal for secure organizing
import requests
requests.post('https://signal-webhook...', json={'text': transcript})

# Save to encrypted database away from surveillance
import sqlite3
conn.execute("INSERT INTO manifestos VALUES (?, ?, ?)", 
             (timestamp, transcript, translation))
```

## Privacy

- **100% Local Processing** - everything runs on your machine
- **No Cloud Dependencies** - except Google Translate (optional)
- **File Permissions** - transcripts saved with user-only access
- **Audio Cleanup** - individual segments deleted after combining
- **No Telemetry** - no usage data collected or sent

## Choosing the Right Tool

### Decision Tree

```
Do you have a GPU?
├─ No → wsl_audio_recorder_cpu.py
└─ Yes
   ├─ Need real-time feedback? → continuous_parallel_recorder.py  
   └─ Want complete sentences? → wsl_audio_recorder.py
```

**Note:** Your first run will download the Whisper model (~1.5GB for large-v3), so have a good internet connection ready.