# windows_microphone_boost_client.py
import pyaudiowpatch as pyaudio
import asyncio
import websockets
import numpy as np
import threading
import json
from queue import Queue
import time
import sys

class MicrophoneCaptureWithBoost:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.audio_queue = Queue()
        self.running = False
        self.current_mic = None
        
        # Audio boost settings
        self.boost_factor = 10.0  # Amplify by 10x (20 dB)
        self.auto_gain = True     # Auto-adjust gain based on levels
        self.target_peak = 10000  # Target peak level (out of 32768)
        self.gain_history = []
        
    def find_microphones(self):
        """Find all available microphone devices"""
        microphones = []
        
        print("🔍 Scanning for microphone devices...")
        print("=" * 80)
        
        for i in range(self.p.get_device_count()):
            try:
                info = self.p.get_device_info_by_index(i)
                name = info['name']
                
                # Look for microphone devices (not loopback)
                if info['maxInputChannels'] > 0 and not info.get('isLoopbackDevice', False):
                    # Check if it's likely a microphone
                    is_mic = False
                    name_lower = name.lower()
                    
                    # Common microphone indicators
                    mic_keywords = ['microphone', 'mic', 'input', 'usb audio', 'webcam', 'headset']
                    
                    # Exclude system audio devices
                    exclude_keywords = ['what u hear', 'stereo mix', 'loopback', 'speaker', 'output']
                    
                    # Check for microphone keywords
                    for keyword in mic_keywords:
                        if keyword in name_lower:
                            is_mic = True
                            break
                    
                    # Check for exclusions
                    for keyword in exclude_keywords:
                        if keyword in name_lower:
                            is_mic = False
                            break
                    
                    # If no keywords found but it's an input device, include it
                    if not is_mic and info['maxInputChannels'] > 0:
                        # Default Windows devices often don't have keywords
                        if 'microsoft sound mapper' in name_lower or name_lower.startswith('microphone'):
                            is_mic = True
                        # Include any remaining input devices as potential mics
                        elif not any(ex in name_lower for ex in exclude_keywords):
                            is_mic = True
                    
                    if is_mic:
                        mic_info = {
                            'index': i,
                            'name': name,
                            'channels': info['maxInputChannels'],
                            'sample_rate': int(info['defaultSampleRate']),
                            'is_default': i == self.p.get_default_input_device_info()['index']
                        }
                        microphones.append(mic_info)
                        
                        default_marker = " ⭐ (Default)" if mic_info['is_default'] else ""
                        print(f"🎤 [{i:3d}] {name}{default_marker}")
                        print(f"        Channels: {mic_info['channels']}, Sample Rate: {mic_info['sample_rate']} Hz")
                        
            except Exception as e:
                continue
        
        print("=" * 80)
        print(f"Found {len(microphones)} microphone device(s)")
        
        return microphones
    
    def select_microphone(self, microphones):
        """Let user select a microphone or use default"""
        if not microphones:
            print("❌ No microphones found!")
            return None
        
        # If only one microphone, use it
        if len(microphones) == 1:
            return microphones[0]
        
        # Find default microphone
        default_mic = None
        for mic in microphones:
            if mic['is_default']:
                default_mic = mic
                break
        
        # If command line argument provided
        if len(sys.argv) > 1:
            try:
                device_id = int(sys.argv[1])
                for mic in microphones:
                    if mic['index'] == device_id:
                        print(f"✅ Using specified microphone: [{device_id}] {mic['name']}")
                        return mic
                print(f"⚠️  Device {device_id} not found, using default")
            except ValueError:
                # Check if it's a boost factor
                if sys.argv[1].startswith('--boost='):
                    try:
                        self.boost_factor = float(sys.argv[1].split('=')[1])
                        print(f"🔊 Using boost factor: {self.boost_factor}x")
                    except:
                        pass
        
        # Interactive selection
        print("\n🎯 Select a microphone:")
        print("0. Use default microphone" + (f" ({default_mic['name']})" if default_mic else ""))
        
        for i, mic in enumerate(microphones, 1):
            default_marker = " ⭐" if mic['is_default'] else ""
            print(f"{i}. [{mic['index']}] {mic['name']}{default_marker}")
        
        try:
            choice = input("\nEnter your choice (0 for default, or device number): ").strip()
            
            if not choice or choice == '0':
                return default_mic or microphones[0]
            
            # Try to parse as index first
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(microphones):
                    return microphones[idx]
            except ValueError:
                pass
            
            # Try to parse as device ID
            try:
                device_id = int(choice)
                for mic in microphones:
                    if mic['index'] == device_id:
                        return mic
            except ValueError:
                pass
            
            print("⚠️  Invalid choice, using default")
            return default_mic or microphones[0]
            
        except KeyboardInterrupt:
            print("\n⚠️  Selection cancelled, using default")
            return default_mic or microphones[0]
    
    def apply_audio_boost(self, audio_data):
        """Apply gain boost to audio data"""
        # Convert to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        
        # Get current peak level
        current_peak = np.max(np.abs(audio_array))
        
        if self.auto_gain and current_peak > 0:
            # Calculate optimal gain to reach target peak
            optimal_gain = self.target_peak / current_peak
            
            # Smooth gain changes to avoid sudden jumps
            if self.gain_history:
                # Use exponential moving average
                alpha = 0.1  # Smoothing factor
                smoothed_gain = alpha * optimal_gain + (1 - alpha) * self.gain_history[-1]
            else:
                smoothed_gain = optimal_gain
            
            # Limit gain to reasonable range
            smoothed_gain = np.clip(smoothed_gain, 1.0, 50.0)
            
            self.gain_history.append(smoothed_gain)
            if len(self.gain_history) > 100:
                self.gain_history.pop(0)
            
            self.boost_factor = smoothed_gain
        
        # Apply boost
        boosted = audio_array * self.boost_factor
        
        # Prevent clipping
        boosted = np.clip(boosted, -32768, 32767)
        
        # Convert back to int16
        return boosted.astype(np.int16).tobytes()
    
    def start_capture(self, microphone):
        """Start capturing from the selected microphone with boost"""
        try:
            # Get device info
            device_info = self.p.get_device_info_by_index(microphone['index'])
            
            # Use optimal settings
            channels = min(device_info['maxInputChannels'], 2)  # Mono or stereo
            rate = microphone['sample_rate']
            
            # Open stream with larger buffer for stability
            stream = self.p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=microphone['index'],
                frames_per_buffer=4096  # Larger buffer for more stable capture
            )
            
            print(f"\n✅ Started capture: {microphone['name']}")
            print(f"   Settings: {rate}Hz, {channels} channel(s)")
            print(f"   Device ID: {microphone['index']}")
            print(f"   Boost: {self.boost_factor}x initial (auto-gain: {self.auto_gain})")
            print("\n🎙️  Microphone is active - speak normally")
            print("📊 Audio levels will be shown every 5 seconds")
            print("🛑 Press Ctrl+C to stop\n")
            
            capture_start = time.time()
            total_frames = 0
            
            while self.running:
                try:
                    # Read audio data
                    data = stream.read(4096, exception_on_overflow=False)
                    
                    if data:
                        # Apply boost
                        boosted_data = self.apply_audio_boost(data)
                        
                        # Queue the boosted audio data
                        self.audio_queue.put((microphone['index'], boosted_data))
                        total_frames += 1
                        
                        # Occasional status update
                        if total_frames % 100 == 0:
                            runtime = time.time() - capture_start
                            print(f"\r⏱️  Recording: {runtime:.1f}s | Frames: {total_frames} | Boost: {self.boost_factor:.1f}x", end='', flush=True)
                        
                except Exception as e:
                    print(f"\n⚠️  Capture warning: {e}")
                    continue
                    
            stream.stop_stream()
            stream.close()
            
            runtime = time.time() - capture_start
            print(f"\n\n🛑 Stopped capture: {microphone['name']}")
            print(f"📊 Total recording time: {runtime:.1f} seconds")
            print(f"📊 Total frames captured: {total_frames}")
            
        except Exception as e:
            print(f"❌ Failed to start capture: {e}")
            print("   Try running as administrator or check if another app is using the microphone")
    
    async def stream_to_docker(self):
        """Stream microphone audio to Docker"""
        print("\n🔗 Connecting to transcription server...")
        
        reconnect_attempts = 0
        max_reconnects = 5
        
        while reconnect_attempts < max_reconnects:
            try:
                async with websockets.connect('ws://localhost:8766') as ws:
                    print("✅ Connected to transcription server!")
                    reconnect_attempts = 0  # Reset on successful connection
                    
                    # Send client info
                    await ws.send(json.dumps({
                        'type': 'client_info',
                        'client': 'windows_microphone_capture',
                        'mode': 'microphone_only',
                        'device': self.current_mic['name'] if self.current_mic else 'Unknown',
                        'boost': self.boost_factor
                    }))
                    
                    bytes_sent = 0
                    chunks_sent = 0
                    last_status = time.time()
                    last_level_log = time.time()
                    
                    while self.running:
                        try:
                            # Get audio from queue with timeout
                            if not self.audio_queue.empty():
                                device_id, data = self.audio_queue.get_nowait()
                                
                                # Send raw audio data
                                await ws.send(data)
                                
                                bytes_sent += len(data)
                                chunks_sent += 1
                                
                                # Calculate audio level
                                audio_array = np.frombuffer(data, dtype=np.int16)
                                level = np.max(np.abs(audio_array))
                                rms = np.sqrt(np.mean(audio_array**2))
                                
                                # Show detailed status every 5 seconds
                                if time.time() - last_status > 5:
                                    # Create level meter
                                    max_bar = 30
                                    level_bar = int((level / 32768) * max_bar)
                                    rms_bar = int((rms / 32768) * max_bar)
                                    
                                    level_meter = "█" * level_bar + "░" * (max_bar - level_bar)
                                    rms_meter = "█" * rms_bar + "░" * (max_bar - rms_bar)
                                    
                                    print(f"\n📊 Audio Status:")
                                    print(f"   Chunks sent: {chunks_sent:,}")
                                    print(f"   Data sent: {bytes_sent:,} bytes ({bytes_sent/1024/1024:.1f} MB)")
                                    print(f"   Peak level: [{level_meter}] {level:5d} (boosted)")
                                    print(f"   RMS level:  [{rms_meter}] {int(rms):5d}")
                                    print(f"   Current boost: {self.boost_factor:.1f}x")
                                    
                                    # Level feedback
                                    if level < 3000:
                                        print("   ⚠️  Still too quiet - speak louder or move closer")
                                    elif level > 28000:
                                        print("   ⚠️  Getting loud - possible distortion")
                                    else:
                                        print("   ✅ Good audio level")
                                    
                                    last_status = time.time()
                                    
                                # Quick level indicator every second
                                elif time.time() - last_level_log > 1:
                                    level_chars = " ▁▂▃▄▅▆▇█"
                                    level_idx = min(int((level / 32768) * len(level_chars)), len(level_chars) - 1)
                                    print(f"\r🎙️ {level_chars[level_idx]} Level: {level:5d} | Boost: {self.boost_factor:.1f}x ", end='', flush=True)
                                    last_level_log = time.time()
                                    
                            else:
                                await asyncio.sleep(0.01)
                                
                        except websockets.exceptions.ConnectionClosed:
                            print("\n❌ Lost connection to server")
                            break
                        except Exception as e:
                            print(f"\n❌ Stream error: {e}")
                            break
                            
            except Exception as e:
                reconnect_attempts += 1
                if reconnect_attempts < max_reconnects:
                    wait_time = min(reconnect_attempts * 2, 10)
                    print(f"❌ Connection failed: {e}")
                    print(f"🔄 Retrying in {wait_time} seconds... (attempt {reconnect_attempts}/{max_reconnects})")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ Failed to connect after {max_reconnects} attempts")
                    print("   Check if the transcription server is running on port 8766")
                    break

