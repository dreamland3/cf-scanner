import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import socket

# 1. تنظیم توکن ربات و لینک مینی‌آپ شما
BOT_TOKEN = "8964001385:AAEO_o4gjhSTEjTZ-BtWNHs_dNCCoQDfr-I"
MINI_APP_URL = "https://dreamland3.github.io/cf-scanner/"

bot = telebot.TeleBot(BOT_TOKEN)

# 2. لیست کامل دامنه‌های اختصاصی IRCf (اضافه شدن اپراتورهای جدید و عمومی)
IRCF_DOMAINS = {
    "public": "cf.ircf.space",     # عمومی
    "mci": "mci.ircf.space",       # همراه اول
    "mtn": "mtn.ircf.space",       # ایرانسل
    "tci": "tci.ircf.space",       # مخابرات
    "mbt": "mbt.ircf.space",       # مبین‌نت
    "rtl": "rtl.ircf.space",       # رایتل
    "pishgaman": "pishgaman.ircf.space", # پیشگامان (آسیاتک/های‌وب معمولا روی این یا عمومی اشتراکی هستند)
    "shatel": "shatel.ircf.space"   # شاتل
}

# نام‌های فارسی برای نمایش در پیام‌ها
PROVIDER_NAMES = {
    "public": "عمومی (همه اپراتورها)",
    "mci": "همراه اول",
    "mtn": "ایرانسل",
    "tci": "مخابرات",
    "mbt": "مبین‌نت",
    "rtl": "رایتل",
    "pishgaman": "آسیاتک / های‌وب",
    "shatel": "شاتل"
}

def fetch_clean_ips(provider_key):
    """استخراج چرخشی آی‌پی‌های تمیز از طریق DNS Resolution جهت دریافت لیست چندتایی"""
    domain = IRCF_DOMAINS.get(provider_key)
    if not domain:
        return []
        
    ips = []
    # ۳ بار تلاش برای گرفتن آی‌پی‌های چرخشی مختلف پشت دامنه
    for _ in range(3):
        try:
            addr_info = socket.getaddrinfo(domain, 80, proto=socket.IPPROTO_TCP)
            for item in addr_info:
                ip = item[4][0]
                # فقط IPv4 و بدون تکراری
                if ":" not in ip and ip not in ips:
                    ips.append(ip)
        except Exception:
            pass
            
    return ips[:5] # برگشت حداکثر ۵ آی‌پی تمیز

# 3. هندلر دستور استارت و منوی اصلی ترکیبی
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

# 4. منوی انتخاب اپراتورها (چیدمان منظم جدید)
@bot.callback_query_handler(func=lambda call: call.data == "show_providers")
def show_providers(call):
    markup = InlineKeyboardMarkup(row_width=2)
    
    # دکمه عمومی در بالاترین بخش قرار می‌گیرد
    btn_public = InlineKeyboardButton("🌍 عمومی (Public)", callback_data="get_public")
    
    btn_mci = InlineKeyboardButton("همراه اول (MCI)", callback_data="get_mci")
    btn_mtn = InlineKeyboardButton("ایرانسل (MTN)", callback_data="get_mtn")
    btn_rtl = InlineKeyboardButton("رایتل (RTL)", callback_data="get_rtl")
    btn_tci = InlineKeyboardButton("مخابرات (TCI)", callback_data="get_tci")
    
    btn_shatel = InlineKeyboardButton("شاتل (Shatel)", callback_data="get_shatel")
    btn_pishgaman = InlineKeyboardButton("آسیاتک / های‌وب", callback_data="get_pishgaman")
    btn_mbt = InlineKeyboardButton("مبین‌نت (MBT)", callback_data="get_mbt")
    
    btn_back = InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")
    
    # چیدمان دکمه‌ها
    markup.add(btn_public) # ردیف اول اختصاصی عمومی
    markup.add(btn_mci, btn_mtn)
    markup.add(btn_rtl, btn_tci)
    markup.add(btn_shatel, btn_pishgaman)
    markup.add(btn_mbt)
    markup.add(btn_back)
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="👇 اپراتور خود را انتخاب کنید تا آخرین آی‌پی‌های تمیز استخراج شوند:", reply_markup=markup)

# 5. پردازش و نمایش آی‌پی‌های تمیز اپراتور انتخاب شده
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
        ip_text = f"❌ در حال حاضر دامنه‌ی اختصاصی [{name}] پاسخی نداد. این مشکل موقتی و از سمت سرور پروژه است. لطفاً از گزینه‌ی «عمومی» یا سایر اپراتورها استفاده کنید."
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 بازگشت به لیست اپراتورها", callback_data="show_providers"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=ip_text, reply_markup=markup, parse_mode="Markdown")

# 6. بازگشت به منوی اصلی ربات
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

# 7. اجرای ربات
if __name__ == "__main__":
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
