// Enhanced Background script with toolbar popup toggle functionality
let ws = null;
let isConnected = false;
let transcriptionBuffer = [];
let reconnectInterval = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_DELAY = 2000;

// NEW: Popup state management
let popupWindows = new Map(); // Track popup windows by tab
let popupState = 'closed'; // 'closed', 'opening', 'open'

// Ensure browser action is always visible
browser.browserAction.setBadgeText({ text: '' });
browser.browserAction.setBadgeBackgroundColor({ color: '#2196F3' });

// NEW: Handle browser action clicks (toolbar icon)
browser.browserAction.onClicked.addListener((tab) => {
  console.log('Toolbar icon clicked, current state:', popupState);
  togglePopupWindow(tab);
});

// NEW: Create and manage popup window
function togglePopupWindow(tab) {
  const tabId = tab.id;
  
  // If popup exists for this tab, close it
  if (popupWindows.has(tabId)) {
    const windowId = popupWindows.get(tabId);
    browser.windows.remove(windowId).then(() => {
      popupWindows.delete(tabId);
      popupState = 'closed';
      console.log('Popup closed');
    }).catch(err => {
      console.error('Error closing popup:', err);
      popupWindows.delete(tabId); // Clean up even if error
      popupState = 'closed';
    });
    return;
  }
  
  // Create new popup window
  if (popupState === 'closed') {
    popupState = 'opening';
    
    browser.windows.create({
      url: browser.runtime.getURL('popup.html'),
      type: 'popup',
      width: 320,
      height: 500,
      left: Math.round((screen.width - 320) - 50), // Position near right edge
      top: 100,
      focused: true
    }).then((window) => {
      popupWindows.set(tabId, window.id);
      popupState = 'open';
      console.log('Popup opened:', window.id);
      
      // Update badge to show popup is open
      browser.browserAction.setBadgeText({ text: '●' });
      browser.browserAction.setBadgeBackgroundColor({ color: '#4CAF50' });
      
    }).catch(err => {
      console.error('Error creating popup:', err);
      popupState = 'closed';
    });
  }
}

// NEW: Handle popup window closing
browser.windows.onRemoved.addListener((windowId) => {
  // Check if this was one of our popup windows
  for (let [tabId, popupWindowId] of popupWindows.entries()) {
    if (popupWindowId === windowId) {
      popupWindows.delete(tabId);
      popupState = 'closed';
      console.log('Popup window closed:', windowId);
      
      // Update badge to show connection status instead
      if (isConnected) {
        browser.browserAction.setBadgeText({ text: transcriptionBuffer.length.toString() });
        browser.browserAction.setBadgeBackgroundColor({ color: '#4CAF50' });
      } else {
        browser.browserAction.setBadgeText({ text: '✗' });
        browser.browserAction.setBadgeBackgroundColor({ color: '#F44336' });
      }
      break;
    }
  }
});

// NEW: Update badge based on state
function updateBadge() {
  if (popupState === 'open') {
    browser.browserAction.setBadgeText({ text: '●' });
    browser.browserAction.setBadgeBackgroundColor({ color: '#4CAF50' });
  } else if (isConnected) {
    if (transcriptionBuffer.length > 0) {
      browser.browserAction.setBadgeText({ text: transcriptionBuffer.length.toString() });
    } else {
      browser.browserAction.setBadgeText({ text: '✓' });
    }
    browser.browserAction.setBadgeBackgroundColor({ color: '#4CAF50' });
  } else {
    browser.browserAction.setBadgeText({ text: '✗' });
    browser.browserAction.setBadgeBackgroundColor({ color: '#F44336' });
  }
}

