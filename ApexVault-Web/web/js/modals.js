let currentSetupItem = null;
let currentGateItem = null;

function openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) {
        el.classList.add('open');
        el.style.display = 'flex';
    }
}

function closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) {
        el.classList.remove('open');
        el.style.display = 'none';
    }
    if (modalId === 'gate-modal' && currentGateItem) {

        if (window.pywebview && pywebview.api && typeof pywebview.api.gate_closed === 'function') {
            pywebview.api.gate_closed(currentGateItem.key);
        }
        currentGateItem = null;
    }
    if (modalId === 'pwd-setup-modal') {
        currentSetupItem = null;
    }
}

function closeGateModal() {
    closeModal('gate-modal');
}

function togglePassword(inputId, iconElement) {    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
        iconElement.innerText = '🙈';
    } else {
        input.type = 'password';
        iconElement.innerText = '👁️';
    }
}

function setError(id, message, color) {
    const el = document.getElementById(id);
    el.style.color = color || '#e74c3c';
    el.innerText = message || '';
}

function showPasswordSetupModal(name, path, type) {
    currentSetupItem = { name: name, path: path, type: type };
    document.getElementById('setup-target-name').innerText = name;
    document.getElementById('pwd1').value = '';
    document.getElementById('pwd2').value = '';
    document.getElementById('chk-face').checked = false;
    setError('setup-err', '');
    openModal('pwd-setup-modal');
    setTimeout(() => { try { document.getElementById('pwd1').focus(); } catch (e) {} }, 80);
}

function showGateModal(key, path, is_folder, has_face) {
    currentGateItem = { key: key, path: path, is_folder: !!is_folder, has_face: !!has_face };
    document.getElementById('gate-target-name').innerText =
        is_folder ? (key.split('\\').pop() || key) : key;
    document.getElementById('gate-pwd').value = '';
    setError('gate-err', '');

    document.getElementById('gate-face-btn-container').style.display = has_face ? 'block' : 'none';

    openModal('gate-modal');
    setTimeout(() => { try { document.getElementById('gate-pwd').focus(); } catch (e) {} }, 80);
}

function submitPasswordSetup(event) {
    if (event) event.preventDefault();
    if (!currentSetupItem) return;

    const t = translations[currentLanguage];
    const p1 = document.getElementById('pwd1').value;
    const p2 = document.getElementById('pwd2').value;
    const faceEnabled = document.getElementById('chk-face').checked;

    if (!p1) { setError('setup-err', t.msgEnterPwd); return; }
    if (p1 !== p2) { setError('setup-err', t.msgMismatch); return; }

    setError('setup-err', t.msgProcessing, '#00F0FF');

    if (faceEnabled &&
        window.pywebview && pywebview.api &&
        typeof pywebview.api.setup_face_recognition === 'function') {
        pywebview.api.setup_face_recognition(currentSetupItem.name).then(faceOk => {
            if (faceOk === true) {
                saveFinalData(p1, true);
            } else {
                setError('setup-err', t.msgFaceSetupFailed);
            }
        });
    } else {
        saveFinalData(p1, faceEnabled);
    }
}

function saveFinalData(password, hasFace) {
    const api = (window.pywebview && pywebview.api) ? pywebview.api : null;
    if (!api || typeof api.save_protection !== 'function') {
        setError('setup-err', 'pywebview API is not ready');
        return;
    }
    api.save_protection(
        currentSetupItem.type,
        currentSetupItem.name,
        currentSetupItem.path,
        password,
        hasFace
    ).then(res => {
        if (res && res.success) {
            closeModal('pwd-setup-modal');
            refreshTable();
        } else {

            setError('setup-err', (res && res.message) || translations[currentLanguage].msgSaveFailed);
        }
    }).catch(err => {
        console.error('save_protection failed', err);
        setError('setup-err', translations[currentLanguage].msgSaveFailed);
    });
}

function submitGateUnlock(event) {
    if (event) event.preventDefault();

    const t = translations[currentLanguage];
    const pwd = document.getElementById('gate-pwd').value;

    if (!pwd) { setError('gate-err', t.msgPwdRequired); return; }

    setError('gate-err', t.msgVerifying, '#00F0FF');

    pywebview.api.verify_unlock(currentGateItem.key, pwd, currentGateItem.is_folder)
        .then(res => {
            if (res.success) {
                closeModal('gate-modal');
            } else {
                setError('gate-err', res.message || t.msgWrongPwd);
            }
        })
        .catch(err => {
            console.error('verify_unlock failed', err);
            setError('gate-err', t.msgWrongPwd);
        });
}

function attemptFaceUnlock() {
    const t = translations[currentLanguage];
    setError('gate-err', t.msgScanning, '#00F0FF');

    pywebview.api.verify_face_unlock(currentGateItem.key, currentGateItem.is_folder)
        .then(res => {
            if (res.success) {
                closeModal('gate-modal');
            } else {
                setError('gate-err', res.message || t.msgFaceFailed);
            }
        })
        .catch(err => {
            console.error('verify_face_unlock failed', err);
            setError('gate-err', t.msgFaceFailed);
        });
}

document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;

    const setupOpen = document.getElementById('pwd-setup-modal').classList.contains('open');
    const gateOpen = document.getElementById('gate-modal').classList.contains('open');
    const dropdown = document.getElementById('lang-dropdown');
    const dropdownOpen = dropdown && !dropdown.classList.contains('hidden');

    if (dropdownOpen) {
        dropdown.classList.add('hidden');
    } else if (setupOpen) {
        closeModal('pwd-setup-modal');
    } else if (gateOpen) {
        closeModal('gate-modal');
    }
});
