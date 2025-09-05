// Wire up buttons for navigation. In Flask, make sure /login and /register routes exist.
document.addEventListener('DOMContentLoaded', () => {
    const loginBtn = document.getElementById('btn-login');
    const registerBtn = document.getElementById('btn-register');

    if (loginBtn) {
        loginBtn.addEventListener('click', () => {
            // Replace with your Flask endpoint paths as needed
            window.location.href = '/login';
        });
    }
    if (registerBtn) {
        registerBtn.addEventListener('click', () => {
            window.location.href = '/register';
        });
    }
});

// Optional: index page buttons (only if you kept them as <button> elements on landing)
document.addEventListener('DOMContentLoaded', () => {
    const toLogin = document.getElementById('btn-login');
    const toRegister = document.getElementById('btn-register');
    if (toLogin) toLogin.addEventListener('click', () => { window.location.href = '/login'; });
    if (toRegister) toRegister.addEventListener('click', () => { window.location.href = '/register'; });
});
