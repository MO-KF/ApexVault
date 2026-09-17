PERSIAN = {
    "active": "تحت حفاظت",
    "type_app": "برنامه",
    "type_folder": "پوشه",
    "credit_msg": "این یک برنامه دانشجویی است، طراحی و پیاده‌سازی شده توسط M-KF.",
    "setup_msg": "تنظیم رمز عبور برای",
    "enter_pwd": "ورود رمز عبور:",
    "confirm_pwd": "تکرار رمز عبور:",
    "mismatch": "رمزهای وارد شده یکسان نیستند!",
    "gate_msg": "دسترسی محدود شده است. برای باز کردن رمز را وارد کنید:",
    "error_pass": "رمز عبور اشتباه است!",
    "not_found": "آیتم یافت نشد!",
    "empty_pwd": "رمز عبور نمی‌تواند خالی باشد!",
    "save_failed": "خطا در ذخیره‌سازی! لطفاً دوباره تلاش کنید.",
}

ENGLISH = {
    "active": "Guarded",
    "type_app": "App",
    "type_folder": "Folder",
    "credit_msg": "This is a student project, designed and developed by M-KF.",
    "setup_msg": "Set Password for",
    "enter_pwd": "Enter Password:",
    "confirm_pwd": "Confirm Password:",
    "mismatch": "Passwords do not match!",
    "gate_msg": "Access is restricted. Enter password to unlock:",
    "error_pass": "Incorrect Password!",
    "not_found": "Item not found!",
    "empty_pwd": "Password cannot be empty!",
    "save_failed": "Saving failed! Please try again.",
}

LANGUAGES = {"English": ENGLISH, "Persian": PERSIAN}
DEFAULT_LANG = "Persian"

def get(lang_name: str) -> dict:
    return LANGUAGES.get(lang_name, LANGUAGES[DEFAULT_LANG])
