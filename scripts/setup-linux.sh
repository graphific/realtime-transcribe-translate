#!/bin/bash
# Meeting Transcriber Linux Setup Script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions for colored output
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_info() { echo -e "${BLUE}→ $1${NC}"; }
print_warning() { echo -e "${YELLOW}! $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                 Meeting Transcriber Setup                      ║
║                     Linux Edition                              ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    print_error "Cannot detect Linux distribution"
    exit 1
fi

print_info "Detected: $OS $VER"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   print_warning "Running as root. Some operations may require sudo later."
fi

# Check system requirements
print_info "Checking system requirements..."

# Check RAM
total_ram=$(free -g | awk '/^Mem:/{print $2}')
if [ "$total_ram" -lt 8 ]; then
    print_warning "System has ${total_ram}GB RAM. 8GB+ recommended for best performance"
else
    print_success "RAM: ${total_ram}GB"
fi

# Check disk space
free_space=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$free_space" -lt 20 ]; then
    print_error "Insufficient disk space. At least 20GB required, only ${free_space}GB available"
    exit 1
fi
print_success "Disk space: ${free_space}GB available"

# Check for Docker
print_info "Checking Docker installation..."

install_docker() {
    print_info "Installing Docker..."
    
    # Remove old versions
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Install prerequisites
    sudo apt-get update
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Set up stable repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    
    print_success "Docker installed successfully"
    print_warning "You need to log out and back in for group changes to take effect"
}

if command -v docker &> /dev/null; then
    docker_version=$(docker --version)
    print_success "Docker installed: $docker_version"
    
    # Check if Docker daemon is running
    if ! docker ps &> /dev/null; then
        print_warning "Docker is installed but not running"
        sudo systemctl start docker
        sudo systemctl enable docker
        print_success "Docker service started"
    fi
    
    # Check if user is in docker group
    if ! groups | grep -q docker; then
        print_warning "User not in docker group. Adding..."
        sudo usermod -aG docker $USER
        print_warning "You'll need to log out and back in for this to take effect"
    fi
else
    print_warning "Docker not found"
    read -p "Install Docker? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        install_docker
    else
        print_error "Docker is required. Please install manually."
        exit 1
    fi
fi

# Check for Docker Compose
print_info "Checking Docker Compose..."
if command -v docker-compose &> /dev/null; then
    compose_version=$(docker-compose --version)
    print_success "Docker Compose installed: $compose_version"
elif docker compose version &> /dev/null; then
    compose_version=$(docker compose version)
    print_success "Docker Compose (plugin) installed: $compose_version"
else
    print_error "Docker Compose not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

# Check for Git
print_info "Checking Git..."
if ! command -v git &> /dev/null; then
    print_warning "Git not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y git
fi
print_success "Git installed"

# Check for Python (for audio clients)
print_info "Checking Python..."
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version)
    print_success "Python installed: $python_version"
else
    print_warning "Python3 not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
fi

# Create project directories
print_info "Creating project structure..."

