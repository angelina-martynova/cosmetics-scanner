class CosmeticsScanner {
    constructor() {
        this.currentUser = null;
        this.currentScan = null;
    }

    init() {
        this.bindEvents();
        this.checkAuthStatus();
    }

    bindEvents() {
        this.initAuthEvents();
        this.initNavigationEvents();
    }

    initAuthEvents() {
        const loginBtn = document.getElementById('loginBtn');
        const registerBtn = document.getElementById('registerBtn');
        const logoutBtn = document.getElementById('logoutBtn');
        const myScansBtn = document.getElementById('myScansBtn');

        if (loginBtn) loginBtn.addEventListener('click', () => this.navigateToLogin());
        if (registerBtn) registerBtn.addEventListener('click', () => this.navigateToRegister());
        if (logoutBtn) logoutBtn.addEventListener('click', () => this.logout());
        if (myScansBtn) myScansBtn.addEventListener('click', () => this.showMyScans());
    }

    initNavigationEvents() {
        // Навигация уже обрабатывается в auth.js
    }

    navigateToLogin() {
        window.location.href = '/login';
    }

    navigateToRegister() {
        window.location.href = '/register';
    }

    logout() {
        if (window.logout) {
            window.logout();
        }
    }

    showMyScans() {
        // Перенаправляем на страницу истории сканирований
        window.location.href = '/scans';
    }

    checkAuthStatus() {
        fetch('/api/status')
            .then(response => {
                if (!response.ok) {
                    this.currentUser = null;
                    this.updateUI();
                    throw new Error('Not authenticated');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'authenticated') {
                    this.currentUser = data.user;
                    this.updateUI();
                }
            })
            .catch(() => {
                this.currentUser = null;
                this.updateUI();
            });
    }

    updateUI() {
        const authButtons = document.getElementById('authButtons');
        const userMenu = document.getElementById('userMenu');
        const userEmail = document.getElementById('userEmail');

        if (authButtons && userMenu && userEmail) {
            if (this.currentUser) {
                authButtons.classList.add('hidden');
                userMenu.classList.remove('hidden');
                userEmail.textContent = this.currentUser.email;
            } else {
                authButtons.classList.remove('hidden');
                userMenu.classList.add('hidden');
            }
        }
    }

    showMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = message;
        
        document.body.appendChild(messageDiv);
        setTimeout(() => messageDiv.remove(), 5000);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    window.app = new CosmeticsScanner();
    window.app.init();
    console.log('CosmeticsScanner initialized');
});