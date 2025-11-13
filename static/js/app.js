class CosmeticsScanner {
    constructor() {
        this.currentUser = null;
        this.currentScan = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkAuthStatus();
    }

    bindEvents() {
        // Инициализация событий
        this.initAuthEvents();
        this.initCameraEvents();
        this.initFileEvents();
    }

    // Инициализация событий аутентификации
    initAuthEvents() {
        document.getElementById('loginBtn').addEventListener('click', () => login());
        document.getElementById('registerBtn').addEventListener('click', () => register());
        document.getElementById('logoutBtn').addEventListener('click', () => logout());
        document.getElementById('myScansBtn').addEventListener('click', () => showMyScans());
    }

    // Инициализация событий для камеры
    initCameraEvents() {
        document.getElementById('openCameraBtn').addEventListener('click', () => openCamera());
    }

    // Инициализация событий для работы с файлами
    initFileEvents() {
        document.getElementById('galleryInput').addEventListener('change', (e) => handleFileSelect(e));
        document.getElementById('uploadFileBtn').addEventListener('click', () => triggerFileInput());
        document.getElementById('fileInput').addEventListener('change', (e) => handleFileSelect(e));
    }

    checkAuthStatus() {
        fetch('/api/status')
            .then(response => response.json())
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

    // Обновление UI при изменении состояния аутентификации
    updateUI() {
        const authButtons = document.getElementById('authButtons');
        const userMenu = document.getElementById('userMenu');
        const userEmail = document.getElementById('userEmail');

        if (this.currentUser) {
            authButtons.classList.add('hidden');
            userMenu.classList.remove('hidden');
            userEmail.textContent = this.currentUser.email;
        } else {
            authButtons.classList.remove('hidden');
            userMenu.classList.add('hidden');
        }
    }

    // Показ сообщений
    showMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = message;
        
        document.body.appendChild(messageDiv);
        setTimeout(() => messageDiv.remove(), 5000);
    }
}

// Инициализация приложения
const app = new CosmeticsScanner();
