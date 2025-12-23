// auth.js

// Функція для входу
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
            resetLoginForm();
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(err => showMessage('Помилка: ' + err.message, 'error'));
}

// Функція для реєстрації
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
            resetRegisterForm();
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(err => showMessage('Помилка: ' + err.message, 'error'));
}

// Функція для виходу
function logout() {
    fetch('/api/logout', { method: 'POST' })
        .then(() => {
            showMessage('Ви вийшли з системи!', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        })
        .catch(err => showMessage('Помилка: ' + err.message, 'error'));
}

// Функція для скидання форми входу
function resetLoginForm() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.reset();
        document.getElementById('emailLogin').value = '';
        document.getElementById('passwordLogin').value = '';
        
        const toggleButton = document.querySelector('#loginForm .password-toggle');
        if (toggleButton && toggleButton.querySelector('img')) {
            toggleButton.querySelector('img').src = '/static/images/visible.svg';
            toggleButton.title = 'Показати пароль';
        }
        const passwordInput = document.getElementById('passwordLogin');
        if (passwordInput) {
            passwordInput.type = 'password';
        }
    }
}

// Функція для скидання форми реєстрації
function resetRegisterForm() {
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.reset();
        document.getElementById('emailRegister').value = '';
        document.getElementById('passwordRegister').value = '';
        
        const toggleButton = document.querySelector('#registerForm .password-toggle');
        if (toggleButton && toggleButton.querySelector('img')) {
            toggleButton.querySelector('img').src = '/static/images/visible.svg';
            toggleButton.title = 'Показати пароль';
        }
        const passwordInput = document.getElementById('passwordRegister');
        if (passwordInput) {
            passwordInput.type = 'password';
        }
    }
}

// Функція для показу/приховування пароля
function togglePasswordVisibility(inputId) {
    const passwordInput = document.getElementById(inputId);
    const toggleButton = passwordInput.parentElement.querySelector('.password-toggle');
    const icon = toggleButton.querySelector('img');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.src = '/static/images/unvisible.svg';
        toggleButton.title = 'Приховати пароль';
    } else {
        passwordInput.type = 'password';
        icon.src = '/static/images/visible.svg';
        toggleButton.title = 'Показати пароль';
    }
}

// Функція для показу повідомлень
function showMessage(message, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    }, 5000);
}

// Функція для запобігання автозаповнення
function preventAutofill(formId) {
    const form = document.getElementById(formId);
    if (form) {
        const fakeFields = document.createElement('div');
        fakeFields.style.display = 'none';
        fakeFields.innerHTML = `
            <input type="text" name="fakeusername">
            <input type="password" name="fakepassword">
        `;
        form.appendChild(fakeFields);
        
        const inputs = form.querySelectorAll('input[type="email"], input[type="password"]');
        inputs.forEach(input => {
            input.setAttribute('autocomplete', 'new-password');
            input.setAttribute('autocorrect', 'off');
            input.setAttribute('autocapitalize', 'off');
            input.setAttribute('spellcheck', 'false');
        });
    }
}

// Обробники форм
document.addEventListener('DOMContentLoaded', function() {
    console.log('Auth.js завантажено - поточна сторінка:', window.location.pathname);
    
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        console.log('Форму входу знайдено, скидання...');
        
        preventAutofill('loginForm');
        
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            login();
        });
        
        const loginToggleButton = loginForm.querySelector('.password-toggle');
        if (loginToggleButton && !loginToggleButton.querySelector('img')) {
            loginToggleButton.innerHTML = '<img src="/static/images/visible.svg" alt="Показати пароль" width="24" height="24">';
            loginToggleButton.title = 'Показати пароль';
        }
        
        setTimeout(() => {
            resetLoginForm();
        }, 100);
    }
    
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        console.log('Форму реєстрації знайдено, скидання...');
        
        preventAutofill('registerForm');
        
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            register();
        });
        
        const registerToggleButton = registerForm.querySelector('.password-toggle');
        if (registerToggleButton && !registerToggleButton.querySelector('img')) {
            registerToggleButton.innerHTML = '<img src="/static/images/visible.svg" alt="Показати пароль" width="24" height="24">';
            registerToggleButton.title = 'Показати пароль';
        }
        
        setTimeout(() => {
            resetRegisterForm();
        }, 100);
    }
    
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