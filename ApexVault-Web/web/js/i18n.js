const translations = {
    fa: {
        chooseLang: "انتخاب زبان / Choose Language",
        navSpecs: "اطلاعات سیستم",
        navPm: "مدیریت قفل/رمزها",
        navAbout: "درباره پروژه",
        titleSpecs: "مشخصات سخت‌افزاری سیستم",
        titleAbout: "سازندگان پروژه",
        lblOs: "سیستم‌عامل:",
        lblDevice: "نام دستگاه:",
        lblCpu: "پردازنده (CPU):",
        lblRam: "حافظه (RAM):",
        lblGpu: "کارت گرافیک (GPU):",
        txtDevDesc: "این یک برنامه دانشجویی است، طراحی و پیاده‌سازی شده توسط M-KF.",
        btnLockApp: "قفل کردن برنامه (.EXE)",
        btnLockFolder: "قفل کردن پوشه امن",
        btnRemove: "حذف محافظت",
        thTarget: "نام هدف",
        thType: "نوع",
        thPath: "مسیر",
        thStatus: "وضعیت",
        statusActive: "تحت حفاظت",
        typeApp: "برنامه",
        typeFolder: "پوشه",
        lblLockedApps: "برنامه‌های قفل شده:",
        lblLockedFolders: "پوشه‌های قفل شده:",
        setupTitle: "تنظیم رمز عبور برای:",
        enterPwd: "ورود رمز عبور:",
        confirmPwd: "تکرار رمز عبور:",
        enableFace: "فعال‌سازی تشخیص چهره (اختیاری)",
        gateTitle: "دسترسی محدود شده است:",
        btnUnlock: "بازگشایی",
        btnFaceUnlock: "📷 بازگشایی با چهره",

        msgEnterPwd: "لطفاً رمز عبور را وارد کنید.",
        msgMismatch: "رمزهای وارد شده یکسان نیستند!",
        msgProcessing: "در حال پردازش...",
        msgVerifying: "در حال بررسی...",
        msgScanning: "در حال اسکن چهره...",
        msgPwdRequired: "رمز عبور الزامی است!",
        msgWrongPwd: "رمز عبور اشتباه است!",
        msgFaceFailed: "❌ چهره شناسایی نشد!",
        msgFaceSetupFailed: "ثبت چهره ناموفق بود یا لغو شد.",
        msgSelectFirst: "ابتدا یک مورد از جدول انتخاب کنید!",
        msgSaveFailed: "ثبت رمز ناموفق بود! دوباره تلاش کنید.",
        msgEmptyTable: "هنوز چیزی قفل نشده است"
    },
    en: {
        chooseLang: "انتخاب زبان / Choose Language",
        navSpecs: "System Info",
        navPm: "Password Manager",
        navAbout: "About Project",
        titleSpecs: "System Specifications",
        titleAbout: "Project Developers",
        lblOs: "OS:",
        lblDevice: "Device Name:",
        lblCpu: "CPU:",
        lblRam: "RAM:",
        lblGpu: "Graphics (GPU):",
        txtDevDesc: "This is a student project, designed and developed by M-KF.",
        btnLockApp: "LOCK APPLICATION (.EXE)",
        btnLockFolder: "LOCK SECURE FOLDER",
        btnRemove: "REMOVE PROTECTION",
        thTarget: "Target Name",
        thType: "Type",
        thPath: "Path",
        thStatus: "Status",
        statusActive: "Guarded",
        typeApp: "App",
        typeFolder: "Folder",
        lblLockedApps: "Locked Apps:",
        lblLockedFolders: "Locked Folders:",
        setupTitle: "Set Password for:",
        enterPwd: "Enter Password:",
        confirmPwd: "Confirm Password:",
        enableFace: "Enable Face ID (Optional)",
        gateTitle: "Access Restricted:",
        btnUnlock: "Unlock",
        btnFaceUnlock: "📷 Unlock with Face ID",
        msgEnterPwd: "Please enter a password.",
        msgMismatch: "Passwords do not match!",
        msgProcessing: "Processing...",
        msgVerifying: "Verifying...",
        msgScanning: "Scanning face...",
        msgPwdRequired: "Password required!",
        msgWrongPwd: "Incorrect password!",
        msgFaceFailed: "❌ Face not recognized!",
        msgFaceSetupFailed: "Face registration failed or canceled.",
        msgSelectFirst: "Please select an item from the table first!",
        msgSaveFailed: "Failed to save the password! Please try again.",
        msgEmptyTable: "Nothing locked yet"
    }
};

let currentLanguage = 'fa';

function applyLanguage(lang) {
    const t = translations[lang];
    if (!t) return;
    currentLanguage = lang;

    document.getElementById('nav-specs').innerText = t.navSpecs;
    document.getElementById('nav-pm').innerText = t.navPm;
    document.getElementById('nav-about').innerText = t.navAbout;
    document.getElementById('title-specs').innerText = t.titleSpecs;
    document.getElementById('title-about').innerText = t.titleAbout;
    document.getElementById('lbl-os').innerText = t.lblOs;
    document.getElementById('lbl-device').innerText = t.lblDevice;
    document.getElementById('lbl-cpu').innerText = t.lblCpu;
    document.getElementById('lbl-ram').innerText = t.lblRam;
    document.getElementById('lbl-gpu').innerText = t.lblGpu;
    document.getElementById('txt-dev-desc').innerText = t.txtDevDesc;

    document.getElementById('btn-lock-app-txt').innerText = t.btnLockApp;
    document.getElementById('btn-lock-folder-txt').innerText = t.btnLockFolder;
    document.getElementById('btn-remove-txt').innerText = t.btnRemove;
    document.getElementById('th-target').innerText = t.thTarget;
    document.getElementById('th-type').innerText = t.thType;
    document.getElementById('th-path').innerText = t.thPath;
    document.getElementById('th-status').innerText = t.thStatus;

    document.getElementById('lbl-locked-apps').innerText = t.lblLockedApps;
    document.getElementById('lbl-locked-folders').innerText = t.lblLockedFolders;

    document.getElementById('setup-title-msg').innerText = t.setupTitle;
    document.getElementById('lbl-enter-pwd').innerText = t.enterPwd;
    document.getElementById('lbl-confirm-pwd').innerText = t.confirmPwd;
    document.getElementById('lbl-enable-face').innerText = t.enableFace;

    document.getElementById('gate-title-msg').innerText = t.gateTitle;
    document.getElementById('lbl-gate-pwd').innerText = t.enterPwd;
    document.getElementById('btn-gate-unlock').innerText = t.btnUnlock;
    document.getElementById('btn-gate-face').innerText = t.btnFaceUnlock;

    document.documentElement.lang = (lang === 'fa') ? 'fa' : 'en';

    if (typeof refreshTable === 'function') refreshTable();
}

function setLanguage(lang) {
    applyLanguage(lang);
    if (window.pywebview && pywebview.api && typeof pywebview.api.set_language === 'function') {
        pywebview.api.set_language(lang === 'fa' ? 'Persian' : 'English');
    }
}