async def main():
    print("🎤 Windows Microphone Audio Capture Client (with Boost)")
    print("=" * 80)
    print("This client captures and amplifies quiet microphone audio")
    print("Usage: python windows_microphone_boost_client.py [device_id] [--boost=10]")
    print("=" * 80)
    
    capture = MicrophoneCaptureWithBoost()
    
    # Check for boost parameter
    for arg in sys.argv[1:]:
        if arg.startswith('--boost='):
            try:
                capture.boost_factor = float(arg.split('=')[1])
                print(f"🔊 Manual boost set to: {capture.boost_factor}x")
            except:
                pass
    
    # Find all microphones
    microphones = capture.find_microphones()
    
    if not microphones:
        print("\n❌ No microphones detected!")
        print("   Please check:")
        print("   - Microphone is connected")
        print("   - Microphone is enabled in Windows Sound settings")
        print("   - No other application is exclusively using the microphone")
        return
    
    # Select microphone
    selected_mic = capture.select_microphone(microphones)
    if not selected_mic:
        print("❌ No microphone selected!")
        return
    
    capture.current_mic = selected_mic
    print(f"\n🎯 Selected: {selected_mic['name']}")
    
    # Start capture
    capture.running = True
    
    # Start capture thread
    capture_thread = threading.Thread(
        target=capture.start_capture, 
        args=(selected_mic,),
        daemon=True
    )
    capture_thread.start()
    
    try:
        # Start streaming
        await capture.stream_to_docker()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
    finally:
        capture.running = False
        time.sleep(0.5)  # Give capture thread time to cleanup
        capture.p.terminate()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    # Command line usage
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python windows_microphone_boost_client.py [device_id] [--boost=factor]")
        print("  device_id: Optional microphone device ID to use")
        print("  --boost=factor: Manual boost factor (e.g., --boost=20 for 20x amplification)")
        print("  If not specified, will show device list and use auto-gain")
        sys.exit(0)
    
    asyncio.run(main())