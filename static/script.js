// Multi-Agent Document Processing System - Frontend JavaScript

class DocumentProcessor {
    constructor() {
        this.apiBase = '';
        this.currentResults = [];
        this.memoryData = null;
        this.systemStatus = null;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadSystemStatus();
        this.setupFileUpload();
    }
    
    bindEvents() {
        // File upload form
        document.getElementById('fileUploadForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFileUpload();
        });
        
        // Text input form
        document.getElementById('textInputForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleTextInput();
        });
        
        // Clear results button
        document.getElementById('clearResults').addEventListener('click', () => {
            this.clearResults();
        });
        
        // Memory management buttons
        document.getElementById('refreshMemory').addEventListener('click', () => {
            this.loadMemoryData();
        });
        
        document.getElementById('clearMemory').addEventListener('click', () => {
            this.clearAllMemory();
        });
    }
    
    setupFileUpload() {
        const fileInput = document.getElementById('fileInput');
        const uploadArea = fileInput.closest('.card-body');
        
        // Drag and drop functionality
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                this.handleFileUpload();
            }
        });
    }
    
    async handleFileUpload() {
        const fileInput = document.getElementById('fileInput');
        const file = fileInput.files[0];
        
        if (!file) {
            this.showError('Please select a file to upload.');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        this.showProcessingStatus(true);
        
        try {
            const response = await fetch('/process/file', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.addResult(result);
                this.showSuccess('File processed successfully!');
                fileInput.value = '';
            } else {
                this.showError(result.message || 'File processing failed.');
            }
        } catch (error) {
            this.showError(`Upload failed: ${error.message}`);
        } finally {
            this.showProcessingStatus(false);
        }
    }
    
    async handleTextInput() {
        const textInput = document.getElementById('textInput');
        const content = textInput.value.trim();
        
        if (!content) {
            this.showError('Please enter some text to process.');
            return;
        }
        
        const payload = {
            content: content,
            metadata: {
                input_method: 'text_area',
                char_count: content.length
            }
        };
        
        this.showProcessingStatus(true);
        
        try {
            const response = await fetch('/process/text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.addResult(result);
                this.showSuccess('Text processed successfully!');
                textInput.value = '';
            } else {
                this.showError(result.message || 'Text processing failed.');
            }
        } catch (error) {
            this.showError(`Processing failed: ${error.message}`);
        } finally {
            this.showProcessingStatus(false);
        }
    }
    
    addResult(result) {
        this.currentResults.unshift(result);
        this.renderResults();
    }
    
    renderResults() {
        const container = document.getElementById('resultsContainer');
        
        if (this.currentResults.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-file-search fa-3x mb-3"></i>
                    <p>No documents processed yet. Upload a file or enter text to get started.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.currentResults.map(result => this.renderResultItem(result)).join('');
    }
    
    renderResultItem(result) {
        const timestamp = new Date(result.classification.timestamp).toLocaleString();
        const confidence = Math.round(result.classification.confidence * 100);
        
        return `
            <div class="result-item fade-in">
                <div class="result-header">
                    <div>
                        <h6 class="result-title">Processing ID: ${result.processing_id}</h6>
                        <div class="result-timestamp">${timestamp}</div>
                    </div>
                    <div>
                        <span class="classification-badge format-${result.classification.format}">
                            ${result.classification.format.toUpperCase()}
                        </span>
                        <span class="classification-badge intent-badge">
                            ${result.classification.intent.toUpperCase()}
                        </span>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6">
                        <h6>Classification</h6>
                        <div class="confidence-score">
                            <small>Confidence:</small>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: ${confidence}%"></div>
                            </div>
                            <small>${confidence}%</small>
                        </div>
                        <div class="mt-2">
                            <small class="text-muted">Status: </small>
                            <span class="status-indicator status-${result.status === 'processed' ? 'healthy' : 'error'}">
                                <span class="status-icon"></span>
                                ${result.status}
                            </span>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <h6>Extracted Data</h6>
                        <div class="json-display">
                            ${this.formatJSON(result.extracted_data)}
                        </div>
                    </div>
                </div>
                
                ${result.metadata && Object.keys(result.metadata).length > 0 ? `
                    <div class="mt-3">
                        <h6>Metadata</h6>
                        <div class="json-display">
                            ${this.formatJSON(result.metadata)}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    formatJSON(obj, indent = 0) {
        if (obj === null) return '<span class="json-null">null</span>';
        if (obj === undefined) return '<span class="json-undefined">undefined</span>';
        
        const spaces = '  '.repeat(indent);
        
        if (typeof obj === 'string') {
            return `<span class="json-string">"${this.escapeHtml(obj)}"</span>`;
        }
        
        if (typeof obj === 'number') {
            return `<span class="json-number">${obj}</span>`;
        }
        
        if (typeof obj === 'boolean') {
            return `<span class="json-boolean">${obj}</span>`;
        }
        
        if (Array.isArray(obj)) {
            if (obj.length === 0) return '[]';
            
            const items = obj.map(item => 
                `${spaces}  ${this.formatJSON(item, indent + 1)}`
            ).join(',\n');
            
            return `[\n${items}\n${spaces}]`;
        }
        
        if (typeof obj === 'object') {
            const keys = Object.keys(obj);
            if (keys.length === 0) return '{}';
            
            const items = keys.map(key => 
                `${spaces}  <span class="json-key">"${key}"</span>: ${this.formatJSON(obj[key], indent + 1)}`
            ).join(',\n');
            
            return `{\n${items}\n${spaces}}`;
        }
        
        return String(obj);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    clearResults() {
        this.currentResults = [];
        this.renderResults();
        this.showSuccess('Results cleared.');
    }
    
    async loadMemoryData() {
        try {
            const response = await fetch('/memory');
            const data = await response.json();
            
            if (response.ok) {
                this.memoryData = data;
                this.renderMemoryData();
            } else {
                this.showError('Failed to load memory data.');
            }
        } catch (error) {
            this.showError(`Memory load failed: ${error.message}`);
        }
    }
    
    renderMemoryData() {
        const container = document.getElementById('memoryContainer');
        
        if (!this.memoryData || Object.keys(this.memoryData.entries).length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-database fa-3x mb-3"></i>
                    <p>No memory entries found. Process some documents to see memory data.</p>
                </div>
            `;
            return;
        }
        
        const entries = Object.values(this.memoryData.entries);
        const stats = this.memoryData.statistics;
        
        container.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="text-center">
                        <h4 class="text-primary">${stats.total_entries}</h4>
                        <small class="text-muted">Total Entries</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <h4 class="text-info">${stats.active_conversations}</h4>
                        <small class="text-muted">Conversations</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <h4 class="text-success">${entries.length}</h4>
                        <small class="text-muted">Active Entries</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <h4 class="text-warning">${new Date(stats.last_update || stats.last_cleanup).toLocaleTimeString()}</h4>
                        <small class="text-muted">Last Update</small>
                    </div>
                </div>
            </div>
            
            <div class="memory-entries">
                ${entries.map(entry => this.renderMemoryEntry(entry)).join('')}
            </div>
        `;
    }
    
    renderMemoryEntry(entry) {
        const timestamp = new Date(entry.timestamp).toLocaleString();
        
        return `
            <div class="memory-item">
                <div class="memory-header">
                    <div class="memory-id">${entry.processing_id}</div>
                    <div class="memory-timestamp">${timestamp}</div>
                </div>
                
                <div class="row">
                    <div class="col-md-4">
                        <small class="text-muted">Classification:</small>
                        ${entry.classification ? `
                            <div>
                                <span class="badge bg-primary">${entry.classification.format}</span>
                                <span class="badge bg-secondary">${entry.classification.intent}</span>
                            </div>
                        ` : '<span class="text-muted">None</span>'}
                    </div>
                    
                    <div class="col-md-4">
                        <small class="text-muted">Agent History:</small>
                        <div>
                            ${entry.agent_history ? entry.agent_history.map(agent => 
                                `<span class="badge bg-light text-dark">${agent}</span>`
                            ).join(' ') : '<span class="text-muted">None</span>'}
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <small class="text-muted">Conversation ID:</small>
                        <div class="memory-id">${entry.conversation_id || 'None'}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    async clearAllMemory() {
        if (!confirm('Are you sure you want to clear all memory data? This action cannot be undone.')) {
            return;
        }
        
        try {
            // Note: This would require a DELETE /memory endpoint for clearing all
            // For now, we'll just refresh the display
            this.memoryData = { entries: {}, statistics: { total_entries: 0, active_conversations: 0 } };
            this.renderMemoryData();
            this.showSuccess('Memory cleared (simulated - implement clear all endpoint).');
        } catch (error) {
            this.showError(`Memory clear failed: ${error.message}`);
        }
    }
    
    async loadSystemStatus() {
        try {
            const response = await fetch('/health');
            const data = await response.json();
            
            if (response.ok) {
                this.systemStatus = data;
                this.renderSystemStatus();
                this.updateSystemStatusAlert();
            } else {
                this.showSystemStatus('System status check failed.', 'warning');
            }
        } catch (error) {
            this.showSystemStatus(`System unreachable: ${error.message}`, 'danger');
        }
    }
    
    renderSystemStatus() {
        const container = document.getElementById('statusContainer');
        
        if (!this.systemStatus) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-server fa-3x mb-3"></i>
                    <p>Unable to load system status.</p>
                </div>
            `;
            return;
        }
        
        const agents = this.systemStatus.agents || {};
        const timestamp = new Date(this.systemStatus.timestamp).toLocaleString();
        
        container.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-6">
                    <h6>Overall Status</h6>
                    <div class="status-indicator status-${this.systemStatus.status === 'healthy' ? 'healthy' : 'error'}">
                        <span class="status-icon"></span>
                        ${this.systemStatus.status.toUpperCase()}
                    </div>
                    <div class="mt-2">
                        <small class="text-muted">Last Check: ${timestamp}</small>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <h6>Memory Status</h6>
                    <div class="status-indicator status-${this.systemStatus.memory === 'active' ? 'healthy' : 'error'}">
                        <span class="status-icon"></span>
                        ${this.systemStatus.memory || 'Unknown'}
                    </div>
                </div>
            </div>
            
            <h6>Agent Status</h6>
            <div class="row">
                ${Object.entries(agents).map(([agent, status]) => `
                    <div class="col-md-4 mb-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <i class="fas fa-robot fa-2x mb-2 text-primary"></i>
                                <h6>${agent.replace('_', ' ').toUpperCase()}</h6>
                                <div class="status-indicator status-${status === 'active' ? 'healthy' : 'error'}">
                                    <span class="status-icon"></span>
                                    ${status}
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    updateSystemStatusAlert() {
        const alert = document.getElementById('systemStatus');
        const message = document.getElementById('statusMessage');
        
        if (this.systemStatus && this.systemStatus.status === 'healthy') {
            this.showSystemStatus('All systems operational.', 'success');
        } else {
            this.showSystemStatus('System issues detected. Some features may be limited.', 'warning');
        }
    }
    
    showSystemStatus(message, type) {
        const alert = document.getElementById('systemStatus');
        const messageEl = document.getElementById('statusMessage');
        
        alert.className = `alert alert-${type}`;
        messageEl.textContent = message;
        alert.classList.remove('d-none');
        
        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => {
                alert.classList.add('d-none');
            }, 5000);
        }
    }
    
    showProcessingStatus(show) {
        const status = document.getElementById('processingStatus');
        if (show) {
            status.classList.remove('d-none');
        } else {
            status.classList.add('d-none');
        }
    }
    
    showSuccess(message) {
        this.showToast('successToast', 'successMessage', message);
    }
    
    showError(message) {
        this.showToast('errorToast', 'errorMessage', message);
    }
    
    showToast(toastId, messageId, message) {
        const toast = document.getElementById(toastId);
        const messageEl = document.getElementById(messageId);
        
        messageEl.textContent = message;
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const processor = new DocumentProcessor();
    
    // Auto-refresh system status every 30 seconds
    setInterval(() => {
        processor.loadSystemStatus();
    }, 30000);
});
