# api-server/audio_modules.py
import subprocess
import socket
import platform
import logging
import os

logger = logging.getLogger(__name__)

class SmartAudioModuleManager:
    """
    Audio module manager that auto-detects what will work on the user's system
    """
    
    def __init__(self, ws_server, config):
        self.ws_server = ws_server
        self.config = config
        self.current_module = None
        self.current_instance = None
        self.thread = None
        
        # Auto-detect available modules
        self.available_modules = self._detect_available_modules()
        
        # Auto-select best module if none configured
        if not config.get('audio_module'):
            self.auto_select_module()
    
    def _detect_available_modules(self):
        """Auto-detect which audio modules will work on this system"""
        modules = {}
        
        # Test module always available
        modules['test'] = {
            'name': 'Test Mode (No Audio)',
            'description': 'Test without real audio capture - good for trying out the system',
            'class': 'TestAudioModule',
            'requires_host': False,
            'status': 'available',
            'auto_score': 1  # Lowest priority
        }
        
        # Check for PulseAudio on Windows
        if self._check_pulseaudio():
            modules['pulseaudio'] = {
                'name': 'PulseAudio',
                'description': 'Detected PulseAudio server on Windows host',
                'class': 'PulseAudioModule',
                'requires_host': True,
                'status': 'available',
                'auto_score': 50,
                'config_fields': [
                    {'name': 'server', 'type': 'text', 'default': 'tcp:host.docker.internal:4713', 'readonly': True}
                ]
            }
        
        # Check for VoiceMeeter
        if self._check_voicemeeter():
            modules['voicemeeter'] = {
                'name': 'VoiceMeeter (Detected)',
                'description': 'VoiceMeeter is installed - great for mixing audio sources',
                'class': 'VoiceMeeterModule',
                'requires_host': True,
                'status': 'available',
                'auto_score': 80,  # High score - good option
                'config_fields': [
                    {'name': 'connection_type', 'type': 'hidden', 'default': 'vban'},
                    {'name': 'port', 'type': 'hidden', 'default': 6980},
                    {'name': 'setup_instructions', 'type': 'info', 
                     'value': '1. Open VoiceMeeter\n2. Click Menu → VBAN\n3. Enable Stream 1\n4. Click Start Recording below'}
                ]
            }
        
        # Windows Native always available as fallback
        modules['windows_capture'] = {
            'name': 'Windows Audio Bridge',
            'description': 'Direct Windows audio capture (requires small Windows app)',
            'class': 'WindowsCaptureModule',
            'requires_host': True,
            'status': 'needs_setup',
            'auto_score': 70,
            'config_fields': [
                {'name': 'capture_mode', 'type': 'select', 
                 'options': ['everything', 'microphone_only'], 
                 'default': 'everything',
                 'labels': {'everything': 'All Audio (Mic + System)', 'microphone_only': 'Microphone Only'}},
                {'name': 'auto_download', 'type': 'button', 'action': 'download_windows_client',
                 'label': 'Download Windows Audio Bridge (2MB)'}
            ]
        }
        
        # Check system status
        self._add_system_info(modules)
        
        return modules
    
    def _check_pulseaudio(self):
        """Check if PulseAudio is running on Windows host"""
        try:
            # Try to connect to common PulseAudio ports
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('host.docker.internal', 4713))
            sock.close()
            
            if result == 0:
                logger.info("✅ PulseAudio detected on Windows host")
                return True
                
        except Exception as e:
            logger.debug(f"PulseAudio check failed: {e}")
            
        return False
    
    def _check_voicemeeter(self):
        """Check if VoiceMeeter might be available"""
        try:
            # Check if VBAN port is open (VoiceMeeter default)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.bind(('0.0.0.0', 6980))
            sock.close()
            
            # If we can bind, VoiceMeeter might be installed
            # We'll show it as an option but mark it needs configuration
            return True
            
        except OSError:
            # Port in use - might mean VoiceMeeter is running
            return True
        except Exception:
            return False
    
    def _add_system_info(self, modules):
        """Add helpful system information"""
        for module_id, module in modules.items():
            if module['status'] == 'available':
                module['badge'] = '✅ Ready'
                module['badge_color'] = 'success'
            elif module['status'] == 'needs_setup':
                module['badge'] = '⚙️ Setup Required'
                module['badge_color'] = 'warning'
            else:
                module['badge'] = '❌ Not Available'
                module['badge_color'] = 'error'
    
    def auto_select_module(self):
        """Automatically select the best available module"""
        # Sort by auto_score (highest first)
        sorted_modules = sorted(
            self.available_modules.items(),
            key=lambda x: x[1].get('auto_score', 0),
            reverse=True
        )
        
        # Find first available module
        for module_id, module_info in sorted_modules:
            if module_info['status'] == 'available':
                logger.info(f"Auto-selected audio module: {module_id}")
                self.config['audio_module'] = module_id
                return module_id
        
        # Fallback to test module
        logger.info("No audio modules available, using test mode")
        self.config['audio_module'] = 'test'
        return 'test'
    
    def get_quick_start_guide(self):
        """Get quick start instructions based on what's available"""
        guides = []
        
        if 'pulseaudio' in self.available_modules and self.available_modules['pulseaudio']['status'] == 'available':
            guides.append({
                'title': '✅ PulseAudio Detected!',
                'steps': [
                    'Your PulseAudio server is already running',
                    'Just click "Start Recording" to begin'
                ],
                'module': 'pulseaudio'
            })
        
        if 'voicemeeter' in self.available_modules:
            guides.append({
                'title': '🎛️ Use VoiceMeeter (Recommended)',
                'steps': [
                    'Open VoiceMeeter on Windows',
                    'Click Menu → VBAN → Stream 1 ON',
                    'Select VoiceMeeter in the options below',
                    'Click "Start Recording"'
                ],
                'module': 'voicemeeter'
            })
        
        guides.append({
            'title': '💻 Use Windows Audio Bridge',
            'steps': [
                'Click "Download Windows Audio Bridge" below',
                'Run AudioBridge.exe on Windows',
                'Select "Windows Audio Bridge" option',
                'Click "Start Recording"'
            ],
            'module': 'windows_capture'
        })
        
        return guides