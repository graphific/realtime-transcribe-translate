# enhanced_windows_audio_client_with_config.py
import pyaudiowpatch as pyaudio
import asyncio
import websockets
import numpy as np
import threading
import json
import time
import os
import sys
from queue import Queue
from pathlib import Path

class ConfigurableAudioCapture:
    def __init__(self, config_path="audio_config.json"):
        self.p = pyaudio.PyAudio()
        self.audio_queue = Queue()
        self.running = False
        self.config_path = config_path
        self.config = self.load_config()
        self.active_streams = {}
        self.control_ws = None
        self.available_devices = []
        
    def load_config(self):
        """Load configuration from file or create default"""
        default_config = {
            "selected_device": None,
            "active_devices": [],
            "sample_rate": 48000,
            "buffer_size": 2048,
            "capture_mode": "auto",
            "server_url": "ws://localhost:8766",
            "control_port": 8768
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    print(f"✅ Loaded config from {self.config_path}")
                    # Merge with defaults for any missing keys
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                print(f"❌ Error loading config: {e}")
        
        print("📝 Using default configuration")
        return default_config
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"💾 Config saved to {self.config_path}")
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def scan_devices(self):
        """Scan all available audio devices"""
        self.available_devices = []
        print("\n🔍 Scanning audio devices...")
        print("=" * 80)
        
        for i in range(self.p.get_device_count()):
            try:
                info = self.p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    device = {
                        'index': i,
                        'name': info['name'],
                        'type': self._get_device_type(info['name']),
                        'channels': info['maxInputChannels'],
                        'sample_rate': int(info['defaultSampleRate']),
                        'is_loopback': info.get('isLoopbackDevice', False) or '[Loopback]' in info['name']
                    }
                    self.available_devices.append(device)
                    
                    # Print device info
                    type_emoji = {
                        'microphone': '🎤',
                        'system_audio': '🔊',
                        'what_u_hear': '✅',
                        'unknown': '❓'
                    }.get(device['type'], '❓')
                    
                    active = "🟢 ACTIVE" if i in self.config['active_devices'] else ""
                    selected = "⭐ PRIMARY" if i == self.config['selected_device'] else ""
                    
                    print(f"{type_emoji} [{i:3d}] {device['name']} {active} {selected}")
                    
            except Exception as e:
                continue
        
        print("=" * 80)
        return self.available_devices
    
    def _get_device_type(self, name):
        """Determine device type from name"""
        name_lower = name.lower()
        if "what u hear" in name_lower:
            return "what_u_hear"
        elif "microphone" in name_lower or "mic" in name_lower:
            return "microphone"
        elif "[loopback]" in name_lower or "speaker" in name_lower:
            return "system_audio"
        return "unknown"
    
    def start_capture_for_device(self, device_index):
        """Start capturing from a specific device"""
        if device_index in self.active_streams:
            print(f"⚠️  Device {device_index} already capturing")
            return
        
        # Get device info
        try:
            device_info = self.p.get_device_info_by_index(device_index)
        except:
            print(f"❌ Device {device_index} not found")
            return
        
        # Start capture thread
        thread = threading.Thread(
            target=self._capture_device,
            args=(device_index, device_info),
            name=f"Capture-{device_index}"
        )
        thread.daemon = True
        thread.start()
        
        self.active_streams[device_index] = {
            'thread': thread,
            'info': device_info
        }
    
    def _capture_device(self, device_index, device_info):
        """Capture audio from a specific device"""
        stream = None
        try:
            # Use config settings or device defaults
            channels = min(device_info['maxInputChannels'], 2)
            rate = self.config.get('sample_rate', int(device_info['defaultSampleRate']))
            buffer_size = self.config.get('buffer_size', 2048)
            
            stream = self.p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=buffer_size
            )
            
            print(f"✅ Started capture: [{device_index}] {device_info['name']} ({rate}Hz, {channels}ch)")
            
            while self.running and device_index in self.active_streams:
                try:
                    data = stream.read(buffer_size, exception_on_overflow=False)
                    if data:
                        self.audio_queue.put((device_index, data))
                        
                except Exception as e:
                    if self.running:
                        print(f"⚠️  Capture error on device {device_index}: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Failed to start capture on device {device_index}: {e}")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            if device_index in self.active_streams:
                del self.active_streams[device_index]
            print(f"🛑 Stopped capture: [{device_index}]")
    
    def stop_capture_for_device(self, device_index):
        """Stop capturing from a specific device"""
        if device_index in self.active_streams:
            del self.active_streams[device_index]
            print(f"⏹️  Stopping device {device_index}")
    
    async def stream_to_docker(self):
        """Stream audio to Docker server"""
        print(f"\n🔗 Connecting to {self.config['server_url']}...")
        
        try:
            async with websockets.connect(self.config['server_url']) as ws:
                print("✅ Connected to Docker server!")
                
                # Send client info
                await ws.send(json.dumps({
                    'type': 'client_info',
                    'client': 'enhanced_windows_capture',
                    'mode': 'configurable',
                    'active_devices': list(self.active_streams.keys())
                }))
                
                bytes_sent = 0
                chunks_sent = 0
                last_status = time.time()
                device_stats = {}
                
                while self.running:
                    try:
                        if not self.audio_queue.empty():
                            device_id, data = self.audio_queue.get_nowait()
                            
                            # Send raw audio data
                            await ws.send(data)
                            
                            # Update stats
                            bytes_sent += len(data)
                            chunks_sent += 1
                            device_stats[device_id] = device_stats.get(device_id, 0) + 1
                            
                            # Show status every 5 seconds
                            if time.time() - last_status > 5:
                                audio_array = np.frombuffer(data, dtype=np.int16)
                                level = np.max(np.abs(audio_array))
                                
                                print(f"\n📊 Status Update:")
                                print(f"   Total: {chunks_sent} chunks, {bytes_sent:,} bytes")
                                print(f"   Active devices: {list(self.active_streams.keys())}")
                                print(f"   Last audio from device {device_id}, Level: {level}")
                                
                                # Send audio level to control WebSocket
                                if self.control_ws:
                                    try:
                                        await self.control_ws.send(json.dumps({
                                            'type': 'audio_level',
                                            'device': device_id,
                                            'level': int(level)
                                        }))
                                    except:
                                        pass
                                
                                last_status = time.time()
                        else:
                            await asyncio.sleep(0.01)
                            
                    except Exception as e:
                        print(f"❌ Stream error: {e}")
                        break
                        
        except Exception as e:
            print(f"❌ Connection error: {e}")
            await asyncio.sleep(2)
    
    async def control_server(self):
        """WebSocket server for web UI control"""
        print(f"🎮 Starting control server on port {self.config['control_port']}...")
        
        async def handle_control(websocket, path):
            self.control_ws = websocket
            print(f"🎮 Control client connected from {websocket.remote_address}")
            
            try:
                # Send initial status
                await websocket.send(json.dumps({
                    'type': 'status',
                    'capturing': self.running,
                    'config': self.config,
                    'devices': self.available_devices
                }))
                
                async for message in websocket:
                    data = json.loads(message)
                    command = data.get('command')
                    
                    if command == 'scan':
                        devices = self.scan_devices()
                        await websocket.send(json.dumps({
                            'type': 'devices',
                            'devices': devices
                        }))
                    
                    elif command == 'save_config':
                        self.config = data.get('config', self.config)
                        self.save_config()
                        await websocket.send(json.dumps({
                            'type': 'config_saved',
                            'success': True
                        }))
                    
                    elif command == 'start':
                        # Update config and start capture
                        if 'config' in data:
                            self.config = data['config']
                            self.save_config()
                        # Restart capture with new config
                        await self.restart_capture()
                    
                    elif command == 'stop':
                        self.stop_all_devices()
                        await websocket.send(json.dumps({
                            'type': 'status',
                            'capturing': False
                        }))
                    
                    elif command == 'update_devices':
                        # Hot-swap devices while running
                        new_active = set(data.get('active_devices', []))
                        current_active = set(self.active_streams.keys())
                        
                        # Stop devices that are no longer active
                        for device_index in current_active - new_active:
                            self.stop_capture_for_device(device_index)
                        
                        # Start devices that are newly active
                        for device_index in new_active - current_active:
                            self.start_capture_for_device(device_index)
                        
                        # Update config
                        self.config['active_devices'] = list(new_active)
                        self.save_config()
                        
            except websockets.exceptions.ConnectionClosed:
                print("🎮 Control client disconnected")
            finally:
                self.control_ws = None
        
        try:
            server = await websockets.serve(handle_control, 'localhost', self.config['control_port'])
            print(f"✅ Control server running on ws://localhost:{self.config['control_port']}")
            await asyncio.Future()  # Run forever
        except Exception as e:
            print(f"❌ Control server error: {e}")
    
    async def restart_capture(self):
        """Restart capture with current config"""
        # Stop all current captures
        self.stop_all_devices()
        await asyncio.sleep(0.5)
        
        # Start devices from config
        for device_index in self.config['active_devices']:
            self.start_capture_for_device(device_index)
    
    def stop_all_devices(self):
        """Stop all active captures"""
        device_list = list(self.active_streams.keys())
        for device_index in device_list:
            self.stop_capture_for_device(device_index)
    
    def print_help(self):
        """Print help information"""
        print(f"""
🎵 Enhanced Windows Audio Capture with Config Support
{'=' * 60}
Config file: {self.config_path}

Current configuration:
- Selected device: {self.config['selected_device']}
- Active devices: {self.config['active_devices']}
- Sample rate: {self.config['sample_rate']} Hz
- Buffer size: {self.config['buffer_size']}

Commands:
- Open http://localhost:8080/audio_control.html in your browser
- Or press Ctrl+C to stop
""")

async def main():
    # Parse command line arguments
    config_path = "audio_config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    capture = ConfigurableAudioCapture(config_path)
    
    # Initial device scan
    capture.scan_devices()
    capture.print_help()
    
    # Start capture
    capture.running = True
    
    # Start devices from config
    if capture.config['active_devices']:
        print(f"\n🚀 Starting capture with {len(capture.config['active_devices'])} configured devices...")
        for device_index in capture.config['active_devices']:
            capture.start_capture_for_device(device_index)
    else:
        print("\n⚠️  No devices configured. Use the web interface to select devices.")
    
    # Create tasks
    tasks = [
        asyncio.create_task(capture.stream_to_docker()),
        asyncio.create_task(capture.control_server())
    ]
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
    finally:
        capture.running = False
        capture.stop_all_devices()
        capture.p.terminate()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(main())