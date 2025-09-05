document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('register-form');
    const account = document.getElementById('account');
    const nameInput = document.getElementById('name');
    const pwd = document.getElementById('password');
    const confirm = document.getElementById('confirm');

    const errAccount = document.getElementById('account-error');
    const errName = document.getElementById('name-error');
    const errPwd = document.getElementById('password-error');
    const errConfirm = document.getElementById('confirm-error');

    const isDigits = (s) => /^\d+$/.test(s);
    const within = (n, min, max) => n >= min && n <= max;

    function validateAccount() {
        const v = account.value.trim();
        if (!v) { errAccount.textContent = '請輸入學號 / 帳號。'; return false; }
        if (!isDigits(v)) { errAccount.textContent = '帳號僅能包含數字。'; return false; }
        if (v.length != 9) { errAccount.textContent = '長度需為9位。'; return false; }
        errAccount.textContent = '';
        return true;
    }

    function validateName() {
        const v = nameInput.value.trim();
        if (!v) { errName.textContent = '請輸入姓名。'; return false; }
        if (v.length < 2) { errName.textContent = '姓名至少需 2 個字。'; return false; }
        if (v.length > 64) { errName.textContent = '姓名至多 64 個字。'; return false; }
        errName.textContent = '';
        return true;
    }

    function validatePassword() {
        const v = pwd.value;
        if (!v) { errPwd.textContent = '請輸入密碼。'; return false; }
        if (!isDigits(v)) { errAccount.textContent = '帳號僅能包含數字、英文字母、 \'-\' 和 \'_\' 。'; return false; }
        if (v.length != 9) { errAccount.textContent = '長度需為9位。'; return false; }
        errPwd.textContent = '';
        return true;
    }

    function validateConfirm() {
        if (!confirm.value) { errConfirm.textContent = '請再次輸入密碼。'; return false; }
        if (confirm.value !== pwd.value) { errConfirm.textContent = '兩次輸入的密碼不一致。'; return false; }
        errConfirm.textContent = '';
        return true;
    }

    account.addEventListener('input', validateAccount);
    nameInput.addEventListener('input', validateName);
    pwd.addEventListener('input', () => { validatePassword(); validateConfirm(); });
    confirm.addEventListener('input', validateConfirm);

    form.addEventListener('submit', (e) => {
        const ok = Boolean(
            validateAccount() & validateName() & validatePassword() & validateConfirm()
        );
        if (!ok) {
            e.preventDefault();
            if (errAccount.textContent) account.focus();
            else if (errName.textContent) nameInput.focus();
            else if (errPwd.textContent) pwd.focus();
            else if (errConfirm.textContent) confirm.focus();
        }
    });
});
