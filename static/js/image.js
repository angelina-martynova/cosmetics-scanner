// Управление камерой для мобильных устройств
class CameraManager {
    constructor() { 
        this.stream = null; 
        this.video = null; 
        this.canvas = null; 
        this.isCameraActive = false; 
        this.modal = null;
    }
    
    async initCamera() {
        try {
            console.log('🎥 Инициализация камеры...');
            
            // Используем существующее модальное окно из HTML
            this.modal = document.getElementById('cameraModal');
            
            if (!this.modal) {
                console.error('❌ Модальное окно камеры не найдено в HTML');
                return;
            }
            
            // Получаем элементы из существующего HTML
            this.video = document.getElementById('cameraVideo');
            this.canvas = document.getElementById('cameraCanvas');
            
            if (!this.video || !this.canvas) {
                console.error('❌ Элементы видео или canvas не найдены');
                return;
            }
            
            // Сбрасываем состояние UI
            this.resetCameraUI();
            
            // Останавливаем предыдущий поток если есть
            this.stopCamera();
            
            console.log('📡 Запрос доступа к камере...');
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }, 
                audio: false 
            });
            
            console.log('✅ Камера доступна');
            this.video.srcObject = this.stream;
            this.isCameraActive = true;
            
            // Показываем интерфейс после успешной инициализации
            this.showCameraInterface();
            
        } catch (error) {
            console.error('❌ Помилка доступу до камери:', error);
            this.showCameraError();
        }
    }

    resetCameraUI() {
        // Сбрасываем UI к начальному состоянию
        if (this.video) this.video.style.display = 'block';
        if (this.canvas) this.canvas.style.display = 'none';
        
        const captureBtn = document.getElementById('captureBtn');
        const retakeBtn = document.getElementById('retakeBtn');
        const usePhotoBtn = document.getElementById('usePhotoBtn');
        
        if (captureBtn) captureBtn.classList.remove('hidden');
        if (retakeBtn) retakeBtn.classList.add('hidden');
        if (usePhotoBtn) usePhotoBtn.classList.add('hidden');
    }

    showCameraInterface() {
        console.log('👁️ Показ интерфейса камеры...');
        
        if (this.modal) {
            this.modal.classList.remove('hidden');
            console.log('✅ Модальное окно камеры показано');
        } else {
            console.error('❌ Модальное окно не найдено');
        }
    }

    capturePhoto() {
        console.log('📸 Создание фото...');
        const context = this.canvas.getContext('2d');
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        this.stopCamera();
        
        // Показываем/скрываем кнопки
        document.getElementById('captureBtn').classList.add('hidden');
        document.getElementById('retakeBtn').classList.remove('hidden');
        document.getElementById('usePhotoBtn').classList.remove('hidden');
        
        // Переключаем видео на canvas
        this.video.style.display = 'none';
        this.canvas.style.display = 'block';
        
        console.log('✅ Фото создано');
    }

    retakePhoto() {
        console.log('🔄 Пересъемка...');
        this.canvas.style.display = 'none';
        this.video.style.display = 'block';
        
        document.getElementById('captureBtn').classList.remove('hidden');
        document.getElementById('retakeBtn').classList.add('hidden');
        document.getElementById('usePhotoBtn').classList.add('hidden');
        
        this.initCamera();
    }

    async usePhoto() {
        console.log('✅ Анализ фото...');
        this.canvas.toBlob(async (blob) => {
            const file = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });
            
            // Передаем метод ввода "camera"
            await processImageFile(file, 'camera');
            
            // Закрываем камеру после анализа
            this.closeCamera();
            
        }, 'image/jpeg', 0.8);
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
            this.isCameraActive = false;
            console.log('⏹️ Камера остановлена');
        }
    }

    closeCamera() {
        console.log('❌ Закрытие камеры...');
        this.stopCamera();
        if (this.modal) {
            this.modal.classList.add('hidden');
            console.log('✅ Модальное окно скрыто');
        }
    }

    showCameraError() {
        alert('Не вдалося отримати доступ до камери. Перевірте дозволи браузера або використовуйте інший пристрій.');
        this.closeCamera();
    }
}

