// auth.js — Skipley

var EYE_OPEN = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
var EYE_OFF = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>';

function login() {
    var email = document.getElementById('emailLogin').value;
    var password = document.getElementById('passwordLogin').value;

    if (!email || !password) {
        showMessage(window.i18n('fillAllFields'), 'error');
        return;
    }

    fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, password: password })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.status === 'success') {
            showMessage(window.i18n('loginSuccess'), 'success');
            resetLoginForm();
            setTimeout(function() { window.location.href = '/'; }, 1000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(function(err) { showMessage(window.i18n('errorOccurred').replace('{{message}}', err.message), 'error'); });
}

function register() {
    var email = document.getElementById('emailRegister').value;
    var password = document.getElementById('passwordRegister').value;

    if (!email || !password) {
        showMessage(window.i18n('fillAllFields'), 'error');
        return;
    }

    fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, password: password })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.status === 'success') {
            showMessage(window.i18n('registerSuccess'), 'success');
            resetRegisterForm();
            setTimeout(function() { window.location.href = '/login'; }, 2000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(function(err) { showMessage(window.i18n('errorOccurred').replace('{{message}}', err.message), 'error'); });
}

function logout() {
    fetch('/api/logout', { method: 'POST' })
        .then(function() {
            showMessage(window.i18n('logoutSuccess'), 'success');
            setTimeout(function() { window.location.reload(); }, 1000);
        })
        .catch(function(err) { showMessage(window.i18n('errorOccurred').replace('{{message}}', err.message), 'error'); });
}

function resetLoginForm() {
    var loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.reset();
        document.getElementById('emailLogin').value = '';
        document.getElementById('passwordLogin').value = '';
        var passwordInput = document.getElementById('passwordLogin');
        if (passwordInput) passwordInput.type = 'password';
        var icon = document.getElementById('toggleIconLogin');
        if (icon) icon.innerHTML = EYE_OPEN;
    }
}

function resetRegisterForm() {
    var registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.reset();
        document.getElementById('emailRegister').value = '';
        document.getElementById('passwordRegister').value = '';
        var passwordInput = document.getElementById('passwordRegister');
        if (passwordInput) passwordInput.type = 'password';
        var icon = document.getElementById('toggleIconRegister');
        if (icon) icon.innerHTML = EYE_OPEN;
    }
}

function togglePasswordVisibility(inputId) {
    var passwordInput = document.getElementById(inputId);
    var iconId = inputId === 'passwordLogin' ? 'toggleIconLogin' : 'toggleIconRegister';
    var icon = document.getElementById(iconId);

    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        if (icon) icon.innerHTML = EYE_OFF;
    } else {
        passwordInput.type = 'password';
        if (icon) icon.innerHTML = EYE_OPEN;
    }
}

function showMessage(message, type) {
    // Сповіщення вимкнено глобально через CSS
}

function preventAutofill(formId) {
    var form = document.getElementById(formId);
    if (form) {
        var inputs = form.querySelectorAll('input[type="email"], input[type="password"]');
        inputs.forEach(function(input) {
            input.setAttribute('autocomplete', 'new-password');
            input.setAttribute('autocorrect', 'off');
            input.setAttribute('autocapitalize', 'off');
            input.setAttribute('spellcheck', 'false');
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Auth.js завантажено - поточна сторінка:', window.location.pathname);

    var loginForm = document.getElementById('loginForm');
    if (loginForm) {
        preventAutofill('loginForm');
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            login();
        });
        setTimeout(function() { resetLoginForm(); }, 100);
    }

    var registerForm = document.getElementById('registerForm');
    if (registerForm) {
        preventAutofill('registerForm');
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            register();
        });
        setTimeout(function() { resetRegisterForm(); }, 100);
    }

    var logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            logout();
        });
    }
});