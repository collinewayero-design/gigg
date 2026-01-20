// ============================================
// GigSpace - Main JavaScript Application
// ============================================

// API Base URL
const API_BASE = window.location.origin + '/api';

// Toast Notification System
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>',
        error: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
        info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">${icons[type]}</div>
        <div class="toast-message">${message}</div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// API Helper Functions
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'Request failed');
        }
        
        return result;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Logout Function
async function logout() {
    try {
        await apiCall('/auth/logout', 'POST');
        showToast('Logged out successfully', 'info');
        setTimeout(() => {
            window.location.href = '/';
        }, 500);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Format Number with Commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Update Balance Display
function updateBalance(newBalance) {
    const navBalance = document.getElementById('nav-balance');
    if (navBalance) {
        navBalance.textContent = formatNumber(newBalance);
    }
    
    const dashBalance = document.getElementById('user-balance');
    if (dashBalance) {
        dashBalance.textContent = formatNumber(newBalance);
    }
}

// ============================================
// AUTH PAGE
// ============================================
if (document.getElementById('auth-form')) {
    const authForm = document.getElementById('auth-form');
    const authTitle = document.getElementById('auth-title');
    const authButton = document.getElementById('auth-button');
    const authToggle = document.getElementById('auth-toggle');
    const usernameField = document.getElementById('username-field');
    
    let isSignup = window.location.search.includes('mode=signup');
    
    function toggleMode() {
        isSignup = !isSignup;
        
        if (isSignup) {
            authTitle.textContent = 'Join the Economy';
            authButton.textContent = 'Create Account';
            authToggle.innerHTML = 'Already have an account? <button type="button" onclick="toggleAuthMode()" class="auth-toggle-btn">Log In</button>';
            usernameField.style.display = 'block';
        } else {
            authTitle.textContent = 'Welcome Back';
            authButton.textContent = 'Log In';
            authToggle.innerHTML = "Don't have an account? <button type=\"button\" onclick=\"toggleAuthMode()\" class=\"auth-toggle-btn\">Sign Up</button>";
            usernameField.style.display = 'none';
        }
    }
    
    window.toggleAuthMode = toggleMode;
    
    if (isSignup) {
        toggleMode();
    }
    
    authForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const username = isSignup ? document.getElementById('username').value : email.split('@')[0];
        
        const submitBtn = authForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Processing...';
        
        try {
            const endpoint = isSignup ? '/auth/signup' : '/auth/login';
            const data = isSignup ? { username, email, password } : { email, password };
            
            const result = await apiCall(endpoint, 'POST', data);
            
            showToast(result.message, 'success');
            
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 500);
            
        } catch (error) {
            showToast(error.message, 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = isSignup ? 'Create Account' : 'Log In';
        }
    });
}

// ============================================
// DASHBOARD PAGE
// ============================================
if (document.getElementById('dashboard-page')) {
    let userData = null;
    
    // Load Dashboard Data
    async function loadDashboard() {
        try {
            // Get user profile
            const profile = await apiCall('/user/profile');
            userData = profile.user;
            
            // Update balance
            updateBalance(userData.balance);
            
            // Update streak
            document.getElementById('daily-streak').textContent = userData.daily_streak;
            
            // Load recent transactions
            const txResponse = await apiCall('/transactions');
            displayTransactions(txResponse.transactions);
            
            // Check daily bonus availability
            checkDailyBonus();
            
        } catch (error) {
            showToast('Error loading dashboard', 'error');
        }
    }
    
    // Display Transactions
    function displayTransactions(transactions) {
        const container = document.getElementById('recent-transactions');
        if (!container) return;
        
        if (transactions.length === 0) {
            container.innerHTML = '<p class="text-center text-muted">No transactions yet</p>';
            return;
        }
        
        container.innerHTML = transactions.slice(0, 5).map(tx => `
            <div class="transaction-item">
                <div class="transaction-info">
                    <div class="transaction-icon ${tx.type.toLowerCase()}">
                        ${tx.type === 'EARN' ? '↑' : '↓'}
                    </div>
                    <div>
                        <div class="transaction-desc">${tx.description}</div>
                        <div class="transaction-date">${tx.timestamp}</div>
                    </div>
                </div>
                <div class="transaction-amount ${tx.type.toLowerCase()}">
                    ${tx.type === 'EARN' ? '+' : '-'}${formatNumber(tx.amount)}
                </div>
            </div>
        `).join('');
    }
    
    // Check Daily Bonus
    function checkDailyBonus() {
        if (!userData) return;
        
        const btn = document.getElementById('claim-daily-btn');
        if (!btn) return;
        
        const now = Date.now();
        const lastClaim = userData.last_daily_claim;
        const ONE_DAY = 24 * 60 * 60 * 1000;
        
        if (lastClaim === 0 || now - lastClaim >= ONE_DAY) {
            btn.disabled = false;
            btn.classList.add('ready');
            btn.textContent = 'Claim Daily Bonus';
        } else {
            const timeLeft = ONE_DAY - (now - lastClaim);
            const hours = Math.floor(timeLeft / (1000 * 60 * 60));
            const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
            
            btn.disabled = true;
            btn.textContent = `Next Bonus in ${hours}h ${minutes}m ${seconds}s`;
            
            setTimeout(checkDailyBonus, 1000);
        }
    }
    
    // Claim Welcome Bonus
    window.claimWelcomeBonus = async function() {
        try {
            const result = await apiCall('/user/claim-welcome', 'POST');
            showToast(result.message, 'success');
            updateBalance(result.new_balance);
            document.getElementById('welcome-bonus-card').style.display = 'none';
        } catch (error) {
            showToast(error.message, 'error');
        }
    };
    
    // Claim Daily Bonus
    window.claimDailyBonus = async function() {
        try {
            const result = await apiCall('/user/claim-daily', 'POST');
            showToast(result.message, 'success');
            updateBalance(result.new_balance);
            document.getElementById('daily-streak').textContent = result.streak;
            checkDailyBonus();
        } catch (error) {
            showToast(error.message, 'error');
        }
    };
    
    // Initialize Dashboard
    loadDashboard();
}

