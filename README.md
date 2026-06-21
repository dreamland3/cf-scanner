# cf-scanner
#  Cloudflare Smart Scanner Bot (cf-scanner)

یک سیستم هوشمند و دوگانه برای تست، اسکن و یافتن آی‌پی‌های تمیز و بدون فیلتر کلودفلر (Cloudflare Clean IPs) مخصوص اپراتورهای مختلف در ایران. این پروژه از دو بخش **ربات تلگرام (بک‌اند پایتون)** و **مینی‌آپ/وب‌آپ (فرانت‌اند جاوااسکریپت)** تشکیل شده است.

---

## ✨ قابلیت‌های کلیدی

- **اسکن زنده (Live Scanner):** قابلیت اسکن مستقیم رنج‌های کلودفلر از داخل محیط مینی‌آپ تلگرام بدون نیاز به نصب هیچ نرم‌افزار جانبی (مخصوص کاربران موبایل و اتصال از طریق پروکسی).
- **لیست آماده اپراتورها:** استخراج و نمایش چرخشی آخرین آی‌پی‌های تمیز ثبت‌شده برای اپراتورهای مختلف (همراه اول، ایرانسل، رایتل، مخابرات، شاتل، پیشگامان و مبین‌نت) از طریق لایه DNS Resolution.
- **طراحی بهینه و سبک:** اجرای کاملاً مستقل در پس‌زمینه سرور به صورت لینوکس سرویس (`systemd`) بدون تداخل با سایر ابزارهای شبکه.
- **امنیت بالا (Production Ready):** جداسازی کامل توکن‌های حساس ربات از بدنه کد گیت‌هاب و تزریق امن آن‌ها از طریق متغیرهای محیطی سیستم‌عامل (`Environment Variables`).

---

## 🛠️ ساختار فنی پروژه (Architecture)

این پروژه از دو بخش مجزا اما متصل به هم تشکیل شده است:

1. **بخش فرانت‌اند (Telegram Mini App):** کدهای HTML/JS/CSS که در روت اصلی مخزن قرار دارند و از طریق **GitHub Pages** میزبانی می‌شوند تا به عنوان وب‌آپ در تلگرام لود شوند.
2. **بخش بک‌اند (Telegram Bot):** فایل `bot.py` که با کتابخانه `pyTelegramBotAPI` نوشته شده و روی سرور لینوکس در دیتاسنتر اجرا می‌شود.

---

## 🚀 راهنمای راه‌اندازی ربات روی سرور لینوکس

برای اجرای پایداری این ربات در پس‌زمینه لینوکس، مراحل زیر انجام شده است:

### ۱. ساخت سرویس اختصاصی لینوکس
یک فایل سرویس در مسیر `/etc/systemd/system/cf-scanner-bot.service` با پیکربندی زیر تنظیم می‌شود:

```ini
[Unit]
Description=Cloudflare Scanner Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/cf-scanner
ExecStart=/root/tg_bot_env/bin/python3 bot.py
Environment="BOT_TOKEN=YOUR_SECRET_TELEGRAM_TOKEN"
Restart=always
RestartSec=5
StandardOutput=append:/root/cf-scanner/bot.log
StandardError=append:/root/cf-scanner/bot.log

[Install]
WantedBy=multi-user.target

دستورات مدیریت سرویس ربات
برای مدیریت این ربات روی سرور از دستورات استاندارد زیر استفاده می‌شود:

شروع به کار و فعال‌سازی خودکار در زمان بوت سرور:

Bash
sudo systemctl daemon-reload
sudo systemctl enable cf-scanner-bot.service
sudo systemctl start cf-scanner-bot.service
بررسی وضعیت زنده بودن ربات:

Bash
sudo systemctl status cf-scanner-bot.service
مشاهده لاگ‌ها و خطاهای احتمالی به صورت زنده:

Bash
tail -f /root/cf-scanner/bot.log
🔒 ملاحظات امنیتی
این مخزن کاملاً پابلیک و متن‌باز است. جهت حفظ امنیت، توکن ربات تلگرام به هیچ عنوان در کدهای این مخزن هاردکد (Hardcode) نشده و کاملاً از طریق دستور os.getenv("BOT_TOKEN") از هسته سیستم‌عامل سرور فراخوانی می‌شود.

🌐 Developed with ❤️ for bypassing networking restrictions.
@MyCfScannerBot
