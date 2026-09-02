# ApexVault

[English](#english) · [فارسی](#فارسی)

<a name="english"></a>
## English

**ApexVault** is a Windows desktop application that locks your programs
(.exe) and folders behind a password — with an optional Face ID unlock.
Built as a student project by **M-KF**.

While the guardian runs, any locked application is terminated the moment
it starts, and any Explorer window showing a locked folder is closed.
Unlocking requires the password (or your face). The app hides to the
system tray when closed and keeps guarding in the background; it starts
automatically with Windows when at least one item is locked.

### Features

- Lock any executable or folder with a password
- Optional Face ID unlock (camera-based, on-device)
- AES-256-GCM encrypted vault; passwords stored as PBKDF2-HMAC-SHA256
  hashes (600k iterations); master key protected by Windows DPAPI
- Bilingual UI: Persian / English
- System tray background guardian + autostart
- Legacy plain-text vaults are migrated transparently and deleted
- Optional Rust crypto core (`apex_crypto/`) for native-speed encryption

### Tech stack

Python 3.10+ · pywebview 6 (WebView2) · vanilla HTML/CSS/JS ·
optional Rust/pyo3 crypto core · optional OpenCV face recognition

### Project layout

```
main.py            entry point (thin launcher)
core/              domain logic (crypto, storage, Win32, monitor, face)
ui/                pywebview JS-API bridge, languages, tray icon
web/               frontend (index.html + css/ + js/ + assets/)
apex_crypto/       optional Rust core (maturin/pyo3)
assets/            icons
```

### Installation & running

```bash
# 1. Clone
git clone <repo-url>
cd apexvault

# 2. Install dependencies (Python 3.10 or newer, Windows)
pip install -r requirements.txt

# 3. Run from the project root
python main.py
```

Optional — Face ID support:

```bash
pip install opencv-python face-recognition
```

Optional — Rust crypto core (needs the Rust toolchain from rustup.rs):

```bash
pip install maturin
cd apex_crypto && maturin develop --release
```

### Security notes

- The vault file (`%APPDATA%\ApexVault\vault_data.apx`) is encrypted with
  AES-256-GCM; its random master key is wrapped with DPAPI, so it is bound
  to *your Windows user account*.
- Passwords are never stored — only PBKDF2 hashes.
- Face embeddings are stored as `.npy` files (no pickle), hashed filenames.
- Logs live in `%APPDATA%\ApexVault\apexvault.log`.

> Student project — use as a convenience lock, not as adversarial-grade
> protection against a determined expert user.

<a name="فارسی"></a>
## فارسی

**ApexVault** یک برنامه دسکتاپ ویندوزی است که برنامه‌ها (.exe) و پوشه‌های
شما را پشت رمز عبور قفل می‌کند — با امکان بازگشایی با تشخیص چهره.
پروژه‌ای دانشجویی، طراحی و پیاده‌سازی **M-KF**.

وقتی نگهبان در حال اجراست، هر برنامه قفل‌شده به‌محض اجرا بسته می‌شود و
هر پنجره اکسپلورری که پوشه قفل‌شده را نشان دهد بسته می‌شود. بازگشایی فقط
با رمز عبور (یا چهره شما) ممکن است. با بستن پنجره، برنامه به tray می‌رود
و در پس‌زمینه به نگهبانی ادامه می‌دهد؛ اگر حداقل یک آیتم قفل شده باشد،
با روشن شدن ویندوز هم به‌صورت خودکار اجرا می‌شود.

### امکانات

- قفل کردن هر برنامه یا پوشه با رمز عبور
- بازگشایی اختیاری با تشخیص چهره (دوربین، کاملاً روی دستگاه)
- کانتینر رمزنگاری‌شده AES-256-GCM؛ رمزها به‌صورت هش PBKDF2-SHA256
  (۶۰۰هزار تکرار)؛ کلید اصلی با DPAPI ویندوز محافظت می‌شود
- رابط دوزبانه: فارسی / انگلیسی
- نگهبان پس‌زمینه در system tray + اجرای خودکار با ویندوز
- مهاجرت شفاف از vault متنی قدیمی و حذف فایل plaintext
- هسته رمزنگاری اختیاری Rust برای سرعت بومی

### اجرا

```bash
pip install -r requirements.txt
python main.py
```

(نیازمندی‌ها و اختیاری‌ها در بخش انگلیسی توضیح داده شده است.)

### نکته امنیتی

پروژه دانشجویی است — به‌عنوان قفل راحتی استفاده کنید، نه محافظت در
برابر کاربر خبره‌ای که عمداً قصد دور زدن دارد.
