import os
import json
from datetime import datetime, time
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)
from dotenv import load_dotenv
import sqlite3
from typing import Dict, Any, List

# .env faylidan o'qish
load_dotenv()
# Bot tokeni
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin usernamelari (trim qiling)
ADMINS = [s.strip() for s in os.getenv("ADMINS", "").split(",") if s.strip()] 

# Conversation states - Istemolchilar uchun
VILOYAT, TUMAN, KVARTALI_TYPE, KVARTALI_NAME, MANZIL, RASM = range(6)

# Admin states
ADMIN_MENU, ADMIN_FILTER_VILOYAT, ADMIN_FILTER_TUMAN, ADMIN_SEARCH_UY = range(6, 10)

# Database fayli
DB_FILE = "data.db"

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

# ==================== DATABASE FUNKSIYALARI ====================

def _get_conn():
    """Database connection yaratish"""
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def _init_db():
    """Jadvallarni yaratish"""
    conn = _get_conn()
    cur = conn.cursor()
    
    # Consumers jadvali
    cur.execute("""
    CREATE TABLE IF NOT EXISTS consumers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        username TEXT,
        first_name TEXT,
        viloyat TEXT NOT NULL,
        tuman TEXT NOT NULL,
        kvartali_type TEXT,
        kvartali_name TEXT,
        manzil TEXT,
        photo_id TEXT,
        date TEXT NOT NULL
    )
    """)
    
    # Settings jadvali
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def load_data() -> Dict[str, Dict[str, List[Dict]]]:
    """
    Barcha ma'lumotlarni nested dict formatida qaytarish
    Format: {viloyat: {tuman: [entry1, entry2, ...]}}
    """
    conn = _get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT user_id, username, first_name, viloyat, tuman, 
               kvartali_type, kvartali_name, manzil, photo_id, date 
        FROM consumers
        ORDER BY viloyat, tuman, date DESC
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    data: Dict[str, Dict[str, List[Dict]]] = {}
    
    for row in rows:
        user_id, username, first_name, viloyat, tuman, kvartali_type, kvartali_name, manzil, photo_id, date = row
        
        entry = {
            'user_id': str(user_id),
            'username': username or "Mavjud emas",
            'first_name': first_name or "Noma'lum",
            'kvartali_type': kvartali_type or "",
            'kvartali_name': kvartali_name or "",
            'manzil': manzil or "",
            'photo_id': photo_id or "",
            'date': date
        }
        
        if viloyat not in data:
            data[viloyat] = {}
        if tuman not in data[viloyat]:
            data[viloyat][tuman] = []
            
        data[viloyat][tuman].append(entry)
    
    return data

def save_consumer_data(user_id: int, username: str, first_name: str, 
                       viloyat: str, tuman: str, kvartali_type: str, 
                       kvartali_name: str, manzil: str, photo_id: str) -> bool:
    """
    Yangi consumer ma'lumotini saqlash
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()
        
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cur.execute("""
            INSERT INTO consumers 
            (user_id, username, first_name, viloyat, tuman, kvartali_type, 
             kvartali_name, manzil, photo_id, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(user_id),
            username,
            first_name,
            viloyat,
            tuman,
            kvartali_type,
            kvartali_name,
            manzil,
            photo_id,
            date
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error saving consumer data: {e}")
        return False

def get_user_data(user_id: int) -> List[Dict]:
    """
    Foydalanuvchining barcha ma'lumotlarini olish
    """
    conn = _get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT user_id, username, first_name, viloyat, tuman, 
               kvartali_type, kvartali_name, manzil, photo_id, date 
        FROM consumers
        WHERE user_id = ?
        ORDER BY date DESC
    """, (str(user_id),))
    
    rows = cur.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        user_id, username, first_name, viloyat, tuman, kvartali_type, kvartali_name, manzil, photo_id, date = row
        result.append({
            'user_id': str(user_id),
            'username': username or "Mavjud emas",
            'first_name': first_name or "Noma'lum",
            'viloyat': viloyat,
            'tuman': tuman,
            'kvartali_type': kvartali_type or "",
            'kvartali_name': kvartali_name or "",
            'manzil': manzil or "",
            'photo_id': photo_id or "",
            'date': date
        })
    
    return result

def get_all_user_ids() -> List[str]:
    """
    Barcha unique user_id larni olish (reminder uchun)
    """
    conn = _get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT DISTINCT user_id FROM consumers")
    rows = cur.fetchall()
    conn.close()
    
    return [row[0] for row in rows]

def search_by_address(search_term: str) -> List[Dict]:
    """
    Manzil bo'yicha qidirish
    """
    conn = _get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT user_id, username, first_name, viloyat, tuman, 
               kvartali_type, kvartali_name, manzil, photo_id, date 
        FROM consumers
        WHERE LOWER(manzil) LIKE ?
        ORDER BY date DESC
    """, (f"%{search_term.lower()}%",))
    
    rows = cur.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        user_id, username, first_name, viloyat, tuman, kvartali_type, kvartali_name, manzil, photo_id, date = row
        results.append({
            'viloyat': viloyat,
            'tuman': tuman,
            'entry': {
                'user_id': str(user_id),
                'username': username or "Mavjud emas",
                'first_name': first_name or "Noma'lum",
                'kvartali_type': kvartali_type or "",
                'kvartali_name': kvartali_name or "",
                'manzil': manzil or "",
                'photo_id': photo_id or "",
                'date': date
            }
        })
    
    return results

