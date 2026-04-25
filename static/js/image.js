// image.js — встроенная камера + галерея, результат через openScanResult

class CameraManager {
    constructor() {
        this.stream = null;
        this.video = null;
        this.canvas = null;
        this.isCameraActive = false;
    }

    async initCamera() {
        try {
            console.log('Ініціалізація камери...');

            this.video = document.getElementById('cameraVideo');
            this.canvas = document.getElementById('cameraCanvas');
            if (!this.video || !this.canvas) {
                console.error('Елементи video або canvas не знайдено');
                return;
            }

            this.resetCameraUI();
            this.stopCamera();

            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false
            });

            this.video.srcObject = this.stream;
            this.isCameraActive = true;
            document.getElementById('cameraModal').classList.remove('hidden');
            console.log('Камера активна');
        } catch (error) {
            console.error('Помилка доступу до камери:', error);
            alert(window.i18n('cameraAccessError') || 'Не вдалося отримати доступ до камери.');
            this.closeCamera();
        }
    }

    resetCameraUI() {
        if (this.video) this.video.style.display = 'block';
        if (this.canvas) this.canvas.style.display = 'none';

        document.getElementById('captureBtn').classList.remove('hidden');
        document.getElementById('retakeBtn').classList.add('hidden');
        document.getElementById('usePhotoBtn').classList.add('hidden');
    }

    capturePhoto() {
        console.log('Створення фото...');
        var context = this.canvas.getContext('2d');
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        this.stopCamera();

        this.video.style.display = 'none';
        this.canvas.style.display = 'block';

        document.getElementById('captureBtn').classList.add('hidden');
        document.getElementById('retakeBtn').classList.remove('hidden');
        document.getElementById('usePhotoBtn').classList.remove('hidden');
        console.log('Фото готово');
    }

    retakePhoto() {
        this.canvas.style.display = 'none';
        this.video.style.display = 'block';
        this.resetCameraUI();
        // Просто возвращаем к видоискателю, поток уже остановлен, нужно перезапустить камеру
        this.initCamera();
    }

    async usePhoto() {
        console.log('Аналіз фото...');
        this.canvas.toBlob(async (blob) => {
            var file = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });
            await processImageFile(file, 'camera');
            cameraManager.closeCamera();
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
}

var cameraManager = new CameraManager();

// Глобальные функции
function openCamera() {
    cameraManager.initCamera();
}

function closeCamera() {
    cameraManager.closeCamera();
}

function openGallery() {
    // Полностью закрываем модальное окно камеры перед вызовом галереи
    cameraManager.closeCamera();
    // Небольшая задержка, чтобы окно успело скрыться и не перехватило фокус
    setTimeout(() => {
        document.getElementById('galleryInput').click();
    }, 100);
}

// Галерея (без дополнительного closeCamera, окно уже закрыто)
var galleryInput = document.getElementById('galleryInput');
if (galleryInput) {
    galleryInput.addEventListener('change', function(e) {
        var file = e.target.files[0];
        if (file) {
            processImageFile(file, 'gallery');
            e.target.value = '';  // сброс
        }
    });
}

// Отправка изображения (камера или галерея) и открытие результата
async function processImageFile(file, source) {
    var resultDiv = document.getElementById('result');
    if (!resultDiv) { alert('Помилка: елемент для результатів не знайдено'); return; }

    try {
        resultDiv.innerHTML = `<div class="loading"><p>${window.i18n('processingImage')}</p></div>`;

        var formData = new FormData();
        formData.append('image', file);
        formData.append('input_method', source);
        formData.append('lang', window.getCurrentLang());   // для языка описаний

        var response = await fetch('/api/analyze', { method: 'POST', body: formData });
        if (!response.ok) throw new Error(window.i18n('serverError') + ': ' + response.status);

        var data = await response.json();
        if (data.status === 'success') {
            window.__lastImageResultData = data;
            openScanResult(data);   // глобальная функция из base.html
            resultDiv.innerHTML = '';  // убираем текст "Processing image..."
        } else {
            resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', data.message)}</div>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', error.message)}</div>`;
    }
}

// Инициализация кнопок
document.addEventListener('DOMContentLoaded', function() {
    console.log('IMAGE.JS ЗАВАНТАЖЕНО');

    var captureBtn = document.getElementById('captureBtn');
    var retakeBtn = document.getElementById('retakeBtn');
    var usePhotoBtn = document.getElementById('usePhotoBtn');

    if (captureBtn) captureBtn.addEventListener('click', () => cameraManager.capturePhoto());
    if (retakeBtn) retakeBtn.addEventListener('click', () => cameraManager.retakePhoto());
    if (usePhotoBtn) usePhotoBtn.addEventListener('click', () => cameraManager.usePhoto());

    // Галерея
        var galleryInput = document.getElementById('galleryInput');
    if (galleryInput) {
        galleryInput.addEventListener('change', function(e) {
            var file = e.target.files[0];
            if (file) {
                cameraManager.closeCamera();   // ← закрываем модальное окно камеры
                processImageFile(file, 'gallery');
                e.target.value = '';
            }
        });
    }
});

// Экспорт в глобальную область
window.openCamera = openCamera;
window.closeCamera = closeCamera;
window.openGallery = openGallery;
window.processImageFile = processImageFile;