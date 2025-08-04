# api-server/websocket_server.py
import asyncio
import websockets
import json
import threading
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranscriptionWebSocketServer:
    """WebSocket server for browser extension communication"""
    
    def __init__(self, port=8765, host='0.0.0.0'):
        self.port = port
        self.host = host
        self.clients = set()
        self.running = False
        self.server = None
        self.loop = None
        self.thread = None
        
    def start(self):
        """Start WebSocket server in background thread"""
        if self.running:
            logger.warning("WebSocket server already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_server)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"WebSocket server starting on ws://{self.host}:{self.port}")
        
    def _run_server(self):
        """Run the asyncio event loop"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._start_server())
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
        finally:
            if self.loop:
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
            logger.info(f"WebSocket server listening on {self.host}:{self.port}")
            
            # Keep server running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            
    async def handle_client(self, websocket, path):
        """Handle client connections"""
        client_addr = websocket.remote_address if websocket.remote_address else "unknown"
        logger.info(f"Client connected: {client_addr}")
        self.clients.add(websocket)
        
        try:
            # Send connection confirmation
            await websocket.send(json.dumps({
                "type": "connection",
                "status": "connected",
                "message": "Connected to transcription server",
                "timestamp": datetime.now().isoformat()
            }))
            
            # Keep connection alive - THIS WAS MISSING!
            while True:
                try:
                    # Wait for messages or ping/pong
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    # Handle any incoming messages
                    if message:
                        logger.debug(f"Received from client: {message}")
                except asyncio.TimeoutError:
                    # Send ping to keep alive
                    await websocket.ping()
                except websockets.exceptions.ConnectionClosed:
                    break
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_addr}")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            self.clients.discard(websocket)
            
    def broadcast_transcription(self, text, lang="en", translation=None):
        """Send transcription to all connected clients"""
        if not self.clients or not self.loop:
            return
            
        message = json.dumps({
            "type": "transcription",
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "language": lang,
            "translation": translation
        })
        
        # Send to all clients
        asyncio.run_coroutine_threadsafe(
            self._broadcast(message),
            self.loop
        )
        
    async def _broadcast(self, message):
        """Broadcast message to all clients"""
        if self.clients:
            # Send to all clients concurrently
            disconnected = []
            for client in list(self.clients):
                try:
                    await client.send(message)
                except:
                    disconnected.append(client)
            
            # Remove disconnected clients
            for client in disconnected:
                self.clients.discard(client)

    def stop(self):
        """Stop the WebSocket server"""
        logger.info("Stopping WebSocket server...")
        self.running = False
        if self.server:
            self.server.close()
        if self.thread:
            self.thread.join(timeout=5)

# Global WebSocket server instance
ws_server = None

def get_websocket_server():
    """Get or create WebSocket server instance"""
    global ws_server
    if ws_server is None:
        ws_server = TranscriptionWebSocketServer()
    return ws_server