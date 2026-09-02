# 🔐 ApexVault

**English** | [فارسی](#فارسی)

---

## English

ApexVault is a Windows desktop application that **locks your apps and folders with a password** (optional Face ID). While ApexVault is running, any locked app is killed the moment it starts, and locked folders are closed as soon as they are opened — until you enter the correct password.

Built with a Python/PyQt6 UI and a Rust cryptography core.

### Features

- 🖥️ Lock any `.exe` application — it terminates instantly when launched without permission
- 📁 Lock folders — Explorer windows of protected folders close automatically
- 🔑 Password protection with PBKDF2-SHA256 (100k iterations, random salt)
- 📷 Optional Face ID unlock (second factor)
- ✕ Cancel button on the password gate — go back to the parent folder
- 🌐 English/Persian UI
- ⚙️ System info page (CPU, GPU, RAM)
- 🚀 Auto-starts with Windows when you have guarded items

### Security Design

| Layer | Detail |
|---|---|
| Vault storage | The whole vault database (`vault_data.json`) is encrypted with AES-256-GCM |
| Encryption key | Random 256-bit key, protected by Windows DPAPI (current-user scoped) |
| Rust core | `apex_crypto` (PyO3): AES-256-GCM + Argon2id, preferred crypto backend |
| Face data | Stored as plain NumPy arrays — no `pickle`, no arbitrary code execution risk |
| Legacy safety | Plaintext passwords from old versions are rejected at verification time |

### Project Structure

```
ApexVault/
├── main.py              # entry point + main window (UI only)
├── ui/                  # dialogs, stylesheets, translations
├── core/                # services: storage, crypto, face auth, monitor, win32
├── assets/              # images & icons
└── apex_crypto/         # Rust crypto core (PyO3 cdylib)
```

### Getting Started

Requirements: Windows 10/11, Python 3.10+, Rust toolchain (for the crypto core).

```bash
pip install PyQt6 opencv-python face_recognition numpy cryptography pywin32

cd apex_crypto
maturin develop   # or: cargo build --release  (then copy the .pyd next to main.py)

python main.py
```

> On first run, ApexVault creates its key (`key.vault`) and encrypted vault in `%APPDATA%\ApexVault`. Deleting `key.vault` makes previously stored entries unrecoverable — treat it like a password manager backup file.

### Disclaimer

This is a student project created for learning purposes. It is not hardened against determined attackers with admin rights on the same machine.

---

## فارسی

<a name="فارسی"></a>

ApexVault یک برنامه دسکتاپ ویندوزی است که **برنامه‌ها و پوشه‌های شما را با رمز قفل می‌کند** (با قابلیت اختیاری Face ID). تا زمانی که ApexVault در حال اجراست، هر برنامه قفل‌شده بلافاصله بعد از اجرا بسته می‌شود و پنجره پوشه‌های محافظت‌شده به‌محض باز شدن بسته می‌شود — تا وقتی رمز درست را وارد کنید.

رابط کاربری با Python/PyQt6 و هسته رمزنگاری با Rust ساخته شده است.

### ویژگی‌ها

- 🖥️ قفل هر برنامه `.exe` — بدون اجازه، بلافاصله بسته می‌شود
- 📁 قفل پوشه‌ها — پنجره‌های اکسپلوررِ پوشه‌های محافظت‌شده خودکار بسته می‌شوند
- 🔑 محافظت با رمز و الگوریتم PBKDF2-SHA256 (۱۰۰هزار تکرار، نمک تصادفی)
- 📷 باز کردن با Face ID (اختیاری، فاکتور دوم)
- ✕ دکمه انصراف روی دیالوگ رمز — برگشت به پوشه والد
- 🌐 رابط دو‌زبانه انگلیسی/فارسی
- ⚙️ صفحه مشخصات سیستم (CPU، GPU، RAM)
- 🚀 اجرای خودکار همراه ویندوز وقتی مورد قفل‌شده دارید

### طراحی امنیتی

| لایه | توضیح |
|---|---|
| ذخیره‌سازی گاوصندوق | کل پایگاه داده گاوصندوق با AES-256-GCM رمزنگاری می‌شود |
| کلید رمزنگاری | کلید تصادفی ۲۵۶ بیتی، محافظت‌شده با DPAPI ویندوز (محدود به کاربر فعلی) |
| هسته Rust | ماژول `apex_crypto` (PyO3): AES-256-GCM + Argon2id، بک‌اند اولویت‌دار |
| داده چهره | ذخیره به‌صورت آرایه NumPy — بدون pickle و بدون ریسک اجرای کد دلخواه |
| سازگاری با نسخه قدیم | رمزهای متن ساده نسخه‌های قبلی هنگام تأیید قطعاً رد می‌شوند |

### ساختار پروژه

```
ApexVault/
├── main.py              # نقطه ورود و پنجره اصلی (فقط UI)
├── ui/                  # دیالوگ‌ها، استایل‌ها، ترجمه‌ها
├── core/                # سرویس‌ها: ذخیره‌سازی، رمزنگاری، چهره، مانیتورینگ، win32
├── assets/              # عکس‌ها و آیکون‌ها
└── apex_crypto/         # هسته رمزنگاری Rust (PyO3 cdylib)
```

### راه‌اندازی

پیش‌نیازها: Windows 10/11، Python 3.10+، ابزار Rust (برای هسته رمزنگاری).

```bash
pip install PyQt6 opencv-python face_recognition numpy cryptography pywin32

cd apex_crypto
maturin develop   # یا: cargo build --release  (سپس فایل .pyd را کنار main.py کپی کنید)

python main.py
```

> در اولین اجرا، ApexVault کلید خود (`key.vault`) و گاوصندوق رمزشده را در `%APPDATA%\ApexVault` می‌سازد. حذف `key.vault` باعث می‌شود ورودی‌های قبلی قابل بازیابی نباشند — مثل فایل بکاپ نرم‌افزار مدیریت رمز با آن رفتار کنید.

### سلب مسئولیت

این یک پروژه دانشجویی با هدف یادگیری است و در برابر مهاجم مصمم با دسترسی ادمین روی همان سیستم مقاوم‌سازی نشده است.
