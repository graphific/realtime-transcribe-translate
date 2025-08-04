# Meeting Transcriber Windows Setup Script
# Requires PowerShell 5.0+ and Administrator privileges

param(
    [switch]$SkipDocker,
    [switch]$SkipAudio,
    [switch]$Unattended
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

# Check if running as Administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Banner
Write-Host @"
╔═══════════════════════════════════════════════════════════════╗
║                 Meeting Transcriber Setup                      ║
║                    Windows Edition                             ║
╚═══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

# Check Administrator
if (-not (Test-Administrator)) {
    Write-Error "This script must be run as Administrator!"
    Write-Host "Please right-click and select 'Run as Administrator'"
    exit 1
}

Write-Success "✓ Running as Administrator"

# Check System Requirements
Write-Info "`nChecking system requirements..."

# Check Windows Version
$winVer = [System.Environment]::OSVersion.Version
if ($winVer.Major -lt 10) {
    Write-Error "Windows 10 or later is required"
    exit 1
}
Write-Success "✓ Windows version: $($winVer.Major).$($winVer.Minor)"

# Check available RAM
$totalRAM = (Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property capacity -Sum).sum /1gb
if ($totalRAM -lt 8) {
    Write-Warning "! System has ${totalRAM}GB RAM. 8GB+ recommended for best performance"
} else {
    Write-Success "✓ RAM: ${totalRAM}GB"
}

# Check available disk space
$drive = Get-PSDrive C
$freeSpace = [math]::Round($drive.Free / 1GB, 2)
if ($freeSpace -lt 20) {
    Write-Error "Insufficient disk space. At least 20GB required, only ${freeSpace}GB available"
    exit 1
}
Write-Success "✓ Disk space: ${freeSpace}GB available"

# Check for Docker Desktop
if (-not $SkipDocker) {
    Write-Info "`nChecking Docker Desktop..."
    
    $dockerInstalled = $false
    try {
        $dockerVersion = docker --version 2>$null
        if ($dockerVersion) {
            Write-Success "✓ Docker Desktop installed: $dockerVersion"
            $dockerInstalled = $true
            
            # Check if Docker is running
            try {
                docker ps 2>$null | Out-Null
                Write-Success "✓ Docker Desktop is running"
            } catch {
                Write-Warning "! Docker Desktop is installed but not running"
                
                if (-not $Unattended) {
                    $response = Read-Host "Start Docker Desktop? (Y/n)"
                    if ($response -ne 'n') {
                        Write-Info "Starting Docker Desktop..."
                        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -WindowStyle Hidden
                        
                        # Wait for Docker to start
                        Write-Info "Waiting for Docker to start (this may take a minute)..."
                        $timeout = 120
                        $elapsed = 0
                        while ($elapsed -lt $timeout) {
                            try {
                                docker ps 2>$null | Out-Null
                                Write-Success "✓ Docker Desktop started"
                                break
                            } catch {
                                Start-Sleep -Seconds 5
                                $elapsed += 5
                                Write-Host "." -NoNewline
                            }
                        }
                        Write-Host ""
                    }
                }
            }
        }
    } catch {
        Write-Warning "! Docker Desktop not found"
    }
    
    if (-not $dockerInstalled) {
        Write-Warning "Docker Desktop is required but not installed"
        
        if (-not $Unattended) {
            $response = Read-Host "Download and install Docker Desktop? (Y/n)"
            if ($response -ne 'n') {
                Write-Info "Downloading Docker Desktop..."
                $dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
                $dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"
                
                try {
                    Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller
                    Write-Success "✓ Downloaded Docker Desktop installer"
                    
                    Write-Info "Installing Docker Desktop (this will take several minutes)..."
                    Start-Process -FilePath $dockerInstaller -ArgumentList "install", "--quiet" -Wait
                    
                    Write-Success "✓ Docker Desktop installed"
                    Write-Warning "! System restart required. Please restart and run this script again."
                    exit 0
                } catch {
                    Write-Error "Failed to install Docker Desktop: $_"
                    Write-Host "Please install Docker Desktop manually from: https://www.docker.com/products/docker-desktop/"
                    exit 1
                }
            }
        } else {
            Write-Error "Docker Desktop is required. Please install from: https://www.docker.com/products/docker-desktop/"
            exit 1
        }
    }
}

# Check for WSL2 (required for Docker)
Write-Info "`nChecking WSL2..."
try {
    $wslVersion = wsl --list --verbose 2>$null
    if ($wslVersion) {
        Write-Success "✓ WSL2 is installed"
    }
} catch {
    Write-Warning "! WSL2 not detected. Docker Desktop requires WSL2."
    
    if (-not $Unattended) {
        $response = Read-Host "Enable WSL2? (Y/n)"
        if ($response -ne 'n') {
            Write-Info "Enabling WSL2..."
            dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
            dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
            
            Write-Success "✓ WSL2 enabled"
            Write-Warning "! System restart required. Please restart and run this script again."
            exit 0
        }
    }
}

# Create project directories
Write-Info "`nCreating project structure..."

$directories = @(
    "data\recordings",
    "data\transcripts", 
    "data\translations",
    "models\whisper",
    "models\huggingface",
    "models\torch"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Success "✓ Created $dir"
    }
}

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Success "✓ Created .env from .env.example"
        
        # Update .env with Windows-specific settings
        $envContent = Get-Content ".env"
        $envContent = $envContent -replace "WHISPER_MODEL=.*", "WHISPER_MODEL=base"
        $envContent | Set-Content ".env"
        
        Write-Info "! Please review and customize .env file"
    } else {
        Write-Warning "! .env.example not found. Creating basic .env"
        @"
# Basic configuration
WHISPER_MODEL=base
LIBRETRANSLATE_LANGS=en,pt,es
WEB_UI_PORT=8080
API_PORT=8000
WEBSOCKET_PORT=8765
"@ | Set-Content ".env"
    }
}

