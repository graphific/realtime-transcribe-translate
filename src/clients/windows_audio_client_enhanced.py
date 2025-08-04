# windows_audio_client_enhanced.py
import pyaudiowpatch as pyaudio
import asyncio
import websockets
import numpy as np
import argparse
import logging
import json
import signal
import sys
from threading import Thread, Event
from queue import Queue
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WindowsAudioCapture:
    def __init__(self, mode='loopback', server_url='ws://localhost:8766', device_index=None):
        self.mode = mode
        self.server_url = server_url
        self.device_index = device_index
        self.audio = pyaudio.PyAudio()
        self.audio_queue = Queue()
        self.command_queue = Queue()
        self.running = False
        self.websocket = None
        self.ws_task = None
        self.capture_thread = None
        self.stats = {
            'bytes_captured': 0,
            'bytes_sent': 0,
            'chunks_captured': 0,
            'chunks_sent': 0,
            'start_time': time.time()
        }
        
    def get_devices(self):
        """List available audio devices"""
        devices = []
        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels'],
                    'sample_rate': info['defaultSampleRate'],
                    'is_input': info['maxInputChannels'] > 0,
                    'loopback': info.get('isLoopbackDevice', False),
                    'is_default': info.get('isDefaultDevice', False),
                    'host_api': self.audio.get_host_api_info_by_index(info['hostApi'])['name']
                })
            except:
                continue
        return devices
    
    def get_loopback_device(self):
        """Get default WASAPI loopback device"""
        try:
            # List all devices for debugging
            logger.info("Available devices:")
            for device in self.get_devices():
                if device['loopback']:
                    logger.info(f"  Loopback: [{device['index']}] {device['name']}")
            
            # Try to get default loopback
            wasapi_info = self.audio.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = self.audio.get_device_info_by_index(
                wasapi_info['defaultOutputDevice']
            )
            
            # Find loopback device
            for i in range(self.audio.get_device_count()):
                info = self.audio.get_device_info_by_index(i)
                if info.get('isLoopbackDevice', False):
                    return info
                    
        except Exception as e:
            logger.error(f"Error finding loopback device: {e}")
            
        return None
    
    def test_device(self, device_index, duration=3):
        """Test a device and return audio levels"""
        try:
            info = self.audio.get_device_info_by_index(device_index)
            
            # Try to open stream
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=min(2, int(info['maxInputChannels'])),
                rate=int(info['defaultSampleRate']),
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024
            )
            
            logger.info(f"Testing device {device_index}: {info['name']}")
            logger.info("Recording for 3 seconds...")
            
            max_level = 0
            has_audio = False
            
            start_time = time.time()
            while time.time() - start_time < duration:
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    level = np.max(np.abs(audio_data)) / 32768.0
                    max_level = max(max_level, level)
                    
                    if level > 0.01:  # Threshold for detecting audio
                        has_audio = True
                        
                except Exception as e:
                    logger.error(f"Error reading audio: {e}")
                    
            stream.stop_stream()
            stream.close()
            
            return {
                "success": True,
                "device_name": info['name'],
                "max_level": float(max_level),
                "has_audio": has_audio
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def handle_commands(self):
        """Handle incoming commands from server"""
        while self.running and self.websocket:
            try:
                # Check for commands
                if not self.command_queue.empty():
                    command = self.command_queue.get_nowait()
                    logger.info(f"Processing command: {command}")
                    
                    if command['command'] == 'list_devices':
                        devices = self.get_devices()
                        await self.websocket.send(json.dumps({
                            "type": "device_list",
                            "devices": devices,
                            "request_id": command.get('request_id')
                        }))
                        
                    elif command['command'] == 'test_device':
                        device_index = command.get('device_index')
                        result = self.test_device(device_index)
                        await self.websocket.send(json.dumps({
                            "type": "device_test",
                            "result": result,
                            "request_id": command.get('request_id')
                        }))
                        
                    elif command['command'] == 'change_device':
                        new_device = command.get('device_index')
                        # TODO: Implement device switching
                        logger.info(f"Device change requested to {new_device}")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Command handler error: {e}")
    
    async def message_receiver(self):
        """Receive messages from server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    logger.info(f"Received command: {data}")
                    self.command_queue.put(data)
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.error(f"Message receiver error: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Message receiver error: {e}")
    
    async def start_capture(self):
        """Start audio capture and streaming"""
        self.running = True
        
        # Get device
        if self.mode == 'loopback':
            if self.device_index is None:
                device = self.get_loopback_device()
                if not device:
                    logger.error("No loopback device found!")
                    return
                self.device_index = device['index']
            else:
                device = self.audio.get_device_info_by_index(self.device_index)
        elif self.mode == 'test':
            # Test mode - generate audio
            device = None
        else:
            if self.device_index is None:
                device = self.audio.get_default_input_device_info()
                self.device_index = device['index']
            else:
                device = self.audio.get_device_info_by_index(self.device_index)
        
        if device:
            logger.info(f"Using device: {device['name']}")
            logger.info(f"  Sample rate: {device['defaultSampleRate']}")
            logger.info(f"  Channels: {device['maxInputChannels']}")
        
        # Start capture thread
        self.capture_thread = Thread(
            target=self._capture_audio if device else self._generate_test_audio, 
            args=(device,) if device else ()
        )
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        # Start status thread
        status_thread = Thread(target=self._print_status)
        status_thread.daemon = True
        status_thread.start()
        
        # Stream audio
        self.ws_task = asyncio.create_task(self._stream_audio())
        await self.ws_task
    
    def _capture_audio(self, device):
        """Capture audio in background thread"""
        try:
            # Adjust parameters for the device
            channels = min(int(device['maxInputChannels']), 2)
            rate = int(device['defaultSampleRate'])
            
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=device['index'],
                frames_per_buffer=2048,  # Larger buffer
                stream_callback=None
            )
            
            logger.info(f"Audio capture started (rate={rate}, channels={channels})")
            
            while self.running:
                try:
                    data = stream.read(2048, exception_on_overflow=False)
                    if data:
                        self.audio_queue.put(data)
                        self.stats['bytes_captured'] += len(data)
                        self.stats['chunks_captured'] += 1
                        
                        # Check audio level periodically
                        if self.stats['chunks_captured'] % 50 == 0:
                            audio_array = np.frombuffer(data, dtype=np.int16)
                            max_level = np.max(np.abs(audio_array))
                            if max_level > 100:
                                logger.info(f"🔊 Audio detected! Level: {max_level}")
                            
                except Exception as e:
                    logger.error(f"Capture error: {e}")
                    
            stream.stop_stream()
            stream.close()
            logger.info("Audio capture stopped")
            
        except Exception as e:
            logger.error(f"Failed to start capture: {e}")
            import traceback
            traceback.print_exc()
    
    def _generate_test_audio(self):
        """Generate test audio for testing"""
        logger.info("Generating test audio...")
        sample_rate = 48000
        chunk_size = 2048
        
        while self.running:
            # Generate sine wave
            t = np.linspace(0, chunk_size/sample_rate, chunk_size)
            frequency = 440 + 100 * np.sin(2 * np.pi * 0.5 * time.time())
            audio = np.sin(2 * np.pi * frequency * t) * 0.3
            audio_int16 = (audio * 32767).astype(np.int16)
            
            data = audio_int16.tobytes()
            self.audio_queue.put(data)
            self.stats['bytes_captured'] += len(data)
            self.stats['chunks_captured'] += 1
            
            time.sleep(chunk_size / sample_rate)
    
    def _print_status(self):
        """Print status periodically"""
        while self.running:
            time.sleep(5)
            runtime = time.time() - self.stats['start_time']
            capture_rate = self.stats['bytes_captured'] / runtime
            send_rate = self.stats['bytes_sent'] / runtime
            
            logger.info(f"""
📊 Audio Bridge Status:
   Runtime: {runtime:.1f}s
   Captured: {self.stats['chunks_captured']} chunks, {self.stats['bytes_captured']:,} bytes
   Sent: {self.stats['chunks_sent']} chunks, {self.stats['bytes_sent']:,} bytes
   Capture rate: {capture_rate:.1f} bytes/sec
   Send rate: {send_rate:.1f} bytes/sec
   Queue size: {self.audio_queue.qsize()}
""")
    
    async def _stream_audio(self):
        """Stream audio to server via WebSocket"""
        retry_count = 0
        
        while self.running and retry_count < 5:
            try:
                logger.info(f"Connecting to {self.server_url}")
                
                async with websockets.connect(
                    self.server_url,
                    ping_interval=20,
                    ping_timeout=10
                ) as websocket:
                    self.websocket = websocket
                    logger.info("✅ Connected to Docker transcriber")
                    retry_count = 0
                    
                    # Send initial info
                    await websocket.send(json.dumps({
                        'type': 'info',
                        'mode': self.mode,
                        'client': 'windows_audio_capture_enhanced',
                        'device_index': self.device_index
                    }))
                    
                    # Start command handler and message receiver
                    command_task = asyncio.create_task(self.handle_commands())
                    receiver_task = asyncio.create_task(self.message_receiver())
                    
                    # Stream audio
                    while self.running:
                        try:
                            # Get audio from queue
                            if not self.audio_queue.empty():
                                data = self.audio_queue.get_nowait()
                                await websocket.send(data)
                                self.stats['bytes_sent'] += len(data)
                                self.stats['chunks_sent'] += 1
                            else:
                                await asyncio.sleep(0.01)
                                
                        except asyncio.CancelledError:
                            break
                        except Exception as e:
                            logger.error(f"Send error: {e}")
                            break
                    
                    # Cancel tasks
                    command_task.cancel()
                    receiver_task.cancel()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection error: {e}")
                retry_count += 1
                if retry_count < 5 and self.running:
                    logger.info(f"Retrying in 5 seconds... ({retry_count}/5)")
                    await asyncio.sleep(5)
        
        self.websocket = None
    
    def stop(self):
        """Stop capture gracefully"""
        logger.info("Stopping audio capture...")
        self.running = False
        
        # Cancel WebSocket task
        if self.ws_task and not self.ws_task.done():
            self.ws_task.cancel()
        
        # Wait for threads
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
            
        # Close PyAudio
        self.audio.terminate()
        
        logger.info("Audio capture stopped")

async def main():
    parser = argparse.ArgumentParser(description='Windows Audio Capture Client')
    parser.add_argument('--mode', choices=['loopback', 'microphone', 'test'], 
                       default='loopback', help='Capture mode')
    parser.add_argument('--server', default='ws://localhost:8766', 
                       help='WebSocket server URL')
    parser.add_argument('--device', type=int, help='Audio device index')
    parser.add_argument('--list-devices', action='store_true', 
                       help='List available devices and exit')
    
    args = parser.parse_args()
    
    capture = WindowsAudioCapture(mode=args.mode, server_url=args.server, 
                                  device_index=args.device)
    
    if args.list_devices:
        print("\n🎤 Available Audio Devices:")
        print("-" * 80)
        for device in capture.get_devices():
            print(f"[{device['index']}] {device['name']}")
            print(f"    Channels: {device['channels']}, "
                  f"Sample Rate: {device['sample_rate']}, "
                  f"Loopback: {device['loopback']}, "
                  f"Host API: {device['host_api']}")
        return
    
    print(f"🎤 Starting {args.mode} capture...")
    print(f"📡 Streaming to: {args.server}")
    print("🛑 Press Ctrl+C to stop\n")
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\n\n🛑 Stopping audio capture...")
        capture.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await capture.start_capture()
    except KeyboardInterrupt:
        pass
    finally:
        capture.stop()

if __name__ == "__main__":
    # For Windows, use a different event loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())