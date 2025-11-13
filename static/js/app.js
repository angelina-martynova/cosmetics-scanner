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
        // Кнопки аутентифікації
        document.getElementById('loginBtn').addEventListener('click', () => window.location.href = "/login"); // Переход на страницу входа
        document.getElementById('registerBtn').addEventListener('click', () => window.location.href = "/register"); // Переход на страницу регистрации
        document.getElementById('logoutBtn').addEventListener('click', () => this.logout());
        document.getElementById('myScansBtn').addEventListener('click', () => this.showMyScans());

        // Закриття модальних вікон
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.hideAllModals();
            }
        });

        // Открытие текстового ввода и галереи
        document.getElementById('galleryInput').addEventListener('change', (e) => this.processImage(e.target.files[0], 'gallery'));
    }

    // Показати плашку для вводу тексту
    openTextInput() {
        document.getElementById('textInputModal').classList.remove('hidden');
    }

    // Закрити плашку для вводу тексту
    closeTextInput() {
        document.getElementById('textInputModal').classList.add('hidden');
        document.getElementById('manualTextInput').value = '';
    }

    // Аутентифікація
    async login(email, password) {
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.currentUser = data.user;
                this.updateUI();
                this.hideAllModals();
                this.showMessage('Успішний вхід!', 'success');
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            this.showMessage('Помилка з\'єднання', 'error');
        }
    }

    // Реєстрація
    async register(email, password) {
        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.showMessage('Реєстрація успішна! Тепер увійдіть.', 'success');
                this.showLoginModal();
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            this.showMessage('Помилка з\'єднання', 'error');
        }
    }

    logout() {
        fetch('/api/logout', { method: 'POST' })
            .then(() => {
                this.currentUser = null;
                this.updateUI();
                this.showMessage('Ви вийшли з системи', 'success');
            });
    }

    // Сканування
    async processManualText() {
        const text = document.getElementById('manualTextInput').value.trim();
        
        if (!text) {
            this.showMessage('Будь ласка, введіть текст', 'error');
            return;
        }

        // Очистка поля ввода
        document.getElementById('manualTextInput').value = '';
        
        this.showLoading('Аналізуємо текст...');
        
        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    input_type: 'text',
                    text: text
                })
            });

            const data = await response.json();
            this.handleAnalysisResult(data);
        } catch (error) {
            this.showMessage('Помилка аналізу', 'error');
        }
    }

    async processImage(file, inputType = 'camera') {
        this.showLoading('Обробляємо зображення...');
        
        const formData = new FormData();
        formData.append('image', file);

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Не вдалося обробити зображення');
            }

            const data = await response.json();
            this.handleAnalysisResult(data);
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    handleAnalysisResult(data) {
        if (data.status === 'success') {
            this.currentScan = data;
            this.displayResults(data);
            
            if (data.scan_id && this.currentUser) {
                this.showMessage('Сканування збережено в історії', 'success');
            }
        } else {
            this.showMessage(data.message, 'error');
        }
    }

    displayResults(data) {
        const resultDiv = document.getElementById('result');
        let html = `
            <h3>🔍 Розпізнаний текст:</h3>
            <div class="text-preview">${this.escapeHtml(data.text)}</div>
        `;

        if (data.ingredients.length === 0) {
            html += '<div class="success">✅ Шкідливих інгредієнтів не знайдено.</div>';
        } else {
            html += '<h3>📋 Виявлені інгредієнти:</h3>';
            
            data.ingredients.forEach(ing => {
                const riskClass = this.getRiskClass(ing.risk_level);
                html += `
                    <div class="ingredient-item ${riskClass}">
                        <strong>${this.escapeHtml(ing.name)}</strong><br>
                        <em>Категорія:</em> ${ing.category || "Невідомо"}<br>
                        <em>Ризик:</em> ${this.getRiskLabel(ing.risk_level)}<br>
                        <em>Опис:</em> ${ing.description || "Немає опису"}
                    </div>
                `;
            });

            // Кнопка експорту
            if (data.scan_id) {
                html += `
                    <div class="export-actions">
                        <button onclick="app.exportToPDF(${data.scan_id})">💾 Зберегти як PDF</button>
                    </div>
                `;
            }
        }

        resultDiv.innerHTML = html;
    }

    // Допоміжні функції
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showMessage(message, type) {
        // Реалізація показу повідомлень
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = message;
        
        document.body.appendChild(messageDiv);
        setTimeout(() => messageDiv.remove(), 5000);
    }

    showLoading(message) {
        document.getElementById('result').innerHTML = `
            <div class="loading">
                <div class="spinner">⏳</div>
                <p>${message}</p>
            </div>
        `;
    }

    // UI управління
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
}

// Ініціалізація додатка
const app = new CosmeticsScanner();