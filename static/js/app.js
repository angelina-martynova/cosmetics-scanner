// app.js — Skipley (adaptive progress bar with random stage messages)

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
   Пулы случайных фраз для этапов (украинский и английский)
   ================================================================ */
const STAGE_PHRASES = {
    uk: {
        stage1: [
            "Ану, подивимось, що там написали…",
            "Дрібний шрифт — але ми розгледіли",
            "Ану, що виробники там написали?",
            "Дивимось, що там за букви…",
            "Придивляємось, чи це крем для обличчя, або рецепт борщу",
            "Читаємо склад, ніби це секретне послання",
            "Шукаємо знайомі назви",
            "Очі напружуємо, але все вичитуємо",
            "Дивимось, де там підвох…",
            "Розбираємо цю \"абетку\" інгредієнтів"
        ],
        stage2: [
            "Дивлюсь, чи не потрапляв цей інгредієнт у чорний список",
            "Перевіряємо по нашій базі…",
            "Зараз скажемо, чи варто хвилюватись",
            "Шукаємо ці компоненти серед 20 000 інших",
            "Спілкуємось із внутрішнім косметологом",
            "Піднімаємо нашу базу знань",
            "Зараз подивимось, що там про це думають науковці",
            "Звіряємо з безпечними списками",
            "Дивимось, чи це \"ок\", чи \"краще не треба\"",
            "Шукаємо збіги з тим, що вже знаємо"
        ],
        stage3: [
            "Готово. Дивись, що маємо",
            "Ось що вийшло…",
            "Перевіряємо, чи нічого не пропустили",
            "Перекладаємо хімічну формулу людською мовою",
            "Ось короткий висновок",
            "Переконуємось, що ніде не закралась помилка",
            "Зараз покажемо результат",
            "Тримай, що з цього всього вийшло",
            "Ну ось, прийшов результат",
            "Тримай готовий звіт"
        ]
    },
    en: {
        stage1: [
            "Let's see what they wrote on it…",
            "Small print — but we made it out",
            "Hmm, what did the manufacturers say?",
            "Let's check those letters…",
            "Making sure it's face cream, not borscht recipe",
            "Reading ingredients like a secret code",
            "Looking for familiar names",
            "Straining our eyes, but we read everything",
            "Watching out for the trick…",
            "Decoding this ingredient alphabet"
        ],
        stage2: [
            "Checking if this ingredient is blacklisted",
            "Looking it up in our database…",
            "About to tell you whether to worry",
            "Searching among 20,000 others",
            "Consulting our inner cosmetologist",
            "Firing up our knowledge base",
            "Let's see what scientists think about it",
            "Verifying against safe lists",
            "Deciding: 'ok' or 'better not'",
            "Matching with what we already know"
        ],
        stage3: [
            "Done. Here's what we've got",
            "And the result is…",
            "Making sure we didn't miss anything",
            "Translating chemistry into human language",
            "Here's the short verdict",
            "Double-checking for any slip‑ups",
            "About to show you the result",
            "Here's what came out of it",
            "Alright, result is in",
            "Your ready‑to‑go report"
        ]
    }
};

/**
 * Возвращает случайную фразу для указанного этапа на текущем языке.
 */
function getRandomStageMessage(stage) {
    const lang = window.getCurrentLang ? window.getCurrentLang() : 'uk';
    const pool = STAGE_PHRASES[lang]?.[stage] || STAGE_PHRASES['uk'][stage];
    if (!pool || pool.length === 0) return '';
    return pool[Math.floor(Math.random() * pool.length)];
}

/* ================================================================
   Глобальные функции управления прогресс-баром + этапы
   ================================================================ */

let progressTimer = null;

/**
 * Запускает плавное заполнение прогресс-бара и показывает этапы.
 * @param {number} duration — ожидаемая длительность операции (мс)
 * @param {Array} stages — [{at: %, msgs: array}, ...] (три этапа)
 */
window.startFakeProgress = function(duration, stages) {
    const fill = document.querySelector('.progress-fill');
    const container = document.getElementById('processingStatus');
    const msgEl = document.getElementById('processingMessage');
    if (!fill) return;

    clearInterval(progressTimer);
    fill.style.transition = 'none';
    fill.style.width = '0%';

    if (container) container.style.display = 'block';

    // Выбираем по одной случайной фразе для каждого этапа
    const chosenMsgs = {};
    if (stages) {
        stages.forEach(s => {
            if (s.msgs && s.msgs.length) {
                chosenMsgs[s.at] = s.msgs[Math.floor(Math.random() * s.msgs.length)];
            }
        });
    }

    // Первое сообщение (первый этап)
    if (stages && stages.length > 0 && msgEl) {
        msgEl.textContent = chosenMsgs[stages[0].at] || '';
    }

    const TARGET = 90;
    const intervalTime = 100;
    const steps = duration / intervalTime;
    const stepPercent = TARGET / steps;

    let current = 0;
    progressTimer = setInterval(() => {
        current += stepPercent;
        if (current >= TARGET) {
            current = TARGET;
            clearInterval(progressTimer);
            progressTimer = null;
        }
        fill.style.width = current + '%';

        // Смена этапа
        if (stages && stages.length > 0 && msgEl) {
            for (let i = stages.length - 1; i >= 0; i--) {
                if (current >= stages[i].at) {
                    const msg = chosenMsgs[stages[i].at];
                    if (msg && msg !== msgEl.textContent) {
                        msgEl.textContent = msg;
                    }
                    break;
                }
            }
        }
    }, intervalTime);
};

/**
 * Завершает прогресс: доводит до 100%,
 * оставляет последнюю фразу на 2 секунды,
 * затем показывает финальное сообщение и скрывает.
 */
window.completeProgress = function() {
    clearInterval(progressTimer);
    progressTimer = null;

    const fill = document.querySelector('.progress-fill');
    const container = document.getElementById('processingStatus');
    const msgEl = document.getElementById('processingMessage');
    if (!fill) return;

    fill.style.transition = 'width 0.3s ease';
    fill.style.width = '100%';

    // Ждём 2 секунды с последней фразой этапа
    setTimeout(() => {
        if (msgEl) msgEl.textContent = window.i18n('analysisComplete');
        setTimeout(() => {
            if (container) container.style.display = 'none';
            fill.style.transition = 'none';
            fill.style.width = '0%';
            if (msgEl) msgEl.textContent = '';
        }, 1000);
    }, 2000);
};

// Инициализация приложения
document.addEventListener('DOMContentLoaded', function() {
    window.app = new CosmeticsScanner();
    window.app.init();
    console.log('CosmeticsScanner ініціалізовано');
});