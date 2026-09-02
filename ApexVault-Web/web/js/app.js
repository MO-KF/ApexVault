let selectedVaultRow = null;

window.addEventListener('pywebviewready', function () {
    loadSystemSpecs();
    loadSavedLanguage();
    refreshTable();
});

function api() {
    return (window.pywebview && pywebview.api) ? pywebview.api : null;
}

function loadSystemSpecs() {
    const a = api();
    if (!a || typeof a.get_system_specs !== 'function') return;
    a.get_system_specs().then(specs => {
        document.getElementById('sys-os').innerText = specs.os || '-';
        document.getElementById('sys-device').innerText = specs.device || '-';
        document.getElementById('sys-cpu').innerText = specs.cpu || '-';
        document.getElementById('sys-ram').innerText = specs.ram || '-';
        document.getElementById('sys-gpu').innerText = specs.gpu || '-';
    }).catch(err => console.error('specs failed', err));
}

function loadSavedLanguage() {

    applyLanguage('fa');
    document.getElementById('lang-fa').checked = true;
}

const TAB_IDS = ['specs', 'pm', 'about'];

function showTab(tabName) {
    TAB_IDS.forEach(name => {
        const el = document.getElementById('tab-' + name);
        if (el) el.style.display = (name === tabName) ? 'block' : 'none';
    });
    const radioIndex = { specs: 'radio-1', pm: 'radio-2', about: 'radio-3' }[tabName];
    if (radioIndex) document.getElementById(radioIndex).checked = true;
    if (tabName === 'specs') loadSystemSpecs();
}

function openAboutTab() {
    showTab('about');
}

function toggleLangMenu(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('lang-dropdown');
    dropdown.classList.toggle('hidden');
}

document.addEventListener('click', function () {
    const dropdown = document.getElementById('lang-dropdown');
    if (dropdown && !dropdown.classList.contains('hidden')) {
        dropdown.classList.add('hidden');
    }
});

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function refreshTable() {
    const a = api();
    if (!a || typeof a.get_vault_items !== 'function') return;

    a.get_vault_items().then(data => {
        const tbody = document.getElementById('vault-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';

        document.getElementById('cnt-locked-apps').innerText = data.apps_count || 0;
        document.getElementById('cnt-locked-folders').innerText = data.folders_count || 0;

        const items = data.items || [];
        const t = translations[currentLanguage];

        if (items.length === 0) {
            const empty = document.createElement('tr');
            empty.className = 'empty-row';
            empty.innerHTML = `<td colspan="4">${escapeHtml(t.msgEmptyTable)}</td>`;
            tbody.appendChild(empty);
            selectedVaultRow = null;
            return;
        }

        items.forEach(item => {
            const row = document.createElement('tr');
            row.className = 'vault-row';

            row.innerHTML = `
                <td>${escapeHtml(item.name)}</td>
                <td>${escapeHtml(item.type)}</td>
                <td class="path-cell" title="${escapeHtml(item.path)}">${escapeHtml(item.path)}</td>
                <td class="status-cell">${escapeHtml(item.status)}</td>`;
            row.onclick = () => selectVaultRow(row, item);
            tbody.appendChild(row);
        });
    }).catch(err => console.error('refreshTable failed', err));
}

function selectVaultRow(rowElement, item) {
    document.querySelectorAll('.vault-row.selected').forEach(r => r.classList.remove('selected'));
    rowElement.classList.add('selected');
    selectedVaultRow = item;
}

function minimizeApp() { const a = api(); if (a) a.minimize_window(); }
function closeApp()    { const a = api(); if (a) a.close_window(); }
function lockApp()     { const a = api(); if (a && a.lock_app) a.lock_app(); }
function lockFolder()  { const a = api(); if (a && a.lock_folder) a.lock_folder(); }

function removeSelectedProtection() {
    if (!selectedVaultRow) {
        alert(translations[currentLanguage].msgSelectFirst);
        return;
    }
    const a = api();
    if (!a) return;
    a.remove_protection(
        selectedVaultRow.item_type || guessItemType(selectedVaultRow.type),
        selectedVaultRow.name,
        selectedVaultRow.path
    ).then(() => {
        selectedVaultRow = null;
        refreshTable();
    });
}

function guessItemType(typeLabel) {
    return (typeLabel === translations.fa.typeFolder ||
            typeLabel === translations.en.typeFolder ||
            typeLabel === 'Folder' || typeLabel === 'پوشه') ? 'folder' : 'app';
}
