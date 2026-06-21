import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import requests

# 1. تنظیم توکن ربات و لینک مینی‌آپ شما
BOT_TOKEN = "8964001385:AAEO_o4gjhSTEjTZ-BtWNHs_dNCCoQDfr-I"
MINI_APP_URL = "https://dreamland3.github.io/cf-scanner/"

bot = telebot.TeleBot(BOT_TOKEN)

# 2. آدرس مخازن پروژه IRCf برای دریافت آی‌پی‌های تمیز روزانه
IRCF_ENDPOINTS = {
    "mci": "https://raw.githubusercontent.com/ircfspace/cf2dns/master/list/mci.html",
    "mtn": "https://raw.githubusercontent.com/ircfspace/cf2dns/master/list/mtn.html",
    "tci": "https://raw.githubusercontent.com/ircfspace/cf2dns/master/list/tci.html",
    "mbt": "https://raw.githubusercontent.com/ircfspace/cf2dns/master/list/mbt.html"
}

def fetch_clean_ips(provider_key):
    """دریافت ۵ آی‌پی تمیز آخر برای هر اپراتور"""
    try:
        url = IRCF_ENDPOINTS.get(provider_key)
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            ips = [line.strip() for line in response.text.split('\n') if line.strip()][:5]
            return ips
    except Exception:
        pass
    return []

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

# 4. منوی انتخاب اپراتورها
@bot.callback_query_handler(func=lambda call: call.data == "show_providers")
def show_providers(call):
    markup = InlineKeyboardMarkup(row_width=2)
    btn_mci = InlineKeyboardButton("همراه اول (MCI)", callback_data="get_mci")
    btn_mtn = InlineKeyboardButton("ایرانسل (MTN)", callback_data="get_mtn")
    btn_tci = InlineKeyboardButton("مخابرات (TCI)", callback_data="get_tci")
    btn_mbt = InlineKeyboardButton("مبین‌نت (MBT)", callback_data="get_mbt")
    btn_back = InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")
    markup.add(btn_mci, btn_mtn, btn_tci, btn_mbt)
    markup.add(btn_back)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="👇 اپراتور خود را انتخاب کنید:", reply_markup=markup)

# 5. پردازش و نمایش آی‌پی‌های تمیز اپراتور انتخاب شده
@bot.callback_query_handler(func=lambda call: call.data.startswith("get_"))
def send_ips(call):
    provider = call.data.split("_")[1]
    provider_names = {"mci": "همراه اول", "mtn": "ایرانسل", "tci": "مخابرات", "mbt": "مبین‌نت"}
    bot.answer_callback_query(call.id, text="در حال دریافت اطلاعات...")
    ips = fetch_clean_ips(provider)
    if ips:
        ip_text = f"✅ **آی‌پی‌های تمیز مخصوص [{provider_names[provider]}]:**\n\n"
        for ip in ips:
            ip_text += f"`{ip}`\n"
        ip_text += "\n📌 برای کپی، روی آی‌پی ضربه بزنید."
    else:
        ip_text = "❌ خطا در دریافت اطلاعات. لطفا دوباره تلاش کنید."
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

# 7. اجرای ربات با مدیریت تایم‌اوت‌های شبکه جهت پایداری بالا در سرور
if __name__ == "__main__":
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