# Audio setup
if (-not $SkipAudio) {
    Write-Info "`nSetting up audio capture options..."
    
    # Option 1: Check for VoiceMeeter
    $voiceMeeterPath = "${env:ProgramFiles(x86)}\VB\Voicemeeter"
    if (Test-Path $voiceMeeterPath) {
        Write-Success "✓ VoiceMeeter detected"
    } else {
        Write-Info "VoiceMeeter not found (recommended for professional audio routing)"
        
        if (-not $Unattended) {
            $response = Read-Host "Open VoiceMeeter download page? (y/N)"
            if ($response -eq 'y') {
                Start-Process "https://vb-audio.com/Voicemeeter/"
            }
        }
    }
    
    # Option 2: Set up PulseAudio
    Write-Info "`nSetting up PulseAudio for Windows..."
    
    $pulseDir = "C:\PulseAudio"
    if (-not (Test-Path $pulseDir)) {
        $pulseUrl = "https://github.com/pgaskin/pulseaudio-win32/releases/download/v13.0/pulseaudio-13.0-x64.zip"
        $pulseZip = "$env:TEMP\pulseaudio.zip"
        
        try {
            Write-Info "Downloading PulseAudio..."
            Invoke-WebRequest -Uri $pulseUrl -OutFile $pulseZip
            
            Write-Info "Extracting PulseAudio..."
            Expand-Archive -Path $pulseZip -DestinationPath $pulseDir -Force
            Remove-Item $pulseZip
            
            # Create config
            $configContent = @"
# PulseAudio configuration for Docker
load-module module-native-protocol-tcp port=4713 auth-anonymous=1
load-module module-esound-protocol-tcp port=4714 auth-anonymous=1
load-module module-waveout sink_name=output source_name=input record=0
set-default-sink output
set-default-source input
"@
            $configContent | Set-Content "$pulseDir\config.pa"
            
            # Create start script
            @"
@echo off
cd /d C:\PulseAudio\bin
echo Starting PulseAudio server...
echo This window must stay open while using Meeting Transcriber
echo.
pulseaudio.exe -F ..\config.pa
"@ | Set-Content "$pulseDir\start-pulseaudio.bat"
            
            Write-Success "✓ PulseAudio configured"
            
            # Create desktop shortcut
            $shell = New-Object -ComObject WScript.Shell
            $shortcut = $shell.CreateShortcut("$env:USERPROFILE\Desktop\Start PulseAudio.lnk")
            $shortcut.TargetPath = "$pulseDir\start-pulseaudio.bat"
            $shortcut.WorkingDirectory = "$pulseDir\bin"
            $shortcut.IconLocation = "mmsys.cpl,3"
            $shortcut.Save()
            
            Write-Success "✓ Created desktop shortcut for PulseAudio"
            
        } catch {
            Write-Warning "Failed to set up PulseAudio: $_"
        }
    } else {
        Write-Success "✓ PulseAudio already installed"
    }
    
    # Option 3: Windows Audio Bridge
    Write-Info "`nSetting up Windows Audio Bridge..."
    
    $audioClientPath = "src\clients\windows_audio_client.py"
    if (Test-Path $audioClientPath) {
        Write-Success "✓ Windows Audio Bridge scripts found"
        
        # Create batch file for easy launching
        @"
@echo off
echo Starting Windows Audio Bridge...
cd /d "%~dp0"
python src\clients\windows_audio_client.py
pause
"@ | Set-Content "StartAudioBridge.bat"
        
        Write-Success "✓ Created StartAudioBridge.bat"
    } else {
        Write-Warning "! Windows Audio Bridge scripts not found in expected location"
    }
}

