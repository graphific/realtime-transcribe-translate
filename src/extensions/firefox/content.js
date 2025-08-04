// Enhanced Content script with aggressive Teams CKEditor manipulation
let floatingWidget = null;
let lastTranscription = '';
let autoInsert = false;
let debugMode = false;

// Enhanced platform-specific selectors
const CHAT_SELECTORS = {
  'teams.microsoft.com': [
    // Primary CKEditor selectors
    'div[data-tid="ckeditor"][contenteditable="true"]',
    'div.ck-editor__editable[contenteditable="true"]',
    'div[role="textbox"][contenteditable="true"]',
    // Legacy selectors
    'div[contenteditable="true"][aria-label*="Type a message" i]',
    'div[contenteditable="true"][data-placeholder*="message" i]'
  ],
  'teams.live.com': [
    'div[data-tid="ckeditor"][contenteditable="true"]',
    'div.ck-editor__editable[contenteditable="true"]',
    'div[role="textbox"][contenteditable="true"]',
    'div[contenteditable="true"][aria-label*="Type a message" i]'
  ],
  'meet.google.com': [
    'textarea[aria-label*="chat" i]',
    'textarea[aria-label*="message" i]',
    'input[aria-label*="Send a message" i]'
  ],
  'zoom.us': [
    'textarea[aria-label*="chat" i]',
    '#chatTextArea'
  ]
};


// HACK: Teams gets cotnent send twice.
// TODO

// Helper functions
function isElementVisible(element) {
  if (!element) return false;
  const rect = element.getBoundingClientRect();
  const style = window.getComputedStyle(element);
  return rect.width > 0 && rect.height > 0 && 
         style.visibility !== 'hidden' && 
         style.display !== 'none' &&
         element.offsetParent !== null;
}

function isTeamsPlatform() {
  const hostname = window.location.hostname;
  return hostname.includes('teams.microsoft.com') || 
         hostname.includes('teams.live.com');
}

function findChatInput() {
  const hostname = window.location.hostname;
  const selectors = CHAT_SELECTORS[hostname] || [];
  
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element && isElementVisible(element)) {
      debugLog('Found chat input with selector:', selector);
      return element;
    }
  }
  
  debugLog('No chat input found');
  return null;
}

function debugLog(...args) {
  if (debugMode) {
    console.log('[DEBUG]', ...args);
  }
}

