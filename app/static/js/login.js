document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('login-form');
    const account = document.getElementById('account');
    const password = document.getElementById('password');

    const errAccount = document.getElementById('account-error');
    const errPassword = document.getElementById('password-error');

    const isDigits = (s) => /^\d+$/.test(s);

    function validateAccount() {
        const v = account.value.trim();
        if (!v) { errAccount.textContent = '請輸入帳號。'; return false; }
        if (!isDigits(v)) { errAccount.textContent = '帳號僅能包含數字、英文字母、 \'-\' 和 \'_\' 。'; return false; }
        if (v.length != 9) { errAccount.textContent = '長度需為9位。'; return false; }
        errAccount.textContent = '';
        return true;
    }

    function validatePassword() {
        const v = password.value;
        if (!v) { errPassword.textContent = '請輸入密碼。'; return false; }
        if (v.length < 4) { errPassword.textContent = '密碼至少需 4 碼。'; return false; }
        if (v.length > 20) { errPassword.textContent = '密碼至多 20 碼。'; return false; }
        errPassword.textContent = '';
        return true;
    }

    account.addEventListener('input', validateAccount);
    password.addEventListener('input', validatePassword);

    form.addEventListener('submit', (e) => {
        const ok = validateAccount() & validatePassword();
        if (!Boolean(ok)) {
            e.preventDefault();
            if (errAccount.textContent) account.focus();
            else if (errPassword.textContent) password.focus();
        }
    });
});