// Enhanced connection function with exponential backoff
function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
    console.log('WebSocket already connecting or connected');
    return;
  }

  if (ws) {
    ws.close();
    ws = null;
  }

  try {
    console.log(`WebSocket connection attempt ${reconnectAttempts + 1}`);
    ws = new WebSocket('ws://localhost:8765');
    
    const connectionTimeout = setTimeout(() => {
      if (ws.readyState === WebSocket.CONNECTING) {
        console.log('Connection timeout - closing socket');
        ws.close();
      }
    }, 10000);
    
    ws.onopen = () => {
      clearTimeout(connectionTimeout);
      console.log('✅ Connected to transcription server');
      isConnected = true;
      reconnectAttempts = 0;
      
      if (reconnectInterval) {
        clearInterval(reconnectInterval);
        reconnectInterval = null;
      }
      
      // Notify popup and content scripts
      browser.runtime.sendMessage({
        type: 'connection_status',
        connected: true
      }).catch(() => {});
      
      updateBadge();
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Received:', data);
        
        if (data.type === 'transcription') {
          transcriptionBuffer.push(data);
          if (transcriptionBuffer.length > 100) {
            transcriptionBuffer.shift();
          }
          
          // Send to active tab's content script
          browser.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]) {
              browser.tabs.sendMessage(tabs[0].id, {
                type: 'new_transcription',
                data: data
              }).catch(() => {});
            }
          });
          
          updateBadge();
        }
      } catch (error) {
        console.error('Error parsing message:', error);
      }
    };
    
    ws.onclose = (event) => {
      clearTimeout(connectionTimeout);
      console.log(`❌ WebSocket closed. Code: ${event.code}, Reason: ${event.reason}`);
      isConnected = false;
      ws = null;
      
      updateBadge();
      
      browser.runtime.sendMessage({
        type: 'connection_status',
        connected: false
      }).catch(() => {});
      
      scheduleReconnect();
    };
    
    ws.onerror = (error) => {
      clearTimeout(connectionTimeout);
      console.error('WebSocket error:', error);
      
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
    
  } catch (error) {
    console.error('Failed to create WebSocket:', error);
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.log('Max reconnection attempts reached. Stopping.');
    browser.browserAction.setBadgeText({ text: '💀' });
    browser.browserAction.setBadgeBackgroundColor({ color: '#666666' });
    return;
  }
  
  if (reconnectInterval) {
    clearInterval(reconnectInterval);
  }
  
  const delay = Math.min(RECONNECT_DELAY * Math.pow(2, reconnectAttempts), 30000);
  console.log(`Scheduling reconnect in ${delay}ms (attempt ${reconnectAttempts + 1})`);
  
  reconnectInterval = setTimeout(() => {
    reconnectAttempts++;
    connectWebSocket();
  }, delay);
}

// Enhanced message handler
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
  try {
    switch (request.type) {
      case 'get_status':
        sendResponse({
          connected: isConnected,
          bufferSize: transcriptionBuffer.length,
          reconnectAttempts: reconnectAttempts,
          popupState: popupState
        });
        break;
        
      case 'get_buffer':
        sendResponse(transcriptionBuffer);
        break;
        
      case 'clear_buffer':
        transcriptionBuffer = [];
        updateBadge();
        sendResponse({ success: true });
        break;
        
      case 'force_reconnect':
        console.log('Force reconnect requested');
        reconnectAttempts = 0;
        if (reconnectInterval) {
          clearInterval(reconnectInterval);
          reconnectInterval = null;
        }
        connectWebSocket();
        sendResponse({ success: true });
        break;
        
      case 'copy_to_clipboard':
        try {
          const textarea = document.createElement('textarea');
          textarea.value = request.text || '';
          document.body.appendChild(textarea);
          textarea.select();
          const success = document.execCommand('copy');
          document.body.removeChild(textarea);
          
          sendResponse({ success: success });
        } catch (error) {
          console.error('Clipboard copy failed:', error);
          sendResponse({ success: false, error: error.message });
        }
        break;
        
      case 'insert_text':
        browser.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs[0]) {
            browser.tabs.sendMessage(tabs[0].id, {
              type: 'insert_text',
              text: request.text
            }).catch((error) => {
              console.warn('Failed to send insert_text to content script:', error);
            });
          }
        });
        sendResponse({ success: true });
        break;
        
      case 'toggle_popup':
        // NEW: Handle popup toggle from content script
        browser.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs[0]) {
            togglePopupWindow(tabs[0]);
          }
        });
        sendResponse({ success: true });
        break;
        
      case 'debug_info':
        sendResponse({
          isConnected: isConnected,
          reconnectAttempts: reconnectAttempts,
          bufferSize: transcriptionBuffer.length,
          wsState: ws ? ws.readyState : null,
          wsStateText: ws ? ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][ws.readyState] : 'NULL',
          popupState: popupState,
          activePopups: popupWindows.size
        });
        break;
        
      default:
        console.warn('Unknown message type:', request.type);
        sendResponse({ success: false, error: 'Unknown message type' });
    }
  } catch (error) {
    console.error('Error handling message:', error);
    sendResponse({ success: false, error: error.message });
  }
  
  return true;
});

