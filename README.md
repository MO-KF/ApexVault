# ApexVault 🔐

یک نرم‌افزار قفل و مدیریت راز برای ویندوز با دو نسخه‌ی مختلف:

| پوشه | نسخه | رابط کاربری | تکنولوژی |
|------|------|-------------|----------|
| [`ApexVault-Python/`](ApexVault-Python/) | نسخه دسکتاپ | PyQt6 (نیتیو) | Python + PyQt6 |
| [`ApexVault-Web/`](ApexVault-Web/) | نسخه وب‌محور | HTML/CSS/JS | Python + pywebview |

هر دو نسخه از یک هسته‌ی رمزنگاری مشترک به نام **apex_crypto** استفاده می‌کنند که با **Rust** نوشته شده و از طریق PyO3 به پایتون وصل می‌شود.

## ویژگی‌ها

- 🔒 گاوصندوق رمزنگاری‌شده با AES-256-GCM
- 🔑 استخراج کلید با Argon2 (مقاوم در برابر حملات جستجوی کلید)
- 👤 احراز هویت چهره (اختیاری)
- 🛡️ مانیتورینگ سیستم و محافظت در برابر ابزارهای نفوذ
- 🌐 رابط دوزبانه (فارسی/انگلیسی)

## ساخت هسته Rust

پیش از اجرا باید ماژول `apex_crypto` را بسازید:

```bash
cd apex_crypto
cargo build --release
# فایل خروجی (apex_crypto.pyd) را در ریشه پروژه کپی کنید
```

پیش‌نیازها: [Rust](https://rustup.rs) و Python 3.10+

## نصب و اجرا

```bash
pip install -r requirements.txt
python main.py
```

## ساختار مخزن

```
ApexVault/
├── ApexVault-Python/   # نسخه دسکتاپ با PyQt6
│   ├── core/           # منطق اصلی (رمزنگاری، احراز چهره، مانیتور)
│   ├── ui/             # رابط کاربری PyQt6
│   ├── assets/         # آیکون‌ها و تصاویر
│   └── apex_crypto/    # هسته Rust (سورس)
└── ApexVault-Web/      # نسخه وب‌محور با pywebview
    ├── core/
    ├── ui/
    ├── web/            # فرانت‌اند HTML/CSS/JS
    └── apex_crypto/    # هسته Rust (سورس)
```

## نکته امنیتی

هرگز فایل‌های `key.vault`، `vault_data.*` یا `config.json` را کامیت نکنید — این فایل‌ها در `.gitignore` مستثنی شده‌اند ولی همیشه قبل از push چک کنید.

## لایسنس

مطابق فایل [LICENSE](ApexVault-Web/LICENSE).
