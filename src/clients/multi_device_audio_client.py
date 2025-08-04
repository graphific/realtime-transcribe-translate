# fixed_multi_device_audio.py
import pyaudiowpatch as pyaudio
import asyncio
import websockets
import numpy as np
import threading
import json
from queue import Queue
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor

# Platform-specific imports for keyboard handling
if sys.platform == 'win32':
    import msvcrt
    import asyncio.windows_events
else:
    import termios
    import tty
    import select

class FixedMultiDeviceCapture:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.audio_queue = Queue(maxsize=100)  # Limit queue size to prevent memory issues
        self.running = False
        self.active_devices = {}  # {device_index: (thread, stream, device_info)}
        self.available_devices = []
        self.selected_index = 0
        self.connected = False
        self.recent_levels = {}
        self.last_ui_update = 0
        self.executor = ThreadPoolExecutor(max_workers=1)  # For keyboard handling
        
    def get_all_devices(self):
        """Get all available audio devices"""
        self.available_devices = []
        
        for i in range(self.p.get_device_count()):
            try:
                info = self.p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    device = {
                        'index': i,
                        'name': info['name'],
                        'channels': info['maxInputChannels'],
                        'rate': int(info['defaultSampleRate']),
                        'type': self._get_device_type(info['name'])
                    }
                    self.available_devices.append(device)
            except Exception:
                continue
                
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
    
    def draw_ui(self):
        """Draw the device selection UI"""
        # Rate limit UI updates
        if time.time() - self.last_ui_update < 0.1:
            return
        self.last_ui_update = time.time()
        
        # Clear screen
        if sys.platform == 'win32':
            os.system('cls')
        else:
            print('\033[2J\033[H')  # ANSI clear screen
        
        print("🎵 Multi-Device Audio Capture Control")
        print("=" * 80)
        print("Use ↑/↓ to navigate, SPACE/ENTER to toggle device, Q to quit")
        print("=" * 80)
        print()
        
        # Show connection status
        status = "🟢 Connected" if self.connected else "🔴 Disconnected"
        print(f"Server Status: {status}")
        print()
        
        # List devices
        for idx, device in enumerate(self.available_devices):
            # Device type emoji
            type_emoji = {
                'what_u_hear': '✅',
                'microphone': '🎤',
                'system_audio': '🔊',
                'unknown': '❓'
            }.get(device['type'], '❓')
            
            # Selection indicator
            if idx == self.selected_index:
                selector = "→"
            else:
                selector = " "
            
            # Active status
            if device['index'] in self.active_devices:
                status = "🟢 ACTIVE"
            else:
                status = "⚪ inactive"
            
            # Print device line
            print(f"{selector} {type_emoji} [{device['index']:3d}] {status} {device['name'][:60]}")
        
        print()
        print("=" * 80)
        print(f"Active devices: {len(self.active_devices)}")
        print(f"Queue size: {self.audio_queue.qsize()}")
        
        # Show recent audio levels
        if self.recent_levels:
            print("\nAudio Levels:")
            for device_id, level in list(self.recent_levels.items())[:5]:  # Limit to 5 devices
                if device_id in self.active_devices:
                    bar_length = min(30, int(level / 1000))
                    bar = "█" * bar_length + "░" * (30 - bar_length)
                    print(f"  [{device_id:3d}] {bar} {level:5d}")
    
    def toggle_device(self, device_index):
        """Toggle device on/off"""
        if device_index in self.active_devices:
            return self.stop_device_capture(device_index)
        else:
            return self.start_device_capture(device_index)
    
    def start_device_capture(self, device_index):
        """Start capturing from a specific device"""
        if device_index in self.active_devices:
            return False
            
        # Find device info
        device_info = None
        for i in range(self.p.get_device_count()):
            try:
                info = self.p.get_device_info_by_index(i)
                if i == device_index:
                    device_info = info
                    break
            except Exception:
                continue
                
        if not device_info:
            return False
            
        # Start capture thread
        thread = threading.Thread(
            target=self._capture_worker,
            args=(device_index, device_info),
            name=f"Capture-{device_index}"
        )
        thread.daemon = True
        thread.start()
        
        # Store in active devices
        self.active_devices[device_index] = {
            'thread': thread,
            'stream': None,
            'info': device_info
        }
        
        return True
    
    def stop_device_capture(self, device_index):
        """Stop capturing from a specific device"""
        if device_index not in self.active_devices:
            return False
            
        # Remove from active devices (thread will detect and stop)
        del self.active_devices[device_index]
        
        # Clear level data
        if device_index in self.recent_levels:
            del self.recent_levels[device_index]
            
        return True
    
    def _capture_worker(self, device_index, device_info):
        """Worker thread for capturing audio from a device"""
        stream = None
        consecutive_errors = 0
        
        try:
            # Open audio stream with more robust settings
            stream = self.p.open(
                format=pyaudio.paInt16,
                channels=min(device_info['maxInputChannels'], 2),
                rate=int(device_info['defaultSampleRate']),
                input=True,
                input_device_index=device_index,
                frames_per_buffer=2048,
                stream_callback=None  # Use blocking mode
            )
            
            # Update stream reference
            if device_index in self.active_devices:
                self.active_devices[device_index]['stream'] = stream
            
            while self.running and device_index in self.active_devices:
                try:
                    # Read with timeout
                    data = stream.read(2048, exception_on_overflow=False)
                    if data:
                        # Only queue if there's space
                        if not self.audio_queue.full():
                            self.audio_queue.put((device_index, data), block=False)
                        consecutive_errors = 0
                    else:
                        time.sleep(0.001)
                        
                except Exception as e:
                    consecutive_errors += 1
                    if consecutive_errors > 10:
                        break
                    time.sleep(0.01)
                    
        except Exception as e:
            pass
        finally:
            # Cleanup
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
            
            # Remove from active devices if still there
            if device_index in self.active_devices:
                del self.active_devices[device_index]
    
    async def stream_to_docker(self):
        """Stream audio to Docker with reconnection logic"""
        reconnect_delay = 1
        
        while self.running:
            try:
                async with websockets.connect(
                    'ws://localhost:8766',
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ) as ws:
                    self.connected = True
                    reconnect_delay = 1  # Reset delay on successful connection
                    
                    # Send client info
                    await ws.send(json.dumps({
                        'type': 'client_info',
                        'client': 'fixed_multi_device_capture',
                        'mode': 'raw_passthrough'
                    }))
                    
                    while self.running and not ws.closed:
                        try:
                            # Get audio with timeout
                            try:
                                device_id, data = self.audio_queue.get(timeout=0.1)
                                
                                # Send raw audio data
                                await asyncio.wait_for(ws.send(data), timeout=5.0)
                                
                                # Update audio levels
                                audio_array = np.frombuffer(data, dtype=np.int16)
                                level = np.max(np.abs(audio_array))
                                self.recent_levels[device_id] = level
                                
                            except asyncio.TimeoutError:
                                continue
                            except Queue.Empty:
                                continue
                                
                        except websockets.exceptions.ConnectionClosed:
                            break
                        except Exception:
                            await asyncio.sleep(0.01)
                            
            except Exception as e:
                self.connected = False
                await asyncio.sleep(min(reconnect_delay, 30))
                reconnect_delay *= 2  # Exponential backoff

