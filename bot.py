# -*- coding: utf-8 -*-
"""
cf-scanner bot: لیست آی‌پی تمیز کلودفلر برای اپراتورهای ایران.

تغییرات نسخه ۱.۱.۰ نسبت به ۱.۰.۰:
- لاگ چرخشی به‌جای ریختن تراس‌بک روی stdout (فایل لاگ دیگر بی‌نهایت رشد نمی‌کند)
- قفل تک‌نمونه (flock) تا خطای 409 Conflict از بین برود
- حلقهٔ polling با backoff نمایی؛ قطعی شبکه دیگر پروسه را از پا نمی‌اندازد
- retry + فالبک DNS-over-HTTPS برای گرفتن لیست آی‌پی‌ها
- کش کوتاه‌مدت (پیش‌فرض ۱۲۰ ثانیه) تا هر فشار دکمه یک کوئری DNS تازه نزند
- محدودیت نرخ ساده برای هر کاربر (جلوگیری از خطای 429)
- دکمهٔ «تلاش مجدد» و پاسخ‌دادن به کال‌بک در هر شرایطی (اسپینر تلگرام گیر نمی‌کند)
- `--selftest` برای تست زنده بدون اجرای polling
"""
import os
import sys
import time
import json
import socket
import signal
import ipaddress
import logging
from logging.handlers import RotatingFileHandler
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

try:
    import fcntl
except ImportError:  # ویندوز
    fcntl = None

BOT_TOKEN = os.getenv("BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://dreamland3.github.io/cf-scanner/")
CACHE_TTL = int(os.getenv("CACHE_TTL", "120"))
REQUEST_GAP = float(os.getenv("REQUEST_GAP", "3"))      # حداقل فاصله بین دو درخواست هر کاربر
LOCK_PATH = os.getenv("LOCK_PATH", "/tmp/cf-scanner.lock")
DOH_ENDPOINT = "https://cloudflare-dns.com/dns-query"
CF_RANGES_URL = "https://www.cloudflare.com/ips-v4"
CF_LIST_URL = "https://raw.githubusercontent.com/ircfspace/shirokhorshid-cleanip/main/v1.json"
PROBE_PORT = int(os.getenv("PROBE_PORT", "443"))
PROBE_TIMEOUT = float(os.getenv("PROBE_TIMEOUT", "1.2"))
NETS_TTL = 6 * 3600        # لیست رنج‌های کلودفلر
PROBE_TTL = 600            # نتیجهٔ تست آی‌پی‌ها

log = logging.getLogger("cf-scanner")

IRCF_DOMAINS = {
    "public": "cf.ircf.space",
    "mci": "mci.ircf.space",
    "mtn": "mtn.ircf.space",
    "tci": "tci.ircf.space",
    "mbt": "mbt.ircf.space",
    "rtl": "rtl.ircf.space",
    "pishgaman": "pishgaman.ircf.space",
    "shatel": "shatel.ircf.space",
}

PROVIDER_NAMES = {
    "public": "عمومی (همه اپراتورها)",
    "mci": "همراه اول",
    "mtn": "ایرانسل",
    "tci": "مخابرات",
    "mbt": "مبین‌نت",
    "rtl": "رایتل",
    "pishgaman": "پیشگامان",
    "shatel": "شاتل",
}

# ---------- زیرساخت ----------

