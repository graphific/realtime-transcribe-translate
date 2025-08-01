#!/usr/bin/env python3
"""
WebSocket-enabled transcriber server
Standalone WebSocket server that can be imported into any transcriber
"""

import asyncio
import websockets
import json
import threading
import time
from datetime import datetime
import queue
import logging
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TranscriptionWebSocketServer:
    """WebSocket server for broadcasting transcriptions to browser extensions"""
    
    def __init__(self, port=8765, host='localhost'):
        self.port = port
        self.host = host
        self.clients = set()
        self.message_queue = queue.Queue()
        self.server_thread = None
        self.loop = None
        self.server = None
        self.running = False
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'clients_connected': 0,
            'total_connections': 0
        }
        
    def start(self):
        """Start WebSocket server in background thread"""
        if self.running:
            logger.warning("Server already running")
            return
            
        self.running = True
        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(1)
        logger.info(f"🌐 WebSocket server started on ws://{self.host}:{self.port}")
        
    def stop(self):
        """Stop the WebSocket server"""
        logger.info("Stopping WebSocket server...")
        self.running = False
        
        if self.loop and self.server:
            # Cancel all clients
            for client in self.clients.copy():
                asyncio.run_coroutine_threadsafe(
                    client.close(),
                    self.loop
                )
            
            # Stop server
            self.server.close()
            asyncio.run_coroutine_threadsafe(
                self.server.wait_closed(),
                self.loop
            )
            
        if self.server_thread:
            self.server_thread.join(timeout=5)
            
        logger.info("✅ WebSocket server stopped")
        
    def _run_server(self):
        """Run the asyncio event loop"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._start_server())
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.loop.close()
            
    async def _start_server(self):
        """Start the WebSocket server"""
        try:
            self.server = await websockets.serve(
                self.handle_client, 
                self.host, 
                self.port,
                ping_interval=20,
                ping_timeout=10
            )
            logger.info(f"Server listening on {self.host}:{self.port}")
            
            # Keep server running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            
    async def handle_client(self, websocket):
        """Handle new client connections with better error handling"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}" if websocket.remote_address else "unknown"
        
        # Add to clients set immediately
        self.clients.add(websocket)
        self.stats['total_connections'] += 1
        self.stats['clients_connected'] = len(self.clients)
        
        logger.info(f"✅ Client connected: {client_id} (Total: {len(self.clients)})")
        
        try:
            # Send connection confirmation
            await websocket.send(json.dumps({
                "type": "connection",
                "status": "connected",
                "message": "Transcription server connected",
                "server_version": "1.0",
                "timestamp": datetime.now().isoformat()
            }))
            
            # Keep connection alive and handle client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from {client_id}: {message}")
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected normally")
        except websockets.exceptions.InvalidMessage as e:
            logger.warning(f"Invalid message from {client_id}: {e}")
        except EOFError:
            logger.warning(f"Client {client_id} connection ended unexpectedly")
        except Exception as e:
            logger.error(f"Unexpected error with client {client_id}: {e}")
        finally:
            # Always remove from clients set
            self.clients.discard(websocket)
            self.stats['clients_connected'] = len(self.clients)
            logger.info(f"❌ Client removed: {client_id} (Remaining: {len(self.clients)})")
                
    async def _handle_client_message(self, websocket, data):
        """Handle messages from clients"""
        msg_type = data.get('type', '')
        
        if msg_type == 'ping':
            # Respond to ping
            await websocket.send(json.dumps({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }))
        elif msg_type == 'get_stats':
            # Send server statistics
            await websocket.send(json.dumps({
                "type": "stats",
                "data": self.stats,
                "timestamp": datetime.now().isoformat()
            }))
        else:
            logger.debug(f"Received message type: {msg_type}")
            
    def broadcast_transcription(self, text, lang="unknown", translation=None, confidence=None):
        """Send transcription to all connected clients"""
        message = {
            "type": "transcription",
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "language": lang,
            "translation": translation,
            "confidence": confidence
        }
        
        # Send to all connected clients
        if self.clients and self.loop:
            self.stats['messages_sent'] += 1
            asyncio.run_coroutine_threadsafe(
                self._broadcast(json.dumps(message)),
                self.loop
            )
            logger.debug(f"Broadcasted transcription to {len(self.clients)} clients")
            
    async def _broadcast(self, message):
        """Broadcast message to all clients"""
        if self.clients:
            # Send to all clients concurrently
            disconnected = []
            tasks = []
            
            for client in self.clients:
                tasks.append(self._send_to_client(client, message, disconnected))
                
            await asyncio.gather(*tasks)
            
            # Remove disconnected clients
            for client in disconnected:
                self.clients.discard(client)
                
    async def _send_to_client(self, client, message, disconnected_list):
        """Send message to a single client with better error handling"""
        try:
            await asyncio.wait_for(client.send(message), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Client send timeout - removing client")
            disconnected_list.append(client)
        except websockets.exceptions.ConnectionClosed:
            disconnected_list.append(client)
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
            disconnected_list.append(client)
            
    def send_status(self, status, details=None):
        """Send status update to clients"""
        message = {
            "type": "status",
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "details": details
        }
        
        if self.clients and self.loop:
            asyncio.run_coroutine_threadsafe(
                self._broadcast(json.dumps(message)),
                self.loop
            )
            
    def send_error(self, error_message):
        """Send error notification to clients"""
        message = {
            "type": "error",
            "timestamp": datetime.now().isoformat(),
            "error": error_message
        }
        
        if self.clients and self.loop:
            asyncio.run_coroutine_threadsafe(
                self._broadcast(json.dumps(message)),
                self.loop
            )
            
    def get_client_count(self):
        """Get number of connected clients"""
        return len(self.clients)
        
    def is_running(self):
        """Check if server is running"""
        return self.running and self.server_thread and self.server_thread.is_alive()


# Convenience functions for integration
def create_websocket_server(port=8765, host='localhost'):
    """Create and start a WebSocket server"""
    server = TranscriptionWebSocketServer(port, host)
    server.start()
    return server


# Example integration mixin
class WebSocketTranscriberMixin:
    """Mixin to add WebSocket broadcasting to any transcriber class"""
    
    def init_websocket(self, port=8765):
        """Initialize WebSocket server"""
        self.ws_server = TranscriptionWebSocketServer(port)
        self.ws_server.start()
        logger.info("WebSocket server initialized")
        
    def broadcast_transcription(self, text, lang="unknown", translation=None, confidence=None):
        """Send transcription to all connected clients with better error handling"""
        if not self.clients or not self.loop:
            logger.debug("No clients connected or loop not available")
            return
            
        message = {
            "type": "transcription",
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "language": lang,
            "translation": translation,
            "confidence": confidence
        }
        
        # Send to all connected clients
        self.stats['messages_sent'] += 1
        
        try:
            asyncio.run_coroutine_threadsafe(
                self._broadcast(json.dumps(message)),
                self.loop
            )
            logger.debug(f"Broadcasted transcription to {len(self.clients)} clients")
        except Exception as e:
            logger.error(f"Error broadcasting transcription: {e}")
            
    def cleanup_websocket(self):
        """Stop WebSocket server"""
        if hasattr(self, 'ws_server'):
            self.ws_server.stop()


# Standalone test server
def run_test_server():
    """Run a test WebSocket server"""
    print("🚀 Starting WebSocket test server...")
    print("📡 Clients can connect to ws://localhost:8765")
    print("🛑 Press Ctrl+C to stop\n")
    
    server = TranscriptionWebSocketServer()
    server.start()
    
    # Handle shutdown
    def signal_handler(sig, frame):
        print("\n\nShutting down...")
        server.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    # Simulate transcriptions
    test_messages = [
        ("Hello, this is a test transcription", "en", "Olá, esta é uma transcrição de teste"),
        ("Como você está hoje?", "pt", "How are you today?"),
        ("The meeting will start in 5 minutes", "en", "A reunião começará em 5 minutos"),
        ("Obrigado pela sua participação", "pt", "Thank you for your participation")
    ]
    
    try:
        message_index = 0
        while True:
            time.sleep(5)
            
            # Get next test message
            text, lang, translation = test_messages[message_index % len(test_messages)]
            message_index += 1
            
            # Send transcription
            server.broadcast_transcription(text, lang, translation, confidence=0.95)
            print(f"📤 Sent: [{lang}] {text}")
            
            # Send status update
            server.send_status(f"Processed message {message_index}")
            
            # Show stats
            if message_index % 5 == 0:
                print(f"📊 Stats: {server.stats}")
                
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    # Run test server when executed directly
    run_test_server()