def get_key_windows():
    """Get a single keypress on Windows"""
    if msvcrt.kbhit():
        key = msvcrt.getch()
        # Handle special keys
        if key in [b'\x00', b'\xe0']:  # Special key prefix
            key = msvcrt.getch()
            if key == b'H':  # Up arrow
                return 'up'
            elif key == b'P':  # Down arrow
                return 'down'
        elif key == b' ':  # Space
            return 'space'
        elif key == b'\r':  # Enter
            return 'enter'
        elif key.lower() == b'q':  # Q key
            return 'q'
    return None

def get_key_unix():
    """Get a single keypress on Unix/Linux/Mac"""
    if select.select([sys.stdin], [], [], 0)[0]:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)
            
            if key == '\x1b':  # ESC sequence
                if select.select([sys.stdin], [], [], 0)[0]:
                    key2 = sys.stdin.read(1)
                    if key2 == '[' and select.select([sys.stdin], [], [], 0)[0]:
                        key3 = sys.stdin.read(1)
                        if key3 == 'A':
                            return 'up'
                        elif key3 == 'B':
                            return 'down'
            elif key == ' ':
                return 'space'
            elif key == '\r' or key == '\n':
                return 'enter'
            elif key.lower() == 'q':
                return 'q'
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None

async def handle_keyboard_input(capture):
    """Handle keyboard input asynchronously"""
    get_key = get_key_windows if sys.platform == 'win32' else get_key_unix
    
    while capture.running:
        # Check for keyboard input in executor to avoid blocking
        key = await asyncio.get_event_loop().run_in_executor(
            capture.executor, get_key
        )
        
        if key:
            if key == 'up' and capture.selected_index > 0:
                capture.selected_index -= 1
                capture.draw_ui()
            elif key == 'down' and capture.selected_index < len(capture.available_devices) - 1:
                capture.selected_index += 1
                capture.draw_ui()
            elif key in ['space', 'enter']:
                if capture.selected_index < len(capture.available_devices):
                    device = capture.available_devices[capture.selected_index]
                    capture.toggle_device(device['index'])
                    capture.draw_ui()
            elif key == 'q':
                capture.running = False
        
        await asyncio.sleep(0.05)

async def ui_refresh_task(capture):
    """Separate task for UI refresh"""
    while capture.running:
        capture.draw_ui()
        await asyncio.sleep(0.5)

async def main():
    capture = FixedMultiDeviceCapture()
    
    # Get all devices
    capture.get_all_devices()
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--devices', nargs='+', type=int, help='Initial device IDs to capture')
    args = parser.parse_args()
    
    capture.running = True
    
    # Setup terminal for Unix
    if sys.platform != 'win32':
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    
    try:
        # Start initial devices
        if args.devices:
            for device_id in args.devices:
                capture.start_device_capture(device_id)
        else:
            # Auto-start What U Hear if available
            for device in capture.available_devices:
                if device['type'] == 'what_u_hear':
                    capture.start_device_capture(device['index'])
                    break
        
        # Initial UI draw
        capture.draw_ui()
        
        # Create tasks
        tasks = [
            asyncio.create_task(capture.stream_to_docker()),
            asyncio.create_task(handle_keyboard_input(capture)),
            asyncio.create_task(ui_refresh_task(capture))
        ]
        
        await asyncio.gather(*tasks)
        
    except KeyboardInterrupt:
        pass
    finally:
        capture.running = False
        
        # Restore terminal settings for Unix
        if sys.platform != 'win32':
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        
        # Cleanup
        capture.executor.shutdown(wait=False)
        
        if sys.platform == 'win32':
            os.system('cls')
        else:
            print('\033[2J\033[H')
            
        print("🛑 Shutting down...")
        
        # Close all streams
        for device_id, device_data in list(capture.active_devices.items()):
            if device_data.get('stream'):
                try:
                    device_data['stream'].close()
                except:
                    pass
                    
        capture.p.terminate()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    # For Windows
    if sys.platform == 'win32':
        # Use ProactorEventLoop for better Windows support
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    
    asyncio.run(main())