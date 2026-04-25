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
        alert(window.i18n('fillAllFields'));
        textInput.focus();
        return;
    }

    try {
        resultDiv.innerHTML = `<div class="loading"><p>${window.i18n('analyzing')}</p></div>`;
        closeTextInput();

        var response = await fetch('/api/analyze_text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: textValue })
        });

        if (!response.ok) throw new Error(window.i18n('serverError') + ': ' + response.status);

        var data = await response.json();
        if (data.status === 'success') {
            window.__lastTextResultData = data;
            displayResults(data);
        } else {
            resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', data.message)}</div>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', error.message)}</div>`;
    }
}

async function processFileUpload() {
    var fileInput = document.getElementById('fileInput');
    var resultDiv = document.getElementById('result');

    if (!fileInput || !resultDiv) { alert('Помилка: елементи не знайдено'); return; }
    if (!fileInput.files || !fileInput.files[0]) {
        alert(window.i18n('selectFile'));
        return;
    }

    var file = fileInput.files[0];

    try {
        resultDiv.innerHTML = `<div class="loading"><p>${window.i18n('processingFile')}</p></div>`;
        closeTextInput();

        var formData = new FormData();
        formData.append('file', file);

        var response = await fetch('/api/upload_text_file', { method: 'POST', body: formData });
        if (!response.ok) throw new Error(window.i18n('serverError') + ': ' + response.status);

        var data = await response.json();
        if (data.status === 'success') {
            window.__lastTextResultData = data;
            displayResults(data);
            fileInput.value = '';
        } else {
            resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', data.message)}</div>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', error.message)}</div>`;
    }
}

// Display results
function displayResults(data) {
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
        html += '<div style="margin-top:16px"><p class="detail-section-label">' + window.i18n('analyzedText') + '</p>';
        html += '<div class="original-text">' + data.text + '</div></div>';
    }

    if (!data.ingredients || data.ingredients.length === 0) {
        html += '<div class="success-msg">' + window.i18n('noHarmfulIngredients') + '</div>';
    }

    resultDiv.innerHTML = html;
}

window.addEventListener('languageChanged', function() {
    if (window.__lastTextResultData) {
        displayResults(window.__lastTextResultData);
    }
});

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