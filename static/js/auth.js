// auth.js

// Функция для входа
function login() {
    const email = document.getElementById('emailLogin').value;
    const password = document.getElementById('passwordLogin').value;
    
    fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            app.showMessage('Вход выполнен успешно!', 'success');
            app.checkAuthStatus();
        } else {
            app.showMessage(data.message, 'error');
        }
    })
    .catch(err => app.showMessage('Ошибка: ' + err.message, 'error'));
}

// Функция для регистрации
function register() {
    const email = document.getElementById('emailRegister').value;
    const password = document.getElementById('passwordRegister').value;
    
    fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            app.showMessage('Регистрация успешна!', 'success');
        } else {
            app.showMessage(data.message, 'error');
        }
    })
    .catch(err => app.showMessage('Ошибка: ' + err.message, 'error'));
}

// Функция для выхода
function logout() {
    fetch('/api/logout', { method: 'POST' })
        .then(() => {
            app.showMessage('Вы вышли из системы!', 'success');
            app.checkAuthStatus();
        })
        .catch(err => app.showMessage('Ошибка: ' + err.message, 'error'));
}
