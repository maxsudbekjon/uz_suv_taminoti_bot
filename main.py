import os
import json
from datetime import datetime, time
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)
from dotenv import load_dotenv

# .env faylidan o'qish
load_dotenv()
# Bot tokeni
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin usernamelari
ADMINS = os.getenv("ADMINS").split(",") 

# Conversation states - Istemolchilar uchun
VILOYAT, TUMAN, KVARTALI_TYPE, KVARTALI_NAME, MANZIL, RASM = range(6)

# Admin states
ADMIN_MENU, ADMIN_FILTER_VILOYAT, ADMIN_FILTER_TUMAN, ADMIN_SEARCH_UY = range(6, 10)

# Ma'lumotlar fayli
DATA_FILE = "consumers_data.json"
SETTINGS_FILE = "bot_settings.json"

# Viloyatlar va tumanlar
VILOYATLAR = {
    "Toshkent shahri": ["Bektemir", "Chilonzor", "Mirobod", "Olmazor", "Sergeli", "Shayxontohur", "Uchtepa", "Yunusobod", "Yakkasaroy", "Yashnobod", "M.Ulug'bek"],
    "Toshkent viloyati": ["Angren", "Bekobod", "Bo'ka", "Bo'stonliq", "Chinoz", "Qibray", "Ohangaron", "Olmaliq", "Oqqo'rg'on", "Parkent", "Piskent", "Yangiyo'l"],
    "Andijon": ["Andijon shahri", "Asaka", "Baliqchi", "Bo'z", "Buloqboshi", "Xo'jaobod", "Izboskan", "Jalaquduq", "Marxamat", "Oltinko'l", "Paxtaobod", "Qo'rg'ontepa", "Shahrixon", "Ulug'nor"],
    "Farg'ona": ["Farg'ona shahri", "Beshariq", "Bog'dod", "Buvayda", "Dang'ara", "Farg'ona", "Furqat", "Qo'qon", "Marg'ilon", "O'zbekiston", "Quva", "Rishton", "So'x", "Toshloq", "Uchko'prik", "Yozyovon"],
    "Namangan": ["Namangan shahri", "Chortoq", "Chust", "Kosonsoy", "Mingbuloq", "Namangan", "Norin", "Pop", "To'raqo'rg'on", "Uchqo'rg'on", "Uychi", "Yangiqo'rg'on"],
    "Samarqand": ["Samarqand shahri", "Bulung'ur", "Ishtixon", "Jomboy", "Kattaqo'rg'on", "Narpay", "Nurobod", "Oqdaryo", "Payariq", "Pastdarg'om", "Paxtachi", "Qo'shrabot", "Samarqand", "Toyloq", "Urgut"],
    "Buxoro": ["Buxoro shahri", "Olot", "G'ijduvon", "Jondor", "Kogon", "Buxoro", "Peshku", "Qorako'l", "Qorovulbozor", "Romitan", "Shofirkon", "Vobkent"],
    "Qashqadaryo": ["Qarshi shahri", "Chiroqchi", "Dehqonobod", "G'uzor", "Kasbi", "Kitob", "Koson", "Mirishkor", "Muborak", "Nishon", "Qamashi", "Qarshi", "Shahrisabz", "Yakkabog'"],
    "Surxondaryo": ["Termiz shahri", "Angor", "Boysun", "Denov", "Jarqo'rg'on", "Muzrabot", "Oltinsoy", "Qiziriq", "Qumqo'rg'on", "Sariosiyo", "Sherobod", "Sho'rchi", "Termiz", "Uzun"],
    "Xorazm": ["Urganch shahri", "Bog'ot", "Gurlan", "Xonqa", "Xazorasp", "Xiva", "Qo'shko'pir", "Shovot", "Urganch", "Yangiariq", "Yangibozor"],
    "Navoiy": ["Navoiy shahri", "Karmana", "Konimex", "Navbahor", "Navoiy", "Nurota", "Tomdi", "Uchquduq", "Xatirchi", "Zarafshon"],
    "Jizzax": ["Jizzax shahri", "Arnasoy", "Baxmal", "Do'stlik", "Forish", "G'allaorol", "Jizzax", "Mirzacho'l", "Paxtakor", "Yangiobod", "Zafarobod", "Zarbdor", "Zomin"],
    "Sirdaryo": ["Guliston shahri", "Boyovut", "Guliston", "Mirzaobod", "Oqoltin", "Sardoba", "Sayxunobod", "Sirdaryo", "Xovos"],
    "Qoraqalpog'iston": ["Nukus shahri", "Amudaryo", "Beruniy", "Chimboy", "Ellikqal'a", "Kegeyli", "Mo'ynoq", "Nukus", "Qonliko'l", "Qorao'zak", "Qo'ng'irot", "Shumanay", "Taxtako'pir", "To'rtko'l", "Xo'jayli"]
}

