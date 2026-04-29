// text.js — модуль текстового ввода

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

    // Этапы: 5%, 33%, 66% от времени (~5 сек)
    var stages = [
        { at: 5,  msgs: STAGE_PHRASES[window.getCurrentLang() || 'uk'].stage1 },
        { at: 33, msgs: STAGE_PHRASES[window.getCurrentLang() || 'uk'].stage2 },
        { at: 66, msgs: STAGE_PHRASES[window.getCurrentLang() || 'uk'].stage3 }
    ];

    try {
        startFakeProgress(5000, stages);
        closeTextInput();

        var response = await fetch('/api/analyze_text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: textValue, lang: window.getCurrentLang() })
        });

        if (!response.ok) throw new Error(window.i18n('serverError') + ': ' + response.status);

        var data = await response.json();
        if (data.status === 'success') {
            window.__lastTextResultData = data;
            openScanResult(data);
            resultDiv.innerHTML = '';
        } else {
            resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', data.message)}</div>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', error.message)}</div>`;
    } finally {
        completeProgress();
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

    // Этапы: 5%, 33%, 66% от времени (~8 сек)
    var stages = [
        { at: 5,  msgs: STAGE_PHRASES[window.getCurrentLang() || 'uk'].stage1 },
        { at: 33, msgs: STAGE_PHRASES[window.getCurrentLang() || 'uk'].stage2 },
        { at: 66, msgs: STAGE_PHRASES[window.getCurrentLang() || 'uk'].stage3 }
    ];

    try {
        startFakeProgress(8000, stages);
        closeTextInput();

        var formData = new FormData();
        formData.append('file', file);

        var response = await fetch('/api/upload_text_file', { method: 'POST', body: formData });
        if (!response.ok) throw new Error(window.i18n('serverError') + ': ' + response.status);

        var data = await response.json();
        if (data.status === 'success') {
            window.__lastTextResultData = data;
            openScanResult(data);
            resultDiv.innerHTML = '';
            fileInput.value = '';
        } else {
            resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', data.message)}</div>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<div class="error-msg">${window.i18n('errorOccurred').replace('{{message}}', error.message)}</div>`;
    } finally {
        completeProgress();
    }
}

window.processFileUpload = processFileUpload;
window.processManualText = processManualText;
window.triggerFileInput = triggerFileInput;
window.openTextInput = openTextInput;
window.closeTextInput = closeTextInput;