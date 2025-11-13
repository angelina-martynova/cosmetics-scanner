// Логика для работы с камерой
class CameraManager {
    constructor() {
        this.stream = null;
        this.video = null;
        this.canvas = null;
        this.isCameraActive = false;
    }

    async initCamera() {
        try {
            this.createCameraModal();

            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
            });

            this.video = document.getElementById('cameraVideo');
            this.canvas = document.getElementById('cameraCanvas');
            this.video.srcObject = this.stream;
            this.isCameraActive = true;

            document.getElementById('cameraModal').classList.remove('hidden');
        } catch (error) {
            console.error('Ошибка доступа к камере:', error);
            this.showCameraError();
        }
    }

    createCameraModal() {
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

        this.bindCameraEvents();
    }

    bindCameraEvents() {
        document.getElementById('captureBtn').addEventListener('click', () => this.capturePhoto());
        document.getElementById('retakeBtn').addEventListener('click', () => this.retakePhoto());
        document.getElementById('usePhotoBtn').addEventListener('click', () => this.usePhoto());
    }

    capturePhoto() {
        const context = this.canvas.getContext('2d');
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        this.stopCamera();
        document.getElementById('captureBtn').classList.add('hidden');
        document.getElementById('retakeBtn').classList.remove('hidden');
        document.getElementById('usePhotoBtn').classList.remove('hidden');
        this.video.style.display = 'none';
        this.canvas.style.display = 'block';
    }

    retakePhoto() {
        this.canvas.style.display = 'none';
        this.video.style.display = 'block';
        document.getElementById('captureBtn').classList.remove('hidden');
        document.getElementById('retakeBtn').classList.add('hidden');
        document.getElementById('usePhotoBtn').classList.add('hidden');
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

// Инициализация камеры
const cameraManager = new CameraManager();
