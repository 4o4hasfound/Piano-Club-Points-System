// Debounce helper
function debounce(fn, ms = 200) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), ms);
    };
}

document.addEventListener('DOMContentLoaded', () => {
    // ===== Records table: filter/sort + edit mode =====
    const recTable = document.getElementById('admin-records-table');
    if (recTable) {
        const tbody = recTable.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));

        const filterType = document.getElementById('filter-type');
        const filterText = document.getElementById('filter-text');
        const sortKey = document.getElementById('sort-key');

        function applyFilterAndSort() {
            const typeVal = (filterType?.value || '').trim();
            const textVal = (filterText?.value || '').trim().toLowerCase();
            const sortVal = (sortKey?.value || 'time_desc');

            // Filter
            rows.forEach(row => {
                const rType = row.dataset.type || '';
                const rTime = row.dataset.time || '';
                const rReason = row.dataset.reason || '';
                const matchesType = !typeVal || rType === typeVal;
                const hay = (rTime + ' ' + rReason).toLowerCase();
                const matchesText = !textVal || hay.includes(textVal);
                row.style.display = (matchesType && matchesText) ? '' : 'none';
            });

            // Sort visible
            const visible = rows.filter(r => r.style.display !== 'none');
            visible.sort((a, b) => {
                const at = a.dataset.time, bt = b.dataset.time;
                const aa = parseInt(a.dataset.amount, 10), ba = parseInt(b.dataset.amount, 10);
                const ta = a.dataset.type, tb = b.dataset.type;
                switch (sortVal) {
                    case 'time_asc': return at.localeCompare(bt);
                    case 'time_desc': return bt.localeCompare(at);
                    case 'amount_asc': return aa - ba;
                    case 'amount_desc': return ba - aa;
                    case 'type_add_first': return (tb === 'add') - (ta === 'add');
                    case 'type_remove_first': return (ta === 'add') - (tb === 'add');
                    default: return 0;
                }
            });
            visible.forEach(r => tbody.appendChild(r));
        }

        // Live update on typing & sort changes
        filterType?.addEventListener('change', applyFilterAndSort);
        sortKey?.addEventListener('change', applyFilterAndSort);
        filterText?.addEventListener('input', debounce(applyFilterAndSort, 120));
        applyFilterAndSort();

        // ---- Edit mode: click "編輯" to toggle inputs ----
        tbody.addEventListener('click', (e) => {
            const editBtn = e.target.closest('.btn-edit');
            const cancelBtn = e.target.closest('.btn-cancel');
            const saveFormBtn = e.target.closest('.form-save button[type="submit"]');

            // Enter edit mode
            if (editBtn) {
                const row = editBtn.closest('tr');
                row.classList.add('editing');

                // toggle controls
                editBtn.classList.add('hidden');
                row.querySelector('.form-save')?.classList.remove('hidden');
                row.querySelector('.btn-cancel')?.classList.remove('hidden');

                // show editors, hide read-only spans
                row.querySelectorAll('.edit').forEach(el => el.classList.remove('hidden'));
                row.querySelectorAll('.ro').forEach(el => el.classList.add('hidden'));
                return;
            }

            // Cancel edit - revert UI only
            if (cancelBtn) {
                const row = cancelBtn.closest('tr');
                row.classList.remove('editing');

                row.querySelector('.btn-edit')?.classList.remove('hidden');
                row.querySelector('.form-save')?.classList.add('hidden');
                row.querySelector('.btn-cancel')?.classList.add('hidden');

                row.querySelectorAll('.edit').forEach(el => el.classList.add('hidden'));
                row.querySelectorAll('.ro').forEach(el => el.classList.remove('hidden'));

                // also reset editor values to current dataset/ro text
                const currentType = row.dataset.type || 'add';
                const currentAmt = row.dataset.amount || '0';
                const currentReason = row.dataset.reason || '';

                const typeEl = row.querySelector('.edit-type');
                const amtEl = row.querySelector('.edit-amount');
                const reasonEl = row.querySelector('.edit-reason');
                if (typeEl) typeEl.value = currentType;
                if (amtEl) amtEl.value = currentAmt;
                if (reasonEl) reasonEl.value = currentReason;
                return;
            }

            // Before SAVE submit: push editor values into hidden inputs
            if (saveFormBtn) {
                const row = saveFormBtn.closest('tr');
                const form = saveFormBtn.closest('form');

                const typeEl = row.querySelector('.edit-type');
                const amtEl = row.querySelector('.edit-amount');
                const reasonEl = row.querySelector('.edit-reason');

                const postType = form.querySelector('.post-type');
                const postAmount = form.querySelector('.post-amount');
                const postReason = form.querySelector('.post-reason');

                if (typeEl && amtEl && reasonEl && postType && postAmount && postReason) {
                    postType.value = typeEl.value === 'remove' ? 'remove' : 'add';
                    postAmount.value = amtEl.value;
                    postReason.value = reasonEl.value;
                }
                // Let the form submit normally
            }
        });
    }

    // ===== All users table: live filter + sort =====
    const usersTable = document.getElementById('admin-users-table');
    if (usersTable) {
        const tbody = usersTable.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const filterText = document.getElementById('users-filter-text');
        const sortKey = document.getElementById('users-sort-key');

        function applyUsers() {
            const q = (filterText?.value || '').toLowerCase();
            const key = (sortKey?.value || 'account_asc');

            // Filter by account or name
            rows.forEach(r => {
                const acc = (r.dataset.account || '').toLowerCase();
                const name = (r.dataset.name || '').toLowerCase();
                const ok = !q || acc.includes(q) || name.includes(q);
                r.style.display = ok ? '' : 'none';
            });

            const visible = rows.filter(r => r.style.display !== 'none');
            visible.sort((a, b) => {
                const aacc = a.dataset.account, bacc = b.dataset.account;
                const an = (a.dataset.name || '').toLowerCase();
                const bn = (b.dataset.name || '').toLowerCase();
                const ap = parseInt(a.dataset.points, 10), bp = parseInt(b.dataset.points, 10);
                switch (key) {
                    case 'account_asc': return aacc.localeCompare(bacc);
                    case 'account_desc': return bacc.localeCompare(aacc);
                    case 'name_asc': return an.localeCompare(bn);
                    case 'name_desc': return bn.localeCompare(an);
                    case 'points_asc': return ap - bp;
                    case 'points_desc': return bp - ap;
                    default: return 0;
                }
            });
            visible.forEach(r => tbody.appendChild(r));
        }

        // Live updates
        filterText?.addEventListener('input', debounce(applyUsers, 120));
        sortKey?.addEventListener('change', applyUsers);
        applyUsers();
    }
});

document.querySelectorAll('.utc-time').forEach(td => {
    const dt = new Date(td.dataset.utc);
    td.textContent = dt.toLocaleString("sv-SE", {
        timeZone: "Asia/Taipei",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });
});