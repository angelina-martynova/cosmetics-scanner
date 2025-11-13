// Управление камерой
class CameraManager {
    constructor() {
        this.stream = null;
        this.video = null;
        this.canvas = null;
        this.isCameraActive = false;
    }

    async initCamera() {
        try {
            // Создаем модальное окно для камеры
            this.createCameraModal();
            
            // Запрашиваем доступ к камере
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });

            // Привязываем видеопоток к элементу video
            this.video = document.getElementById('cameraVideo');
            this.canvas = document.getElementById('cameraCanvas');
            
            this.video.srcObject = this.stream;
            this.isCameraActive = true;

            // Показываем интерфейс камеры
            document.getElementById('cameraModal').classList.remove('hidden');

        } catch (error) {
            console.error('Ошибка доступа к камере:', error);
            this.showCameraError();
        }
    }

    createCameraModal() {
        // Убедимся, что модальное окно существует
        if (!document.getElementById('cameraModal')) {
            const modalHTML = `
                <div id="cameraModal" class="modal">
                    <div class="modal-content">
                        <h3>📷 Сканирование камерой</h3>
                        <div class="camera-preview">
                            <video id="cameraVideo" autoplay playsinline></video>
                            <canvas id="cameraCanvas" style="display: none;"></canvas>
                        </div>
                        <div class="camera-controls">
                            <button id="captureBtn">📸 Сделать снимок</button>
                            <button id="retakeBtn" class="hidden">🔄 Переснять</button>
                            <button id="usePhotoBtn" class="hidden">✅ Использовать фото</button>
                            <button onclick="app.openGallery()">📂 Выбрать из галереи</button>
                            <button onclick="app.closeCamera()">❌ Отмена</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }
        
        // Привязываем события после создания элементов
        this.bindCameraEvents();
    }

    bindCameraEvents() {
        document.getElementById('captureBtn').addEventListener('click', () => this.capturePhoto());
        document.getElementById('retakeBtn').addEventListener('click', () => this.retakePhoto());
        document.getElementById('usePhotoBtn').addEventListener('click', () => this.usePhoto());
    }

    capturePhoto() {
        const context = this.canvas.getContext('2d');
        
        // Устанавливаем размеры canvas как у video
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        
        // Рисуем текущий кадр на canvas
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        // Останавливаем поток для экономии батареи
        this.stopCamera();
        
        // Показываем кнопки подтверждения
        document.getElementById('captureBtn').classList.add('hidden');
        document.getElementById('retakeBtn').classList.remove('hidden');
        document.getElementById('usePhotoBtn').classList.remove('hidden');
        
        // Показываем превью
        this.video.style.display = 'none';
        this.canvas.style.display = 'block';
    }

    retakePhoto() {
        // Сбрасываем сделанное фото
        this.canvas.style.display = 'none';
        this.video.style.display = 'block';
        
        // Показываем кнопки подтверждения
        document.getElementById('captureBtn').classList.remove('hidden');
        document.getElementById('retakeBtn').classList.add('hidden');
        document.getElementById('usePhotoBtn').classList.add('hidden');
        
        // Перезапускаем камеру
        this.initCamera();
    }

    async usePhoto() {
        this.canvas.toBlob(async (blob) => {
            const file = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });
            await app.processImage(file, 'camera');
            this.closeCamera();
        }, 'image/jpeg', 0.8);
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
            this.isCameraActive = false;
        }
    }

    closeCamera() {
        this.stopCamera();
        document.getElementById('cameraModal').classList.add('hidden');
    }

    showCameraError() {
        alert('Не удалось получить доступ к камере. Проверьте разрешения браузера.');
        this.closeCamera();
    }
}

// Основной класс приложения
class CosmeticsScanner {
    constructor() {
        this.currentUser = null;
        this.currentScan = null;
        this.cameraManager = new CameraManager();
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkAuthStatus();
    }

    bindEvents() {
        // Кнопки аутентификации
        document.getElementById('loginBtn').addEventListener('click', () => window.location.href = "/login");
        document.getElementById('registerBtn').addEventListener('click', () => window.location.href = "/register");
        document.getElementById('logoutBtn').addEventListener('click', () => this.logout());
        document.getElementById('myScansBtn').addEventListener('click', () => this.showMyScans());

        // Закрытие модальных окон
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.hideAllModals();
            }
        });

        // Обработка галереи
        document.getElementById('galleryInput').addEventListener('change', (e) => {
            if (e.target.files[0]) {
                this.processImage(e.target.files[0], 'gallery');
            }
        });

        // Добавление обработчика для выбора текстового файла
         document.getElementById('uploadFileBtn').addEventListener('click', () => this.triggerFileInput());
        document.getElementById('fileInput').addEventListener('change', (e) => this.handleFileSelect(e));
    }

    // Показать плашку для ввода текста
    openTextInput() {
        document.getElementById('textInputModal').classList.remove('hidden');
    }

    // Закрыть плашку для ввода текста
    closeTextInput() {
        document.getElementById('textInputModal').classList.add('hidden');
        document.getElementById('manualTextInput').value = '';
    }

    // Методы для камеры
    openCamera() {
        this.cameraManager.initCamera();
    }

    closeCamera() {
        this.cameraManager.closeCamera();
    }

    openGallery() {
        document.getElementById('galleryInput').click();
    }

     // Метод для открытия выбора файла
    triggerFileInput() {
        document.getElementById('fileInput').click();
    }

    // Обработка выбранного текстового файла
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            const formData = new FormData();
            formData.append('file', file);

            fetch('/api/upload_text_file', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.showMessage('Файл успешно загружен и проанализирован');
                } else {
                    this.showMessage('Ошибка: ' + data.message, 'error');
                }
            })
            .catch(error => {
                this.showMessage('Ошибка при загрузке файла: ' + error, 'error');
            });
        }
    }

    // Скрыть все модальные окна
    hideAllModals() {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => modal.classList.add('hidden'));
    }

    // Показать модальное окно логина (если нужно)
    showLoginModal() {
        // Реализация показа модального окна логина
        console.log('Show login modal');
    }

    // Показать модальное окно регистрации (если нужно)
    showRegisterModal() {
        // Реализация показа модального окна регистрации
        console.log('Show register modal');
    }

    // Показать мои сканирования
    showMyScans() {
        window.location.href = "/scans";
    }

    // Аутентификация
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

    // Регистрация
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

    // Сканирование
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

            // Кнопка експорта
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

    // Вспомогательные функции для классификации рисков
    getRiskClass(riskLevel) {
        switch(riskLevel) {
            case 'low': return 'risk-low';
            case 'medium': return 'risk-medium';
            case 'high': return 'risk-high';
            default: return 'risk-unknown';
        }
    }

    getRiskLabel(riskLevel) {
        switch(riskLevel) {
            case 'low': return 'Низький';
            case 'medium': return 'Середній';
            case 'high': return 'Високий';
            default: return 'Невідомо';
        }
    }

    // Допоміжні функції
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

  // Показать сообщение
    showMessage(message, type = 'success') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = message;
        document.body.appendChild(messageDiv);
        setTimeout(() => messageDiv.remove(), 5000);
    }

    // Показать загрузку
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

    // Функция для экспорта (заглушка)
    exportToPDF(scanId) {
        this.showMessage('Функція експорту в розробці', 'info');
    }
}

// Глобальные функции для HTML
function openCamera() {
    app.openCamera();
}

function openGallery() {
    app.openGallery();
}

function closeCamera() {
    app.closeCamera();
}

function openTextInput() {
    app.openTextInput();
}

function closeTextInput() {
    app.closeTextInput();
}

function processManualText() {
    app.processManualText();
}

// Инициализация приложения
const app = new CosmeticsScanner();