def load_settings() -> Dict[str, Any]:
    """Sozlamalarni bazadan olish"""
    defaults = {
        "reminder_time": "10:00",
        "reminder_enabled": False,
        "reminder_day": None
    }
    
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM settings")
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        return defaults
    
    result = defaults.copy()
    for key, value in rows:
        try:
            result[key] = json.loads(value)
        except:
            if value in ("True", "False"):
                result[key] = (value == "True")
            elif value.isdigit():
                result[key] = int(value)
            else:
                result[key] = value
    
    return result

def save_settings(settings: Dict[str, Any]) -> bool:
    """Sozlamalarni bazaga saqlash"""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        
        for key, value in settings.items():
            if isinstance(value, (dict, list)):
                val_str = json.dumps(value, ensure_ascii=False)
            else:
                val_str = str(value)
            
            cur.execute("""
                INSERT INTO settings (key, value) 
                VALUES (?, ?) 
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (key, val_str))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error saving settings: {e}")
        return False

def is_admin(username: str) -> bool:
    """Adminlikni tekshirish"""
    return username in ADMINS

# ==================== KLAVIATURA FUNKSIYALARI ====================

def main_menu_keyboard():
    """Oddiy foydalanuvchi uchun doimiy pastki menyu"""
    return ReplyKeyboardMarkup(
        [["📂 Mening ma'lumotlarim"]], 
        resize_keyboard=True, 
        one_time_keyboard=False
    )

def admin_menu_keyboard():
    """Admin uchun doimiy pastki menyu"""
    keyboard = [
        ["📊 Barcha ma'lumotlar", "📥 Yuklab olish"],
        ["🏠 Qidirish: Uy raqami", "🔍 Filter: Viloyat"],
        ["🏘 Filter: Tuman", "⏰ Eslatma sozlash"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_viloyat_keyboard():
    """Viloyatlar klaviaturasi"""
    viloyatlar = list(VILOYATLAR.keys())
    keyboard = []
    for i in range(0, len(viloyatlar), 2):
        row = viloyatlar[i:i+2]
        keyboard.append(row)
    keyboard.append(["📂 Mening ma'lumotlarim"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_tuman_keyboard(viloyat: str):
    """Tumanlar klaviaturasi"""
    tumanlar = VILOYATLAR.get(viloyat, [])
    keyboard = []
    for i in range(0, len(tumanlar), 2):
        row = tumanlar[i:i+2]
        keyboard.append(row)
    keyboard.append(["📂 Mening ma'lumotlarim"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================== HELPER FUNKSIYALAR ====================

async def _store_bot_message(msg, context: ContextTypes.DEFAULT_TYPE):
    """Bot xabarini saqlash (keyinroq o'chirish uchun)"""
    try:
        context.user_data['last_bot_message'] = {
            'chat_id': msg.chat_id, 
            'message_id': msg.message_id
        }
    except:
        context.user_data.pop('last_bot_message', None)

async def _delete_last_bot_message(context: ContextTypes.DEFAULT_TYPE):
    """Oxirgi bot xabarini o'chirish"""
    info = context.user_data.get('last_bot_message')
    if not info:
        return
    try:
        await context.bot.delete_message(
            chat_id=info['chat_id'], 
            message_id=info['message_id']
        )
    except:
        pass
    context.user_data.pop('last_bot_message', None)

# ==================== BOT HANDLERLARI ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botni boshlash"""
    user = update.effective_user
    
    if is_admin(user.username):
        reply_markup = admin_menu_keyboard()
        await update.message.reply_text(
            f"👋 Assalomu alaykum, {user.first_name}!\n\n"
            "🔐 Admin panelga xush kelibsiz.\n"
            "Quyidagi bo'limlardan birini tanlang:",
            reply_markup=reply_markup
        )
    else:
        reply_markup = main_menu_keyboard()
        await update.message.reply_text(
            f"👋 Assalomu alaykum, {user.first_name}!\n\n"
            "O'zingizning oldingi ma'lumotlaringizni ko'rish uchun "
            "'📂 Mening ma'lumotlarim' tugmasini bosing.",
            reply_markup=reply_markup
        )
    
    return ConversationHandler.END

async def fill_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reminder tugmasi bosilganda conversationni boshlash"""
    query = update.callback_query
    await query.answer()
    
    try:
        await query.message.delete()
    except:
        pass
    
    msg = await context.bot.send_message(
        chat_id=query.from_user.id,
        text="📋 Ma'lumot to'ldirish uchun viloyatingizni tanlang:",
        reply_markup=create_viloyat_keyboard()
    )
    await _store_bot_message(msg, context)
    return VILOYAT

# ==================== CONVERSATION HANDLERS ====================

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
    
    keyboard = [
        ["Kvartal", "Mahalla"], 
        ["📂 Mening ma'lumotlarim"]
    ]
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
        keyboard = [["Kvartal", "Mahalla"], ["📂 Mening ma'lumotlarim"]]
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
    user = update.effective_user
    
    # Database ga saqlash
    success = save_consumer_data(
        user_id=user.id,
        username=user.username or "Mavjud emas",
        first_name=user.first_name or "Noma'lum",
        viloyat=context.user_data['viloyat'],
        tuman=context.user_data['tuman'],
        kvartali_type=context.user_data['kvartali_type'],
        kvartali_name=context.user_data['kvartali_name'],
        manzil=context.user_data['manzil'],
        photo_id=photo.file_id
    )
    
    if success:
        settings = load_settings()
        reminder_time = settings.get('reminder_time', '10:00')
        
        success_message = (
            "✅ <b>Ma'lumotlar muvaffaqiyatli saqlandi!</b>\n\n"
            "📋 <b>Sizning ma'lumotlaringiz:</b>\n"
            f"📍 Viloyat: <b>{context.user_data['viloyat']}</b>\n"
            f"🏘 Tuman: <b>{context.user_data['tuman']}</b>\n"
            f"🏘 {context.user_data['kvartali_type']}: <b>{context.user_data['kvartali_name']}</b>\n"
            f"🏠 Manzil: <b>{context.user_data['manzil']}</b>\n"
            f"📅 Sana: <b>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</b>\n\n"
            f"⏰ <b>Keyingi to'ldirish vaqti: {reminder_time}</b>\n\n"
            "Rahmat! 🙏"
        )
        
        await update.message.reply_text(
            success_message,
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Ma'lumotlarni saqlashda xatolik yuz berdi. Iltimos qayta urinib ko'ring.",
            reply_markup=main_menu_keyboard()
        )
    
    context.user_data.clear()
    return ConversationHandler.END

# ==================== FOYDALANUVCHI FUNKSIYALARI ====================

async def my_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi o'z ma'lumotlarini ko'radi"""
    user = update.effective_user
    user_entries = get_user_data(user.id)
    
    if not user_entries:
        await update.message.reply_text(
            "📭 Sizda saqlangan ma'lumotlar topilmadi.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    await update.message.reply_text(
        f"📋 Sizning ma'lumotlaringiz: {len(user_entries)} ta\n\n"
        "Ma'lumotlar yuborilmoqda...",
        reply_markup=main_menu_keyboard()
    )
    
    for i, entry in enumerate(user_entries, 1):
        text = (
            f"#{i}\n"
            f"👤 <b>{entry['first_name']}</b>\n"
            f"🏙 Viloyat: {entry['viloyat']}\n"
            f"📍 Tuman: {entry['tuman']}\n"
            f"🏡 {entry['kvartali_type']}: {entry['kvartali_name']}\n"
            f"📫 Manzil: {entry['manzil']}\n"
            f"🕒 Sana: {entry['date']}"
        )
        
        if entry.get("photo_id"):
            await update.message.reply_photo(
                photo=entry["photo_id"],
                caption=text,
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(text, parse_mode="HTML")

# ==================== ADMIN FUNKSIYALARI ====================

async def show_all_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha ma'lumotlarni ko'rsatish (Admin)"""
    user = update.effective_user
    
    if not is_admin(user.username):
        await update.message.reply_text("❌ Sizda bu funksiyadan foydalanish huquqi yo'q!")
        return
    
    data = load_data()
    
    if not data:
        await update.message.reply_text(
            "📭 Hozircha ma'lumotlar yo'q!", 
            reply_markup=admin_menu_keyboard()
        )
        return
    
    total_count = sum(len(entries) for vil in data.values() for entries in vil.values())
    
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
                if not isinstance(entry, dict):
                    continue
                
                caption = (
                    f"#{i}\n"
                    f"👤 Ism: <b>{entry.get('first_name', '-')}</b>\n"
                    f"🏘 {entry.get('kvartali_type', '-')}: <b>{entry.get('kvartali_name', '-')}</b>\n"
                    f"🏠 Manzil: <b>{entry.get('manzil', '-')}</b>\n"
                    f"📅 Sana: <b>{entry.get('date', '-')}</b>\n"
                    f"👤 Username: @{entry.get('username', '-')}"
                )
                
                photo_id = entry.get('photo_id')
                if photo_id:
                    await update.message.reply_photo(
                        photo=photo_id,
                        caption=caption,
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(caption, parse_mode='HTML')
    
    await update.message.reply_text("✅ Tayyor.", reply_markup=admin_menu_keyboard())

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
            reply_markup=admin_menu_keyboard()
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
            
            if entry.get('photo_id'):
                await update.message.reply_photo(
                    photo=entry['photo_id'],
                    caption=caption,
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(caption, parse_mode='HTML')
    
    await update.message.reply_text("✅ Tayyor.", reply_markup=admin_menu_keyboard())
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
            reply_markup=create_tuman_keyboard(viloyat) if viloyat else admin_menu_keyboard()
        )
        return ADMIN_FILTER_TUMAN
    
    data = load_data()
    
    if viloyat not in data or tuman not in data[viloyat]:
        await update.message.reply_text(
            f"📭 {viloyat} - {tuman} uchun ma'lumotlar topilmadi!",
            reply_markup=admin_menu_keyboard()
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
        
        if entry.get('photo_id'):
            await update.message.reply_photo(
                photo=entry['photo_id'],
                caption=caption,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(caption, parse_mode='HTML')
    
    await update.message.reply_text("✅ Tayyor.", reply_markup=admin_menu_keyboard())
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
    search_term = update.message.text
    results = search_by_address(search_term)
    
    if not results:
        await update.message.reply_text(
            f"❌ '{search_term}' bo'yicha natija topilmadi!",
            reply_markup=admin_menu_keyboard()
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
        
        if entry.get('photo_id'):
            await update.message.reply_photo(
                photo=entry['photo_id'],
                caption=caption,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(caption, parse_mode='HTML')
    
    await update.message.reply_text("✅ Tayyor.", reply_markup=admin_menu_keyboard())
    return ConversationHandler.END

async def export_all_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin uchun: barcha ma'lumotlarni JSON fayl sifatida yuklab olish"""
    user = update.effective_user
    if not is_admin(user.username):
        await update.message.reply_text("❌ Sizda bu funksiyadan foydalanish huquqi yo'q!")
        return
    
    data = load_data()
    if not data:
        await update.message.reply_text("📭 Hozircha ma'lumotlar yo'q!", reply_markup=admin_menu_keyboard())
        return
    
    fname = f"consumers_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        with open(fname, "rb") as doc:
            await context.bot.send_document(
                chat_id=update.effective_user.id,
                document=doc,
                filename=fname,
                caption="📥 Barcha ma'lumotlar (JSON fayl)"
            )
        
        await update.message.reply_text(
            "✅ Ma'lumotlar fayl sifatida yuborildi.", 
            reply_markup=admin_menu_keyboard()
        )
    except Exception as e:
        print(f"Error exporting data: {e}")
        await update.message.reply_text("❌ Fayl yaratishda yoki yuborishda xatolik yuz berdi.")
    finally:
        try:
            if os.path.exists(fname):
                os.remove(fname)
        except:
            pass

# ==================== ESLATMA FUNKSIYALARI ====================

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Eslatma vaqtini o'rnatish (oylik kun)"""
    user = update.effective_user
    
    if not is_admin(user.username):
        await update.message.reply_text("❌ Sizda bu funksiyadan foydalanish huquqi yo'q!")
        return
    
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
    """Eslatma kunini callback orqali o'rnatish"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    try:
        if data == "day_off":
            settings = load_settings()
            settings['reminder_enabled'] = False
            settings['reminder_day'] = None
            save_settings(settings)
            
            if getattr(context, "job_queue", None):
                for job in context.job_queue.get_jobs_by_name("monthly_reminder"):
                    job.schedule_removal()
            
            await query.edit_message_text("❌ Eslatma o'chirildi!", parse_mode='HTML')
            await context.bot.send_message(
                chat_id=query.from_user.id, 
                text="✅ Eslatma o'chirildi va sozlamalar saqlandi."
            )
            return
        
        if data and data.startswith("day_"):
            day = int(data.split("_", 1)[1])
            
            settings = load_settings()
            settings['reminder_day'] = day
            settings['reminder_enabled'] = True
            settings.setdefault('reminder_time', "10:00")
            save_settings(settings)
            
            if getattr(context, "job_queue", None):
                for job in context.job_queue.get_jobs_by_name("monthly_reminder"):
                    job.schedule_removal()
                context.job_queue.run_monthly(
                    send_reminder,
                    when=time(hour=10, minute=0),
                    day=day,
                    name="monthly_reminder"
                )
            
            await query.edit_message_text(
                f"✅ <b>Eslatma muvaffaqiyatli o'rnatildi!</b>\n\n"
                f"📅 Har oyning <b>{day}-kuni</b>\n"
                f"⏰ Soat: <b>{settings.get('reminder_time', '10:00')}</b>\n"
                f"Barcha istemolchilarga eslatma yuboriladi.",
                parse_mode='HTML'
            )
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=f"✅ Yangi eslatma saqlandi: har oyning {day}-kuni soat {settings.get('reminder_time', '10:00')}"
            )
            return
        
        await query.edit_message_text("❌ Noma'lum tugma ma'lumoti. Iltimos qayta urinib ko'ring.")
    except Exception as e:
        print(f"Error in set_reminder_callback: {e}")
        try:
            await query.edit_message_text("❌ Xatolik yuz berdi. Iltimos qayta urinib ko'ring.")
        except:
            pass

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Barcha istemolchilarga eslatma yuborish"""
    user_ids = get_all_user_ids()
    success_count = 0
    fail_count = 0
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📝 Ma'lumot to'ldirish", callback_data="fill_info")]])
    
    for user_id in user_ids:
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text="⏰ <b>Eslatma!</b>\n\n"
                     "📋 Issiq suv hisoblagichingizning yangi ma'lumotlarini yuborish vaqti keldi.\n\n"
                     "Ma'lumotlarni yuborish uchun quyidagi tugmani bosing:",
                parse_mode='HTML',
                reply_markup=kb
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"❌ Error sending to {user_id}: {e}")
    
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

async def send_reminder_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin uchun: hozir barcha foydalanuvchilarga eslatma yuborish (test)"""
    user = update.effective_user
    if not is_admin(user.username):
        await update.message.reply_text("❌ Sizda bu funksiyadan foydalanish huquqi yo'q!")
        return
    
    await update.message.reply_text("🔁 Eslatma yuborish boshlandi. Iltimos kuting...")
    
    user_ids = get_all_user_ids()
    
    if not user_ids:
        await update.message.reply_text("📭 Bazada foydalanuvchi ma'lumotlari yo'q.")
        return
    
    success = []
    failed = []
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📝 Ma'lumot to'ldirish", callback_data="fill_info")]])
    
    for uid in user_ids:
        try:
            chat_id = int(uid)
            await context.bot.send_message(
                chat_id=chat_id,
                text="⏰ <b>Eslatma!</b>\n\n"
                     "📋 Issiq suv hisoblagichingizning yangi ma'lumotlarini yuborish vaqti keldi.\n\n"
                     "Ma'lumotlarni yuborish uchun quyidagi tugmani bosing:",
                parse_mode='HTML',
                reply_markup=kb
            )
            success.append(uid)
        except Exception as e:
            failed.append((uid, str(e)))
    
    report = (
        f"📊 Eslatma yuborish hisobot:\n\n"
        f"Jami maqsadli foydalanuvchilar: {len(user_ids)}\n"
        f"✅ Muvaffaqiyatli: {len(success)}\n"
        f"❌ Xatolik: {len(failed)}\n"
    )
    
    if failed:
        report += "\nXatoliklar (bir nechta):\n"
        for uid, err in failed[:20]:
            report += f"- {uid}: {err}\n"
    
    await update.message.reply_text(report)
    await update.message.reply_text("✅ Eslatma yuborish tugallandi.")

# ==================== YORDAMCHI FUNKSIYALAR ====================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bekor qilish"""
    user = update.effective_user
    
    if is_admin(user.username):
        reply_markup = admin_menu_keyboard()
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
            "⏰ <b>Eslatma sozlash</b> - Oylik eslatma sozlash\n"
            "📥 <b>Yuklab olish</b> - Barcha ma'lumotlarni fayl sifatida olish\n\n"
            "❌ <b>/cancel</b> - Jarayonni bekor qilish\n"
            "🔔 <b>/send_reminder</b> - Test uchun hozir eslatma yuborish"
        )
        reply_markup = admin_menu_keyboard()
    else:
        text = (
            "📋 <b>Bot haqida ma'lumot:</b>\n\n"
            "Bu bot orqali siz issiq suv hisoblagichingizning ma'lumotlarini yuborishingiz mumkin.\n\n"
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
        reply_markup = main_menu_keyboard()
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)

# ==================== ASOSIY FUNKSIYA ====================

def main():
    """Botni ishga tushirish"""
    # Database ni initialize qilish
    _init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Consumer conversation handler
    consumer_conv = ConversationHandler(
        entry_points=[
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
    
    # Viloyat filter conversation
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
    
    # Tuman filter conversation
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
    
    # Uy raqami search conversation
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
    
    # Command handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("send_reminder", send_reminder_now))
    
    # Message handlerlar
    application.add_handler(MessageHandler(filters.Regex("^📊 Barcha ma'lumotlar$"), show_all_data))
    application.add_handler(MessageHandler(filters.Regex("^⏰ Eslatma sozlash$"), set_reminder))
    application.add_handler(MessageHandler(filters.Regex("^📂 Mening ma'lumotlarim$"), my_data))
    application.add_handler(MessageHandler(filters.Regex("^📥 Yuklab olish$"), export_all_data))
    
    # Callback handlerlar
    application.add_handler(CallbackQueryHandler(set_reminder_callback, pattern="^day_"))
    application.add_handler(CallbackQueryHandler(fill_info_callback, pattern="^fill_info$"))
    
    # Eslatma jobini yuklash
    settings = load_settings()
    if settings.get('reminder_enabled', False):
        try:
            reminder_day = settings.get('reminder_day', 1)
            if application.job_queue:
                application.job_queue.run_monthly(
                    send_reminder,
                    when=time(hour=10, minute=0),
                    day=reminder_day,
                    name="monthly_reminder"
                )
                print(f"📅 Har oyning {reminder_day}-kuni soat 10:00 da eslatma yuboriladi")
        except Exception as e:
            print(f"⚠️ Eslatma o'rnatishda xatolik: {e}")
    
    print("✅ Bot ishga tushdi!")
    try:
        bot_username = application.bot.username
        print(f"📊 Bot username: @{bot_username}")
    except:
        print("📊 Bot username: unknown")
    
    print(f"⏰ Eslatma: {'Yoniq' if settings.get('reminder_enabled') else 'O\'chiq'}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()