// Create floating widget with enhanced debug controls
function createFloatingWidget() {
  if (floatingWidget) return;
  
  floatingWidget = document.createElement('div');
  floatingWidget.id = 'transcription-widget';
  floatingWidget.innerHTML = `
    <div class="widget-header">
      <span class="widget-title">Live Transcription</span>
      <span class="widget-status" id="connection-status">●</span>
      <button class="widget-reconnect" id="reconnect-btn" title="Force reconnect">🔄</button>
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
      <div class="debug-controls" id="debug-controls" style="display: none;">
        <div style="margin: 8px 0; font-size: 12px; font-weight: bold; color: #666;">Debug Tools</div>
        <div class="debug-grid">
          <button class="debug-btn" id="debug-find-input">🔍 Find Input</button>
          <button class="debug-btn" id="debug-test-clipboard">📋 Test Clipboard</button>
          <button class="debug-btn" id="debug-test-insert">✏️ Test Insert</button>
          <button class="debug-btn" id="debug-analyze-dom">🏗️ Analyze DOM</button>
          <button class="debug-btn" id="debug-test-events">⚡ Test Events</button>
          <button class="debug-btn" id="debug-ckeditor">📝 CKEditor Info</button>
          <button class="debug-btn" id="debug-test-all">🧪 Test All Methods</button>
          <button class="debug-btn" id="debug-force-clear">🧹 Force Clear</button>
        </div>
        <div class="debug-output" id="debug-output"></div>
      </div>
      <div class="widget-controls">
        <button class="widget-btn debug-toggle" id="debug-toggle-btn" title="Toggle debug mode">🐛 Debug</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(floatingWidget);
  makeDraggable(floatingWidget);
  
  // Event listeners
  document.getElementById('minimize-btn').addEventListener('click', toggleMinimize);
  document.getElementById('reconnect-btn').addEventListener('click', forceReconnect);
  document.getElementById('copy-btn').addEventListener('click', copyLastTranscription);
  document.getElementById('insert-btn').addEventListener('click', insertLastTranscription);
  document.getElementById('auto-btn').addEventListener('click', toggleAutoInsert);
  document.getElementById('clear-btn').addEventListener('click', clearDisplay);
  document.getElementById('debug-toggle-btn').addEventListener('click', toggleDebugMode);
  
  // Debug button listeners
  document.getElementById('debug-find-input').addEventListener('click', debugFindInput);
  document.getElementById('debug-test-clipboard').addEventListener('click', debugTestClipboard);
  document.getElementById('debug-test-insert').addEventListener('click', debugTestInsert);
  document.getElementById('debug-analyze-dom').addEventListener('click', debugAnalyzeDOM);
  document.getElementById('debug-test-events').addEventListener('click', debugTestEvents);
  document.getElementById('debug-ckeditor').addEventListener('click', debugCKEditor);
  document.getElementById('debug-test-all').addEventListener('click', debugTestAllMethods);
  document.getElementById('debug-force-clear').addEventListener('click', debugClearInput);
  
  console.log('Floating widget with enhanced debug features created successfully');
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

// Widget control functions
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

function toggleDebugMode() {
  debugMode = !debugMode;
  const debugControls = document.getElementById('debug-controls');
  const debugBtn = document.getElementById('debug-toggle-btn');
  
  if (debugMode) {
    debugControls.style.display = 'block';
    debugBtn.textContent = '🐛 Debug ON';
    debugBtn.classList.add('active');
    showNotification('Debug mode enabled');
  } else {
    debugControls.style.display = 'none';
    debugBtn.textContent = '🐛 Debug';
    debugBtn.classList.remove('active');
    showNotification('Debug mode disabled');
  }
}

function forceReconnect() {
  showNotification('Reconnecting...');
  browser.runtime.sendMessage({ type: 'force_reconnect' }, (response) => {
    if (response && response.success) {
      showNotification('Reconnection initiated');
    } else {
      showNotification('Reconnection failed');
    }
  });
}

function updateTranscription(data) {
  const display = document.getElementById('transcription-display');
  
  const waitingMsg = display.querySelector('.waiting-message');
  if (waitingMsg) waitingMsg.remove();
  
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
  
  while (display.children.length > 10) {
    display.removeChild(display.firstChild);
  }
  
  display.scrollTop = display.scrollHeight;
  lastTranscription = data.translation || data.text;
  
  if (autoInsert) {
    insertText(lastTranscription, true);
  }
}

// MAIN TEXT INSERTION FUNCTION
function insertText(text, autoSubmit = false) {
  const chatInput = findChatInput();
  
  if (!chatInput) {
    debugLog('Could not find chat input');
    showNotification('Could not find chat input field');
    return false;
  }
  
  debugLog('Inserting text into:', chatInput.tagName, chatInput.className);
  
  if (isTeamsPlatform()) {
    return insertIntoTeamsCKEditor(chatInput, text, autoSubmit);
  } else {
    return insertIntoGenericInput(chatInput, text, autoSubmit);
  }
}

function insertIntoGenericInput(chatInput, text, autoSubmit) {
  try {
    chatInput.focus();
    
    if (chatInput.tagName === 'TEXTAREA' || chatInput.tagName === 'INPUT') {
      const existingText = chatInput.value;
      const newText = existingText ? existingText + ' ' + text : text;
      chatInput.value = newText;
    } else if (chatInput.contentEditable === 'true') {
      const existingText = chatInput.textContent || '';
      const newText = existingText ? existingText + ' ' + text : text;
      chatInput.textContent = newText;
      setCursorToEnd(chatInput);
    }
    
    triggerInputEvents(chatInput);
    
    if (autoSubmit) {
      setTimeout(() => submitGenericChat(chatInput), 200);
    }
    
    showNotification('Text inserted');
    return true;
  } catch (error) {
    debugLog('Error inserting text:', error);
    return false;
  }
}

// AGGRESSIVE TEAMS CKEDITOR INSERTION
function insertIntoTeamsCKEditor(chatInput, text, autoSubmit) {
  debugLog('🎯 Aggressive Teams insertion - direct CKEditor manipulation');
  
  try {
    // Method 1: Try to directly manipulate CKEditor's internal data
    if (insertUsingCKEditorAPI(chatInput, '1 '+text, autoSubmit)) {
      return true;
    }
    
    // Method 2: Force DOM manipulation with comprehensive event simulation
    if (insertUsingForcedDOM(chatInput, '2 '+text, autoSubmit)) {
      return true;
    }
    
    // Method 3: Use browser automation techniques
    if (insertUsingBrowserAutomation(chatInput, '3 '+ text, autoSubmit)) {
      return true;
    }
    
    // Method 4: Fallback to copy-paste instruction
    insertUsingClipboardInstruction(chatInput, '4 '+text);
    return false;
    
  } catch (error) {
    debugLog('Error in aggressive Teams insertion:', error);
    showNotification('All methods failed - try manual paste');
    return false;
  }
}

// Method 1: Try to find and use CKEditor's internal API
function insertUsingCKEditorAPI(chatInput, text, autoSubmit) {
  try {
    debugLog('Trying CKEditor API manipulation...');
    
    // Look for CKEditor instance in various places
    const editorInstances = [
      // Modern CKEditor 5
      chatInput._ckEditor,
      chatInput.ckeditorInstance,
      
      // Check window for CKEditor instances
      window.CKEDITOR && window.CKEDITOR.instances,
      
      // Look for CKEditor in the element's properties
      ...Object.keys(chatInput).filter(key => key.toLowerCase().includes('ck')).map(key => chatInput[key]),
      
      // Check parent elements
      chatInput.parentElement && chatInput.parentElement._ckEditor,
      
      // Look for any CKEditor references in the DOM
      ...Array.from(document.querySelectorAll('[class*="ck-"]')).map(el => el._ckEditor).filter(Boolean)
    ].filter(Boolean);
    
    debugLog(`Found ${editorInstances.length} potential CKEditor instances`);
    
    for (let i = 0; i < editorInstances.length; i++) {
      const editor = editorInstances[i];
      debugLog(`Testing editor instance ${i + 1}:`, typeof editor);
      
      try {
        // CKEditor 5 API
        if (editor && editor.model && editor.model.change) {
          debugLog('Trying CKEditor 5 model.change...');
          editor.model.change(writer => {
            const insertPosition = editor.model.document.selection.getFirstPosition();
            writer.insertText(text, insertPosition);
          });
          debugLog('✅ CKEditor 5 insertion successful');
          
          if (autoSubmit) {
            setTimeout(() => submitTeamsChat(chatInput), 300);
          }
          return true;
        }
        
        // CKEditor 5 setData API
        if (editor && editor.setData) {
          debugLog('Trying CKEditor 5 setData...');
          const existingData = editor.getData() || '';
          const newData = existingData ? existingData + ' ' + text : `<p>${text}</p>`;
          editor.setData(newData);
          debugLog('✅ CKEditor 5 setData successful');
          
          if (autoSubmit) {
            setTimeout(() => submitTeamsChat(chatInput), 300);
          }
          return true;
        }
        
        // CKEditor 4 API
        if (editor && editor.insertHtml) {
          debugLog('Trying CKEditor 4 insertHtml...');
          editor.insertHtml(text);
          debugLog('✅ CKEditor 4 insertion successful');
          
          if (autoSubmit) {
            setTimeout(() => submitTeamsChat(chatInput), 300);
          }
          return true;
        }
        
        // CKEditor 4 setData
        if (editor && editor.setData && typeof editor.setData === 'function') {
          debugLog('Trying CKEditor 4 setData...');
          const existingData = editor.getData() || '';
          const newData = existingData ? existingData + ' ' + text : text;
          editor.setData(newData);
          debugLog('✅ CKEditor 4 setData successful');
          
          if (autoSubmit) {
            setTimeout(() => submitTeamsChat(chatInput), 300);
          }
          return true;
        }
        
      } catch (e) {
        debugLog(`Editor instance ${i + 1} failed:`, e.message);
      }
    }
    
    debugLog('❌ No working CKEditor API found');
    return false;
    
  } catch (error) {
    debugLog('CKEditor API method failed:', error);
    return false;
  }
}

// Method 2: Force DOM manipulation with comprehensive event simulation
function insertUsingForcedDOM(chatInput, text, autoSubmit) {
  try {
    debugLog('Trying forced DOM manipulation...');
    
    // Step 1: Focus and activate the editor
    chatInput.focus();
    chatInput.click();
    
    // Step 2: Clear any existing content first
    chatInput.innerHTML = '';
    
    // Step 3: Create proper paragraph structure
    const paragraph = document.createElement('p');
    paragraph.textContent = text;
    
    // Remove any placeholder attributes
    paragraph.removeAttribute('data-placeholder');
    paragraph.classList.remove('ck-placeholder');
    
    chatInput.appendChild(paragraph);
    
    // Step 4: Set cursor to end of text
    const range = document.createRange();
    const selection = window.getSelection();
    range.setStart(paragraph.firstChild || paragraph, paragraph.textContent.length);
    range.setEnd(paragraph.firstChild || paragraph, paragraph.textContent.length);
    selection.removeAllRanges();
    selection.addRange(range);
    
    // Step 5: Remove placeholder classes from the editor
    chatInput.classList.remove('ck-blurred');
    chatInput.classList.add('ck-focused');
    
    // Step 6: Fire a comprehensive sequence of events
    const events = [
      // Focus events
      new FocusEvent('focusin', { bubbles: true }),
      new FocusEvent('focus', { bubbles: true }),
      
      // Mouse events (simulate clicking)
      new MouseEvent('mousedown', { bubbles: true }),
      new MouseEvent('mouseup', { bubbles: true }),
      new MouseEvent('click', { bubbles: true }),
      
      // Keyboard events (simulate typing)
      new KeyboardEvent('keydown', { key: 'a', bubbles: true }),
      new KeyboardEvent('keypress', { key: 'a', bubbles: true }),
      new KeyboardEvent('keyup', { key: 'a', bubbles: true }),
      
      // Input events
      new InputEvent('beforeinput', { 
        bubbles: true, 
        inputType: 'insertText',
        data: text
      }),
      new InputEvent('input', { 
        bubbles: true, 
        inputType: 'insertText',
        data: text
      }),
      
      // Change events
      new Event('change', { bubbles: true }),
      
      // CKEditor specific events
      new CustomEvent('ck-change', { 
        bubbles: true,
        detail: { source: 'user' }
      }),
      new CustomEvent('ck-update', { bubbles: true }),
      new CustomEvent('ckeditor:change', { bubbles: true }),
      
      // Composition events (for international input)
      new CompositionEvent('compositionstart', { bubbles: true }),
      new CompositionEvent('compositionupdate', { bubbles: true, data: text }),
      new CompositionEvent('compositionend', { bubbles: true, data: text })
    ];
    
    // Fire events on both the editor and paragraph
    events.forEach((event, index) => {
      setTimeout(() => {
        try {
          chatInput.dispatchEvent(event);
          paragraph.dispatchEvent(event);
          debugLog(`Fired event ${index + 1}/${events.length}: ${event.type}`);
        } catch (e) {
          debugLog(`Failed to fire event ${event.type}:`, e.message);
        }
      }, index * 10); // 10ms delay between events
    });
    
    // Step 7: Wait for events to process, then check result
    setTimeout(() => {
      const currentContent = chatInput.textContent || '';
      debugLog(`Content after forced DOM: "${currentContent}"`);
      
      if (currentContent.includes(text)) {
        debugLog('✅ Forced DOM manipulation successful');
        showNotification('Text inserted successfully');
        
        if (autoSubmit) {
          setTimeout(() => submitTeamsChat(chatInput), 300);
        }
        return true;
      } else {
        debugLog('❌ Forced DOM manipulation failed');
        return false;
      }
    }, events.length * 10 + 200);
    
    return true; // Optimistically return true
    
  } catch (error) {
    debugLog('Forced DOM method failed:', error);
    return false;
  }
}

// Method 3: Browser automation techniques
function insertUsingBrowserAutomation(chatInput, text, autoSubmit) {
  try {
    debugLog('Trying browser automation techniques...');
    
    // Focus the input
    chatInput.focus();
    chatInput.click();
    
    // Method 3a: Use document.execCommand to insert text
    try {
      // Select all existing content
      const range = document.createRange();
      range.selectNodeContents(chatInput);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      
      // Use execCommand to insert text
      const success = document.execCommand('insertText', false, text);
      debugLog(`execCommand insertText result: ${success}`);
      
      if (success) {
        debugLog('✅ Browser automation successful');
        
        if (autoSubmit) {
          setTimeout(() => submitTeamsChat(chatInput), 300);
        }
        return true;
      }
    } catch (e) {
      debugLog('execCommand method failed:', e);
    }
    
    // Method 3b: Simulate character-by-character typing
    try {
      debugLog('Trying character-by-character typing...');
      
      // Clear existing content
      chatInput.innerHTML = '<p><br data-cke-filler="true"></p>';
      
      let currentText = '';
      for (let i = 0; i < text.length; i++) {
        setTimeout(() => {
          const char = text[i];
          currentText += char;
          
          // Update the paragraph content
          let paragraph = chatInput.querySelector('p');
          if (!paragraph) {
            paragraph = document.createElement('p');
            chatInput.appendChild(paragraph);
          }
          
          // Remove filler breaks
          const fillerBr = paragraph.querySelector('br[data-cke-filler="true"]');
          if (fillerBr) fillerBr.remove();
          
          paragraph.textContent = currentText;
          paragraph.classList.remove('ck-placeholder');
          paragraph.removeAttribute('data-placeholder');
          
          // Fire input event for each character
          const inputEvent = new InputEvent('input', {
            bubbles: true,
            inputType: 'insertText',
            data: char
          });
          chatInput.dispatchEvent(inputEvent);
          paragraph.dispatchEvent(inputEvent);
          
          // Set cursor to end
          const range = document.createRange();
          const selection = window.getSelection();
          range.setStart(paragraph.firstChild || paragraph, paragraph.textContent.length);
          range.setEnd(paragraph.firstChild || paragraph, paragraph.textContent.length);
          selection.removeAllRanges();
          selection.addRange(range);
          
          // If this is the last character, check success
          if (i === text.length - 1) {
            setTimeout(() => {
              const finalContent = chatInput.textContent || '';
              debugLog(`Final content after typing: "${finalContent}"`);
              
              if (finalContent.includes(text)) {
                debugLog('✅ Character typing successful');
                showNotification('Text inserted via typing simulation');
                
                if (autoSubmit) {
                  setTimeout(() => submitTeamsChat(chatInput), 300);
                }
              } else {
                debugLog('❌ Character typing failed');
              }
            }, 100);
          }
          
        }, i * 50); // 50ms delay between characters
      }
      
      return true; // Optimistically return true
    } catch (e) {
      debugLog('Character typing failed:', e);
    }
    
    return false;
    
  } catch (error) {
    debugLog('Browser automation method failed:', error);
    return false;
  }
}

// Fallback clipboard instruction method
function insertUsingClipboardInstruction(chatInput, text) {
  try {
    debugLog('Using clipboard with instruction method...');
    
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      showNotification('Clipboard not available');
      return false;
    }
    
    navigator.clipboard.writeText(text).then(() => {
      // Focus the input
      chatInput.focus();
      chatInput.click();
      
      // Show instruction notification
      showPersistentNotification('Text copied! Press Ctrl+V to paste in chat', 5000);
      
      // Add visual indicator to the chat input
      const originalBorder = chatInput.style.border;
      chatInput.style.border = '2px solid #4CAF50';
      
      // Remove visual indicator after 5 seconds
      setTimeout(() => {
        chatInput.style.border = originalBorder;
      }, 5000);
      
    }).catch(error => {
      debugLog('Clipboard write failed:', error);
      showNotification('Clipboard access failed');
    });
    
    return true;
  } catch (error) {
    debugLog('Clipboard instruction method failed:', error);
    return false;
  }
}

function setCursorToEnd(element) {
  try {
    const range = document.createRange();
    const selection = window.getSelection();
    
    range.selectNodeContents(element);
    range.collapse(false);
    
    selection.removeAllRanges();
    selection.addRange(range);
  } catch (error) {
    debugLog('Failed to set cursor position:', error);
  }
}

function triggerInputEvents(element) {
  const events = [
    new Event('input', { bubbles: true, cancelable: true }),
    new Event('change', { bubbles: true, cancelable: true }),
    new InputEvent('input', { 
      bubbles: true, 
      cancelable: true,
      inputType: 'insertText'
    }),
    new KeyboardEvent('keyup', { bubbles: true, cancelable: true })
  ];
  
  events.forEach(event => {
    try {
      element.dispatchEvent(event);
    } catch (e) {
      debugLog('Failed to dispatch event:', event.type);
    }
  });
}

// Submit functions
function submitTeamsChat(chatInput) {
  try {
    // Method 1: Find and click send button
    const sendButton = document.querySelector('button[data-tid="newMessageCommands-send"]') ||
                      document.querySelector('button[name="send"]') ||
                      document.querySelector('button[title*="Send"]') ||
                      document.querySelector('button[aria-label*="Send"]');
    
    if (sendButton && !sendButton.disabled) {
      debugLog('Clicking Teams send button');
      sendButton.click();
      showNotification('Message sent');
      return true;
    }
    
    // Method 2: Ctrl+Enter
    debugLog('Trying Ctrl+Enter for Teams');
    const ctrlEnterEvent = new KeyboardEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
      which: 13,
      ctrlKey: true,
      bubbles: true,
      cancelable: true
    });
    
    chatInput.dispatchEvent(ctrlEnterEvent);
    showNotification('Sent via Ctrl+Enter');
    return true;
  } catch (error) {
    debugLog('Error submitting Teams chat:', error);
    showNotification('Send failed - use Ctrl+Enter manually');
    return false;
  }
}

function submitGenericChat(chatInput) {
  const enterEvent = new KeyboardEvent('keydown', {
    key: 'Enter',
    code: 'Enter',
    keyCode: 13,
    which: 13,
    bubbles: true
  });
  chatInput.dispatchEvent(enterEvent);
  showNotification('Sent via Enter key');
  return true;
}

// DEBUG FUNCTIONS
function debugOutput(message) {
  const output = document.getElementById('debug-output');
  if (output) {
    output.innerHTML = `<div style="background: #f0f0f0; padding: 6px; margin: 4px 0; border-radius: 3px; font-size: 11px; white-space: pre-wrap;">${message}</div>` + output.innerHTML;
    
    // Keep only last 5 debug messages
    while (output.children.length > 5) {
      output.removeChild(output.lastChild);
    }
  }
  debugLog(message);
}

function debugFindInput() {
  debugOutput('🔍 Searching for chat input...');
  
  const hostname = window.location.hostname;
  const selectors = CHAT_SELECTORS[hostname] || [];
  
  debugOutput(`Platform: ${hostname}`);
  debugOutput(`Selectors to try: ${selectors.length}`);
  
  selectors.forEach((selector, index) => {
    const elements = document.querySelectorAll(selector);
    debugOutput(`${index + 1}. "${selector}" → ${elements.length} found`);
    
    elements.forEach((el, i) => {
      const visible = isElementVisible(el);
      const focused = document.activeElement === el;
      debugOutput(`   Element ${i + 1}: visible=${visible}, focused=${focused}, id="${el.id}", class="${el.className.substring(0, 50)}"`);
    });
  });
  
  const found = findChatInput();
  if (found) {
    debugOutput(`✅ Selected input: ${found.tagName} with class "${found.className.substring(0, 50)}"`);
    found.style.outline = '3px solid red';
    setTimeout(() => {
      found.style.outline = '';
    }, 3000);
  } else {
    debugOutput('❌ No suitable input found');
  }
}

function debugTestClipboard() {
  debugOutput('📋 Testing clipboard functionality...');
  
  const testText = `Clipboard test ${new Date().toLocaleTimeString()}`;
  
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(testText).then(() => {
      debugOutput('✅ Clipboard write successful');
      
      // Try to read it back
      navigator.clipboard.readText().then(readText => {
        debugOutput(`✅ Clipboard read successful: "${readText}"`);
        debugOutput('✅ Clipboard API fully functional');
        
        // Test paste simulation
        const input = findChatInput();
        if (input) {
          input.focus();
          debugOutput('Testing paste event simulation...');
          
          const pasteEvent = new ClipboardEvent('paste', {
            bubbles: true,
            cancelable: true
          });
          
          const handled = input.dispatchEvent(pasteEvent);
          debugOutput(`Paste event result: ${handled}`);
        }
        
      }).catch(err => {
        debugOutput(`❌ Clipboard read failed: ${err.message}`);
      });
      
    }).catch(err => {
      debugOutput(`❌ Clipboard write failed: ${err.message}`);
    });
  } else {
    debugOutput('❌ Clipboard API not available');
  }
}

function debugTestInsert() {
  const testText = `Test insert ${new Date().toLocaleTimeString()}`;
  debugOutput(`✏️ Testing insert with: "${testText}"`);
  
  const input = findChatInput();
  if (!input) {
    debugOutput('❌ No input found for testing');
    return;
  }
  
  debugOutput(`Before insert - Content: "${input.textContent}"`);
  debugOutput(`Before insert - HTML: ${input.innerHTML.substring(0, 100)}`);
  
  const success = insertText(testText, false);
  
  setTimeout(() => {
    debugOutput(`After insert - Content: "${input.textContent}"`);
    debugOutput(`After insert - HTML: ${input.innerHTML.substring(0, 100)}`);
    debugOutput(`Result: ${success ? '✅ Success' : '❌ Failed'}`);
    
    const sendButton = document.querySelector('button[data-tid="newMessageCommands-send"]');
    if (sendButton) {
      debugOutput(`Send button disabled: ${sendButton.disabled}`);
    }
  }, 1000);
}

function debugAnalyzeDOM() {
  debugOutput('🏗️ Analyzing DOM structure...');
  
  const input = findChatInput();
  if (!input) {
    debugOutput('❌ No input found');
    return;
  }
  
  debugOutput(`Tag: ${input.tagName}`);
  debugOutput(`ID: "${input.id}"`);
  debugOutput(`Classes: "${input.className}"`);
  debugOutput(`ContentEditable: ${input.contentEditable}`);
  debugOutput(`Data attributes: ${Array.from(input.attributes).filter(a => a.name.startsWith('data-')).map(a => `${a.name}="${a.value}"`).join(', ')}`);
  
  const paragraph = input.querySelector('p');
  if (paragraph) {
    debugOutput(`Paragraph found:`);
    debugOutput(`  Classes: "${paragraph.className}"`);
    debugOutput(`  Content: "${paragraph.textContent}"`);
    debugOutput(`  HTML: ${paragraph.innerHTML.substring(0, 100)}`);
    debugOutput(`  Has placeholder: ${paragraph.hasAttribute('data-placeholder')}`);
  }
  
  const fillers = input.querySelectorAll('br[data-cke-filler="true"]');
  debugOutput(`CKE filler breaks: ${fillers.length}`);
  
  debugOutput(`Current focus: ${document.activeElement === input ? 'YES' : 'NO'}`);
}

function debugTestEvents() {
  debugOutput('⚡ Testing event firing...');
  
  const input = findChatInput();
  if (!input) {
    debugOutput('❌ No input found');
    return;
  }
  
  input.focus();
  
  const events = [
    'focus',
    'input', 
    'change',
    'keydown',
    'keyup'
  ];
  
  events.forEach(eventType => {
    try {
      const event = new Event(eventType, { bubbles: true });
      input.dispatchEvent(event);
      debugOutput(`✅ Fired: ${eventType}`);
    } catch (e) {
      debugOutput(`❌ Failed: ${eventType} - ${e.message}`);
    }
  });
  
  // Test CKEditor specific events
  const ckEvents = ['ck-change', 'ck-update'];
  ckEvents.forEach(eventType => {
    try {
      const event = new CustomEvent(eventType, { bubbles: true });
      input.dispatchEvent(event);
      debugOutput(`✅ Fired CK: ${eventType}`);
    } catch (e) {
      debugOutput(`❌ Failed CK: ${eventType} - ${e.message}`);
    }
  });
}

function debugCKEditor() {
  debugOutput('📝 CKEditor analysis...');
  
  const input = findChatInput();
  if (!input) {
    debugOutput('❌ No input found');
    return;
  }
  
  // Check for CKEditor 4
  if (window.CKEDITOR) {
    debugOutput(`CKEditor 4 detected: ${Object.keys(window.CKEDITOR.instances).length} instances`);
    Object.keys(window.CKEDITOR.instances).forEach(id => {
      debugOutput(`  Instance: ${id}`);
    });
  } else {
    debugOutput('CKEditor 4: Not found');
  }
  
  // Check for CKEditor 5
  if (input._ckEditor) {
    debugOutput('CKEditor 5: Found on input element');
    try {
      debugOutput(`  State: ${input._ckEditor.isReadOnly ? 'readonly' : 'editable'}`);
    } catch (e) {
      debugOutput(`  Error accessing state: ${e.message}`);
    }
  } else {
    debugOutput('CKEditor 5: Not found on input element');
  }
  
  // Check for any CKEditor CSS classes
  const ckElements = document.querySelectorAll('[class*="ck-"]');
  debugOutput(`Elements with CK classes: ${ckElements.length}`);
  
  // Check send button state
  const sendButton = document.querySelector('button[data-tid="newMessageCommands-send"]');
  if (sendButton) {
    debugOutput(`Send button: ${sendButton.disabled ? 'DISABLED' : 'ENABLED'}`);
    debugOutput(`Send button classes: "${sendButton.className}"`);
  } else {
    debugOutput('Send button: Not found');
  }
}

// Enhanced clear function that actually works
function debugClearInput() {
  debugOutput('🧹 Enhanced clearing input...');
  
  const input = findChatInput();
  if (!input) {
    debugOutput('❌ No input found');
    return;
  }
  
  try {
    // Method 1: Try CKEditor API first
    if (input._ckEditor && input._ckEditor.setData) {
      input._ckEditor.setData('');
      debugOutput('✅ Cleared via CKEditor API');
      return;
    }
    
    // Method 2: Force DOM clear
    input.focus();
    input.click();
    
    // Clear all content
    input.innerHTML = '';
    
    // Recreate proper empty structure
    const paragraph = document.createElement('p');
    paragraph.setAttribute('data-placeholder', 'Type a message');
    paragraph.className = 'ck-placeholder';
    
    const br = document.createElement('br');
    br.setAttribute('data-cke-filler', 'true');
    paragraph.appendChild(br);
    
    input.appendChild(paragraph);
    
    // Remove focus classes
    input.classList.remove('ck-focused');
    input.classList.add('ck-blurred');
    
    // Fire events
    const events = [
      new Event('input', { bubbles: true }),
      new Event('change', { bubbles: true }),
      new CustomEvent('ck-change', { bubbles: true }),
      new Event('blur', { bubbles: true })
    ];
    
    events.forEach(event => input.dispatchEvent(event));
    
    debugOutput('✅ Input force-cleared with proper structure');
    
  } catch (error) {
    debugOutput(`❌ Clear failed: ${error.message}`);
  }
}

// Test all insertion methods individually
function debugTestAllMethods() {
  debugOutput('🧪 Testing all insertion methods...');
  
  const input = findChatInput();
  if (!input) {
    debugOutput('❌ No input found');
    return;
  }
  
  const testText = `Method test ${new Date().toLocaleTimeString()}`;
  
  // Test Method 1: CKEditor API
  setTimeout(() => {
    debugOutput('Testing Method 1: CKEditor API...');
    insertUsingCKEditorAPI(input, testText + ' [Method1]', false);
  }, 1000);
  
  // Test Method 2: Forced DOM
  setTimeout(() => {
    debugOutput('Testing Method 2: Forced DOM...');
    insertUsingForcedDOM(input, testText + ' [Method2]', false);
  }, 3000);
  
  // Test Method 3: Browser Automation
  setTimeout(() => {
    debugOutput('Testing Method 3: Browser Automation...');
    insertUsingBrowserAutomation(input, testText + ' [Method3]', false);
  }, 6000);
}

// Enhanced notification that persists longer
function showPersistentNotification(message, duration = 3000) {
  try {
    const existingNotifications = document.querySelectorAll('.widget-notification');
    existingNotifications.forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = 'widget-notification persistent';
    notification.innerHTML = `
      <div style="margin-bottom: 8px; font-weight: bold;">${message}</div>
      <div style="font-size: 11px; opacity: 0.8;">Click to dismiss</div>
    `;
    
    // Add click to dismiss
    notification.addEventListener('click', () => {
      notification.remove();
    });
    
    // Style for persistence
    notification.style.cssText += `
      cursor: pointer !important;
      padding: 16px !important;
      max-width: 350px !important;
      white-space: normal !important;
      line-height: 1.4 !important;
    `;
    
    if (floatingWidget) {
      floatingWidget.appendChild(notification);
    } else {
      notification.style.cssText += `
        position: fixed !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        background: #333 !important;
        color: white !important;
        border-radius: 6px !important;
        font-size: 14px !important;
        z-index: 999999 !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4) !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
      `;
      document.body.appendChild(notification);
    }
    
    // Auto-remove after duration
    setTimeout(() => {
      if (notification.parentNode) {
        notification.style.transition = 'opacity 0.3s ease';
        notification.style.opacity = '0';
        setTimeout(() => {
          if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
          }
        }, 300);
      }
    }, duration);
    
  } catch (error) {
    debugLog('Failed to show persistent notification:', error);
    console.log('NOTIFICATION:', message);
  }
}

// Utility functions
function copyLastTranscription() {
  if (!lastTranscription) {
    showNotification('No transcription to copy');
    return;
  }
  
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(lastTranscription).then(() => {
      showNotification('Copied to clipboard');
    }).catch(() => {
      copyViaBackground();
    });
  } else {
    copyViaBackground();
  }
  
  function copyViaBackground() {
    browser.runtime.sendMessage({
      type: 'copy_to_clipboard',
      text: lastTranscription
    }, (response) => {
      if (response && response.success) {
        showNotification('Copied to clipboard');
      } else {
        showNotification('Copy failed');
      }
    });
  }
}

function insertLastTranscription() {
  if (!lastTranscription) {
    showNotification('No transcription to insert');
    return;
  }
  
  insertText(lastTranscription, autoInsert);
}

function toggleAutoInsert() {
  autoInsert = !autoInsert;
  const btn = document.getElementById('auto-btn');
  btn.textContent = `🔄 Auto: ${autoInsert ? 'ON' : 'OFF'}`;
  btn.classList.toggle('active', autoInsert);
  
  showNotification(`Auto-insert ${autoInsert ? 'enabled' : 'disabled'}`);
}

function clearDisplay() {
  const display = document.getElementById('transcription-display');
  display.innerHTML = '<p class="waiting-message">Waiting for transcriptions...</p>';
  lastTranscription = '';
  showNotification('Display cleared');
}

function showNotification(message) {
  try {
    const existingNotifications = document.querySelectorAll('.widget-notification');
    existingNotifications.forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = 'widget-notification';
    notification.textContent = message;
    
    if (floatingWidget) {
      floatingWidget.appendChild(notification);
    } else {
      notification.style.cssText = `
        position: fixed !important;
        top: 20px !important;
        right: 20px !important;
        background: #333 !important;
        color: white !important;
        padding: 12px 16px !important;
        border-radius: 4px !important;
        font-size: 14px !important;
        z-index: 999999 !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
      `;
      document.body.appendChild(notification);
    }
    
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 3000);
  } catch (error) {
    debugLog('Failed to show notification:', error);
    console.log('NOTIFICATION:', message);
  }
}

// Message listener and initialization
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
  try {
    switch (request.type) {
      case 'ping':
        sendResponse({ status: 'ok', widget: !!floatingWidget });
        break;
        
      case 'new_transcription':
        updateTranscription(request.data);
        sendResponse({ success: true });
        break;
        
      case 'connection_status':
        const statusEl = document.getElementById('connection-status');
        const reconnectBtn = document.getElementById('reconnect-btn');
        if (statusEl) {
          statusEl.classList.toggle('connected', request.connected);
          statusEl.classList.toggle('disconnected', !request.connected);
          
          if (reconnectBtn) {
            reconnectBtn.style.display = request.connected ? 'none' : 'inline-block';
          }
        }
        sendResponse({ success: true });
        break;
        
      case 'insert_text':
        const success = insertText(request.text);
        sendResponse({ success: success });
        break;
        
      case 'toggle_widget':
        if (floatingWidget) {
          const isHidden = floatingWidget.style.display === 'none';
          floatingWidget.style.display = isHidden ? 'block' : 'none';
          showNotification(isHidden ? 'Widget shown' : 'Widget hidden');
        }
        sendResponse({ success: true });
        break;
        
      case 'show_widget':
        if (floatingWidget) {
          floatingWidget.style.display = 'block';
          showNotification('Widget shown');
        }
        sendResponse({ success: true });
        break;
        
      default:
        debugLog('Unknown message type:', request.type);
        sendResponse({ success: false, error: 'Unknown message type' });
    }
  } catch (error) {
    debugLog('Error handling runtime message:', error);
    sendResponse({ success: false, error: error.message });
  }
  
  return true;
});

function initializeWithRetry(attempts = 0) {
  if (attempts > 5) {
    console.warn('Failed to initialize after 5 attempts');
    return;
  }
  
  if (document.body) {
    createFloatingWidget();
    
    browser.runtime.sendMessage({ type: 'get_status' }, (response) => {
      if (response && response.connected) {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) {
          statusEl.classList.add('connected');
        }
      }
    });
    
    console.log('Enhanced content script with aggressive Teams support initialized successfully');
  } else {
    console.log(`Initialization attempt ${attempts + 1} - waiting for DOM...`);
    setTimeout(() => initializeWithRetry(attempts + 1), 1000);
  }
}

// Start initialization
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => initializeWithRetry());
} else {
  initializeWithRetry();
}

window.addEventListener('beforeunload', () => {
  if (floatingWidget) {
    floatingWidget.remove();
  }
});

console.log('Enhanced content script loaded with aggressive Teams CKEditor support');