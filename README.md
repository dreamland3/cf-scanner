# cf-scanner

ابزار پیدا کردن آی‌پی تمیز کلودفلر برای کاربران ایران: یک ربات تلگرام و یک مینی‌اپ.

مشکل اصلی این است که آی‌پی‌های کلودفلر که از یک اپراتور جواب می‌دهند، از اپراتور دیگر
جواب نمی‌دهند یا سرعتشان افتضاح است. این پروژه دو راه برای پیدا کردنشان می‌دهد.

## دو روش کار

روش اول، اسکن زنده: مینی‌اپ تلگرام که از روی خود گوشی کاربر آی‌پی‌ها را تست می‌کند.
مناسب کسی که فیلترشکن کل سیستمش را ندارد و فقط با پروکسی داخلی تلگرام آنلاین است.
یک لیست از آی‌پی‌های رایج کلودفلر را یکی‌یکی با تایم‌اوت ۸۰۰ میلی‌ثانیه صدا می‌زند،
هر کدام زیر ۵۰۰ میلی‌ثانیه جواب داد می‌ماند، آخرش بر اساس سرعت مرتب می‌شود و با یک ضربه
کپی می‌شود.

روش دوم، لیست آماده: ربات لیست آی‌پی تمیز هر اپراتور را از دامنه‌های اختصاصی هر اپراتور
می‌گیرد (`socket.getaddrinfo`، فقط IPv4، سه بار تلاش) و پنج تا برمی‌گرداند. مناسب کسی
که VPN کل سیستمش روشن است ولی می‌خواهد کانفیگش را عوض کند.

اپراتورهای فعلی: همراه اول، ایرانسل، رایتل، مخابرات، شاتل، پیشگامان، مبین‌نت و لیست عمومی.

## فایل‌ها

```
bot.py        ربات تلگرام (pyTelegramBotAPI) - لیست‌های آماده + دکمه ورود به مینی‌اپ
index.html    مینی‌اپ، تک‌فایل، بدون بیلد و بدون وابستگی، روی GitHub Pages میزبانی می‌شود
requirements.txt
```

فقط همین دو فایل کد هست. `bot.py` حدود ۶ کیلوبایت و `index.html` حدود ۷.۵ کیلوبایت است.

## اجرا

نیاز: پایتون ۳.۹ به بالا.

```
pip install -r requirements.txt
export BOT_TOKEN="توکن ربات از BotFather"
python3 bot.py
```

توکن هیچ‌وقت داخل کد نیست، از متغیر محیطی خوانده می‌شود. اگر نباشد برنامه با پیام خطا
بالا نمی‌آید.

`MINI_APP_URL` بالای `bot.py` باید آدرس مینی‌اپ باشد (همان GitHub Pages همین مخزن).
اگر عوضش کنی دکمه اسکن زنده از کار می‌افتد.

## اجرای دائمی با systemd

توکن را در یک فایل با دسترسی ۶۰۰ بگذار:

```
echo 'BOT_TOKEN=توکن' | sudo tee /etc/cf-scanner.env >/dev/null
sudo chmod 600 /etc/cf-scanner.env
```

بعد یونیت `cf-scanner-bot.service` این مخزن را کپی کن:

```
sudo cp cf-scanner-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cf-scanner-bot
```

لاگ زنده:

```
tail -f /root/cf-scanner/bot.log
```

## مینی‌اپ

`index.html` را از تنظیمات مخزن (Settings → Pages) روی شاخه main منتشر کن. چون تک‌فایل و
بدون وابستگی است، همان‌جا کار می‌کند. اگر رنج یا پورت دیگری می‌خواهی، فقط آرایه `ipPool`
و پورت داخل `testIPLatency` را عوض کن.

## ورودی‌ها و پیشنهاد کار

issue و pull request باز است. اگر دامنه اپراتور جدیدی اضافه شد، هم `IRCF_DOMAINS` در
`bot.py` و هم جدول همین فایل را با هم به‌روز کن.

چیزهایی که خودم می‌خواهم اضافه کنم: اسکن موازی به‌جای یکی‌یکی (اسکن الان کند است)، پورت
قابل تنظیم، و retry برای قطعی‌های API تلگرام که در لاگ زیاد دیده می‌شود.

## مجوز

MIT. فایل LICENSE را ببین.

---

## English

Cloudflare clean-IP finder for Iranian users. It is two pieces: a Telegram bot (Python)
and a Telegram Mini App (a single HTML file).

The problem it solves: Cloudflare edge IPs that work well from one Iranian ISP are often
dead or slow from another. The project gives two ways to find working ones.

Live scan: the Mini App probes a pool of Cloudflare IPs from the user's own device with an
800 ms timeout, keeps the ones answering under 500 ms, sorts them by measured latency and
copies them on tap. This is for users whose only connection is Telegram's built-in MTProto
proxy.

Ready lists: the bot resolves the per-operator domains over DNS (IPv4 only, three attempts)
and returns up to five IPs. This is for users with a system-wide VPN who want to swap the
IPs in their config.

Operators covered: MCI, Irancell, Rightel, TCI, Shatel, Pishgaman, Mobinnet, plus a public
list.

### Run

Python 3.9+.

```
pip install -r requirements.txt
export BOT_TOKEN="token from BotFather"
python3 bot.py
```

The token is read from the environment only; the script refuses to start without it.
Set `MINI_APP_URL` at the top of `bot.py` to the published GitHub Pages URL of
`index.html`, otherwise the live-scan button points nowhere.

For a permanent install, put the token in `/etc/cf-scanner.env` (mode 600) and use the
`cf-scanner-bot.service` unit in this repository.

### Notes

Tested on Python 3.12 with pyTelegramBotAPI 4.34.0 and requests 2.34.2.

Known rough edges, in the order I want to fix them: the live scan is sequential and slow on
large pools, the port is hard-coded to 443, and the bot logs a lot of Telegram API timeouts
and `409 Conflict` errors when more than one instance polls at the same time.

### License

MIT. See LICENSE.
