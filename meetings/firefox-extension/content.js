// Content script - runs on web pages
let floatingWidget = null;
let lastTranscription = '';
let autoInsert = false;

// Platform-specific selectors for chat input
const CHAT_SELECTORS = {
  'meet.google.com': [
    'textarea[aria-label*="chat" i]',
    'textarea[aria-label*="message" i]',
    'textarea[jsname="YPqjbf"]',
    'div[contenteditable="true"][aria-label*="message" i]',
    'input[aria-label*="Send a message" i]'
  ],
  'zoom.us': [
    'textarea[aria-label*="chat" i]',
    '#chatTextArea',
    'div[contenteditable="true"][role="textbox"]'
  ],
  'teams.microsoft.com': [
    'div[data-tid="ckeditor"]',
    'div[contenteditable="true"][role="textbox"]',
    'p[data-placeholder*="message" i]',
    'div[aria-label*="Type a new message" i]'
  ],
  'default': [
    'input[type="text"]:focus',
    'textarea:focus',
    'div[contenteditable="true"]:focus'
  ]
};

// Create floating widget
function createFloatingWidget() {
  if (floatingWidget) return;
  
  floatingWidget = document.createElement('div');
  floatingWidget.id = 'transcription-widget';
  floatingWidget.innerHTML = `
    <div class="widget-header">
      <span class="widget-title">Live Transcription</span>
      <span class="widget-status" id="connection-status">●</span>
      <button class="widget-minimize" id="minimize-btn">−</button>
    </div>
    <div class="widget-content" id="widget-content">
      <div class="transcription-display" id="transcription-display">
        <p class="waiting-message">Waiting for transcriptions...</p>
      </div>
      <div class="widget-controls">
        <button class="widget-btn" id="copy-btn" title="Copy to clipboard">📋 Copy</button>
        <button class="widget-btn" id="insert-btn" title="Insert into chat">💬 Insert</button>
        <button class="widget-btn" id="auto-btn" title="Toggle auto-insert">🔄 Auto: OFF</button>
        <button class="widget-btn" id="clear-btn" title="Clear display">🗑️ Clear</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(floatingWidget);
  
  // Make widget draggable
  makeDraggable(floatingWidget);
  
  // Event listeners
  document.getElementById('minimize-btn').addEventListener('click', toggleMinimize);
  document.getElementById('copy-btn').addEventListener('click', copyLastTranscription);
  document.getElementById('insert-btn').addEventListener('click', insertLastTranscription);
  document.getElementById('auto-btn').addEventListener('click', toggleAutoInsert);
  document.getElementById('clear-btn').addEventListener('click', clearDisplay);
}

// Make element draggable
function makeDraggable(element) {
  let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
  const header = element.querySelector('.widget-header');
  
  header.onmousedown = dragMouseDown;
  
  function dragMouseDown(e) {
    e = e || window.event;
    e.preventDefault();
    pos3 = e.clientX;
    pos4 = e.clientY;
    document.onmouseup = closeDragElement;
    document.onmousemove = elementDrag;
  }
  
  function elementDrag(e) {
    e = e || window.event;
    e.preventDefault();
    pos1 = pos3 - e.clientX;
    pos2 = pos4 - e.clientY;
    pos3 = e.clientX;
    pos4 = e.clientY;
    element.style.top = (element.offsetTop - pos2) + "px";
    element.style.left = (element.offsetLeft - pos1) + "px";
  }
  
  function closeDragElement() {
    document.onmouseup = null;
    document.onmousemove = null;
  }
}

// Toggle minimize
function toggleMinimize() {
  const content = document.getElementById('widget-content');
  const btn = document.getElementById('minimize-btn');
  
  if (content.style.display === 'none') {
    content.style.display = 'block';
    btn.textContent = '−';
  } else {
    content.style.display = 'none';
    btn.textContent = '+';
  }
}

// Update transcription display
function updateTranscription(data) {
  const display = document.getElementById('transcription-display');
  
  // Clear waiting message
  const waitingMsg = display.querySelector('.waiting-message');
  if (waitingMsg) waitingMsg.remove();
  
  // Create transcription element
  const transcriptionEl = document.createElement('div');
  transcriptionEl.className = 'transcription-item';
  
  const timestamp = new Date(data.timestamp).toLocaleTimeString();
  
  transcriptionEl.innerHTML = `
    <div class="transcription-time">${timestamp}</div>
    <div class="transcription-text" data-lang="${data.language}">
      <span class="lang-tag">${data.language.toUpperCase()}</span>
      ${data.text}
    </div>
    ${data.translation ? `
      <div class="transcription-translation">
        <span class="lang-tag">TRANS</span>
        ${data.translation}
      </div>
    ` : ''}
  `;
  
  display.appendChild(transcriptionEl);
  
  // Keep only last 10 transcriptions
  while (display.children.length > 10) {
    display.removeChild(display.firstChild);
  }
  
  // Scroll to bottom
  display.scrollTop = display.scrollHeight;
  
  // Update last transcription
  lastTranscription = data.translation || data.text;
  
  // Auto-insert if enabled
  if (autoInsert) {
    insertText(lastTranscription, true); // true = auto-submit
  }
}

// Find chat input element
function findChatInput() {
  const hostname = window.location.hostname;
  const selectors = CHAT_SELECTORS[hostname] || CHAT_SELECTORS.default;
  
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) return element;
  }
  
  // Try all selectors as fallback
  for (const selectorList of Object.values(CHAT_SELECTORS)) {
    for (const selector of selectorList) {
      const element = document.querySelector(selector);
      if (element) return element;
    }
  }
  
  return null;
}

// Insert text into chat
function insertText(text, autoSubmit = false) {
  const chatInput = findChatInput();
  
  if (!chatInput) {
    console.warn('Could not find chat input');
    showNotification('Could not find chat input field');
    return false;
  }
  
  // Handle different input types
  if (chatInput.tagName === 'TEXTAREA' || chatInput.tagName === 'INPUT') {
    // Append to existing text
    const existingText = chatInput.value;
    chatInput.value = existingText ? existingText + ' ' + text : text;
    chatInput.focus();
    
    // Trigger input event
    chatInput.dispatchEvent(new Event('input', { bubbles: true }));
    chatInput.dispatchEvent(new Event('change', { bubbles: true }));
    
    // Auto-submit if enabled
    if (autoSubmit) {
      setTimeout(() => {
        submitChat(chatInput);
      }, 100);
    }
  } else if (chatInput.contentEditable === 'true') {
    chatInput.focus();
    
    // Append to existing content
    const existingText = chatInput.textContent || chatInput.innerText || '';
    const newText = existingText ? existingText + ' ' + text : text;
    
    // Set text content
    chatInput.textContent = newText;
    
    // Move cursor to end
    const range = document.createRange();
    const sel = window.getSelection();
    range.selectNodeContents(chatInput);
    range.collapse(false);
    sel.removeAllRanges();
    sel.addRange(range);
    
    // Trigger input events
    chatInput.dispatchEvent(new Event('input', { bubbles: true }));
    chatInput.dispatchEvent(new InputEvent('input', { 
      bubbles: true,
      data: text,
      inputType: 'insertText'
    }));
    
    // Auto-submit if enabled
    if (autoSubmit) {
      setTimeout(() => {
        submitChat(chatInput);
      }, 100);
    }
  }
  
  showNotification('Text inserted into chat');
  return true;
}

// Submit chat message
function submitChat(chatInput) {
  const hostname = window.location.hostname;
  
  // Platform-specific submit methods
  if (hostname.includes('meet.google.com')) {
    // Google Meet - look for send button
    const sendButton = document.querySelector('[aria-label*="Send a message"]') ||
                      document.querySelector('[aria-label*="Send"]') ||
                      document.querySelector('button[jsname="SoqoBf"]');
    
    if (sendButton) {
      sendButton.click();
    } else {
      // Fallback: Enter key
      const enterEvent = new KeyboardEvent('keydown', {
        key: 'Enter',
        code: 'Enter',
        keyCode: 13,
        which: 13,
        bubbles: true
      });
      chatInput.dispatchEvent(enterEvent);
    }
  } else if (hostname.includes('zoom.us')) {
    // Zoom - Enter key
    const enterEvent = new KeyboardEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
      which: 13,
      bubbles: true
    });
    chatInput.dispatchEvent(enterEvent);
  } else if (hostname.includes('teams.microsoft.com')) {
    // Teams - look for send button
    const sendButton = document.querySelector('[data-tid="newMessageCommands-send"]') ||
                      document.querySelector('[aria-label*="Send"]') ||
                      document.querySelector('button[title*="Send"]');
    
    if (sendButton) {
      sendButton.click();
    } else {
      // Fallback: Ctrl+Enter for Teams
      const enterEvent = new KeyboardEvent('keydown', {
        key: 'Enter',
        code: 'Enter',
        keyCode: 13,
        which: 13,
        ctrlKey: true,
        bubbles: true
      });
      chatInput.dispatchEvent(enterEvent);
    }
  } else {
    // Generic: Try Enter key
    const enterEvent = new KeyboardEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
      which: 13,
      bubbles: true
    });
    chatInput.dispatchEvent(enterEvent);
  }
  
  showNotification('Message sent');
}

// Copy to clipboard
function copyLastTranscription() {
  if (!lastTranscription) {
    showNotification('No transcription to copy');
    return;
  }
  
  navigator.clipboard.writeText(lastTranscription).then(() => {
    showNotification('Copied to clipboard');
  }).catch(() => {
    // Fallback
    const textarea = document.createElement('textarea');
    textarea.value = lastTranscription;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showNotification('Copied to clipboard');
  });
}

// Insert last transcription
function insertLastTranscription() {
  if (!lastTranscription) {
    showNotification('No transcription to insert');
    return;
  }
  
  insertText(lastTranscription, autoInsert); // Pass autoInsert flag for auto-submit
}

// Toggle auto-insert
function toggleAutoInsert() {
  autoInsert = !autoInsert;
  const btn = document.getElementById('auto-btn');
  btn.textContent = `🔄 Auto: ${autoInsert ? 'ON' : 'OFF'}`;
  btn.classList.toggle('active', autoInsert);
  
  showNotification(`Auto-insert ${autoInsert ? 'enabled' : 'disabled'}`);
}

// Clear display
function clearDisplay() {
  const display = document.getElementById('transcription-display');
  display.innerHTML = '<p class="waiting-message">Waiting for transcriptions...</p>';
  lastTranscription = '';
  showNotification('Display cleared');
}

// Show notification
function showNotification(message) {
  const notification = document.createElement('div');
  notification.className = 'widget-notification';
  notification.textContent = message;
  
  floatingWidget.appendChild(notification);
  
  setTimeout(() => {
    notification.remove();
  }, 2000);
}

// Message listener
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.type) {
    case 'new_transcription':
      updateTranscription(request.data);
      break;
      
    case 'connection_status':
      const statusEl = document.getElementById('connection-status');
      if (statusEl) {
        statusEl.classList.toggle('connected', request.connected);
        statusEl.classList.toggle('disconnected', !request.connected);
      }
      break;
      
    case 'insert_text':
      insertText(request.text);
      break;
  }
});

// Initialize widget
if (document.body) {
  createFloatingWidget();
} else {
  document.addEventListener('DOMContentLoaded', createFloatingWidget);
}

// Update connection status
browser.runtime.sendMessage({ type: 'get_status' }, (response) => {
  if (response && response.connected) {
    const statusEl = document.getElementById('connection-status');
    if (statusEl) {
      statusEl.classList.add('connected');
    }
  }
});