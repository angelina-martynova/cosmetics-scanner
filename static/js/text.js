// Открыть окно ввода текста
function openTextInput() {
    console.log('Opening text input modal...');
    const modal = document.getElementById('textInputModal');
    if (modal) {
        modal.classList.remove('hidden');
        console.log('Modal opened');
    } else {
        console.error('textInputModal not found');
    }
}

// Закрыть окно ввода текста
function closeTextInput() {
    const modal = document.getElementById('textInputModal');
    const textInput = document.getElementById('manualTextInput');
    if (modal) modal.classList.add('hidden');
    if (textInput) textInput.value = '';
}

// Функция для вызова файлового ввода
function triggerFileInput() {
    console.log('Triggering file input...');
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.click();
    } else {
        console.error('fileInput not found');
    }
}

// Функция для обработки ручного ввода текста
async function processManualText() {
    console.log('processManualText called');
    
    const textInput = document.getElementById('manualTextInput');
    const resultDiv = document.getElementById('result');
    
    console.log('Elements found:', {
        textInput: textInput,
        resultDiv: resultDiv,
        textInputValue: textInput ? textInput.value : 'null'
    });
    
    if (!textInput) {
        console.error('Элемент manualTextInput не найден');
        alert('Помилка: текстове поле не знайдено');
        return;
    }
    
    if (!resultDiv) {
        console.error('Элемент result не найден');
        alert('Помилка: елемент для результатів не знайдено');
        return;
    }
    
    const textValue = textInput.value.trim();
    console.log('Text value:', textValue);
    
    if (!textValue) {
        alert('Будь ласка, введіть текст для аналізу');
        textInput.focus();
        return;
    }

    try {
        console.log('Starting analysis...');
        resultDiv.innerHTML = '<p>Аналізується...</p>';
        closeTextInput();
        
        const response = await fetch('/api/analyze_text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: textValue })
        });

        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`Помилка сервера: ${response.status}`);
        }

        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.status === 'success') {
            displayResults(data);
        } else {
            resultDiv.innerHTML = `<p class="error">Помилка: ${data.message}</p>`;
        }
        
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<p class="error">Помилка при аналізі: ${error.message}</p>`;
    }
}

// Функция для обработки загрузки текстового файла
async function processFileUpload() {
    console.log('processFileUpload called');
    
    const fileInput = document.getElementById('fileInput');
    const resultDiv = document.getElementById('result');
    
    console.log('File input:', fileInput);
    console.log('File input files:', fileInput ? fileInput.files : 'null');
    
    if (!fileInput) {
        console.error('Элемент fileInput не найден');
        alert('Помилка: елемент вибору файлу не знайдено');
        return;
    }
    
    if (!resultDiv) {
        console.error('Элемент result не найден');
        alert('Помилка: елемент для результатів не знайдено');
        return;
    }
    
    if (!fileInput.files || !fileInput.files[0]) {
        alert('Будь ласка, виберіть файл');
        return;
    }

    const file = fileInput.files[0];
    console.log('Selected file:', file.name, file.type, file.size);

    try {
        resultDiv.innerHTML = '<p>Обробляється файл...</p>';
        closeTextInput();
        
        const formData = new FormData();
        formData.append('file', file);

        console.log('Sending file to server...');
        const response = await fetch('/api/upload_text_file', {
            method: 'POST',
            body: formData
        });

        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Server error response:', errorText);
            throw new Error(`Помилка сервера: ${response.status}`);
        }

        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.status === 'success') {
            displayResults(data);
            // Очищаем input после успешной загрузки
            fileInput.value = '';
        } else {
            resultDiv.innerHTML = `<p class="error">Помилка: ${data.message}</p>`;
        }
        
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<p class="error">Помилка при обробці файлу: ${error.message}</p>`;
    }
}

// Функция для отображения результатов
function displayResults(data) {
    const resultDiv = document.getElementById('result');
    
    if (!resultDiv) {
        console.error('Элемент result не найден при отображении результатов');
        return;
    }
    
    let html = `
        <div class="result-section">
            <h3>Аналізований текст:</h3>
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
            const riskClass = `risk-${ingredient.risk_level || 'unknown'}`;
            html += `
                <div class="ingredient-item ${riskClass}">
                    <div class="ingredient-name">${ingredient.name}</div>
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
                <p>Не знайдено потенційно шкідливих інгредієнтів</p>
            </div>
        `;
    }

    resultDiv.innerHTML = html;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== TEXT.JS LOADED ===');
    console.log('Checking elements:');
    console.log('manualTextInput:', document.getElementById('manualTextInput'));
    console.log('textInputModal:', document.getElementById('textInputModal'));
    console.log('fileInput:', document.getElementById('fileInput'));
    console.log('result:', document.getElementById('result'));
    
    // Обработчик для файлового input - ВАЖНО!
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            console.log('File input changed, files:', e.target.files);
            if (e.target.files && e.target.files[0]) {
                console.log('Calling processFileUpload...');
                processFileUpload();
            }
        });
    } else {
        console.error('fileInput element not found!');
    }
    
    // Проверяем все кнопки в модальном окне
    const modal = document.getElementById('textInputModal');
    if (modal) {
        const buttons = modal.querySelectorAll('button');
        console.log('Buttons in modal:', buttons.length);
        buttons.forEach((btn, index) => {
            console.log(`Button ${index}:`, btn.textContent, btn.onclick);
        });
    }
});

// Глобальная функция для вызова из HTML
window.processFileUpload = processFileUpload;
window.processManualText = processManualText;
window.triggerFileInput = triggerFileInput;
window.openTextInput = openTextInput;
window.closeTextInput = closeTextInput;