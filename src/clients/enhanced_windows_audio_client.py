# enhanced_windows_audio_client.py
import pyaudiowpatch as pyaudio
import asyncio
import websockets
import numpy as np
import threading
import json
from queue import Queue
import time

class EnhancedAudioCapture:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.audio_queue = Queue()
        self.running = False
        
    def find_devices(self):
        """Find the best audio devices"""
        devices = {
            'microphone': None,
            'system_audio': None,
            'what_u_hear': None
        }
        
        print("🔍 Scanning audio devices...")
        
        for i in range(self.p.get_device_count()):
            try:
                info = self.p.get_device_info_by_index(i)
                name = info['name']
                
                # Look for What U Hear (captures everything)
                if "What U Hear" in name and info['maxInputChannels'] > 0:
                    devices['what_u_hear'] = (i, info)
                    print(f"✅ Found What U Hear: [{i}] {name}")
                
                # Look for microphone
                elif ("Microphone" in name or "Mic" in name) and info['maxInputChannels'] > 0:
                    devices['microphone'] = (i, info)
                    print(f"🎤 Found Microphone: [{i}] {name}")
                
                # Look for system audio loopback
                elif info.get('isLoopbackDevice', False):
                    devices['system_audio'] = (i, info)
                    print(f"🔊 Found System Audio: [{i}] {name}")
                    
            except Exception as e:
                continue
                
        return devices
    
    def start_capture(self, device_index, device_info):
        """Start capturing from a specific device"""
        try:
            # Use highest quality settings
            channels = min(device_info['maxInputChannels'], 2)
            rate = int(device_info['defaultSampleRate'])
            
            stream = self.p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=2048
            )
            
            print(f"✅ Started capture: {device_info['name']} ({rate}Hz, {channels}ch)")
            
            while self.running:
                try:
                    data = stream.read(2048, exception_on_overflow=False)
                    if data:
                        # Add device ID to the data for mixing
                        self.audio_queue.put((device_index, data))
                        
                except Exception as e:
                    print(f"❌ Capture error: {e}")
                    break
                    
            stream.stop_stream()
            stream.close()
            print(f"🛑 Stopped capture: {device_info['name']}")
            
        except Exception as e:
            print(f"❌ Failed to start capture: {e}")
    
    async def stream_to_docker(self):
        """Stream mixed audio to Docker"""
        print("🔗 Connecting to Docker...")
        
        async with websockets.connect('ws://localhost:8766') as ws:
            print("✅ Connected to Docker!")
            
            # Send info about our client
            await ws.send(json.dumps({
                'type': 'client_info',
                'client': 'enhanced_windows_capture',
                'mode': 'mixed_audio'
            }))
            
            bytes_sent = 0
            chunks_sent = 0
            last_status = time.time()
            
            while self.running:
                try:
                    # Get audio from queue
                    if not self.audio_queue.empty():
                        device_id, data = self.audio_queue.get_nowait()
                        
                        # Send raw audio data
                        await ws.send(data)
                        
                        bytes_sent += len(data)
                        chunks_sent += 1
                        
                        # Show status every 5 seconds
                        if time.time() - last_status > 5:
                            audio_array = np.frombuffer(data, dtype=np.int16)
                            level = np.max(np.abs(audio_array))
                            print(f"📊 Sent: {chunks_sent} chunks, {bytes_sent:,} bytes, Level: {level}")
                            last_status = time.time()
                    else:
                        await asyncio.sleep(0.01)
                        
                except Exception as e:
                    print(f"❌ Stream error: {e}")
                    break

async def main():
    capture = EnhancedAudioCapture()
    devices = capture.find_devices()
    
    # Priority: What U Hear > Microphone > System Audio
    device_to_use = None
    
    if devices['what_u_hear']:
        device_to_use = devices['what_u_hear']
        print("🎯 Using What U Hear (captures microphone + system audio)")
    elif devices['microphone']:
        device_to_use = devices['microphone']
        print("🎯 Using Microphone only")
    elif devices['system_audio']:
        device_to_use = devices['system_audio']
        print("🎯 Using System Audio only")
    else:
        print("❌ No suitable audio device found!")
        return
    
    print(f"\n🚀 Starting enhanced audio capture...")
    print("🎵 Join your meeting and start speaking!")
    print("🛑 Press Ctrl+C to stop\n")
    
    capture.running = True
    
    # Start capture thread
    device_index, device_info = device_to_use
    capture_thread = threading.Thread(
        target=capture.start_capture, 
        args=(device_index, device_info)
    )
    capture_thread.daemon = True
    capture_thread.start()
    
    try:
        # Start streaming
        await capture.stream_to_docker()
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
    finally:
        capture.running = False
        capture.p.terminate()

if __name__ == "__main__":
    asyncio.run(main())