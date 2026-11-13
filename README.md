# cf-scanner

ابزار پیدا کردن آی‌پی تمیز کلودفلر برای کاربران ایران: یک ربات تلگرام و یک مینی‌اپ.

مشکل اصلی این است که آی‌پی‌های کلودفلر که از یک اپراتور جواب می‌دهند، از اپراتور دیگر
جواب نمی‌دهند یا سرعتشان افتضاح است. این پروژه دو راه برای پیدا کردنشان می‌دهد.

## دو روش کار

روش اول، اسکن زنده: مینی‌اپ تلگرام که از روی خود گوشی کاربر آی‌پی‌ها را تست می‌کند.
مناسب کسی که فیلترشکن کل سیستمش را ندارد و فقط با پروکسی داخلی تلگرام آنلاین است.
بیست‌وچهار آی‌پی نمونه از رنج‌های مختلف کلودفلر، شش‌تا شش‌تا و موازی تست می‌شوند، هر کدام
زیر ۶۰۰ میلی‌ثانیه جواب داد می‌ماند، آخرش بر اساس تأخیر مرتب می‌شود و با یک ضربه کپی
می‌شود. پورت را هم می‌شود عوض کرد (۴۴۳، ۲۰۵۳، ۸۴۴۳، ۸۰).

روش دوم، لیست آماده: ربات لیست آی‌پی هر اپراتور را از دامنهٔ اختصاصی همان اپراتور می‌گیرد
(`socket.getaddrinfo`، فقط IPv4، چند تلاش، با فالبک DNS-over-HTTPS). هر آی‌پی برگشتی با
رنج‌های رسمی کلودفلر اعتبارسنجی می‌شود و هر چیزی که مال کلودفلر نباشد دور ریخته می‌شود،
چون آی‌پی غیرکلودفلر کانفیگ کاربر را می‌شکند. اگر لیست اختصاصی یک اپراتور در دسترس نبود،
ربات به‌جای پیام خالی، آی‌پی‌های زنده‌ای می‌دهد که همین حالا از سمت سرور روی پورت ۴۴۳ تست
شده‌اند و در پیام هم می‌نویسد که این‌ها لیست اختصاصی نیستند.

اپراتورهای فعلی: همراه اول، ایرانسل، رایتل، مخابرات، شاتل، پیشگامان، مبین‌نت و لیست عمومی.

## فایل‌ها

```
bot.py             ربات تلگرام (pyTelegramBotAPI) - لیست‌های آماده + دکمهٔ ورود به مینی‌اپ
index.html         مینی‌اپ، تک‌فایل، بدون بیلد و بدون وابستگی، روی GitHub Pages
requirements.txt
```

## اجرا

نیاز: پایتون ۳.۹ به بالا.

```
pip install -r requirements.txt
export BOT_TOKEN="توکن ربات از BotFather"
python3 bot.py
```

توکن هیچ‌وقت داخل کد نیست. برای تست بدون بالا آوردن ربات (بدون قطع شدن نمونهٔ در حال اجرا):

```
python3 bot.py --selftest
```

این دستور اتصال تلگرام را چک می‌کند، هر هشت اپراتور را می‌گیرد و جدول نتیجه را چاپ می‌کند.

متغیرهای محیطی اختیاری: `MINI_APP_URL`، `CACHE_TTL` (پیش‌فرض ۱۲۰ ثانیه)،
`REQUEST_GAP` (فاصلهٔ مجاز بین دو فشار دکمهٔ هر کاربر)، `PROBE_PORT`، `PROBE_TIMEOUT`.

## اجرای دائمی با systemd

توکن را در فایلی با دسترسی ۶۰۰ بگذار:

```
echo 'BOT_TOKEN=توکن' | sudo tee /etc/cf-scanner.env >/dev/null
sudo chmod 600 /etc/cf-scanner.env
```

بعد یونیت `cf-scanner-bot.service` را نصب کن:

```
sudo cp cf-scanner-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cf-scanner-bot
```

لاگ:

```
tail -f /root/cf-scanner/bot.log
```

## نکته‌های فنی

- قفل تک‌نمونه (`flock` روی `/tmp/cf-scanner.lock`) جلوی خطای `409 Conflict` را می‌گیرد؛
  این خطا وقتی رخ می‌دهد که دو نمونه هم‌زمان از یک توکن polling کنند.
- حلقهٔ polling با backoff نمایی است، پس قطعی موقت شبکه یا خطای ۵۰۲ تلگرام پروسه را
  از پا نمی‌اندازد.
- نتیجهٔ لیست‌ها ۱۲۰ ثانیه و نتیجهٔ تست آی‌پی‌ها ۱۰ دقیقه کش می‌شود تا هر فشار دکمه یک
  کوئری تازه نزند.
- هر کاربر حداقل سه ثانیه بین دو درخواست فاصله دارد (جلوگیری از ۴۲۹).

## مینی‌اپ

`index.html` را از تنظیمات مخزن (Settings → Pages) روی شاخهٔ main منتشر کن. تک‌فایل است و
وابستگی ندارد. اگر رنج دیگری می‌خواهی، فقط آرایهٔ `ipPool` را عوض کن.

## مشارکت

issue و pull request باز است. اگر دامنهٔ اپراتور جدیدی اضافه شد، هم `IRCF_DOMAINS` در
`bot.py` و هم جدول همین فایل را با هم به‌روز کن. تعداد اپراتورهای زنده را می‌شود با
`--selftest` دید.

## مجوز

MIT. فایل LICENSE را ببین.

---

## English

Cloudflare clean-IP finder for Iranian users: a Telegram bot plus a single-file Telegram
Mini App.

Live scan: the Mini App probes 24 sample IPs from different Cloudflare ranges, six at a
time, keeps whatever answers under 600 ms on the selected port, and sorts the survivors by
measured latency. It runs on the user's device, which matters for people whose only
connection is Telegram's built-in MTProto proxy.

Ready lists: the bot resolves each operator's dedicated domain (IPv4, retries, DNS-over-HTTPS
fallback) and validates every returned address against Cloudflare's published ranges, because
a non-Cloudflare address silently breaks the user's config. When an operator's list is
unavailable the bot returns addresses it has just probed on port 443 and says so in the
message instead of showing an error.

Run:

```
pip install -r requirements.txt
export BOT_TOKEN="token from BotFather"
python3 bot.py            # run the bot
python3 bot.py --selftest # check token and all operators without polling
```

The token is read from the environment only; a single-instance lock prevents 409 conflicts,
polling backs off on API errors, list results are cached for two minutes, and each user gets
one request per three seconds.

License: MIT.
