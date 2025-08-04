// web-ui/static/app.js
class TranscriberUI {
    constructor() {
        this.apiUrl = 'http://localhost:8000';
        this.wsUrl = 'ws://localhost:8765';
        this.ws = null;
        this.currentModule = null;
        this.isRecording = false;
        
        this.init();
    }
    
    async init() {
        // Connect WebSocket
        this.connectWebSocket();
        
        // Load available modules
        await this.loadModules();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Load saved config
        await this.loadConfig();
    }
    
    connectWebSocket() {
        this.ws = new WebSocket(this.wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateWSStatus(true);
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'transcription') {
                this.addTranscription(data);
            }
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateWSStatus(false);
            // Reconnect after 5 seconds
            setTimeout(() => this.connectWebSocket(), 5000);
        };
    }
    
    async loadModules() {
        try {
            const response = await axios.get(`${this.apiUrl}/api/audio/modules`);
            const modules = response.data.modules;
            
            // Update UI with available modules
            Object.entries(modules).forEach(([key, module]) => {
                const card = document.querySelector(`[data-module="${key}"]`);
                if (card) {
                    // Update card with actual module info
                    card.querySelector('h3').textContent = module.name;
                    card.querySelector('p').textContent = module.description;
                }
            });
            
        } catch (error) {
            console.error('Failed to load modules:', error);
        }
    }
    
    setupEventListeners() {
        // Module selection
        document.querySelectorAll('.select-module').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const module = e.target.closest('.module-card').dataset.module;
                this.selectModule(module);
            });
        });
        
        // Recording controls
        document.getElementById('start-recording').addEventListener('click', () => {
            this.startRecording();
        });
        
        document.getElementById('stop-recording').addEventListener('click', () => {
            this.stopRecording();
        });
        
        // Config save
        document.getElementById('save-config').addEventListener('click', () => {
            this.saveConfig();
        });
        
        // Config test
        document.getElementById('test-config').addEventListener('click', () => {
            this.testConfig();
        });
    }
    
    async selectModule(module) {
        this.currentModule = module;
        
        // Update UI
        document.querySelectorAll('.module-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-module="${module}"]`).classList.add('selected');
        
        // Show config panel
        document.getElementById('config-panel').style.display = 'block';
        
        // Load module-specific config form
        await this.loadModuleConfig(module);
        
        // Update status
        document.getElementById('module-text').textContent = module;
    }
    
    async loadModuleConfig(module) {
        // Get module info
        const response = await axios.get(`${this.apiUrl}/api/audio/modules`);
        const moduleInfo = response.data.modules[module];
        
        const configForm = document.getElementById('config-form');
        configForm.innerHTML = '';
        
        if (moduleInfo.config_fields) {
            moduleInfo.config_fields.forEach(field => {
                const div = document.createElement('div');
                div.className = 'form-group';
                
                const label = document.createElement('label');
                label.textContent = field.name;
                div.appendChild(label);
                
                if (field.type === 'select') {
                    const select = document.createElement('select');
                    select.name = field.name;
                    select.id = `config-${field.name}`;
                    
                    if (field.options === 'dynamic') {
                        // Load options from API
                        this.loadSelectOptions(select, module, field.name);
                    } else {
                        field.options.forEach(opt => {
                            const option = document.createElement('option');
                            option.value = opt;
                            option.textContent = opt;
                            select.appendChild(option);
                        });
                    }
                    
                    div.appendChild(select);
                } else if (field.type === 'text') {
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.name = field.name;
                    input.id = `config-${field.name}`;
                    input.value = field.default || '';
                    div.appendChild(input);
                } else if (field.type === 'number') {
                    const input = document.createElement('input');
                    input.type = 'number';
                    input.name = field.name;
                    input.id = `config-${field.name}`;
                    input.value = field.default || '';
                    div.appendChild(input);
                }
                
                configForm.appendChild(div);
            });
        } else {
            configForm.innerHTML = '<p>No configuration required for this module.</p>';
        }
    }
    
    async startRecording() {
        if (!this.currentModule) {
            alert('Please select an audio capture method first');
            return;
        }
        
        const config = this.getConfigValues();
        
        try {
            const response = await axios.post(`${this.apiUrl}/api/audio/start`, {
                module: this.currentModule,
                config: config
            });
            
            if (response.data.status === 'started') {
                this.isRecording = true;
                this.updateRecordingUI();
            }
        } catch (error) {
            alert('Failed to start recording: ' + error.message);
        }
    }
    
    async stopRecording() {
        try {
            const response = await axios.post(`${this.apiUrl}/api/audio/stop`);
            
            if (response.data.status === 'stopped') {
                this.isRecording = false;
                this.updateRecordingUI();
            }
        } catch (error) {
            alert('Failed to stop recording: ' + error.message);
        }
    }
    
    updateRecordingUI() {
        document.getElementById('start-recording').disabled = this.isRecording;
        document.getElementById('stop-recording').disabled = !this.isRecording;
        document.getElementById('status-text').textContent = 
            this.isRecording ? 'Recording...' : 'Ready';
    }
    
    addTranscription(data) {
        const feed = document.getElementById('transcription-feed');
        
        // Remove placeholder
        const placeholder = feed.querySelector('.placeholder');
        if (placeholder) placeholder.remove();
        
        const item = document.createElement('div');
        item.className = 'transcription-item';
        item.innerHTML = `
            <div class="transcription-time">${new Date(data.timestamp).toLocaleTimeString()}</div>
            <div class="transcription-text">[${data.language}] ${data.text}</div>
            ${data.translation ? `<div class="transcription-translation">${data.translation}</div>` : ''}
        `;
        
        feed.appendChild(item);
        
        // Keep only last 20 items
        while (feed.children.length > 20) {
            feed.removeChild(feed.firstChild);
        }
        
        // Scroll to bottom
        feed.scrollTop = feed.scrollHeight;
    }
    
    updateWSStatus(connected) {
        const status = document.getElementById('ws-status');
        status.textContent = connected ? '🟢' : '🔴';
    }
    
    getConfigValues() {
        const config = {};
        document.querySelectorAll('#config-form input, #config-form select').forEach(el => {
            config[el.name] = el.value;
        });
        return config;
    }
    
    async saveConfig() {
        const config = {
            module: this.currentModule,
            moduleConfig: this.getConfigValues(),
            settings: {
                targetLanguage: document.getElementById('target-language').value,
                enableTranslation: document.getElementById('enable-translation').checked,
                saveAudio: document.getElementById('save-audio').checked,
                autoInsert: document.getElementById('auto-insert').checked
            }
        };
        
        try {
            await axios.post(`${this.apiUrl}/api/config`, config);
            alert('Configuration saved!');
        } catch (error) {
            alert('Failed to save configuration: ' + error.message);
        }
    }
    
    async loadConfig() {
        try {
            const response = await axios.get(`${this.apiUrl}/api/config`);
            const config = response.data;
            
            if (config.module) {
                this.selectModule(config.module);
            }
            
            if (config.settings) {
                document.getElementById('target-language').value = config.settings.targetLanguage || 'pt';
                document.getElementById('enable-translation').checked = config.settings.enableTranslation !== false;
                document.getElementById('save-audio').checked = config.settings.saveAudio !== false;
                document.getElementById('auto-insert').checked = config.settings.autoInsert !== false;
            }
        } catch (error) {
            console.error('Failed to load config:', error);
        }
    }
    
    async testConfig() {
        if (!this.currentModule) {
            alert('Please select a module first');
            return;
        }
        
        const config = this.getConfigValues();
        
        try {
            const response = await axios.post(`${this.apiUrl}/api/audio/test`, {
                module: this.currentModule,
                config: config
            });
            
            alert(response.data.message || 'Test completed');
        } catch (error) {
            alert('Test failed: ' + error.message);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new TranscriberUI();
});