// ============================================
// EARN PAGE
// ============================================
if (document.getElementById('earn-page')) {
    let currentFilter = 'ALL';
    
    async function loadTasks() {
        try {
            const result = await apiCall('/tasks');
            displayTasks(result.tasks);
        } catch (error) {
            showToast('Error loading tasks', 'error');
        }
    }
    
    function displayTasks(tasks) {
        const container = document.getElementById('tasks-container');
        if (!container) return;
        
        const filteredTasks = currentFilter === 'ALL' 
            ? tasks 
            : tasks.filter(t => t.type === currentFilter);
        
        if (filteredTasks.length === 0) {
            container.innerHTML = '<p class="text-center">No tasks available</p>';
            return;
        }
        
        container.innerHTML = filteredTasks.map(task => `
            <div class="task-card">
                <div class="task-header">
                    <div class="task-type-icon ${task.type.toLowerCase()}">
                        ${getTaskIcon(task.type)}
                    </div>
                    <div class="task-reward">+${task.reward} GC</div>
                </div>
                <h3 class="task-title">${task.title}</h3>
                <p class="task-description">${task.description}</p>
                <button class="btn btn-primary btn-block" onclick="completeTask(${task.id})">
                    Start Task
                </button>
            </div>
        `).join('');
    }
    
    function getTaskIcon(type) {
        const icons = {
            VIDEO: '▶',
            CPA: '📱',
            SURVEY: '✓'
        };
        return icons[type] || '•';
    }
    
    window.setFilter = function(filter) {
        currentFilter = filter;
        
        // Update button states
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === filter);
        });
        
        loadTasks();
    };
    
    window.completeTask = async function(taskId) {
        try {
            const result = await apiCall(`/tasks/${taskId}/complete`, 'POST');
            showToast(result.message, 'success');
            updateBalance(result.new_balance);
            loadTasks();
        } catch (error) {
            showToast(error.message, 'error');
        }
    };
    
    loadTasks();
}

// ============================================
// SHOP PAGE
// ============================================
if (document.getElementById('shop-page')) {
    async function loadShopItems() {
        try {
            const result = await apiCall('/shop/items');
            displayShopItems(result.items);
        } catch (error) {
            showToast('Error loading shop', 'error');
        }
    }
    
    function displayShopItems(items) {
        const container = document.getElementById('shop-items-container');
        if (!container) return;
        
        container.innerHTML = items.map(item => `
            <div class="shop-item-card">
                <div class="shop-item-image">
                    <img src="${item.imageUrl}" alt="${item.title}">
                    <div class="shop-item-category">${item.category}</div>
                </div>
                <h3 class="shop-item-title">${item.title}</h3>
                <div class="shop-item-footer">
                    <div class="shop-item-price">${formatNumber(item.price)} GC</div>
                    <button class="shop-buy-btn" onclick="purchaseItem(${item.id}, '${item.title}', ${item.price})">
                        🛒
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    window.purchaseItem = async function(itemId, title, price) {
        if (!confirm(`Purchase ${title} for ${formatNumber(price)} GC?`)) {
            return;
        }
        
        try {
            const result = await apiCall(`/shop/purchase/${itemId}`, 'POST', { quantity: 1 });
            showToast(result.message, 'success');
            updateBalance(result.new_balance);
        } catch (error) {
            showToast(error.message, 'error');
        }
    };
    
    loadShopItems();
}