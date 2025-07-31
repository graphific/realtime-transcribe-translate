## Key Features in Latest Versions

### All Scripts Include:
- ✅ cuDNN fix: `os.environ['CUDNN_FRONTEND_ENABLED'] = '0'`
- ✅ Automatic language detection (English/Portuguese)
- ✅ Bidirectional translation
- ✅ Audio file combination on exit
- ✅ Separate transcript and translation files

### GPU Version Features (`wsl_audio_recorder.py`):
- Automatic GPU/CPU detection and fallback
- Thread-safe file writing
- Queue-based audio processing for no data loss
- VAD filter parameters for better accuracy
- Pre-speech buffer (0.5s) and post-speech padding

### Continuous Version Features (`continuous_parallel_recorder.py`):
- Thread pool executor for parallel transcription
- Real-time status monitoring
- Continuous recording with zero gaps
- Automatic segment management
- Single process with multiple threads (avoids multiprocessing issues)# Real-Time Bilingual Speech Transcription on WSL2

A real-time speech recognition system that automatically detects English/Portuguese and translates between them.

## Features
- Real-time speech detection and recording
- Automatic language detection (English/Portuguese)
- Bidirectional translation
- Saves transcripts and translations
- Voice Activity Detection (VAD) for automatic sentence segmentation

## Prerequisites

### System Requirements
- Windows 10/11 with WSL2
- WSLg (for audio support)
- NVIDIA GPU (optional, for faster transcription)

### Check WSL Audio Support
```bash
# Check if PulseAudio is working
pactl info

# You should see:
# Server Name: pulseaudio
# Default Source: RDPSource
```

## Installation

### 1. Create Conda Environment
```bash
conda create -n audio python=3.10
conda activate audio
```

### 2. Install System Dependencies
```bash
# Install audio tools
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio
sudo apt-get install alsa-utils

# Install ffmpeg for audio processing
sudo apt-get install ffmpeg
```

### 3. Install Python Packages

#### For GPU Support (Recommended)
```bash
# Install PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install cuDNN 9 for faster-whisper
pip install nvidia-cudnn-cu12==9.1.0.70

# Install other dependencies
pip install numpy silero-vad faster-whisper pydub googletrans==4.0.0-rc1
conda install -c conda-forge python-sounddevice
```

#### For CPU Only
```bash
# Install PyTorch CPU version
pip install torch torchvision torchaudio

# Install other dependencies
pip install numpy silero-vad faster-whisper pydub googletrans==4.0.0-rc1
conda install -c conda-forge python-sounddevice
```

### 4. Set Library Paths for GPU Mode
```bash
# Add to your ~/.bashrc or create a launcher script
export LD_LIBRARY_PATH=/home/$USER/miniconda3/envs/audio/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH
```

## Common Issues and Solutions

### Issue 1: PortAudio Library Not Found
```bash
# Install PortAudio
sudo apt-get install portaudio19-dev
```

### Issue 2: ALSA/Audio Not Working in Conda
```bash
# Remove conda's ALSA if it conflicts
rm -rf /home/$USER/miniconda3/envs/audio/lib/alsa-lib
conda uninstall alsa-lib -y

# Test audio
arecord -d 2 -f cd test.wav
```

### Issue 3: libstdc++ Version Mismatch
```bash
# Update libstdc++ in conda environment
conda install -c conda-forge libstdcxx-ng
```

### Issue 4: Sounddevice Returns Empty Device List
This is a known WSL issue. The workaround is to use `arecord` directly (implemented in the scripts).

### Issue 5: cuDNN Errors with GPU
```bash
# Install cuDNN 9 (required for faster-whisper)
pip install nvidia-cudnn-cu12==9.1.0.70

# Set library path before running
export LD_LIBRARY_PATH=/home/$USER/miniconda3/envs/audio/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH

# Note: This may show a pip warning about torch requiring cudnn 8.9.2.26, but it works fine
```

## Usage

### Run the Transcriber

#### Option 1: Direct Run (after setting library paths)
```bash
export LD_LIBRARY_PATH=/home/$USER/miniconda3/envs/audio/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH
python wsl_audio_recorder.py
```

#### Option 2: Create a Launcher Script (Recommended)
```bash
# Create launcher script
cat > run_transcriber.sh << 'EOF'
#!/bin/bash
conda activate audio
export LD_LIBRARY_PATH=/home/$USER/miniconda3/envs/audio/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH
python wsl_audio_recorder.py
EOF

chmod +x run_transcriber.sh
./run_transcriber.sh
```

### Controls
- Speak naturally - the system detects speech automatically
- Pause briefly between sentences
- Press `Ctrl+C` to stop and save combined recording

### Output Files
- `transcripts/transcript_N.txt` - Original language transcriptions
- `translations/translation_N.txt` - Translated text
- `recordings/` - Individual sentence audio files
- `combined_recording_TIMESTAMP.wav` - Combined audio after exit

## Script Versions

### 1. `wsl_audio_recorder.py` (Main Version - Best for Complete Sentences)
- Uses GPU if available (large-v3 model) with automatic CPU fallback
- 1.5 second silence detection for natural speech boundaries
- Includes pre/post speech buffering for complete capture
- Best accuracy for sentence-level transcription
- Non-blocking transcription with thread safety
- **Use when**: You want complete, well-formed sentences