def load_data():
    """Ma'lumotlarni yuklash (bo'sh yoki buzilgan JSONni qayta tiklash bilan)"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            text = f.read()
            if not text.strip():
                return {}
            return json.loads(text)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        # Agar fayl bo'sh yoki buzilgan bo'lsa, uni qayta yaratamiz
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return {}

def save_data(data):
    """Ma'lumotlarni saqlash"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_settings():
    """Sozlamalarni yuklash (bo'sh yoki buzilgan JSONni qayta tiklash bilan)"""
    default = {"reminder_time": "18:00", "reminder_enabled": False}
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            text = f.read()
            if not text.strip():
                return default
            return json.loads(text)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        # Agar fayl buzilgan bo'lsa, uni default bilan qayta yozamiz
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return default

def save_settings(settings):
    """Sozlamalarni saqlash"""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def is_admin(username):
    """Adminlikni tekshirish"""
    return username in ADMINS

# ==== O'zgartirilgan klaviaturalar: doimiy pastki menyu qo'shiladi ====
def main_menu_keyboard():
    """Doimiy pastki menyu (har doim pastda ko'rinadi)"""
    return ReplyKeyboardMarkup([["📂 Mening ma'lumotlarim"]], resize_keyboard=True, one_time_keyboard=False)

def create_viloyat_keyboard():
    """Viloyatlar klaviaturasi (oxirgi qatorda doimiy menyu)"""
    viloyatlar = list(VILOYATLAR.keys())
    keyboard = []
    for i in range(0, len(viloyatlar), 2):
        row = viloyatlar[i:i+2]
        keyboard.append(row)
    # Pastki qatorda doimiy menyuni qo'shamiz — foydalanuchi har doim ko'radi
    keyboard.append(["📂 Mening ma'lumotlarim"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_tuman_keyboard(viloyat):
    """Tumanlar klaviaturasi (oxirgi qatorda doimiy menyu)"""
    tumanlar = VILOYATLAR.get(viloyat, [])
    keyboard = []
    for i in range(0, len(tumanlar), 2):
        row = tumanlar[i:i+2]
        keyboard.append(row)
    keyboard.append(["📂 Mening ma'lumotlarim"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def _store_bot_message(msg, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['last_bot_message'] = {'chat_id': msg.chat_id, 'message_id': msg.message_id}
    except Exception:
        context.user_data.pop('last_bot_message', None)

async def _delete_last_bot_message(context: ContextTypes.DEFAULT_TYPE):
    info = context.user_data.get('last_bot_message')
    if not info:
        return
    try:
        await context.bot.delete_message(chat_id=info['chat_id'], message_id=info['message_id'])
    except Exception:
        pass
    context.user_data.pop('last_bot_message', None)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botni boshlash — doimiy pastki menyu ko'rsatiladi"""
    user = update.effective_user
    
    # Admin uchun maxsus menyu
    if is_admin(user.username):
        keyboard = [
            ["📊 Barcha ma'lumotlar", "🔍 Filter: Viloyat"],
            ["🏘 Filter: Tuman", "🏠 Qidirish: Uy raqami"],
            ["📝 Ma'lumot yuborish", "⏰ Eslatma sozlash"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"👋 Assalomu alaykum, {user.first_name}!\n\n"
            "🔐 Admin panelga xush kelibsiz.\n"
            "Quyidagi bo'limlardan birini tanlang:",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    # Oddiy istemolchi uchun — doimiy pastki menyu ko'rsatiladi
    reply_markup = main_menu_keyboard()
    await update.message.reply_text(
        f"👋 Assalomu alaykum, {user.first_name}!\n\n"
        "O'zingizning oldingi ma'lumotlaringizni ko'rish uchun '📂 Mening ma'lumotlarim' tugmasini bosing.",
        reply_markup=reply_markup
    )
    # Menyuda yuborilgan xabarni o'chirishga hojat yo'q — doimiy menyu doimo qoladi
    return ConversationHandler.END

async def start_fill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi '📝 Ma'lumot yuborish' tugmasini bossin — viloyat so'raladi"""
    # agar oldingi bot xabari saqlangan bo'lsa, o'chiramiz (konversatsiya ichida eski promptlarni tozalash uchun)
    await _delete_last_bot_message(context)

    msg = await update.message.reply_text(
        "📋 Ma'lumot to'ldirish uchun viloyatingizni tanlang:",
        reply_markup=create_viloyat_keyboard()
    )
    await _store_bot_message(msg, context)
    return VILOYAT

async def get_viloyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Viloyatni olish"""
    await _delete_last_bot_message(context)
    viloyat = update.message.text
    
    if viloyat not in VILOYATLAR:
        await update.message.reply_text(
            "❌ Iltimos, ro'yxatdan viloyat tanlang!",
            reply_markup=create_viloyat_keyboard()
        )
        return VILOYAT
    
    context.user_data['viloyat'] = viloyat
    
    msg = await update.message.reply_text(
        "📍 Tumaningizni tanlang:",
        reply_markup=create_tuman_keyboard(viloyat)
    )
    await _store_bot_message(msg, context)
    return TUMAN

async def get_tuman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tumanni olish"""
    await _delete_last_bot_message(context)
    tuman = update.message.text
    viloyat = context.user_data.get('viloyat')
    
    if tuman not in VILOYATLAR.get(viloyat, []):
        await update.message.reply_text(
            "❌ Iltimos, ro'yxatdan tuman tanlang!",
            reply_markup=create_tuman_keyboard(viloyat)
        )
        return TUMAN
    
    context.user_data['tuman'] = tuman
    
    keyboard = [["Kvartal", "Mahalla"], ["📝 Ma'lumot yuborish", "📂 Mening ma'lumotlarim"]]
    msg = await update.message.reply_text(
        "🏘 Kvartal yoki mahallada yashayszmi?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    await _store_bot_message(msg, context)
    return KVARTALI_TYPE

async def get_kvartali_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kvartal yoki mahalla turini olish"""
    await _delete_last_bot_message(context)
    kvartali_type = update.message.text
    
    if kvartali_type not in ["Kvartal", "Mahalla"]:
        keyboard = [["Kvartal", "Mahalla"], ["📝 Ma'lumot yuborish", "📂 Mening ma'lumotlarim"]]
        await update.message.reply_text(
            "❌ Iltimos, Kvartal yoki Mahalla tanlang!",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return KVARTALI_TYPE
    
    context.user_data['kvartali_type'] = kvartali_type
    
    msg = await update.message.reply_text(
        f"✍️ {kvartali_type} nomini kiriting:",
        reply_markup=main_menu_keyboard()
    )
    await _store_bot_message(msg, context)
    return KVARTALI_NAME

async def get_kvartali_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kvartal yoki mahalla nomini olish"""
    await _delete_last_bot_message(context)
    context.user_data['kvartali_name'] = update.message.text
    
    msg = await update.message.reply_text(
        "🏠 Uy manzilini kiriting:\n"
        "(Masalan: 12-uy, 5-kvartira)",
        reply_markup=main_menu_keyboard()
    )
    await _store_bot_message(msg, context)
    return MANZIL

async def get_manzil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manzilni olish"""
    await _delete_last_bot_message(context)
    context.user_data['manzil'] = update.message.text
    
    msg = await update.message.reply_text(
        "📸 Issiq suv hisoblagichining rasmini yuboring:",
        reply_markup=main_menu_keyboard()
    )
    await _store_bot_message(msg, context)
    return RASM

async def get_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rasmni olish va ma'lumotlarni saqlash"""
    await _delete_last_bot_message(context)
    if not update.message.photo:
        msg = await update.message.reply_text(
            "❌ Iltimos, rasm yuboring!",
            reply_markup=main_menu_keyboard()
        )
        await _store_bot_message(msg, context)
        return RASM
    
    photo = update.message.photo[-1]
    context.user_data['photo_id'] = photo.file_id
    
    # Ma'lumotlarni saqlash
    data = load_data()
    user = update.effective_user
    
    viloyat = context.user_data['viloyat']
    tuman = context.user_data['tuman']
    
    # Struktura yaratish
    if viloyat not in data:
        data[viloyat] = {}
    if tuman not in data[viloyat]:
        data[viloyat][tuman] = []
    
    # Yangi ma'lumot
    entry = {
        'user_id': str(user.id),
        'username': user.username or "Mavjud emas",
        'first_name': user.first_name,
        'kvartali_type': context.user_data['kvartali_type'],
        'kvartali_name': context.user_data['kvartali_name'],
        'manzil': context.user_data['manzil'],
        'photo_id': context.user_data['photo_id'],
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    data[viloyat][tuman].append(entry)
    save_data(data)
    
    # Keyingi to'ldirish vaqtini olish
    settings = load_settings()
    reminder_time = settings.get('reminder_time', '18:00')
    
    # Tasdiqlash xabari
    success_message = (
        "✅ <b>Ma'lumotlar muvaffaqiyatli saqlandi!</b>\n\n"
        "📋 <b>Sizning ma'lumotlaringiz:</b>\n"
        f"📍 Viloyat: <b>{viloyat}</b>\n"
        f"🏘 Tuman: <b>{tuman}</b>\n"
        f"🏘 {context.user_data['kvartali_type']}: <b>{context.user_data['kvartali_name']}</b>\n"
        f"🏠 Manzil: <b>{context.user_data['manzil']}</b>\n"
        f"📅 Sana: <b>{entry['date']}</b>\n\n"
        f"⏰ <b>Keyingi to'ldirish vaqti: {reminder_time}</b>\n\n"
        "Rahmat! 🙏"
    )
    
    await update.message.reply_text(
        success_message,
        parse_mode='HTML',
        reply_markup=main_menu_keyboard()
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def show_all_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha ma'lumotlarni ko'rsatish (Admin)"""
    user = update.effective_user
    
    if not is_admin(user.username):
        await update.message.reply_text("❌ Sizda bu funksiyadan foydalanish huquqi yo'q!")
        return
    
    data = load_data()
    
    if not data:
        await update.message.reply_text("📭 Hozircha ma'lumotlar yo'q!")
        return
    
    total_count = 0
    for viloyat_data in data.values():
        for tuman_data in viloyat_data.values():
            total_count += len(tuman_data)
    
    await update.message.reply_text(
        f"📊 <b>Umumiy statistika:</b>\n\n"
        f"📝 Jami ma'lumotlar: <b>{total_count} ta</b>\n"
        f"📍 Viloyatlar soni: <b>{len(data)} ta</b>\n\n"
        f"Ma'lumotlar yuborilmoqda...",
        parse_mode='HTML',
        reply_markup=admin_menu_keyboard()
    )
    
    for viloyat, viloyat_data in data.items():
        for tuman, entries in viloyat_data.items():
            header = f"📍 <b>{viloyat} - {tuman}</b>\n📊 Jami: {len(entries)} ta\n" + "─" * 30
            await update.message.reply_text(header, parse_mode='HTML')
            
            for i, entry in enumerate(entries, 1):
                caption = (
                    f"#{i}\n"
                    f"👤 Ism: <b>{entry['first_name']}</b>\n"
                    f"🏘 {entry['kvartali_type']}: <b>{entry['kvartali_name']}</b>\n"
                    f"🏠 Manzil: <b>{entry['manzil']}</b>\n"
                    f"📅 Sana: <b>{entry['date']}</b>\n"
                    f"👤 Username: @{entry['username']}"
                )
                
                await update.message.reply_photo(
                    photo=entry['photo_id'],
                    caption=caption,
                    parse_mode='HTML'
                )
async def fill_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reminderdagi 'Ma'lumot to'ldirish' tugmasi bosilganda conversationni boshlash"""
    query = update.callback_query
    await query.answer()
    # Foydalanuvchiga yuborilgan reminder xabarini o'chirish
    try:
        await query.message.delete()
    except Exception:
        pass
    # Conversation boshlash uchun viloyat so'raymiz
    msg = await context.bot.send_message(
        chat_id=query.from_user.id,
        text="📋 Ma'lumot to'ldirish uchun viloyatingizni tanlang:",
        reply_markup=create_viloyat_keyboard()
    )
    await _store_bot_message(msg, context)
    return VILOYAT

async def my_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi o'z yuborgan ma'lumotlarini ko'radi"""
    user = update.effective_user
    data = load_data()
    user_entries = []
    for viloyat, vil_data in data.items():
        for tuman, entries in vil_data.items():
            for entry in entries:
                if str(user.id) == entry.get('user_id'):
                    user_entries.append((viloyat, tuman, entry))
    if not user_entries:
        await update.message.reply_text("📭 Sizda saqlangan ma'lumotlar topilmadi.", reply_markup=main_menu_keyboard())
        return
    await update.message.reply_text(f"📋 Sizning ma'lumotlaringiz: {len(user_entries)} ta\n\nMa'lumotlar yuborilmoqda...", reply_markup=main_menu_keyboard())
    for i, (vil, tum, entry) in enumerate(user_entries, 1):
        caption = (
            f"#{i}\n"
            f"📍 <b>{vil} - {tum}</b>\n"
            f"👤 Ism: <b>{entry['first_name']}</b>\n"
            f"🏘 {entry['kvartali_type']}: <b>{entry['kvartali_name']}</b>\n"
            f"🏠 Manzil: <b>{entry['manzil']}</b>\n"
            f"📅 Sana: <b>{entry['date']}</b>\n"
            f"👤 Username: @{entry['username']}"
        )
        try:
            await update.message.reply_photo(photo=entry['photo_id'], caption=caption, parse_mode='HTML')
        except Exception:
            await update.message.reply_text(caption, parse_mode='HTML')

async def filter_by_viloyat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Viloyat bo'yicha filtrlash boshlash"""
    user = update.effective_user
    
    if not is_admin(user.username):
        await update.message.reply_text("❌ Sizda bu funksiyadan foydalanish huquqi yo'q!")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔍 Viloyatni tanlang:",
        reply_markup=create_viloyat_keyboard()
    )
    return ADMIN_FILTER_VILOYAT

async def filter_by_viloyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Viloyat bo'yicha filtrlash"""
    viloyat = update.message.text
    
    if viloyat not in VILOYATLAR:
        await update.message.reply_text(
            "❌ Iltimos, ro'yxatdan viloyat tanlang!",
            reply_markup=create_viloyat_keyboard()
        )
        return ADMIN_FILTER_VILOYAT
    
    data = load_data()
    
    if viloyat not in data:
        await update.message.reply_text(
            f"📭 {viloyat} uchun ma'lumotlar topilmadi!",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    total = sum(len(entries) for entries in data[viloyat].values())
    
    await update.message.reply_text(
        f"📍 <b>{viloyat}</b>\n"
        f"📊 Jami: <b>{total} ta</b> ma'lumot\n\n"
        f"Ma'lumotlar yuborilmoqda...",
        parse_mode='HTML',
        reply_markup=admin_menu_keyboard()
    )
    
    for tuman, entries in data[viloyat].items():
        header = f"🏘 <b>{tuman}</b>\n📊 Soni: {len(entries)} ta\n" + "─" * 30
        await update.message.reply_text(header, parse_mode='HTML')
        
        for i, entry in enumerate(entries, 1):
            caption = (
                f"#{i}\n"
                f"👤 Ism: <b>{entry['first_name']}</b>\n"
                f"🏘 {entry['kvartali_type']}: <b>{entry['kvartali_name']}</b>\n"
                f"🏠 Manzil: <b>{entry['manzil']}</b>\n"
                f"📅 Sana: <b>{entry['date']}</b>\n"
                f"👤 Username: @{entry['username']}"
            )
            
            await update.message.reply_photo(
                photo=entry['photo_id'],
                caption=caption,
                parse_mode='HTML'
            )
    
    return ConversationHandler.END

async def filter_by_tuman_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tuman bo'yicha filtrlash boshlash"""
    user = update.effective_user
    
    if not is_admin(user.username):
        await update.message.reply_text("❌ Sizda bu funksiyadan foydalanish huquqi yo'q!")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔍 Avval viloyatni tanlang:",
        reply_markup=create_viloyat_keyboard()
    )
    context.user_data['admin_action'] = 'filter_tuman'
    return ADMIN_FILTER_VILOYAT

async def filter_tuman_get_viloyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tuman uchun viloyatni olish"""
    viloyat = update.message.text
    
    if viloyat not in VILOYATLAR:
        await update.message.reply_text(
            "❌ Iltimos, ro'yxatdan viloyat tanlang!",
            reply_markup=create_viloyat_keyboard()
        )
        return ADMIN_FILTER_VILOYAT
    
    context.user_data['filter_viloyat'] = viloyat
    
    await update.message.reply_text(
        "🏘 Tumanni tanlang:",
        reply_markup=create_tuman_keyboard(viloyat)
    )
    return ADMIN_FILTER_TUMAN

async def filter_by_tuman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tuman bo'yicha filtrlash"""
    tuman = update.message.text
    viloyat = context.user_data.get('filter_viloyat')
    
    if not viloyat or tuman not in VILOYATLAR.get(viloyat, []):
        await update.message.reply_text(
            "❌ Iltimos, ro'yxatdan tuman tanlang!",
            reply_markup=create_tuman_keyboard(viloyat)
        )
        return ADMIN_FILTER_TUMAN
    
    data = load_data()
    
    if viloyat not in data or tuman not in data[viloyat]:
        await update.message.reply_text(
            f"📭 {viloyat} - {tuman} uchun ma'lumotlar topilmadi!",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    entries = data[viloyat][tuman]
    
    await update.message.reply_text(
        f"📍 <b>{viloyat} - {tuman}</b>\n"
        f"📊 Jami: <b>{len(entries)} ta</b> ma'lumot\n\n"
        f"Ma'lumotlar yuborilmoqda...",
        parse_mode='HTML',
        reply_markup=admin_menu_keyboard()
    )
    
    for i, entry in enumerate(entries, 1):
        caption = (
            f"#{i}\n"
            f"👤 Ism: <b>{entry['first_name']}</b>\n"
            f"🏘 {entry['kvartali_type']}: <b>{entry['kvartali_name']}</b>\n"
            f"🏠 Manzil: <b>{entry['manzil']}</b>\n"
            f"📅 Sana: <b>{entry['date']}</b>\n"
            f"👤 Username: @{entry['username']}"
        )
        
        await update.message.reply_photo(
            photo=entry['photo_id'],
            caption=caption,
            parse_mode='HTML'
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def search_by_uy_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Uy raqami bo'yicha qidirish boshlash"""
    user = update.effective_user
    
    if not is_admin(user.username):
        await update.message.reply_text("❌ Sizda bu funksiyadan foydalanish huquqi yo'q!")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔍 Uy manzilini kiriting:\n"
        "(Masalan: 12-uy yoki 5-kvartira)",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADMIN_SEARCH_UY

async def search_by_uy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Uy raqami bo'yicha qidirish"""
    search_term = update.message.text.lower()
    data = load_data()
    
    results = []
    
    for viloyat, viloyat_data in data.items():
        for tuman, entries in viloyat_data.items():
            for entry in entries:
                if search_term in entry['manzil'].lower():
                    results.append({
                        'viloyat': viloyat,
                        'tuman': tuman,
                        'entry': entry
                    })
    
    if not results:
        await update.message.reply_text(
            f"❌ '{search_term}' bo'yicha natija topilmadi!"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"🔍 Qidiruv natijalari: <b>{len(results)} ta</b>\n\n"
        f"Ma'lumotlar yuborilmoqda...",
        parse_mode='HTML',
        reply_markup=admin_menu_keyboard()
    )
    
    for i, result in enumerate(results, 1):
        entry = result['entry']
        caption = (
            f"#{i}\n"
            f"📍 <b>{result['viloyat']} - {result['tuman']}</b>\n"
            f"👤 Ism: <b>{entry['first_name']}</b>\n"
            f"🏘 {entry['kvartali_type']}: <b>{entry['kvartali_name']}</b>\n"
            f"🏠 Manzil: <b>{entry['manzil']}</b>\n"
            f"📅 Sana: <b>{entry['date']}</b>\n"
            f"👤 Username: @{entry['username']}"
        )
        
        await update.message.reply_photo(
            photo=entry['photo_id'],
            caption=caption,
            parse_mode='HTML'
        )
    
    return ConversationHandler.END

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Eslatma vaqtini o'rnatish (oylik kun)"""
    user = update.effective_user
    
    if not is_admin(user.username):
        await update.message.reply_text("❌ Sizda bu funksiyadan foydalanish huquqi yo'q!")
        return
    
    # Oyning kunlari uchun klaviatura
    keyboard = []
    row = []
    for i in range(1, 32):
        row.append(InlineKeyboardButton(str(i), callback_data=f"day_{i}"))
        if len(row) == 7:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ O'chirish", callback_data="day_off")])
    
    settings = load_settings()
    current_day = settings.get('reminder_day', 'O\'chirilgan')
    enabled = settings.get('reminder_enabled', False)
    
    status = "✅ Yoniq" if enabled else "❌ O'chiq"
    
    await update.message.reply_text(
        f"⏰ <b>Eslatma sozlamalari</b>\n\n"
        f"Joriy kun: <b>{current_day}-kun</b>\n"
        f"Soat: <b>10:00</b> (default)\n"
        f"Holat: <b>{status}</b>\n\n"
        f"Oyning qaysi kunida eslatma yuborilsin?",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Eslatma vaqtini callback orqali o'rnatish"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "day_off":
        settings = load_settings()
        settings['reminder_enabled'] = False
        save_settings(settings)
        
        # Oldingi jobni o'chirish
        current_jobs = context.job_queue.get_jobs_by_name("daily_reminder")
        for job in current_jobs:
            job.schedule_removal()
        
        await query.edit_message_text(
            "❌ Eslatma o'chirildi!",
            parse_mode='HTML'
        )
        return  
    
    # Vaqtni olish
    reminder_time = query.data.replace("time_", "")
    hour, minute = map(int, reminder_time.split(":"))
    
    # Sozlamalarni saqlash
    settings = load_settings()
    settings['reminder_time'] = reminder_time
    settings['reminder_enabled'] = True
    save_settings(settings)
    
    day = int(query.data.replace("day_", ""))
    
    # Sozlamalarni saqlash
    settings = load_settings()
    settings['reminder_day'] = day
    settings['reminder_enabled'] = True
    save_settings(settings)
    # Oldingi jobni o'chirish
    current_jobs = context.job_queue.get_jobs_by_name("monthly_reminder")
    for job in current_jobs:
        job.schedule_removal()
    
    # Yangi job qo'shish
    context.job_queue.run_monthly(
        send_reminder,
        when=time(hour=10, minute=0),  # Default 10:00
        day=day,
        name="monthly_reminder"
    )
    
    await query.edit_message_text(
        f"✅ <b>Eslatma muvaffaqiyatli o'rnatildi!</b>\n\n"
        f"📅 Har oyning <b>{day}-kuni</b>\n"
        f"⏰ Soat: <b>10:00</b>\n"
        f"Barcha istemolchilarga eslatma yuboriladi.",
        parse_mode='HTML'
    )
def admin_menu_keyboard():
    """Admin uchun doimiy pastki menyu"""
    keyboard = [
        ["📊 Barcha ma'lumotlar", "🔍 Filter: Viloyat"],
        ["🏘 Filter: Tuman", "🏠 Qidirish: Uy raqami"],
        ["📝 Ma'lumot yuborish", "⏰ Eslatma sozlash"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Barcha istemolchilarga eslatma yuborish — inline tugma bilan, tugma bosilganda conversation boshlanadi"""
    data = load_data()
    sent_users = set()
    success_count = 0
    fail_count = 0
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📝 Ma'lumot to'ldirish", callback_data="fill_info")]])

    for viloyat_data in data.values():
        for entries in viloyat_data.values():
            for entry in entries:
                user_id = entry['user_id']
                if user_id not in sent_users:
                    try:
                        await context.bot.send_message(
                            chat_id=int(user_id),
                            text="⏰ <b>Eslatma!</b>\n\n"
                                 "📋 Issiq suv hisoblagichingizning yangi ma'lumotlarini yuborish vaqti keldi.\n\n"
                                 "Ma'lumotlarni yuborish uchun quyidagi tugmani bosing:",
                            parse_mode='HTML',
                            reply_markup=kb
                        )
                        sent_users.add(user_id)
                        success_count += 1
                    except Exception as e:
                        fail_count += 1
                        print(f"❌ Error sending to {user_id}: {e}")
    
    # Adminlarga hisobot
    for admin in ADMINS:
        try:
            await context.bot.send_message(
                chat_id=admin,
                text=f"📊 <b>Eslatma yuborish natijalari:</b>\n\n"
                     f"✅ Muvaffaqiyatli: {success_count} ta\n"
                     f"❌ Xatolik: {fail_count} ta\n"
                     f"📊 Jami: {success_count + fail_count} ta",
                parse_mode='HTML'
            )
        except:
            pass

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bekor qilish"""
    user = update.effective_user
    
    if is_admin(user.username):
        keyboard = [
            ["📊 Barcha ma'lumotlar", "🔍 Filter: Viloyat"],
            ["🏘 Filter: Tuman", "🏠 Qidirish: Uy raqami"],
            ["📝 Ma'lumot yuborish", "⏰ Eslatma sozlash"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    else:
        reply_markup = main_menu_keyboard()
    
    await update.message.reply_text(
        "❌ Bekor qilindi.\n\n"
        "Qayta boshlash uchun /start buyrug'ini yuboring.",
        reply_markup=reply_markup
    )
    context.user_data.clear()
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam buyrug'i"""
    user = update.effective_user
    
    if is_admin(user.username):
        text = (
            "🔐 <b>Admin buyruqlari:</b>\n\n"
            "📊 <b>Barcha ma'lumotlar</b> - Barcha viloyat va tumanlarning ma'lumotlarini ko'rish\n"
            "🔍 <b>Filter: Viloyat</b> - Ma'lum viloyat bo'yicha ma'lumotlarni ko'rish\n"
            "🏘 <b>Filter: Tuman</b> - Ma'lum tuman bo'yicha ma'lumotlarni ko'rish\n"
            "🏠 <b>Qidirish: Uy raqami</b> - Uy raqami bo'yicha qidirish\n"
            "📝 <b>Ma'lumot yuborish</b> - O'zingiz ma'lumot yuborish\n"
            "⏰ <b>Eslatma sozlash</b> - Kunlik eslatma vaqtini belgilash\n\n"
            "❌ <b>/cancel</b> - Jarayonni bekor qilish"
        )
    else:
        text = (
            "📋 <b>Bot haqida ma'lumot:</b>\n\n"
            "Bu bot orqali siz issiq suv hisoblagichingizning ma'lumotlarini yuborishingiz mumkin.\n\n"
            "📝 Boshlash: menyudan '📝 Ma'lumot yuborish' tugmasini bosing yoki reminder dagi tugmani ishlating.\n"
            "❌ <b>/cancel</b> - Bekor qilish\n"
            "❓ <b>/help</b> - Yordam\n\n"
            "Ma'lumot yuborish jarayoni:\n"
            "1️⃣ Viloyatingizni tanlang\n"
            "2️⃣ Tumaningizni tanlang\n"
            "3️⃣ Kvartal yoki mahalla tanlang\n"
            "4️⃣ Kvartal/mahalla nomini kiriting\n"
            "5️⃣ Uy manzilini kiriting\n"
            "6️⃣ Hisoblagich rasmini yuboring\n\n"
            "❗️ Bot sizga belgilangan vaqtda eslatma yuboradi."
        )
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=main_menu_keyboard())

def main():
    """Botni ishga tushirish"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Istemolchilar uchun conversation handler (faqat menu tugmasi yoki reminder tugmasi orqali boshlanadi)
    consumer_conv = ConversationHandler(
        entry_points=[
            # MessageHandler(filters.Regex("^📝 Ma'lumot yuborish$"), start_fill),
            CallbackQueryHandler(fill_info_callback, pattern="^fill_info$")
        ],
        states={
            VILOYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_viloyat)],
            TUMAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tuman)],
            KVARTALI_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_kvartali_type)],
            KVARTALI_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_kvartali_name)],
            MANZIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_manzil)],
            RASM: [MessageHandler(filters.PHOTO, get_rasm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="consumer_conversation",
        persistent=False
    )
    
    # Viloyat filtri uchun conversation handler
    viloyat_filter_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🔍 Filter: Viloyat$"), filter_by_viloyat_start)
        ],
        states={
            ADMIN_FILTER_VILOYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, filter_by_viloyat)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="viloyat_filter"
    )
    
    # Tuman filtri uchun conversation handler
    tuman_filter_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🏘 Filter: Tuman$"), filter_by_tuman_start)
        ],
        states={
            ADMIN_FILTER_VILOYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, filter_tuman_get_viloyat)],
            ADMIN_FILTER_TUMAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, filter_by_tuman)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="tuman_filter"
    )
    
    # Uy raqami qidirish uchun conversation handler
    search_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🏠 Qidirish: Uy raqami$"), search_by_uy_start)
        ],
        states={
            ADMIN_SEARCH_UY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_by_uy)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="search_by_uy"
    )
    
    # Handlerlarni qo'shish
    application.add_handler(consumer_conv)
    application.add_handler(viloyat_filter_conv)
    application.add_handler(tuman_filter_conv)
    application.add_handler(search_conv)
    
    # Buyruq va boshqa handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^📊 Barcha ma'lumotlar$"), show_all_data))
    application.add_handler(MessageHandler(filters.Regex("^⏰ Eslatma sozlash$"), set_reminder))
    application.add_handler(CallbackQueryHandler(set_reminder_callback, pattern="^day_"))
    application.add_handler(CallbackQueryHandler(fill_info_callback, pattern="^fill_info$"))
    application.add_handler(MessageHandler(filters.Regex("^📂 Mening ma'lumotlarim$"), my_data))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Eslatma jobini yuklash
    settings = load_settings()
    if settings.get('reminder_enabled', False):
        try:
            reminder_day = settings.get('reminder_day', 1)
            if application.job_queue:
                application.job_queue.run_monthly(
                    send_reminder,
                    when=time(hour=10, minute=0),  # Default 10:00
                    day=reminder_day,
                    name="monthly_reminder"
                )
                print(f"📅 Har oyning {reminder_day}-kuni soat 10:00 da eslatma yuboriladi")
        except Exception as e:
            print(f"⚠️ Eslatma o'rnatishda xatolik: {e}")
    
    print("✅ Bot ishga tushdi!")
    try:
        bot_username = application.bot.username
    except RuntimeError:
        bot_username = "unknown"
    print(f"📊 Bot username: @{bot_username}")
    print(f"⏰ Eslatma: {'Yoniq' if settings.get('reminder_enabled') else "O'chiq"}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()