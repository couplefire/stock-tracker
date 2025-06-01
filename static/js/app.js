// Global state
let items = [];
let emails = [];
let editingItemId = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadItems();
    loadEmails();
    updateTrackerStatus();
    
    // Refresh data every 5 seconds
    setInterval(() => {
        loadItems();
        updateTrackerStatus();
    }, 5000);
});

// API Functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'API request failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

// Load items
async function loadItems() {
    try {
        items = await apiCall('/api/items');
        renderItems();
    } catch (error) {
        console.error('Failed to load items:', error);
    }
}

// Load emails
async function loadEmails() {
    try {
        emails = await apiCall('/api/emails');
        renderEmails();
    } catch (error) {
        console.error('Failed to load emails:', error);
    }
}

// Update tracker status
async function updateTrackerStatus() {
    try {
        const status = await apiCall('/api/tracker/status');
        const indicator = document.getElementById('tracker-status');
        const state = document.getElementById('tracker-state');
        
        if (status.running) {
            indicator.classList.add('active');
            state.textContent = `Running (checking every ${status.check_interval}s)`;
        } else {
            indicator.classList.remove('active');
            state.textContent = 'Stopped';
        }
    } catch (error) {
        console.error('Failed to get tracker status:', error);
    }
}

// Render items
function renderItems() {
    const container = document.getElementById('items-list');
    
    if (items.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-box-open"></i>
                <p>No items being tracked yet. Click "Add Item" to get started.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = items.map(item => {
        const availabilityClass = item.is_available === null ? 'checking' : 
                                item.is_available ? 'available' : 'out-of-stock';
        const availabilityText = item.is_available === null ? 'Checking...' : 
                               item.is_available ? 'Available' : 'Out of Stock';
        
        return `
            <div class="item-card">
                <div class="item-header">
                    <div>
                        <div class="item-name">${escapeHtml(item.name)}</div>
                        <a href="${escapeHtml(item.url)}" target="_blank" class="item-url">
                            ${escapeHtml(item.url)}
                        </a>
                    </div>
                    <span class="availability-badge ${availabilityClass}">
                        ${availabilityText}
                    </span>
                </div>
                
                <div class="item-rule">
                    Pattern: "${escapeHtml(item.rule_pattern)}"<br>
                    Out of stock when matches ≥ ${item.rule_count}
                </div>
                
                <div class="item-details">
                    ${item.last_checked ? `Last checked: ${item.last_checked}` : 'Not checked yet'}
                </div>
                
                <div class="item-actions">
                    <button class="btn btn-sm btn-primary" onclick="checkItem(${item.id})">
                        <i class="fas fa-sync"></i> Check Now
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="editItem(${item.id})">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteItem(${item.id})">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Render emails
function renderEmails() {
    const container = document.getElementById('emails-list');
    
    if (emails.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-envelope-open"></i>
                <p>No email addresses configured. Add one to receive notifications.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = emails.map(email => `
        <div class="email-item">
            <span class="email-address">${escapeHtml(email.email)}</span>
            <button class="btn btn-sm btn-danger" onclick="deleteEmail(${email.id})">
                <i class="fas fa-trash"></i> Remove
            </button>
        </div>
    `).join('');
}

// Item Modal Functions
function showAddItemModal() {
    editingItemId = null;
    document.getElementById('item-modal-title').textContent = 'Add New Item';
    document.getElementById('item-form').reset();
    document.getElementById('item-modal').classList.add('show');
}

function editItem(id) {
    const item = items.find(i => i.id === id);
    if (!item) return;
    
    editingItemId = id;
    document.getElementById('item-modal-title').textContent = 'Edit Item';
    document.getElementById('item-name').value = item.name;
    document.getElementById('item-url').value = item.url;
    document.getElementById('item-pattern').value = item.rule_pattern;
    document.getElementById('item-count').value = item.rule_count;
    document.getElementById('item-modal').classList.add('show');
}

function closeItemModal() {
    document.getElementById('item-modal').classList.remove('show');
    editingItemId = null;
}

async function saveItem(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = {
        name: formData.get('name'),
        url: formData.get('url'),
        rule_pattern: formData.get('rule_pattern'),
        rule_count: parseInt(formData.get('rule_count'))
    };
    
    try {
        if (editingItemId) {
            await apiCall(`/api/items/${editingItemId}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
            showNotification('Item updated successfully', 'success');
        } else {
            await apiCall('/api/items', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            showNotification('Item added successfully', 'success');
        }
        
        closeItemModal();
        loadItems();
    } catch (error) {
        console.error('Failed to save item:', error);
    }
}

async function deleteItem(id) {
    if (!confirm('Are you sure you want to delete this item?')) return;
    
    try {
        await apiCall(`/api/items/${id}`, { method: 'DELETE' });
        showNotification('Item deleted successfully', 'success');
        loadItems();
    } catch (error) {
        console.error('Failed to delete item:', error);
    }
}

async function checkItem(id) {
    try {
        await apiCall(`/api/items/${id}/check`, { method: 'POST' });
        showNotification('Item check initiated', 'info');
        
        // Update UI to show checking state
        const item = items.find(i => i.id === id);
        if (item) {
            item.is_available = null;
            renderItems();
        }
    } catch (error) {
        console.error('Failed to check item:', error);
    }
}

// Email Modal Functions
function showAddEmailModal() {
    document.getElementById('email-form').reset();
    document.getElementById('email-modal').classList.add('show');
}

function closeEmailModal() {
    document.getElementById('email-modal').classList.remove('show');
}

async function saveEmail(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = {
        email: formData.get('email')
    };
    
    try {
        await apiCall('/api/emails', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        showNotification('Email added successfully', 'success');
        closeEmailModal();
        loadEmails();
    } catch (error) {
        console.error('Failed to save email:', error);
    }
}

async function deleteEmail(id) {
    if (!confirm('Are you sure you want to remove this email address?')) return;
    
    try {
        await apiCall(`/api/emails/${id}`, { method: 'DELETE' });
        showNotification('Email removed successfully', 'success');
        loadEmails();
    } catch (error) {
        console.error('Failed to delete email:', error);
    }
}

// Utility Functions
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function showNotification(message, type = 'info') {
    // Simple notification - could be enhanced with a toast library
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
    }
} 