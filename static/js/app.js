// app.js — Skipley (stable progress bar)

class CosmeticsScanner {
    constructor() {
        this.currentUser = null;
        this.currentScan = null;
    }

    init() {
        this.checkAuthStatus();
    }

    checkAuthStatus() {
        fetch('/api/status')
            .then(function(response) {
                if (!response.ok) throw new Error('Not authenticated');
                return response.json();
            })
            .then(function(data) {
                if (data.status === 'authenticated') {
                    this.currentUser = data.user;
                    var scansLink = document.getElementById('sidebarScansLink');
                    if (scansLink) scansLink.style.display = 'flex';
                    var loggedOut = document.getElementById('sidebarAuthLoggedOut');
                    var loggedIn = document.getElementById('sidebarAuthLoggedIn');
                    if (loggedOut) loggedOut.style.display = 'none';
                    if (loggedIn) loggedIn.style.display = 'block';
                }
            }.bind(this))
            .catch(function() {
                this.currentUser = null;
            }.bind(this));
    }

    showMessage(message, type) {
        if (typeof showMessage === 'function') {
            showMessage(message, type);
        }
    }
}

/* ================================================================
   Глобальные функции управления прогресс-баром
   ================================================================ */

let progressTimer = null;

/**
 * Запускает заполнение прогресс-бара (от 0% до 90%).
 * Вызывается другими модулями.
 */
window.startFakeProgress = function() {
    const fill = document.querySelector('.progress-fill');
    if (!fill) {
        console.warn('progress-fill не найден');
        return;
    }

    // Сбрасываем и делаем видимым
    clearInterval(progressTimer);
    fill.style.transition = 'none';
    fill.style.width = '0%';

    const DURATION = 8000;   // 8 секунд до 90%
    const TARGET = 90;
    const INTERVAL = 80;     // обновления каждые 80мс → 100 шагов
    const STEP = (TARGET * INTERVAL) / DURATION; // примерно 0.9% за шаг

    let current = 0;
    progressTimer = setInterval(() => {
        current += STEP;
        if (current >= TARGET) {
            current = TARGET;
            clearInterval(progressTimer);
            progressTimer = null;
        }
        fill.style.width = current + '%';
        console.log('Progress: ' + current.toFixed(1) + '%');
    }, INTERVAL);
};

/**
 * Завершает прогресс: доводит до 100% и скрывает.
 */
window.completeProgress = function() {
    clearInterval(progressTimer);
    progressTimer = null;

    const fill = document.querySelector('.progress-fill');
    const container = document.getElementById('processingStatus');
    if (!fill) return;

    fill.style.transition = 'width 0.25s ease';
    fill.style.width = '100%';

    setTimeout(() => {
        if (container) container.style.display = 'none';
        fill.style.transition = 'none';
        fill.style.width = '0%';
    }, 600);
};

/**
 * Показывает текстовое сообщение над прогресс-баром.
 */
window.showProcessingMessage = function(messageKey) {
    const container = document.getElementById('processingStatus');
    const msg = document.getElementById('processingMessage');
    if (container && msg) {
        msg.textContent = window.i18n(messageKey);
        container.style.display = 'block';
    }
};

// Инициализация приложения
document.addEventListener('DOMContentLoaded', function() {
    window.app = new CosmeticsScanner();
    window.app.init();
    console.log('CosmeticsScanner ініціалізовано');
});