### 2. `continuous_parallel_recorder.py` (Continuous Real-time Version)
- Threaded architecture for continuous capture
- 1.2 second silence detection for faster response
- Processes segments in parallel using thread pool
- Shows real-time status updates
- Never misses audio, even during processing
- **Use when**: You need real-time transcription with minimal delay

### 3. `wsl_audio_recorder_cpu.py` (CPU-Only Version)
- Forces CPU mode with base model
- 0.5 second silence detection for quick response
- Optimized for systems without GPU
- Lower accuracy but faster processing
- **Use when**: GPU is not available or having issues

## Comparison of Results

### Continuous Version (`threaded_continuous_recorder.py`)
- **Pros**: Real-time feedback, never misses audio, parallel processing
- **Cons**: May split sentences unnaturally
- **Output**: Multiple smaller segments
```
Segment 1: Pode comprar em milhares de lojas online.
Segment 2: Mesmo sem saldo no Paypal
Segment 3: Nossa proteção ao comprador.
```

### Main Version (`wsl_audio_recorder.py`)
- **Pros**: Natural sentence boundaries, complete thoughts
- **Cons**: 1.5 second wait time, may miss rapid speech
- **Output**: Complete sentences
```
em milhares de lojas online mesmo sem saldo no Paypal nossa proteção 
ao comprador pode ajudá-lo a comprar com segurança em todo o mundo...
```

## Testing Audio

### Test Recording
```bash
# Test with arecord
arecord -d 3 -f cd test.wav
aplay test.wav

# Check audio levels
arecord -vvv -f dat /dev/null
```

### Test Python Audio
```python
# Test sounddevice
python -c "import sounddevice as sd; print(sd.query_devices())"

# Test PyTorch CUDA
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

## Which Version to Use?

### For Reading/Dictation (Complete Sentences)
Use **`wsl_audio_recorder.py`** - Waits for natural pauses, captures complete thoughts

### For Conversations/Real-time Feedback  
Use **`continuous_parallel_recorder.py`** - Immediate feedback, continuous processing

### For Systems Without GPU
Use **`wsl_audio_recorder_cpu.py`** - CPU-optimized version

## Performance Tips

### For Best Quality
- Use GPU mode with large-v3 model
- Ensure CUDA is properly installed
- Speak clearly with minimal background noise
- Use `wsl_audio_recorder.py` for complete sentences

### For Fastest Response
- Use `threaded_continuous_recorder.py`
- Reduce silence threshold if needed
- Use smaller audio chunks

### For Continuous Text Reading
- Use `threaded_continuous_recorder.py` for no gaps
- Or use `wsl_audio_recorder.py` with natural pauses between sentences

## Troubleshooting Checklist

1. ✅ Audio recording works: `arecord -d 2 test.wav`
2. ✅ Conda environment activated: `conda activate audio`
3. ✅ No ALSA conflicts: Remove conda's ALSA if needed
4. ✅ PyTorch installed: `python -c "import torch"`
5. ✅ CUDA available (optional): `nvidia-smi` shows GPU
6. ✅ cuDNN library path set: Export LD_LIBRARY_PATH before running

## Working Configuration Summary

This setup has been tested and confirmed working on:
- WSL2 with Ubuntu
- NVIDIA GPU with CUDA 12.0
- PyTorch 2.2.0 with CUDA 12.1
- cuDNN 9.1.0.70
- Whisper large-v3 model with GPU acceleration
- Real-time continuous recording with threading

The key fixes that made everything work:
1. Installing cuDNN 9 via pip: `pip install nvidia-cudnn-cu12==9.1.0.70`
2. Setting library path: `export LD_LIBRARY_PATH=/path/to/nvidia/cudnn/lib:$LD_LIBRARY_PATH`
3. Removing conda's ALSA: `rm -rf ~/miniconda3/envs/audio/lib/alsa-lib`
4. Using threading instead of multiprocessing for reliability
5. Adding `CUDNN_FRONTEND_ENABLED='0'` to handle cuDNN issues

## Quick Start Guide

```bash
# For complete sentence transcription (recommended for most uses)
export LD_LIBRARY_PATH=/home/$USER/miniconda3/envs/audio/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH
python wsl_audio_recorder.py

# For real-time continuous transcription
export LD_LIBRARY_PATH=/home/$USER/miniconda3/envs/audio/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH
python threaded_continuous_recorder.py

# For CPU-only systems
python wsl_audio_recorder_cpu.py
```

## Technical Details

### Audio Flow
1. `arecord` → Continuous raw audio stream
2. Silero VAD → Speech detection
3. Buffer → Accumulate speech segments
4. Whisper → Transcription
5. Google Translate → Translation

### Models Used
- **VAD**: Silero Voice Activity Detection
- **ASR**: OpenAI Whisper (large-v3 or base)
- **Translation**: Google Translate API

## License
MIT License - Feel free to modify and use!

## Acknowledgments
- OpenAI Whisper for speech recognition
- Silero team for VAD model
- Google Translate for translation services