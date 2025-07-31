document.addEventListener('DOMContentLoaded', () => {
  const statusDot = document.getElementById('status-dot');
  const statusText = document.getElementById('status-text');
  const transcriptionList = document.getElementById('transcription-list');
  
  // Get status
  browser.runtime.sendMessage({ type: 'get_status' }, (response) => {
    if (response) {
      updateStatus(response.connected);
      
      // Get buffer
      browser.runtime.sendMessage({ type: 'get_buffer' }, (buffer) => {
        if (buffer && buffer.length > 0) {
          displayTranscriptions(buffer);
        }
      });
    }
  });
  
  // Update status display
  function updateStatus(connected) {
    statusDot.classList.toggle('connected', connected);
    statusDot.classList.toggle('disconnected', !connected);
    statusText.textContent = connected ? 'Connected to server' : 'Disconnected';
  }
  
  // Display transcriptions
  function displayTranscriptions(buffer) {
    transcriptionList.innerHTML = '';
    
    buffer.slice(-10).forEach(item => {
      const div = document.createElement('div');
      div.className = 'transcription-item';
      
      const time = new Date(item.timestamp).toLocaleTimeString();
      
      div.innerHTML = `
        <div class="transcription-time">${time}</div>
        <div class="transcription-text">[${item.language}] ${item.text}</div>
        ${item.translation ? `<div class="transcription-translation">${item.translation}</div>` : ''}
      `;
      
      transcriptionList.appendChild(div);
    });
    
    transcriptionList.scrollTop = transcriptionList.scrollHeight;
  }
  
  // Copy all button
  document.getElementById('copy-all-btn').addEventListener('click', () => {
    browser.runtime.sendMessage({ type: 'get_buffer' }, (buffer) => {
      if (buffer && buffer.length > 0) {
        const text = buffer.map(item => 
          `[${new Date(item.timestamp).toLocaleTimeString()}] ${item.text}${item.translation ? ' | ' + item.translation : ''}`
        ).join('\n');
        
        navigator.clipboard.writeText(text).then(() => {
          const btn = document.getElementById('copy-all-btn');
          btn.textContent = 'Copied!';
          setTimeout(() => {
            btn.textContent = 'Copy All';
          }, 2000);
        });
      }
    });
  });
  
  // Clear button
  document.getElementById('clear-btn').addEventListener('click', () => {
    browser.runtime.sendMessage({ type: 'clear_buffer' }, () => {
      transcriptionList.innerHTML = '<div class="empty-state">No transcriptions yet</div>';
    });
  });
  
  // Open widget button
  document.getElementById('open-widget-btn').addEventListener('click', () => {
    browser.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        browser.tabs.sendMessage(tabs[0].id, {
          type: 'show_widget'
        });
        window.close();
      }
    });
  });
  
  // Listen for updates
  browser.runtime.onMessage.addListener((request) => {
    if (request.type === 'connection_status') {
      updateStatus(request.connected);
    }
  });
});