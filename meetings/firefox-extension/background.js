// Background script - manages WebSocket connection
let ws = null;
let isConnected = false;
let transcriptionBuffer = [];
let reconnectInterval = null;

// Connect to WebSocket server
function connectWebSocket() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    return;
  }

  try {
    ws = new WebSocket('ws://localhost:8765');
    
    ws.onopen = () => {
      console.log('Connected to transcription server');
      isConnected = true;
      
      // Clear reconnect interval
      if (reconnectInterval) {
        clearInterval(reconnectInterval);
        reconnectInterval = null;
      }
      
      // Notify popup and content scripts
      browser.runtime.sendMessage({
        type: 'connection_status',
        connected: true
      }).catch(() => {}); // Ignore if no listeners
      
      // Update badge
      browser.browserAction.setBadgeText({ text: '✓' });
      browser.browserAction.setBadgeBackgroundColor({ color: '#4CAF50' });
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received:', data);
      
      if (data.type === 'transcription') {
        // Add to buffer
        transcriptionBuffer.push(data);
        if (transcriptionBuffer.length > 100) {
          transcriptionBuffer.shift(); // Keep last 100
        }
        
        // Send to active tab's content script
        browser.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs[0]) {
            browser.tabs.sendMessage(tabs[0].id, {
              type: 'new_transcription',
              data: data
            }).catch(() => {}); // Ignore if content script not ready
          }
        });
        
        // Update badge with count
        browser.browserAction.setBadgeText({ 
          text: transcriptionBuffer.length.toString() 
        });
      }
    };
    
    ws.onclose = () => {
      console.log('Disconnected from transcription server');
      isConnected = false;
      ws = null;
      
      // Update badge
      browser.browserAction.setBadgeText({ text: '✗' });
      browser.browserAction.setBadgeBackgroundColor({ color: '#F44336' });
      
      // Notify popup and content scripts
      browser.runtime.sendMessage({
        type: 'connection_status',
        connected: false
      }).catch(() => {});
      
      // Try to reconnect every 5 seconds
      if (!reconnectInterval) {
        reconnectInterval = setInterval(connectWebSocket, 5000);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
  } catch (error) {
    console.error('Failed to connect:', error);
    
    // Retry connection
    if (!reconnectInterval) {
      reconnectInterval = setInterval(connectWebSocket, 5000);
    }
  }
}

// Message handler
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.type) {
    case 'get_status':
      sendResponse({
        connected: isConnected,
        bufferSize: transcriptionBuffer.length
      });
      break;
      
    case 'get_buffer':
      sendResponse(transcriptionBuffer);
      break;
      
    case 'clear_buffer':
      transcriptionBuffer = [];
      browser.browserAction.setBadgeText({ text: '0' });
      sendResponse({ success: true });
      break;
      
    case 'copy_to_clipboard':
      // Copy text to clipboard
      const textarea = document.createElement('textarea');
      textarea.value = request.text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      sendResponse({ success: true });
      break;
      
    case 'insert_text':
      // Forward to content script
      browser.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0]) {
          browser.tabs.sendMessage(tabs[0].id, {
            type: 'insert_text',
            text: request.text
          });
        }
      });
      sendResponse({ success: true });
      break;
  }
  
  return true; // Keep message channel open for async response
});

// Initialize connection
connectWebSocket();

// Keep trying to connect
setInterval(() => {
  if (!isConnected) {
    connectWebSocket();
  }
}, 10000);