def setup_logging():
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    # فقط همین فایل لاگ را می‌نویسیم؛ systemd هم دیگر در آن نمی‌نویسد
    # (StandardOutput=null در یونیت) تا چرخش لاگ درست کار کند
    try:
        fh = RotatingFileHandler("/root/cf-scanner/bot.log", maxBytes=2_000_000,
                                 backupCount=3, encoding="utf-8")
    except OSError:
        fh = RotatingFileHandler("bot.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    if not log.handlers:
        log.addHandler(fh)
        log.addHandler(sh)


def acquire_lock():
    """جلوگیری از اجرای دو نمونه هم‌زمان (ریشهٔ خطای 409 Conflict)."""
    if fcntl is None:
        return None
    fh = open(LOCK_PATH, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log.error("نمونهٔ دیگری از ربات در حال اجراست؛ این پروسه بسته می‌شود.")
        sys.exit(0)
    fh.write(str(os.getpid()))
    fh.flush()
    return fh


_cache = {}
_cache_lock = threading.Lock()
_nets = {"ts": 0, "nets": []}
_probe = {"ts": 0, "ips": []}
_last_call = {}
_rate_lock = threading.Lock()


def rate_ok(user_id):
    now = time.time()
    with _rate_lock:
        last = _last_call.get(user_id, 0)
        if now - last < REQUEST_GAP:
            return False
        _last_call[user_id] = now
        return True


# ---------- گرفتن آی‌پی ----------

def _resolve_dns(domain, attempts=3):
    """کوئری DNS ساده، فقط IPv4، با چند تلاش."""
    ips = []
    for i in range(attempts):
        try:
            for item in socket.getaddrinfo(domain, 80, proto=socket.IPPROTO_TCP):
                ip = item[4][0]
                if ":" not in ip and ip not in ips:
                    ips.append(ip)
        except OSError as e:
            log.debug("DNS %s تلاش %d: %s", domain, i + 1, e)
        if ips:
            break
        time.sleep(0.4)
    return ips


def _resolve_doh(domain):
    """فالبک DNS-over-HTTPS (بدون وابستگی جدید)."""
    try:
        r = requests.get(
            DOH_ENDPOINT,
            params={"name": domain, "type": "A"},
            headers={"accept": "application/dns-json"},
            timeout=6,
        )
        r.raise_for_status()
        answers = r.json().get("Answer", [])
        return [
            a["data"] for a in answers
            if a.get("type") == 1 and "." in a.get("data", "") and ":" not in a["data"]
        ]
    except Exception as e:
        log.warning("فالبک DoH برای %s جواب نداد: %s", domain, e)
        return []


def cf_networks():
    """رنج‌های رسمی IPv4 کلودفلر (کش ۶ ساعته)."""
    now = time.time()
    if _nets["nets"] and now - _nets["ts"] < NETS_TTL:
        return _nets["nets"]
    nets = []
    try:
        r = requests.get(CF_RANGES_URL, timeout=8)
        r.raise_for_status()
        for token in r.text.split():
            if "/" in token:
                try:
                    nets.append(ipaddress.ip_network(token))
                except ValueError:
                    pass
    except Exception as e:
        log.warning("گرفتن رنج‌های کلودفلر نشد: %s", e)
    if nets:
        _nets.update(ts=now, nets=nets)
    return _nets["nets"]


def is_cloudflare(ip):
    nets = cf_networks()
    if not nets:
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in n for n in nets)


def _tcp_latency(ip, port=PROBE_PORT, timeout=PROBE_TIMEOUT):
    t0 = time.time()
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return round((time.time() - t0) * 1000)
    except OSError:
        return None


def _candidates():
    """کاندیدها: (آی‌پی, تگ). تگ ircf یعنی از لیست تست‌شدهٔ پروژهٔ IRCF آمده."""
    cands = []
    seen = set()
    for n in cf_networks():
        if n.num_addresses >= 16:
            for host in (1, 100, 200):
                ip = str(n.network_address + host)
                if ip not in seen:
                    seen.add(ip)
                    cands.append((ip, "range"))
    try:
        r = requests.get(CF_LIST_URL, timeout=8)
        r.raise_for_status()
        for item in r.json().get("ipv4", []):
            ip = item.split(":")[0]
            if ip not in seen:
                seen.add(ip)
                cands.append((ip, "ircf"))
    except Exception as e:
        log.warning("لیست عمومی IRCF در دسترس نبود: %s", e)
    return cands[:120]


def _net_of(ip):
    """شبکهٔ مادری یک آی‌پی در لیست کلودفلر (برای پخش‌کردن نتایج بین رنج‌ها)."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None
    for n in cf_networks():
        if addr in n:
            return str(n)
    return None


def probe_clean_ips():
    """سریع‌ترین آی‌پی‌های زنده روی پورت ۴۴۳ + آی‌پی‌های تست‌شدهٔ IRCF."""
    now = time.time()
    if _probe["ips"] and now - _probe["ts"] < PROBE_TTL:
        return _probe["ips"]

    cands = _candidates()
    alive = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(_tcp_latency, ip): (ip, tag) for ip, tag in cands}
        for f in as_completed(futs):
            ms = f.result()
            if ms is not None:
                ip, tag = futs[f]
                alive.append({"ip": ip, "ms": ms, "tag": tag})

    # اول آی‌پی‌های تست‌شدهٔ IRCF (حداکثر ۳)، بعد سریع‌ترین‌ها با شرط پخش بین رنج‌ها
    result = [a["ip"] for a in sorted([a for a in alive if a["tag"] == "ircf"],
                                      key=lambda a: a["ms"])[:3]]
    used_nets = {_net_of(ip) for ip in result}
    for a in sorted(alive, key=lambda a: a["ms"]):
        if len(result) >= 5:
            break
        if a["ip"] in result:
            continue
        net = _net_of(a["ip"])
        if net in used_nets:
            continue
        used_nets.add(net)
        result.append(a["ip"])
    for a in sorted(alive, key=lambda a: a["ms"]):      # اگر کم آمد، بدون شرط پخش
        if len(result) >= 5:
            break
        if a["ip"] not in result:
            result.append(a["ip"])

    if result:
        _probe.update(ts=now, ips=result)
    log.info("تست آی‌پی: %d از %d جواب داد؛ انتخاب: %s", len(alive), len(cands), ",".join(result))
    return result


def fetch_clean_ips(provider_key):
    """(آی‌پی‌ها, منبع) برمی‌گرداند؛ منبع یا operator است یا probed."""
    domain = IRCF_DOMAINS.get(provider_key)
    now = time.time()
    with _cache_lock:
        hit = _cache.get(provider_key)
        if hit and now - hit[0] < CACHE_TTL:
            return hit[1], hit[2]

    ips, source = [], "operator"
    if domain:
        raw = _resolve_dns(domain)
        if len(raw) < 2:
            raw = list(dict.fromkeys(raw + _resolve_doh(domain)))
        valid = [ip for ip in raw if is_cloudflare(ip)]
        if len(valid) != len(raw):
            log.warning("%s: %d آی‌پی غیرکلودفلر حذف شد", provider_key, len(raw) - len(valid))
        ips = valid[:5]

    if not ips:
        ips = probe_clean_ips()
        source = "probed"

    with _cache_lock:
        _cache[provider_key] = (now, ips, source)
    log.info("لیست %s (%s): %d آی‌پی", provider_key, source, len(ips))
    return ips, source


def fetch_many(keys):
    """چند اپراتور را موازی می‌گیرد (برای /all)."""
    out = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(fetch_clean_ips, k): k for k in keys}
        for f in as_completed(futs):
            k = futs[f]
            try:
                out[k] = f.result()
            except Exception as e:
                log.warning("خطا در %s: %s", k, e)
                out[k] = []
    return out


# ---------- ربات ----------
if not BOT_TOKEN:
    raise SystemExit("خطا: متغیر محیطی BOT_TOKEN تنظیم نشده است.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")


def main_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(
            text="🚀 اسکن زنده (مخصوص پروکسی تلگرام)",
            web_app=WebAppInfo(url=MINI_APP_URL),
        )
    )
    markup.add(
        InlineKeyboardButton(
            text="📊 لیست آماده اپراتورها (مخصوص فیلترشکن)",
            callback_data="show_providers",
        )
    )
    return markup


WELCOME = (
    "👋 به ربات اسکنر هوشمند کلودفلر خوش آمدید!\n\n"
    "لطفاً با توجه به وضعیت اتصال خود، یکی از روش‌های زیر را انتخاب کنید:\n\n"
    "🚀 **روش اول (اسکن زنده):** مخصوص افرادی که فیلترشکن گوشی‌شان خاموش است و فقط "
    "با پروکسی داخلی تلگرام (MTProto) آنلاین هستند.\n\n"
    "📊 **روش دوم (لیست آماده):** مخصوص افرادی که فیلترشکن (VPN) کل سیستم‌شان روشن است."
)


def providers_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("🌍 عمومی (Public)", callback_data="get_public"))
    markup.add(
        InlineKeyboardButton("همراه اول (MCI)", callback_data="get_mci"),
        InlineKeyboardButton("ایرانسل (MTN)", callback_data="get_mtn"),
    )
    markup.add(
        InlineKeyboardButton("رایتل (RTL)", callback_data="get_rtl"),
        InlineKeyboardButton("مخابرات (TCI)", callback_data="get_tci"),
    )
    markup.add(
        InlineKeyboardButton("شاتل (Shatel)", callback_data="get_shatel"),
        InlineKeyboardButton("پیشگامان", callback_data="get_pishgaman"),
    )
    markup.add(InlineKeyboardButton("مبین‌نت (MBT)", callback_data="get_mbt"))
    markup.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main"))
    return markup


def ips_text(provider):
    name = PROVIDER_NAMES.get(provider, provider)
    try:
        ips, source = fetch_clean_ips(provider)
    except Exception:
        log.exception("خطای غیرمنتظره در گرفتن لیست %s", provider)
        ips, source = [], "none"
    if not ips:
        text = (
            f"❌ در حال حاضر دامنه‌ی اختصاصی [{name}] پاسخی نداد.\n"
            "این مشکل معمولاً موقتی و از سمت سرور پروژه است. کمی بعد دوباره امتحان کنید."
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 تلاش مجدد", callback_data=f"get_{provider}"))
        markup.add(InlineKeyboardButton("🔙 بازگشت به لیست اپراتورها", callback_data="show_providers"))
        return text, markup
    if source == "probed":
        lines = [
            f"ℹ️ لیست اختصاصی [{name}] الان در دسترس نیست.",
            "این‌ها آی‌پی‌های کلودفلر هستند که همین حالا از سمت سرور تست و تأیید شده‌اند:\n",
        ]
    else:
        lines = [f"✅ **آی‌پی‌های تمیز و زنده مخصوص [{name}]:**\n"]
    lines += [f"`{ip}`" for ip in ips]
    lines.append("\n📌 برای کپی، روی آی‌پی ضربه بزنید.")
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 به‌روزرسانی", callback_data=f"get_{provider}"))
    markup.add(InlineKeyboardButton("🔙 بازگشت به لیست اپراتورها", callback_data="show_providers"))
    return "\n".join(lines), markup


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.send_message(message.chat.id, WELCOME, reply_markup=main_menu())


@bot.message_handler(commands=["status"])
def send_status(message):
    with _cache_lock:
        cached = {k: v[1] for k, v in _cache.items()}
    text = (
        f"وضعیت ربات: فعال ✅\n"
        f"اپراتورهای پشتیبانی‌شده: {len(IRCF_DOMAINS)}\n"
        f"کش فعلی: {len(cached)} اپراتور\n"
        f"مدت اعتبار کش: {CACHE_TTL} ثانیه"
    )
    bot.send_message(message.chat.id, text)


@bot.callback_query_handler(func=lambda call: call.data == "show_providers")
def show_providers(call):
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="👇 اپراتور خود را انتخاب کنید تا آخرین آی‌پی‌های تمیز استخراج شوند:",
            reply_markup=providers_menu(),
        )
    except Exception as e:
        log.warning("ویرایش پیام ناموفق بود: %s", e)
    finally:
        bot.answer_callback_query(call.id, text="لیست اپراتورها")


@bot.callback_query_handler(func=lambda call: call.data.startswith("get_"))
def send_ips(call):
    provider = call.data.split("_", 1)[1]
    if provider not in IRCF_DOMAINS:
        bot.answer_callback_query(call.id, text="اپراتور نامعتبر")
        return
    if not rate_ok(call.from_user.id):
        bot.answer_callback_query(call.id, text="کمی صبر کنید و دوباره بزنید", show_alert=False)
        return
    bot.answer_callback_query(call.id, text="در حال استخراج دیتای زنده...")
    text, markup = ips_text(provider)
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=markup,
        )
    except Exception as e:
        log.warning("ارسال لیست ناموفق بود: %s", e)


@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=WELCOME,
            reply_markup=main_menu(),
        )
    except Exception as e:
        log.warning("بازگشت به منو ناموفق بود: %s", e)
    finally:
        bot.answer_callback_query(call.id)


# ---------- اجرا ----------

def selftest():
    """تست زنده بدون polling: توکن، اتصال تلگرام و همهٔ اپراتورها."""
    setup_logging()
    me = bot.get_me()
    print(f"ربات: @{me.username} (id {me.id})")
    print(f"مینی‌اپ: {MINI_APP_URL}\n")
    print(f"{'اپراتور':<12} {'تعداد':>6}  {'منبع':<9} آی‌پی‌ها")
    print("-" * 60)
    for key in IRCF_DOMAINS:
        ips, src = fetch_clean_ips(key)
        print(f"{key:<12} {len(ips):>6}  {src:<9} {', '.join(ips) if ips else '—'}")
    return 0


def run_polling():
    setup_logging()
    lock = acquire_lock()
    log.info("ربات بالا آمد؛ شروع polling")

    stop = {"flag": False}

    def _bye(signum, frame):
        stop["flag"] = True
        log.info("سیگنال %s: توقف تمیز", signum)

    signal.signal(signal.SIGTERM, _bye)
    signal.signal(signal.SIGINT, _bye)

    delay = 5
    while not stop["flag"]:
        try:
            bot.polling(
                non_stop=True,
                none_stop=True,
                timeout=60,
                long_polling_timeout=60,
                allowed_updates=["message", "callback_query"],
            )
            delay = 5
        except Exception as e:
            log.warning("خطای polling (%s)؛ تلاش مجدد در %s ثانیه", e, delay)
            time.sleep(delay)
            delay = min(delay * 2, 60)
    log.info("ربات متوقف شد")
    if lock:
        lock.close()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    run_polling()
