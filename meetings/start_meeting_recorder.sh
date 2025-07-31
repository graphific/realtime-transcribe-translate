#!/bin/bash
echo "🎤 Starting Meeting Recorder..."
echo "This will capture ALL system audio including:"
echo "  - Your voice (if unmuted)"
echo "  - Other participants"
echo "  - System sounds"
echo ""
read -p "Press Enter to start recording..."

# Activate conda environment if needed
if command -v conda &> /dev/null; then
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate audio
fi

# Set library path for GPU
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib/python3.10/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH

# Run the recorder
python system_audio_recorder.py
