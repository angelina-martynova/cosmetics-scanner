// Відкрити вікно введення тексту
function openTextInput() {
    console.log('Відкриття вікна введення тексту...');
    const modal = document.getElementById('textInputModal');
    if (modal) {
        modal.classList.remove('hidden');
        console.log('Модальне вікно відкрито');
    } else {
        console.error('textInputModal не знайдено');
    }
}

// Закрити вікно введення тексту
function closeTextInput() {
    const modal = document.getElementById('textInputModal');
    const textInput = document.getElementById('manualTextInput');
    if (modal) modal.classList.add('hidden');
    if (textInput) textInput.value = '';
}

// Функція для виклику файлового введення
function triggerFileInput() {
    console.log('Активація файлового введення...');
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.click();
    } else {
        console.error('fileInput не знайдено');
    }
}

// Функція для обробки ручного введення тексту
async function processManualText() {
    console.log('processManualText викликано');
    
    const textInput = document.getElementById('manualTextInput');
    const resultDiv = document.getElementById('result');
    
    console.log('Знайдені елементи:', {
        textInput: textInput,
        resultDiv: resultDiv,
        textInputValue: textInput ? textInput.value : 'null'
    });
    
    if (!textInput) {
        console.error('Елемент manualTextInput не знайдено');
        alert('Помилка: текстове поле не знайдено');
        return;
    }
    
    if (!resultDiv) {
        console.error('Елемент result не знайдено');
        alert('Помилка: елемент для результатів не знайдено');
        return;
    }
    
    const textValue = textInput.value.trim();
    console.log('Значення тексту:', textValue);
    
    if (!textValue) {
        alert('Будь ласка, введіть текст для аналізу');
        textInput.focus();
        return;
    }

    try {
        console.log('Початок аналізу...');
        resultDiv.innerHTML = '<p>Аналізується...</p>';
        closeTextInput();
        
        const response = await fetch('/api/analyze_text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: textValue })
        });

        console.log('Статус відповіді:', response.status);
        
        if (!response.ok) {
            throw new Error(`Помилка сервера: ${response.status}`);
        }

        const data = await response.json();
        console.log('Дані відповіді:', data);
        
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

// Функція для обробки завантаження текстового файлу
async function processFileUpload() {
    console.log('processFileUpload викликано');
    
    const fileInput = document.getElementById('fileInput');
    const resultDiv = document.getElementById('result');
    
    console.log('Файлове введення:', fileInput);
    console.log('Файли файлового введення:', fileInput ? fileInput.files : 'null');
    
    if (!fileInput) {
        console.error('Елемент fileInput не знайдено');
        alert('Помилка: елемент вибору файлу не знайдено');
        return;
    }
    
    if (!resultDiv) {
        console.error('Елемент result не знайдено');
        alert('Помилка: елемент для результатів не знайдено');
        return;
    }
    
    if (!fileInput.files || !fileInput.files[0]) {
        alert('Будь ласка, виберіть файл');
        return;
    }

    const file = fileInput.files[0];
    console.log('Обраний файл:', file.name, file.type, file.size);

    try {
        resultDiv.innerHTML = '<p>Обробляється файл...</p>';
        closeTextInput();
        
        const formData = new FormData();
        formData.append('file', file);

        console.log('Відправка файлу на сервер...');
        const response = await fetch('/api/upload_text_file', {
            method: 'POST',
            body: formData
        });

        console.log('Статус відповіді:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Відповідь сервера з помилкою:', errorText);
            throw new Error(`Помилка сервера: ${response.status}`);
        }

        const data = await response.json();
        console.log('Дані відповіді:', data);
        
        if (data.status === 'success') {
            displayResults(data);
            // Очищаємо input після успішного завантаження
            fileInput.value = '';
        } else {
            resultDiv.innerHTML = `<p class="error">Помилка: ${data.message}</p>`;
        }
        
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<p class="error">Помилка при обробці файлу: ${error.message}</p>`;
    }
}

// Функція для відображення результатів
function displayResults(data) {
    const resultDiv = document.getElementById('result');
    
    if (!resultDiv) {
        console.error('Елемент result не знайдено при відображенні результатів');
        return;
    }
    
    let html = `
        <div class="result-section">
            <h3>Проаналізований текст:</h3>
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

// Ініціалізація при завантаженні сторінки
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== TEXT.JS ЗАВАНТАЖЕНО ===');
    console.log('Перевірка елементів:');
    console.log('manualTextInput:', document.getElementById('manualTextInput'));
    console.log('textInputModal:', document.getElementById('textInputModal'));
    console.log('fileInput:', document.getElementById('fileInput'));
    console.log('result:', document.getElementById('result'));
    
    // Обробник для файлового input - ВАЖЛИВО!
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            console.log('Файлове введення змінено, файли:', e.target.files);
            if (e.target.files && e.target.files[0]) {
                console.log('Виклик processFileUpload...');
                processFileUpload();
            }
        });
    } else {
        console.error('fileInput елемент не знайдено!');
    }
    
    // Прив'язка кнопки "Скасувати" в модальному вікні
    const cancelButton = document.querySelector('#textInputModal .modal-actions button:last-child');
    if (cancelButton && cancelButton.textContent.includes('Скасувати')) {
        cancelButton.addEventListener('click', closeTextInput);
    }
});

// Глобальна функція для виклику з HTML
window.processFileUpload = processFileUpload;
window.processManualText = processManualText;
window.triggerFileInput = triggerFileInput;
window.openTextInput = openTextInput;
window.closeTextInput = closeTextInput;