directories=(
    "data/recordings"
    "data/transcripts"
    "data/translations"
    "models/whisper"
    "models/huggingface"
    "models/torch"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "Created $dir"
    fi
done

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "Created .env from .env.example"
        print_info "Please review and customize .env file"
    else
        print_warning ".env.example not found. Creating basic .env"
        cat > .env << 'EOL'
# Basic configuration
WHISPER_MODEL=base
LIBRETRANSLATE_LANGS=en,pt,es
WEB_UI_PORT=8080
API_PORT=8000
WEBSOCKET_PORT=8765
EOL
    fi
fi

# Audio setup
print_info "Setting up audio capture..."

# Check PulseAudio
if command -v pactl &> /dev/null; then
    print_success "PulseAudio installed"
    
    # Check if PulseAudio is running
    if pactl info &> /dev/null; then
        print_success "PulseAudio is running"
        
        # Enable network streaming
        print_info "Configuring PulseAudio for network streaming..."
        
        # Check if TCP module is loaded
        if ! pactl list modules short | grep -q module-native-protocol-tcp; then
            pactl load-module module-native-protocol-tcp port=4713 auth-anonymous=1
            print_success "Enabled PulseAudio TCP streaming"
            
            # Make it permanent
            if [ -f /etc/pulse/default.pa ]; then
                if ! grep -q "module-native-protocol-tcp" /etc/pulse/default.pa; then
                    echo "load-module module-native-protocol-tcp port=4713 auth-anonymous=1" | sudo tee -a /etc/pulse/default.pa > /dev/null
                    print_success "Made PulseAudio TCP streaming permanent"
                fi
            fi
        else
            print_success "PulseAudio TCP streaming already enabled"
        fi
    else
        print_warning "PulseAudio installed but not running"
        systemctl --user start pulseaudio
    fi
else
    print_warning "PulseAudio not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y pulseaudio pulseaudio-utils
fi

# NVIDIA GPU setup (optional)
print_info "Checking for NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    print_success "NVIDIA drivers detected"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    
    # Check for NVIDIA Container Toolkit
    if ! command -v nvidia-container-cli &> /dev/null; then
        print_warning "NVIDIA Container Toolkit not found"
        read -p "Install NVIDIA Container Toolkit for GPU support? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            print_info "Installing NVIDIA Container Toolkit..."
            
            distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
            curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
            curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
            
            sudo apt-get update
            sudo apt-get install -y nvidia-container-toolkit
            sudo systemctl restart docker
            
            print_success "NVIDIA Container Toolkit installed"
        fi
    else
        print_success "NVIDIA Container Toolkit installed"
    fi
    
    # Test GPU in Docker
    print_info "Testing GPU in Docker..."
    if docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        print_success "GPU working in Docker"
    else
        print_warning "GPU test failed. GPU acceleration may not work."
    fi
else
    print_info "No NVIDIA GPU detected. System will use CPU for transcription."
fi

# Create convenience scripts
print_info "Creating convenience scripts..."

# Start script
cat > start-transcriber.sh << 'EOL'
#!/bin/bash
echo "Starting Meeting Transcriber..."
docker-compose -f docker/docker-compose.yml up -d

echo
echo "Waiting for services to start..."
sleep 5

echo
echo "Meeting Transcriber is ready!"
echo
echo "Web UI: http://localhost:8080"
echo "API: http://localhost:8000"
echo
echo "To stop, run: ./stop-transcriber.sh"
EOL
chmod +x start-transcriber.sh

# Stop script
cat > stop-transcriber.sh << 'EOL'
#!/bin/bash
echo "Stopping Meeting Transcriber..."
docker-compose -f docker/docker-compose.yml down
echo
echo "Services stopped."
EOL
chmod +x stop-transcriber.sh

# Logs script
cat > view-logs.sh << 'EOL'
#!/bin/bash
echo "Meeting Transcriber Logs (Ctrl+C to exit)"
echo "========================================"
docker-compose -f docker/docker-compose.yml logs -f
EOL
chmod +x view-logs.sh

# Audio client setup script
cat > setup-audio-client.sh << 'EOL'
#!/bin/bash
echo "Setting up Python audio client environment..."

# Create virtual environment
python3 -m venv venv

# Activate and install requirements
source venv/bin/activate
pip install --upgrade pip
pip install pyaudiowpatch numpy websockets asyncio

echo
echo "Audio client environment ready!"
echo "To use: source venv/bin/activate"
echo "Then: python src/clients/linux_audio_client.py"
EOL
chmod +x setup-audio-client.sh

print_success "Created convenience scripts"

# Final summary
echo
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Setup Complete! 🎉                          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"

echo
print_info "Next steps:"
echo "1. Start the system: ${GREEN}./start-transcriber.sh${NC}"
echo "2. Open web interface: ${GREEN}http://localhost:8080${NC}"
echo "3. For audio capture:"
echo "   - System audio is captured via PulseAudio (already configured)"
echo "   - For advanced setup, see: ${GREEN}docs/USAGE.md${NC}"
echo
echo "4. Install browser extension:"
echo "   - Open Firefox"
echo "   - Go to about:debugging"
echo "   - Load src/extensions/firefox/manifest.json"
echo
echo "For help, see: ${GREEN}docs/USAGE.md${NC}"

# Test if we can use Docker without sudo
if ! docker ps &> /dev/null; then
    echo
    print_warning "IMPORTANT: You need to log out and back in for Docker group changes to take effect!"
    print_warning "After logging back in, run: ./start-transcriber.sh"
else
    # Prompt to start now
    echo
    read -p "Start Meeting Transcriber now? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_info "Starting services..."
        ./start-transcriber.sh
        
        print_info "Opening web interface..."
        if command -v xdg-open &> /dev/null; then
            xdg-open http://localhost:8080
        elif command -v open &> /dev/null; then
            open http://localhost:8080
        else
            print_info "Please open http://localhost:8080 in your browser"
        fi
    fi
fi

print_success "Setup completed successfully!"