// Управління камерою для мобільних пристроїв
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
            // Створюємо елементи для камери тільки один раз
            if (!this.modal) {
                this.createCameraUI();
            }

            // Запитуємо доступ до камери
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    facingMode: 'environment', // Задня камера
                    width: { ideal: 1920 },
                    height: { ideal: 1080 }
                },
                audio: false
            });

            this.video.srcObject = this.stream;
            this.isCameraActive = true;
            
            // Показуємо інтерфейс камери
            this.showCameraInterface();

        } catch (error) {
            console.error('Помилка доступу до камери:', error);
            this.showCameraError();
        }
    }

    createCameraUI() {
        // Створюємо інтерфейс камери лише один раз
        const cameraHTML = `
            <div id="cameraInterface" class="modal">
                <div class="modal-content">
                    <h3>📷 Сканування камерою</h3>
                    <div class="camera-preview">
                        <video id="cameraVideo" autoplay playsinline></video>
                        <canvas id="cameraCanvas" style="display: none;"></canvas>
                    </div>
                    <div class="camera-controls">
                        <button id="captureBtn">📸 Зробити знімок</button>
                        <button id="retakeBtn" class="hidden">🔄 Перезняти</button>
                        <button id="usePhotoBtn" class="hidden">✅ Використати фото</button>
                        <button onclick="cameraManager.closeCamera()">❌ Скасувати</button>
                    </div>
                </div>
            </div>
        `;
        
        this.modal = document.createElement('div');
        this.modal.innerHTML = cameraHTML;
        document.body.appendChild(this.modal);
        
        this.video = document.getElementById('cameraVideo');
        this.canvas = document.getElementById('cameraCanvas');
        
        // Прив'язуємо події
        document.getElementById('captureBtn').addEventListener('click', () => this.capturePhoto());
        document.getElementById('retakeBtn').addEventListener('click', () => this.retakePhoto());
        document.getElementById('usePhotoBtn').addEventListener('click', () => this.usePhoto());
    }

    showCameraInterface() {
        // Показуємо інтерфейс камери
        document.getElementById('cameraInterface').classList.remove('hidden');
    }

    capturePhoto() {
        const context = this.canvas.getContext('2d');
        
        // Встановлюємо розміри canvas як у video
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        
        // Малюємо поточний кадр на canvas
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        // Зупиняємо потік для економії батареї
        this.stopCamera();
        
        // Показуємо кнопки підтвердження
        document.getElementById('captureBtn').classList.add('hidden');
        document.getElementById('retakeBtn').classList.remove('hidden');
        document.getElementById('usePhotoBtn').classList.remove('hidden');
        
        // Показуємо прев'ю
        this.video.style.display = 'none';
        this.canvas.style.display = 'block';
    }

    retakePhoto() {
        // Скидаємо зроблене фото
        this.canvas.style.display = 'none';
        this.video.style.display = 'block';
        
        // Показуємо кнопки підтвердження
        document.getElementById('captureBtn').classList.remove('hidden');
        document.getElementById('retakeBtn').classList.add('hidden');
        document.getElementById('usePhotoBtn').classList.add('hidden');
        
        // Перезапускаємо камеру
        this.initCamera();
    }

    async usePhoto() {
        // Конвертуємо canvas в blob
        this.canvas.toBlob(async (blob) => {
            const file = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });
            
            // Обробляємо фото через головний додаток
            await app.processImage(file, 'camera');
            
            // Закриваємо камеру
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
        const cameraInterface = document.getElementById('cameraInterface');
        if (cameraInterface) {
            cameraInterface.remove();
        }
    }

    showCameraError() {
        alert('Не вдалося отримати доступ до камери. Перевірте дозволи браузера або використовуйте інший пристрій.');
        this.closeCamera();
    }
}

// Функції для глобального доступу
function openCamera() {
    cameraManager.initCamera();
}

function openGallery() {
    document.getElementById('galleryInput').click();
}

// Обробка вибору файлів
document.getElementById('galleryInput').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        app.processImage(file, 'gallery');
    }
});

// Ініціалізація менеджера камери
const cameraManager = new CameraManager();