# Create convenience scripts
Write-Info "`nCreating convenience scripts..."

# Start script
@"
@echo off
echo Starting Meeting Transcriber...
docker-compose -f docker\docker-compose.yml up -d
echo.
echo Services starting...
timeout /t 5 /nobreak > nul
echo.
echo Meeting Transcriber is ready!
echo.
echo Web UI: http://localhost:8080
echo API: http://localhost:8000
echo.
echo To stop, run: StopTranscriber.bat
"@ | Set-Content "StartTranscriber.bat"

# Stop script
@"
@echo off
echo Stopping Meeting Transcriber...
docker-compose -f docker\docker-compose.yml down
echo.
echo Services stopped.
"@ | Set-Content "StopTranscriber.bat"

# View logs script
@"
@echo off
echo Meeting Transcriber Logs (Ctrl+C to exit)
echo ========================================
docker-compose -f docker\docker-compose.yml logs -f
"@ | Set-Content "ViewLogs.bat"

Write-Success "✓ Created convenience scripts"

# Final summary
Write-Host "`n" -NoNewline
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    Setup Complete! 🎉                          ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Info "`nNext steps:"
Write-Host "1. Start the system: " -NoNewline
Write-Success ".\StartTranscriber.bat"

Write-Host "2. Open web interface: " -NoNewline
Write-Success "http://localhost:8080"

Write-Host "3. For audio capture, choose one:"
Write-Host "   - Run " -NoNewline
Write-Success ".\StartAudioBridge.bat" -NoNewline
Write-Host " (easiest)"
Write-Host "   - Start " -NoNewline
Write-Success "C:\PulseAudio\start-pulseaudio.bat" -NoNewline
Write-Host " (cross-platform)"
Write-Host "   - Use " -NoNewline
Write-Success "VoiceMeeter" -NoNewline
Write-Host " (professional)"

Write-Host "`n4. Install browser extension:"
Write-Host "   - Open Firefox"
Write-Host "   - Go to about:debugging"
Write-Host "   - Load src\extensions\firefox\manifest.json"

Write-Host "`nFor help, see: " -NoNewline
Write-Success "docs\USAGE.md"

# Prompt to start now
if (-not $Unattended) {
    Write-Host "`n"
    $response = Read-Host "Start Meeting Transcriber now? (Y/n)"
    if ($response -ne 'n') {
        Write-Info "Starting services..."
        Start-Process -FilePath ".\StartTranscriber.bat" -WindowStyle Hidden
        
        Write-Info "Waiting for services to start..."
        Start-Sleep -Seconds 10
        
        Write-Success "Opening web interface..."
        Start-Process "http://localhost:8080"
    }
}

Write-Host "`nSetup completed successfully!" -ForegroundColor Green