// auth.js

// Функция для входа
function login() {
    const email = document.getElementById('emailLogin').value;
    const password = document.getElementById('passwordLogin').value;
    
    if (!email || !password) {
        showMessage('Будь ласка, заповніть всі поля', 'error');
        return;
    }
    
    fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showMessage('Вхід виконано успішно!', 'success');
            // Сбрасываем форму
            resetLoginForm();
            // Перенаправляем на главную страницу после успешного входа
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(err => showMessage('Помилка: ' + err.message, 'error'));
}

// Функция для регистрации
function register() {
    const email = document.getElementById('emailRegister').value;
    const password = document.getElementById('passwordRegister').value;
    
    if (!email || !password) {
        showMessage('Будь ласка, заповніть всі поля', 'error');
        return;
    }
    
    fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showMessage('Реєстрація успішна! Тепер ви можете увійти.', 'success');
            // Сбрасываем форму
            resetRegisterForm();
            // Перенаправляем на страницу входа после успешной регистрации
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(err => showMessage('Помилка: ' + err.message, 'error'));
}

// Функция для выхода
function logout() {
    fetch('/api/logout', { method: 'POST' })
        .then(() => {
            showMessage('Ви вийшли з системи!', 'success');
            // Обновляем страницу после выхода
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        })
        .catch(err => showMessage('Помилка: ' + err.message, 'error'));
}

// Функция для сброса формы входа
function resetLoginForm() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.reset();
        // Явно очищаем значения полей
        document.getElementById('emailLogin').value = '';
        document.getElementById('passwordLogin').value = '';
        
        // Сбрасываем состояние кнопки показа пароля
        const toggleButton = document.querySelector('#loginForm .password-toggle');
        if (toggleButton) {
            toggleButton.textContent = '👁️';
            toggleButton.title = 'Показати пароль';
        }
        const passwordInput = document.getElementById('passwordLogin');
        if (passwordInput) {
            passwordInput.type = 'password';
        }
    }
}

// Функция для сброса формы регистрации
function resetRegisterForm() {
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.reset();
        // Явно очищаем значения полей
        document.getElementById('emailRegister').value = '';
        document.getElementById('passwordRegister').value = '';
        
        // Сбрасываем состояние кнопки показа пароля
        const toggleButton = document.querySelector('#registerForm .password-toggle');
        if (toggleButton) {
            toggleButton.textContent = '👁️';
            toggleButton.title = 'Показати пароль';
        }
        const passwordInput = document.getElementById('passwordRegister');
        if (passwordInput) {
            passwordInput.type = 'password';
        }
    }
}

// Функция для показа/скрытия пароля
function togglePasswordVisibility(inputId) {
    const passwordInput = document.getElementById(inputId);
    const toggleButton = passwordInput.parentElement.querySelector('.password-toggle');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleButton.textContent = '🙈';
        toggleButton.title = 'Приховати пароль';
    } else {
        passwordInput.type = 'password';
        toggleButton.textContent = '👁️';
        toggleButton.title = 'Показати пароль';
    }
}

// Функция для показа сообщений
function showMessage(message, type) {
    // Создаем элемент сообщения
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    // Удаляем сообщение через 5 секунд
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    }, 5000);
}

// Функция для предотвращения автозаполнения
function preventAutofill(formId) {
    const form = document.getElementById(formId);
    if (form) {
        // Добавляем скрытые поля для обмана браузера
        const fakeFields = document.createElement('div');
        fakeFields.style.display = 'none';
        fakeFields.innerHTML = `
            <input type="text" name="fakeusername">
            <input type="password" name="fakepassword">
        `;
        form.appendChild(fakeFields);
        
        // Отключаем автозаполнение для реальных полей
        const inputs = form.querySelectorAll('input[type="email"], input[type="password"]');
        inputs.forEach(input => {
            input.setAttribute('autocomplete', 'new-password');
            input.setAttribute('autocorrect', 'off');
            input.setAttribute('autocapitalize', 'off');
            input.setAttribute('spellcheck', 'false');
        });
    }
}

// Обработчики форм
document.addEventListener('DOMContentLoaded', function() {
    console.log('Auth.js loaded - current page:', window.location.pathname);
    
    // Обработчик формы входа
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        console.log('Login form found, resetting...');
        
        // Предотвращаем автозаполнение
        preventAutofill('loginForm');
        
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            login();
        });
        
        // Сбрасываем форму входа при загрузке с задержкой
        setTimeout(() => {
            resetLoginForm();
        }, 100);
    }
    
    // Обработчик формы регистрации
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        console.log('Register form found, resetting...');
        
        // Предотвращаем автозаполнение
        preventAutofill('registerForm');
        
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            register();
        });
        
        // Сбрасываем форму регистрации при загрузке с задержкой
        setTimeout(() => {
            resetRegisterForm();
        }, 100);
    }
    
    // Добавляем кнопку "Назад" на страницы аутентификации
    if (window.location.pathname === '/login' || window.location.pathname === '/register') {
        const backButton = document.createElement('button');
        backButton.textContent = '← Назад';
        backButton.className = 'back-button';
        backButton.onclick = function() {
            window.location.href = '/';
        };
        document.body.appendChild(backButton);
    }
});