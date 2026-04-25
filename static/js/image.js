// image.js — Skipley Camera Module

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
            console.log('Ініціалізація камери...');

            this.modal = document.getElementById('cameraModal');
            if (!this.modal) { console.error('Модальне вікно камери не знайдено'); return; }

            this.video = document.getElementById('cameraVideo');
            this.canvas = document.getElementById('cameraCanvas');
            if (!this.video || !this.canvas) { console.error('Елементи video або canvas не знайдено'); return; }

            this.resetCameraUI();
            this.stopCamera();

            console.log('Запит доступу до камери...');
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false
            });

            console.log('Камера доступна');
            this.video.srcObject = this.stream;
            this.isCameraActive = true;
            this.showCameraInterface();

        } catch (error) {
            console.error('Помилка доступу до камери:', error);
            this.showCameraError();
        }
    }

    resetCameraUI() {
        if (this.video) this.video.style.display = 'block';
        if (this.canvas) this.canvas.style.display = 'none';

        var captureBtn = document.getElementById('captureBtn');
        var retakeBtn = document.getElementById('retakeBtn');
        var usePhotoBtn = document.getElementById('usePhotoBtn');

        if (captureBtn) captureBtn.classList.remove('hidden');
        if (retakeBtn) retakeBtn.classList.add('hidden');
        if (usePhotoBtn) usePhotoBtn.classList.add('hidden');
    }

    showCameraInterface() {
        if (this.modal) {
            this.modal.classList.remove('hidden');
        }
    }

    capturePhoto() {
        var context = this.canvas.getContext('2d');
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        this.stopCamera();

        document.getElementById('captureBtn').classList.add('hidden');
        document.getElementById('retakeBtn').classList.remove('hidden');
        document.getElementById('usePhotoBtn').classList.remove('hidden');

        this.video.style.display = 'none';
        this.canvas.style.display = 'block';
        console.log('Фото створено');
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
        this.canvas.toBlob(async function(blob) {
            var file = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });
            await processImageFile(file, 'camera');
            cameraManager.closeCamera();
        }, 'image/jpeg', 0.8);
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(function(track) { track.stop(); });
            this.stream = null;
            this.isCameraActive = false;
        }
    }

    closeCamera() {
        this.stopCamera();
        if (this.modal) this.modal.classList.add('hidden');
    }

    showCameraError() {
        alert(window.i18n('cameraAccessError'));
        this.closeCamera();
    }
}

// Функція для обробки зображень
async function processImageFile(file, source) {
    var resultDiv = document.getElementById('result');
    if (!resultDiv) { alert('Помилка: елемент для результатів не знайдено'); return; }

    try {
        resultDiv.innerHTML = `<div class="loading"><p>${window.i18n('processingImage')}</p></div>`;

        var formData = new FormData();
        formData.append('image', file);
        formData.append('input_method', source === 'camera' ? 'camera' : 'device');

        var response = await fetch('/api/analyze', { method: 'POST', body: formData });
        if (!response.ok) throw new Error(window.i18n('serverError') + ': ' + response.status);

        var data = await response.json();
        if (data.status === 'success') {
            window.__lastImageResultData = data;
            displayImageResults(data);
        } else {
            resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', data.message)}</div>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', error.message)}</div>`;
    }
}

// Функція для відображення результатів
function displayImageResults(data) {
    var resultDiv = document.getElementById('result');
    if (!resultDiv) return;

    var html = '';

    if (data.ingredients && data.ingredients.length > 0) {
        var counts = {};
        data.ingredients.forEach(function(ing) {
            var lvl = ing.risk_level || 'safe';
            counts[lvl] = (counts[lvl] || 0) + 1;
        });

        html += '<div class="results-summary"><div class="results-summary-header">';
        html += '<h2>' + window.i18n('analysisComplete') + '</h2>';
        html += '<span class="results-count">' + window.i18n('ingredientsFound', data.ingredients.length) + '</span>';
        html += '</div><div class="risk-counts">';
        for (var lvl in counts) {
            var riskLabel = window.i18n('risk_' + lvl) || lvl;
            html += '<span class="risk-badge risk-' + lvl + '"><span class="dot"></span>' + counts[lvl] + ' ' + riskLabel + '</span>';
        }
        html += '</div></div>';

        html += '<div class="ingredients-list">';
        data.ingredients.forEach(function(ingredient) {
            var riskClass = 'risk-' + (ingredient.risk_level || 'safe');
            var riskLabel = window.i18n('risk_' + (ingredient.risk_level || 'safe')) || (ingredient.risk_level || 'safe');
            html += '<div class="ingredient-item">';
            html += '<div class="ingredient-info">';
            html += '<div class="ingredient-name">' + ingredient.name + '</div>';
            html += '<div class="ingredient-desc">' + (ingredient.description || ingredient.category || '') + '</div>';
            html += '</div>';
            html += '<span class="risk-badge risk-sm ' + riskClass + '"><span class="dot"></span>' + riskLabel + '</span>';
            html += '</div>';
        });
        html += '</div>';
    }

    if (data.text) {
        html += '<div style="margin-top:16px"><p class="detail-section-label">' + window.i18n('recognizedText') + '</p>';
        html += '<div class="original-text">' + data.text + '</div></div>';
    }

    if (!data.ingredients || data.ingredients.length === 0) {
        html += '<div class="success-msg">' + window.i18n('noHarmfulIngredients') + '</div>';
    }

    resultDiv.innerHTML = html;
}

// Глобальні функції
function openCamera() {
    cameraManager.initCamera();
}

function closeCamera() {
    cameraManager.closeCamera();
}

function openGallery() {
    closeCamera();
    document.getElementById('galleryInput').click();
}

window.addEventListener('languageChanged', function() {
    if (window.__lastImageResultData) {
        displayImageResults(window.__lastImageResultData);
    }
});

// Ініціалізація
document.addEventListener('DOMContentLoaded', function() {
    console.log('IMAGE.JS ЗАВАНТАЖЕНО');

    var captureBtn = document.getElementById('captureBtn');
    var retakeBtn = document.getElementById('retakeBtn');
    var usePhotoBtn = document.getElementById('usePhotoBtn');

    if (captureBtn) captureBtn.addEventListener('click', function() { cameraManager.capturePhoto(); });
    if (retakeBtn) retakeBtn.addEventListener('click', function() { cameraManager.retakePhoto(); });
    if (usePhotoBtn) usePhotoBtn.addEventListener('click', function() { cameraManager.usePhoto(); });

    var galleryInput = document.getElementById('galleryInput');
    if (galleryInput) {
        galleryInput.addEventListener('change', function(e) {
            var file = e.target.files[0];
            if (file) {
                closeCamera();
                processImageFile(file, 'gallery');
                e.target.value = '';
            }
        });
    }
});

var cameraManager = new CameraManager();

window.openCamera = openCamera;
window.closeCamera = closeCamera;
window.openGallery = openGallery;
window.processImageFile = processImageFile;