// Global variables
let currentSessionId = null;
let refreshInterval = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadSessions();
    setupEventListeners();
    
    // Auto-refresh every 30 seconds
    refreshInterval = setInterval(() => {
        loadStats();
        loadSessions();
    }, 30000);
});

// Set up event listeners
function setupEventListeners() {
    // Crawl form submission
    const crawlForm = document.getElementById('crawlForm');
    crawlForm.addEventListener('submit', handleCrawlSubmit);
    
    // Modal close on background click
    const modal = document.getElementById('sessionModal');
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });
    
    // Escape key to close modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
}

// Handle crawl form submission
async function handleCrawlSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        url: formData.get('url'),
        max_pages: parseInt(formData.get('maxPages')),
        delay: parseFloat(formData.get('delay'))
    };
    
    // Validate URL
    if (!data.url) {
        showMessage('Please enter a URL', 'error');
        return;
    }
    
    try {
        showMessage('Starting crawl...', 'success');
        
        const response = await fetch('/api/crawl', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(`Crawl started successfully! Session ID: ${result.session_id}`, 'success');
            
            // Reset form
            e.target.reset();
            
            // Refresh sessions and stats
            setTimeout(() => {
                loadStats();
                loadSessions();
            }, 1000);
        } else {
            showMessage(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Network error: ${error.message}`, 'error');
    }
}

// Load and display statistics
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('totalSessions').textContent = data.total_sessions;
            document.getElementById('totalPages').textContent = data.total_pages;
            document.getElementById('totalLinks').textContent = data.total_links;
            document.getElementById('activeSessions').textContent = data.active_sessions;
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Load and display sessions
async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();
        
        if (response.ok) {
            displaySessions(data.sessions);
        } else {
            showMessage(`Error loading sessions: ${data.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Network error: ${error.message}`, 'error');
    }
}

// Display sessions in the UI
function displaySessions(sessions) {
    const container = document.getElementById('sessionsList');
    
    if (sessions.length === 0) {
        container.innerHTML = '<div class="loading">No crawl sessions found. Start your first crawl above!</div>';
        return;
    }
    
    container.innerHTML = sessions.map(session => `
        <div class="session-card" onclick="showSessionDetails(${session.id})">
            <div class="session-header">
                <div class="session-url">${session.start_url}</div>
                <div class="session-status status-${session.status}">
                    ${session.status}
                </div>
            </div>
            <div class="session-info">
                <div class="info-item">
                    <span class="info-value">${session.total_pages}</span>
                    <span class="info-label">Pages</span>
                </div>
                <div class="info-item">
                    <span class="info-value">${session.max_pages}</span>
                    <span class="info-label">Max Pages</span>
                </div>
                <div class="info-item">
                    <span class="info-value">${formatDate(session.start_time)}</span>
                    <span class="info-label">Started</span>
                </div>
                <div class="info-item">
                    <span class="info-value">${session.end_time ? formatDate(session.end_time) : 'Running'}</span>
                    <span class="info-label">Finished</span>
                </div>
            </div>
        </div>
    `).join('');
}

// Show session details in modal
async function showSessionDetails(sessionId) {
    currentSessionId = sessionId;
    
    try {
        // Load session details
        const sessionResponse = await fetch(`/api/sessions/${sessionId}/status`);
        const sessionData = await sessionResponse.json();
        
        // Load session pages
        const pagesResponse = await fetch(`/api/sessions/${sessionId}/pages`);
        const pagesData = await pagesResponse.json();
        
        if (sessionResponse.ok && pagesResponse.ok) {
            displaySessionModal(sessionData.session, pagesData.pages);
        } else {
            showMessage('Error loading session details', 'error');
        }
    } catch (error) {
        showMessage(`Network error: ${error.message}`, 'error');
    }
}

// Display session details in modal
function displaySessionModal(session, pages) {
    const modal = document.getElementById('sessionModal');
    const modalTitle = document.getElementById('modalTitle');
    const sessionDetails = document.getElementById('sessionDetails');
    const pagesList = document.getElementById('pagesList');
    
    modalTitle.textContent = `Session #${session.id} - ${session.start_url}`;
    
    // Session details
    sessionDetails.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
            <div>
                <strong>Status:</strong><br>
                <span class="session-status status-${session.status}">${session.status}</span>
            </div>
            <div>
                <strong>Pages Crawled:</strong><br>
                ${session.total_pages} / ${session.max_pages}
            </div>
            <div>
                <strong>Started:</strong><br>
                ${formatDateTime(session.start_time)}
            </div>
            <div>
                <strong>Finished:</strong><br>
                ${session.end_time ? formatDateTime(session.end_time) : 'Still running'}
            </div>
        </div>
    `;
    
    // Pages list
    if (pages.length === 0) {
        pagesList.innerHTML = '<p>No pages crawled yet.</p>';
    } else {
        pagesList.innerHTML = `
            <h4>Crawled Pages (${pages.length})</h4>
            <div style="overflow-x: auto;">
                <table class="pages-table">
                    <thead>
                        <tr>
                            <th>URL</th>
                            <th>Title</th>
                            <th>Status</th>
                            <th>Words</th>
                            <th>Links</th>
                            <th>Response Time</th>
                            <th>Crawled At</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${pages.map(page => `
                            <tr>
                                <td class="page-url" title="${page.url}">${page.url}</td>
                                <td class="page-title" title="${page.title}">${page.title || 'No Title'}</td>
                                <td>${page.status_code}</td>
                                <td>${page.word_count}</td>
                                <td>${page.link_count}</td>
                                <td>${page.response_time ? (page.response_time * 1000).toFixed(0) + 'ms' : 'N/A'}</td>
                                <td>${formatDateTime(page.crawl_time)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    modal.classList.remove('hidden');
}

// Export session data
async function exportSession() {
    if (!currentSessionId) return;
    
    try {
        const response = await fetch(`/api/sessions/${currentSessionId}/export`);
        const data = await response.json();
        
        if (response.ok) {
            // Create and download JSON file
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `crawl_session_${currentSessionId}_${new Date().getTime()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            showMessage('Session data exported successfully!', 'success');
        } else {
            showMessage(`Export error: ${data.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Network error: ${error.message}`, 'error');
    }
}

// Close modal
function closeModal() {
    const modal = document.getElementById('sessionModal');
    modal.classList.add('hidden');
    currentSessionId = null;
}

// Refresh sessions manually
function refreshSessions() {
    loadStats();
    loadSessions();
    showMessage('Data refreshed!', 'success');
}

// Show status message
function showMessage(message, type) {
    const messageDiv = document.getElementById('statusMessage');
    messageDiv.textContent = message;
    messageDiv.className = `status-message ${type}`;
    messageDiv.classList.remove('hidden');
    
    // Hide message after 5 seconds
    setTimeout(() => {
        messageDiv.classList.add('hidden');
    }, 5000);
}

// Format date for display
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

// Format date and time for display
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Clean up intervals when page unloads
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});