// Функция для обработки изображений
async function processImageFile(file, source) {
    const resultDiv = document.getElementById('result');
    
    if (!resultDiv) {
        console.error('❌ Елемент result не знайдено');
        alert('Помилка: елемент для результатів не знайдено');
        return;
    }

    try {
        resultDiv.innerHTML = '<p class="loading">Обробляється зображення...</p>';
        
        const formData = new FormData();
        formData.append('image', file);
        
        // Передаем метод ввода в зависимости от источника
        if (source === 'camera') {
            formData.append('input_method', 'camera');
        } else {
            formData.append('input_method', 'device'); // Для галереи
        }

        console.log('📤 Отправка изображения на сервер...');
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });

        console.log('📥 Ответ сервера:', response.status);
        
        if (!response.ok) {
            throw new Error(`Помилка сервера: ${response.status}`);
        }

        const data = await response.json();
        console.log('📊 Данные ответа:', data);
        
        if (data.status === 'success') {
            displayImageResults(data);
        } else {
            resultDiv.innerHTML = `<p class="error">Помилка: ${data.message}</p>`;
        }
        
    } catch (error) {
        console.error('❌ Error:', error);
        resultDiv.innerHTML = `<p class="error">Помилка при обробці зображення: ${error.message}</p>`;
    }
}

// Функция для отображения результатов
function displayImageResults(data) {
    const resultDiv = document.getElementById('result');
    
    if (!resultDiv) {
        console.error('❌ Елемент result не знайдено при відображенні результатів');
        return;
    }
    
    let html = `
        <div class="result-section">
            <h3>Розпізнаний текст:</h3>
            <div class="text-preview">${data.text || 'Текст не знайдено'}</div>
        </div>
    `;

    if (data.ingredients && data.ingredients.length > 0) {
        html += `
            <div class="result-section">
                <h3>Знайдені інгредієнти:</h3>
                <div class="ingredients-list">
        `;
        
        data.ingredients.forEach(ingredient => {
            const riskClass = ingredient.risk_level === 'high' ? 'high-risk' : 
                            ingredient.risk_level === 'medium' ? 'medium-risk' :
                            ingredient.risk_level === 'low' ? 'low-risk' : 'safe';
            
            html += `
                <div class="ingredient-item ${riskClass}">
                    <div class="ingredient-name"><strong>${ingredient.name}</strong></div>
                    <div class="ingredient-category">Категорія: ${ingredient.category}</div>
                    <div class="ingredient-description">${ingredient.description}</div>
                    <div class="risk-level">Рівень ризику: ${ingredient.risk_level}</div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    } else {
        html += `
            <div class="result-section">
                <h3>Інгредієнти:</h3>
                <p class="success">Не знайдено потенційно шкідливих інгредієнтів</p>
            </div>
        `;
    }

    resultDiv.innerHTML = html;
}

// Глобальные функции
function openCamera() {
    console.log('🖱️ openCamera вызвана');
    cameraManager.initCamera();
}

function closeCamera() {
    cameraManager.closeCamera();
}

function openGallery() {
    console.log('🖱️ openGallery вызвана');
    // Закрываем модальное окно камеры перед открытием галереи
    closeCamera();
    document.getElementById('galleryInput').click();
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 IMAGE.JS ЗАГРУЖЕН');
    
    // Привязываем события для кнопок в существующем модальном окне
    const captureBtn = document.getElementById('captureBtn');
    const retakeBtn = document.getElementById('retakeBtn');
    const usePhotoBtn = document.getElementById('usePhotoBtn');
    
    if (captureBtn) {
        captureBtn.addEventListener('click', () => cameraManager.capturePhoto());
    }
    if (retakeBtn) {
        retakeBtn.addEventListener('click', () => cameraManager.retakePhoto());
    }
    if (usePhotoBtn) {
        usePhotoBtn.addEventListener('click', () => cameraManager.usePhoto());
    }
    
    // Обработчик для галереи
    const galleryInput = document.getElementById('galleryInput');
    if (galleryInput) {
        galleryInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                console.log('📁 Файл выбран из галереи:', file.name);
                // Закрываем модальное окно камеры при выборе файла
                closeCamera();
                processImageFile(file, 'gallery');
                // Очищаем input
                e.target.value = '';
            }
        });
    }
});

// Глобальный экземпляр
const cameraManager = new CameraManager();

// Делаем функции глобальными
window.openCamera = openCamera;
window.closeCamera = closeCamera;
window.openGallery = openGallery;
window.processImageFile = processImageFile;

console.log('✅ Image.js модуль загружен и готов');