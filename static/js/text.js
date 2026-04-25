// text.js — Skipley Text Input Module

function openTextInput() {
    var modal = document.getElementById('textInputModal');
    if (modal) modal.classList.remove('hidden');
}

function closeTextInput() {
    var modal = document.getElementById('textInputModal');
    var textInput = document.getElementById('manualTextInput');
    if (modal) modal.classList.add('hidden');
    if (textInput) textInput.value = '';
}

function triggerFileInput() {
    var fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.click();
}

async function processManualText() {
    var textInput = document.getElementById('manualTextInput');
    var resultDiv = document.getElementById('result');

    if (!textInput || !resultDiv) {
        alert('Помилка: необхідні елементи не знайдено');
        return;
    }

    var textValue = textInput.value.trim();
    if (!textValue) {
        alert('Будь ласка, введіть текст для аналізу');
        textInput.focus();
        return;
    }

    try {
        resultDiv.innerHTML = '<div class="loading"><p>Аналізується...</p></div>';
        closeTextInput();

        var response = await fetch('/api/analyze_text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: textValue })
        });

        if (!response.ok) throw new Error('Помилка сервера: ' + response.status);

        var data = await response.json();
        if (data.status === 'success') {
            displayResults(data);
        } else {
            resultDiv.innerHTML = '<div class="error-msg">Помилка: ' + data.message + '</div>';
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = '<div class="error-msg">Помилка при аналізі: ' + error.message + '</div>';
    }
}

async function processFileUpload() {
    var fileInput = document.getElementById('fileInput');
    var resultDiv = document.getElementById('result');

    if (!fileInput || !resultDiv) { alert('Помилка: елементи не знайдено'); return; }
    if (!fileInput.files || !fileInput.files[0]) { alert('Будь ласка, виберіть файл'); return; }

    var file = fileInput.files[0];

    try {
        resultDiv.innerHTML = '<div class="loading"><p>Обробляється файл...</p></div>';
        closeTextInput();

        var formData = new FormData();
        formData.append('file', file);

        var response = await fetch('/api/upload_text_file', { method: 'POST', body: formData });
        if (!response.ok) throw new Error('Помилка сервера: ' + response.status);

        var data = await response.json();
        if (data.status === 'success') {
            displayResults(data);
            fileInput.value = '';
        } else {
            resultDiv.innerHTML = '<div class="error-msg">Помилка: ' + data.message + '</div>';
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = '<div class="error-msg">Помилка при обробці файлу: ' + error.message + '</div>';
    }
}

// Display results in new design
function displayResults(data) {
    var resultDiv = document.getElementById('result');
    if (!resultDiv) return;

    var html = '';

    if (data.ingredients && data.ingredients.length > 0) {
        // Summary
        var counts = {};
        data.ingredients.forEach(function(ing) {
            var lvl = ing.risk_level || 'safe';
            counts[lvl] = (counts[lvl] || 0) + 1;
        });

        html += '<div class="results-summary"><div class="results-summary-header">';
        html += '<h2>Аналіз завершено</h2>';
        html += '<span class="results-count">' + data.ingredients.length + ' інгредієнтів</span>';
        html += '</div><div class="risk-counts">';
        for (var lvl in counts) {
            html += '<span class="risk-badge risk-' + lvl + '"><span class="dot"></span>' + counts[lvl] + ' ' + lvl + '</span>';
        }
        html += '</div></div>';

        // Ingredients list
        html += '<div class="ingredients-list">';
        data.ingredients.forEach(function(ingredient) {
            var riskClass = 'risk-' + (ingredient.risk_level || 'safe');
            html += '<div class="ingredient-item">';
            html += '<div class="ingredient-info">';
            html += '<div class="ingredient-name">' + ingredient.name + '</div>';
            html += '<div class="ingredient-desc">' + (ingredient.description || ingredient.category || '') + '</div>';
            html += '</div>';
            html += '<span class="risk-badge risk-sm ' + riskClass + '"><span class="dot"></span>' + (ingredient.risk_level || 'safe') + '</span>';
            html += '</div>';
        });
        html += '</div>';
    }

    if (data.text) {
        html += '<div style="margin-top:16px"><p class="detail-section-label">Проаналізований текст</p>';
        html += '<div class="original-text">' + data.text + '</div></div>';
    }

    if (!data.ingredients || data.ingredients.length === 0) {
        html += '<div class="success-msg">Не знайдено потенційно шкідливих інгредієнтів</div>';
    }

    resultDiv.innerHTML = html;
}

// Ініціалізація
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== TEXT.JS ЗАВАНТАЖЕНО ===');

    var fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files && e.target.files[0]) processFileUpload();
        });
    }
});

window.processFileUpload = processFileUpload;
window.processManualText = processManualText;
window.triggerFileInput = triggerFileInput;
window.openTextInput = openTextInput;
window.closeTextInput = closeTextInput;
