#!/bin/bash

# Setup script for system audio capture
# This configures PulseAudio for recording all system audio

echo "🎧 System Audio Capture Setup"
echo "============================"
echo ""

# Function to print colored output
print_status() {
    echo -e "\033[0;32m[✓]\033[0m $1"
}

print_error() {
    echo -e "\033[0;31m[✗]\033[0m $1"
}

print_info() {
    echo -e "\033[0;34m[i]\033[0m $1"
}

# Check if PulseAudio is running
if ! pactl info &> /dev/null; then
    print_error "PulseAudio is not running!"
    exit 1
fi

print_status "PulseAudio is running"

# List current audio sources
echo ""
echo "Current Audio Sources:"
echo "====================="
pactl list short sources | nl -v 0

# Find monitor sources
echo ""
echo "Available Monitor Sources (for recording system audio):"
echo "====================================================="
MONITORS=$(pactl list short sources | grep '\.monitor' | cut -f2)

if [ -z "$MONITORS" ]; then
    print_error "No monitor sources found!"
    echo ""
    echo "Creating a virtual audio setup..."
    
    # Create virtual sink
    SINK_ID=$(pactl load-module module-null-sink sink_name=meeting_recorder sink_properties=device.description="Meeting_Recorder")
    print_status "Created virtual sink: meeting_recorder (ID: $SINK_ID)"
    
    # Create loopback
    LOOPBACK_ID=$(pactl load-module module-loopback source=meeting_recorder.monitor)
    print_status "Created loopback (ID: $LOOPBACK_ID)"
    
    MONITOR_SOURCE="meeting_recorder.monitor"
else
    echo "$MONITORS" | nl -v 1
    MONITOR_SOURCE=$(echo "$MONITORS" | head -n1)
fi

echo ""
print_info "Selected monitor source: $MONITOR_SOURCE"

# Test recording
echo ""
echo "Testing audio capture..."
echo "========================"
print_info "Recording 3 seconds of system audio..."

if parec --device="$MONITOR_SOURCE" --rate=16000 --channels=1 --format=s16le -d 3 > test_audio.raw 2>/dev/null; then
    SIZE=$(stat -c%s test_audio.raw 2>/dev/null || stat -f%z test_audio.raw 2>/dev/null)
    if [ "$SIZE" -gt 1000 ]; then
        print_status "Audio capture successful! (Recorded $SIZE bytes)"
        rm test_audio.raw
    else
        print_error "Audio captured but file is too small"
    fi
else
    print_error "Audio capture failed"
fi

# Create configuration file
echo ""
echo "Creating configuration file..."
cat > audio_config.py << EOF
# Auto-generated audio configuration
MONITOR_SOURCE = "$MONITOR_SOURCE"
SAMPLE_RATE = 16000

print(f"Using monitor source: {MONITOR_SOURCE}")
EOF

print_status "Configuration saved to audio_config.py"

# Show instructions
echo ""
echo "Setup Instructions for Meetings:"
echo "==============================="
echo ""
echo "Option 1 - Capture Everything (Recommended):"
echo "  1. Join your meeting normally"
echo "  2. Run: python system_audio_recorder.py"
echo "  3. All audio will be captured and transcribed"
echo ""
echo "Option 2 - Selective Capture:"
echo "  1. Set meeting audio output to 'Meeting_Recorder'"
echo "  2. You'll still hear audio normally"
echo "  3. Only meeting audio is transcribed"
echo ""
echo "Option 3 - Windows Audio Loopback (WSL2):"
echo "  1. Use Windows 'Stereo Mix' if available"
echo "  2. Or use VB-Audio Virtual Cable"
echo "  3. Route audio through virtual device"
echo ""
echo "To make setup permanent, add to ~/.bashrc:"
echo "  export PULSE_MONITOR='$MONITOR_SOURCE'"
echo ""

# Create quick launcher
cat > start_meeting_recorder.sh << 'EOF'
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
EOF

chmod +x start_meeting_recorder.sh
print_status "Created launcher: start_meeting_recorder.sh"

echo ""
print_status "Setup complete!"
echo ""
echo "To start recording meetings:"
echo "  ./start_meeting_recorder.sh"