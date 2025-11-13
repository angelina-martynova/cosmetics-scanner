// Логика для регистрации пользователя
async function register() {
    const email = document.getElementById('emailRegister').value;
    const password = document.getElementById('passwordRegister').value;

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        if (data.status === 'success') {
            app.showMessage('Реєстрація успішна! Тепер увійдіть.', 'success');
            window.location.href = "/login";
        } else {
            app.showMessage(data.message, 'error');
        }
    } catch (error) {
        app.showMessage('Помилка з\'єднання', 'error');
    }
}

// Логика для входа пользователя
async function login() {
    const email = document.getElementById('emailLogin').value;
    const password = document.getElementById('passwordLogin').value;

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        if (data.status === 'success') {
            app.showMessage('Успішний вхід!', 'success');
            window.location.href = "/";
        } else {
            app.showMessage(data.message, 'error');
        }
    } catch (error) {
        app.showMessage('Помилка з\'єднання', 'error');
    }
}

// Логика для выхода пользователя
function logout() {
    fetch('/api/logout', { method: 'POST' })
        .then(() => {
            app.showMessage('Ви вийшли з системи', 'success');
            window.location.href = '/login';
        })
        .catch(() => {
            app.showMessage('Помилка при виході', 'error');
        });
}
