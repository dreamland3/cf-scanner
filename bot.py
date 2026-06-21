import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import socket
import os

# ۱. خواندن توکن به صورت کاملاً امن از متغیرهای محیطی سرور
BOT_TOKEN = os.getenv("BOT_TOKEN")
MINI_APP_URL = "https://dreamland3.github.io/cf-scanner/"

if not BOT_TOKEN:
    raise ValueError("خطا: توکن ربات در سرور تنظیم نشده است!")

bot = telebot.TeleBot(BOT_TOKEN)

# ۲. لیست کامل دامنه‌های اختصاصی IRCf
IRCF_DOMAINS = {
    "public": "cf.ircf.space",     # عمومی
    "mci": "mci.ircf.space",       # همراه اول
    "mtn": "mtn.ircf.space",       # ایرانسل
    "tci": "tci.ircf.space",       # مخابرات
    "mbt": "mbt.ircf.space",       # مبین‌نت
    "rtl": "rtl.ircf.space",       # رایتل
    "pishgaman": "pishgaman.ircf.space", # پیشگامان
    "shatel": "shatel.ircf.space"   # شاتل
}

PROVIDER_NAMES = {
    "public": "عمومی (همه اپراتورها)",
    "mci": "همراه اول",
    "mtn": "ایرانسل",
    "tci": "مخابرات",
    "mbt": "مبین‌نت",
    "rtl": "رایتل",
    "pishgaman": "پیشگامان",
    "shatel": "شاتل"
}

def fetch_clean_ips(provider_key):
    domain = IRCF_DOMAINS.get(provider_key)
    if not domain:
        return []
    ips = []
    for _ in range(3):
        try:
            addr_info = socket.getaddrinfo(domain, 80, proto=socket.IPPROTO_TCP)
            for item in addr_info:
                ip = item[4][0]
                if ":" not in ip and ip not in ips:
                    ips.append(ip)
        except Exception:
            pass
    return ips[:5]

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 به ربات اسکنر هوشمند کلودفلر خوش آمدید!\n\n"
        "لطفاً با توجه به وضعیت اتصال خود، یکی از روش‌های زیر را انتخاب کنید:\n\n"
        "🚀 **روش اول (اسکن زنده):** مخصوص افرادی که فیلترشکن گوشی‌شان خاموش است و فقط با پروکسی داخلی تلگرام (MTProto) آنلاین هستند.\n\n"
        "📊 **روش دوم (لیست آماده):** مخصوص افرادی که فیلترشکن (VPN) کل سیستم‌شان روشن است."
    )
    markup = InlineKeyboardMarkup(row_width=1)
    webapp_btn = InlineKeyboardButton(text="🚀 اسکن زنده (مخصوص پروکسی تلگرام)", web_app=WebAppInfo(url=MINI_APP_URL))
    ready_btn = InlineKeyboardButton(text="📊 لیست آماده اپراتورها (مخصوص فیلترشکن)", callback_data="show_providers")
    markup.add(webapp_btn, ready_btn)
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "show_providers")
def show_providers(call):
    markup = InlineKeyboardMarkup(row_width=2)
    btn_public = InlineKeyboardButton("🌍 عمومی (Public)", callback_data="get_public")
    btn_mci = InlineKeyboardButton("همراه اول (MCI)", callback_data="get_mci")
    btn_mtn = InlineKeyboardButton("ایرانسل (MTN)", callback_data="get_mtn")
    btn_rtl = InlineKeyboardButton("رایتل (RTL)", callback_data="get_rtl")
    btn_tci = InlineKeyboardButton("مخابرات (TCI)", callback_data="get_tci")
    btn_shatel = InlineKeyboardButton("شاتل (Shatel)", callback_data="get_shatel")
    btn_pishgaman = InlineKeyboardButton("پیشگامان", callback_data="get_pishgaman")
    btn_mbt = InlineKeyboardButton("مبین‌نت (MBT)", callback_data="get_mbt")
    btn_back = InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")
    
    markup.add(btn_public)
    markup.add(btn_mci, btn_mtn)
    markup.add(btn_rtl, btn_tci)
    markup.add(btn_shatel, btn_pishgaman)
    markup.add(btn_mbt)
    markup.add(btn_back)
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="👇 اپراتور خود را انتخاب کنید تا آخرین آی‌پی‌های تمیز استخراج شوند:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("get_"))
def send_ips(call):
    provider = call.data.split("_")[1]
    name = PROVIDER_NAMES.get(provider, provider)
    bot.answer_callback_query(call.id, text="در حال استخراج دیتای زنده...")
    
    ips = fetch_clean_ips(provider)
    if ips:
        ip_text = f"✅ **آی‌پی‌های تمیز و زنده مخصوص [{name}]:**\n\n"
        for ip in ips:
            ip_text += f"`{ip}`\n"
        ip_text += "\n📌 برای کپی، روی آی‌پی ضربه بزنید."
    else:
        ip_text = f"❌ در حال حاضر دامنه‌ی اختصاصی [{name}] پاسخی نداد. این مشکل موقتی و از سمت سرور پروژه است. لطفاً از سایر اپراتورها استفاده کنید."
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 بازگشت به لیست اپراتورها", callback_data="show_providers"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=ip_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    markup = InlineKeyboardMarkup(row_width=1)
    webapp_btn = InlineKeyboardButton(text="🚀 اسکن زنده (مخصوص پروکسی تلگرام)", web_app=WebAppInfo(url=MINI_APP_URL))
    ready_btn = InlineKeyboardButton(text="📊 لیست آماده اپراتورها (مخصوص فیلترشکن)", callback_data="show_providers")
    markup.add(webapp_btn, ready_btn)
    welcome_text = (
        "👋 به ربات اسکنر هوشمند کلودفلر خوش آمدید!\n\n"
        "لطفاً با توجه به وضعیت اتصال خود، یکی از روش‌های زیر را انتخاب کنید:"
    )
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=welcome_text, reply_markup=markup)

if __name__ == "__main__":
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