// Listen for extension startup
browser.runtime.onStartup.addListener(() => {
  console.log('Extension started - connecting to WebSocket');
  connectWebSocket();
});

// Listen for extension installation/update
browser.runtime.onInstalled.addListener((details) => {
  console.log('Extension installed/updated:', details.reason);
  
  browser.browserAction.setBadgeText({ text: '●' });
  browser.browserAction.setBadgeBackgroundColor({ color: '#2196F3' });
  
  connectWebSocket();
  
  if (browser.notifications) {
    browser.notifications.create({
      type: 'basic',
      iconUrl: 'icon-48.png',
      title: 'Live Transcription Assistant',
      message: 'Click the toolbar icon to open the transcription panel!'
    }).catch(() => {
      console.log('Notifications not supported');
    });
  }
});

// Handle tab changes to inject content script if needed
browser.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    const meetingSites = [
      'meet.google.com',
      'zoom.us',
      'teams.microsoft.com',
      'teams.live.com'
    ];
    
    const isMeetingSite = meetingSites.some(site => tab.url.includes(site));
    
    if (isMeetingSite) {
      console.log('Meeting site detected:', tab.url);
      
      browser.tabs.sendMessage(tabId, { type: 'ping' }).catch(() => {
        console.log('Content script should load automatically on meeting site');
      });
    }
  }
});

// NEW: Handle tab switching - clean up popup windows for closed tabs
browser.tabs.onRemoved.addListener((tabId) => {
  if (popupWindows.has(tabId)) {
    const windowId = popupWindows.get(tabId);
    browser.windows.remove(windowId).catch(() => {
      console.log('Popup window already closed');
    });
    popupWindows.delete(tabId);
    
    if (popupWindows.size === 0) {
      popupState = 'closed';
    }
  }
});

// Initialize connection on script load
console.log('Background script loaded - initializing WebSocket connection');
connectWebSocket();

// Periodic health check
setInterval(() => {
  if (!isConnected && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
    console.log('Health check: Not connected, attempting reconnect');
    connectWebSocket();
  }
  
  updateBadge();
}, 30000);

// Handle extension suspension/wake
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    console.log('Extension became visible - checking connection');
    if (!isConnected) {
      connectWebSocket();
    }
  }
});

// Cleanup on extension disable/uninstall
browser.runtime.onSuspend.addListener(() => {
  console.log('Extension suspending - cleaning up');
  if (ws) {
    ws.close();
  }
  if (reconnectInterval) {
    clearInterval(reconnectInterval);
  }
  
  // Close all popup windows
  for (let windowId of popupWindows.values()) {
    browser.windows.remove(windowId).catch(() => {});
  }
  popupWindows.clear();
});

// Error handling
window.addEventListener('error', (event) => {
  console.error('Background script error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection in background:', event.reason);
});

console.log('Enhanced background script loaded with toolbar toggle support');