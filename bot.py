import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ===== ТВОИ ДАННЫЕ =====
BOT_TOKEN = "8699450261:AAHWOh4pVXD23O_rHXC1vpjzTl1VcjUBArg"
ADMIN_ID = 7717714437
MANAGER_USERNAME = "Vajnigoi"
SHEET_ID = "ТВОЙ_ID_ТАБЛИЦЫ"  # ← ВСТАВЬ СЮДА
# ========================

# Подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1

bot = telebot.TeleBot(BOT_TOKEN)

# ===== КЛАВИАТУРЫ =====
def user_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📚 Ашық сабақ"), KeyboardButton("🤖 AI видеолар"))
    markup.add(KeyboardButton("🛒 Тапсырыс(24/7)"))
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("➕ Добавить товар"), KeyboardButton("📊 Статистика"))
    markup.add(KeyboardButton("📦 Список товаров"), KeyboardButton("🗑 Удалить товар"))
    markup.add(KeyboardButton("✅ Подтвердить оплату"), KeyboardButton("🏠 Главное меню"))
    return markup

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С GOOGLE SHEETS =====
def get_all_products():
    """Получить все товары из таблицы"""
    return sheet.get_all_records()

def get_products_by_category(category):
    """Получить товары по категории"""
    products = get_all_products()
    return [p for p in products if p['category'] == category]

def add_product_to_sheet(name, category, price, file_id):
    """Добавить товар в таблицу"""
    products = get_all_products()
    new_id = len(products) + 1
    sheet.append_row([new_id, name, category, price, file_id])
    return new_id

def delete_product_from_sheet(product_id):
    """Удалить товар по ID"""
    products = get_all_products()
    for i, p in enumerate(products, start=2):  # строка 2 (после заголовка)
        if p['id'] == product_id:
            sheet.delete_rows(i)
            return True
    return False

def get_product_by_id(product_id):
    """Найти товар по ID"""
    products = get_all_products()
    for p in products:
        if p['id'] == product_id:
            return p
    return None

# ===== ОЖИДАЮЩИЕ ПЛАТЕЖИ =====
pending_payments = {}

# ===== ОСНОВНЫЕ КОМАНДЫ =====
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Қош келдіңіз! / Добро пожаловать!", reply_markup=user_menu())

@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "👨‍💼 Админ панелі:", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def back_to_menu(message):
    bot.send_message(message.chat.id, "👋 Главное меню:", reply_markup=user_menu())

# ===== КНОПКИ ПОКУПАТЕЛЯ =====
@bot.message_handler(func=lambda m: m.text == "📚 Ашық сабақ")
def show_lessons(message):
    products = get_products_by_category("Ашық сабақ")
    if not products:
        bot.send_message(message.chat.id, "📭 Әлі өнім жоқ")
        return
    
    for p in products:
        markup = InlineKeyboardMarkup()
        btn = InlineKeyboardButton(f"💳 Купить {p['price']} руб", callback_data=f"buy_{p['id']}")
        markup.add(btn)
        bot.send_message(message.chat.id, f"📘 *{p['name']}*\n💰 Цена: {p['price']} руб.", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🤖 AI видеолар")
def show_ai(message):
    products = get_products_by_category("AI видео")
    if not products:
        bot.send_message(message.chat.id, "📭 Әлі өнім жоқ")
        return
    
    for p in products:
        markup = InlineKeyboardMarkup()
        btn = InlineKeyboardButton(f"💳 Купить {p['price']} руб", callback_data=f"buy_{p['id']}")
        markup.add(btn)
        bot.send_message(message.chat.id, f"🎥 *{p['name']}*\n💰 Цена: {p['price']} руб.", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🛒 Тапсырыс(24/7)")
def order(message):
    bot.send_message(message.chat.id, f"📞 *Байланыс / Контакты:*\n\n👤 Менеджер: @{MANAGER_USERNAME}\n💬 24/7 қолжетімді", parse_mode="Markdown")

# ===== ПОКУПКА =====
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    product_id = int(call.data.split("_")[1])
    user_id = call.from_user.id
    
    product = get_product_by_id(product_id)
    if not product:
        bot.answer_callback_query(call.id, "❌ Товар не найден")
        return
    
    pending_payments[user_id] = {
        "product_id": product_id,
        "product_name": product['name'],
        "price": product['price'],
        "file_id": product['file_id']
    }
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📤 Отправить чек", callback_data=f"receipt_{product_id}"))
    markup.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_payment"))
    
    bot.send_message(call.message.chat.id,
        f"💳 *Оплата товара:* {product['name']}\n💰 *Сумма:* {product['price']} руб.\n\n"
        f"📌 *Реквизиты:*\n"
        f"┌─────────────────────┐\n"
        f"│  💳 Карта: 1234 5678 9012 3456\n"
        f"│  👤 Получатель: Асхат\n"
        f"│  💰 Сумма: {product['price']} руб.\n"
        f"└─────────────────────┘\n\n"
        f"✅ *После оплаты* нажми «Отправить чек» и отправь фото чека",
        parse_mode="Markdown", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("receipt_"))
def ask_receipt(call):
    bot.edit_message_text("📸 *Отправь ФОТО чека:*\n\nПросто отправь изображение чека.", 
                          call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_payment")
def cancel_payment(call):
    user_id = call.from_user.id
    if user_id in pending_payments:
        del pending_payments[user_id]
    bot.edit_message_text("❌ Оплата отменена.", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

# ===== ОБРАБОТКА ЧЕКА =====
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username or "нет"
    
    if user_id not in pending_payments:
        bot.reply_to(message, "❌ У тебя нет активного платежа. Нажми /start")
        return
    
    payment = pending_payments[user_id]
    file_id = message.photo[-1].file_id
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{user_id}"))
    markup.add(InlineKeyboardButton("❌ Отказать", callback_data=f"reject_{user_id}"))
    
    admin_text = (f"💰 *НОВЫЙ ПЛАТЕЖ!*\n\n"
                  f"👤 Пользователь: {user_name} (@{user_username})\n"
                  f"🆔 ID: `{user_id}`\n"
                  f"📦 Товар: {payment['product_name']}\n"
                  f"💰 Сумма: {payment['price']} руб.")
    
    bot.send_photo(ADMIN_ID, file_id, caption=admin_text, parse_mode="Markdown", reply_markup=markup)
    bot.reply_to(message, f"✅ Чек отправлен! Ожидай подтверждения.")
    payment['status'] = 'checking'

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_payment(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
    
    user_id = int(call.data.split("_")[1])
    if user_id not in pending_payments:
        bot.answer_callback_query(call.id, "❌ Платеж не найден")
        return
    
    payment = pending_payments[user_id]
    
    bot.send_message(user_id, f"✅ *Оплата подтверждена!*\n\n📦 {payment['product_name']}\n📎 Вот твой файл:", parse_mode="Markdown")
    bot.send_document(user_id, payment['file_id'])
    
    del pending_payments[user_id]
    bot.edit_message_caption(f"✅ ПЛАТЕЖ ПОДТВЕРЖДЕН! Пользователь {user_id} получил файл.", 
                              call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "✅ Подтверждено!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def reject_payment(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
    
    user_id = int(call.data.split("_")[1])
    if user_id not in pending_payments:
        bot.answer_callback_query(call.id, "❌ Платеж не найден")
        return
    
    payment = pending_payments[user_id]
    bot.send_message(user_id, f"❌ *Оплата НЕ подтверждена!*\n\n📞 Свяжись с менеджером: @{MANAGER_USERNAME}", parse_mode="Markdown")
    
    del pending_payments[user_id]
    bot.edit_message_caption(f"❌ ПЛАТЕЖ ОТКЛОНЕН! Пользователь {user_id} уведомлен.", 
                              call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "❌ Отклонено")

# ===== АДМИН: ФУНКЦИИ =====
@bot.message_handler(func=lambda m: m.text == "✅ Подтвердить оплату")
def show_pending(message):
    if message.from_user.id != ADMIN_ID:
        return
    if not pending_payments:
        bot.send_message(message.chat.id, "📭 Нет ожидающих платежей")
        return
    
    text = "💰 *Ожидающие платежи:*\n\n"
    for uid, p in pending_payments.items():
        text += f"👤 ID: `{uid}`\n📦 {p['product_name']} | {p['price']} руб.\n\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить товар")
def add_product(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(message.chat.id, "📝 Отправь в формате:\n`/add|Название|Категория|Цена|file_id`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_add)

def process_add(message):
    try:
        parts = message.text.split('|')
        if len(parts) >= 5:
            _, name, category, price, file_id = parts[:5]
            add_product_to_sheet(name, category, int(price), file_id)
            bot.send_message(message.chat.id, f"✅ Товар '{name}' добавлен!", reply_markup=admin_menu())
        else:
            bot.send_message(message.chat.id, "❌ Неверный формат. Пример:\n`/add|Курс|Ашық сабақ|500|file_id`", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

@bot.message_handler(func=lambda m: m.text == "📦 Список товаров")
def list_products_admin(message):
    if message.from_user.id != ADMIN_ID:
        return
    products = get_all_products()
    if not products:
        bot.send_message(message.chat.id, "📭 Нет товаров")
        return
    text = "📦 *Товары:*\n"
    for p in products:
        text += f"🆔 {p['id']}. {p['name']} | {p['price']} руб.\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить товар")
def delete_product(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(message.chat.id, "🗑 Введите ID товара для удаления:\n\n/lista - список ID")
    bot.register_next_step_handler(msg, process_delete)

def process_delete(message):
    try:
        product_id = int(message.text)
        if delete_product_from_sheet(product_id):
            bot.send_message(message.chat.id, f"✅ Товар {product_id} удален!", reply_markup=admin_menu())
        else:
            bot.send_message(message.chat.id, "❌ Товар не найден")
    except:
        bot.send_message(message.chat.id, "❌ Введите ID цифрой!")

@bot.message_handler(commands=['lista'])
def lista(message):
    if message.from_user.id != ADMIN_ID:
        return
    products = get_all_products()
    if products:
        text = "📦 ID товаров:\n"
        for p in products:
            text += f"🔹 {p['id']} - {p['name']} ({p['price']} руб.)\n"
        bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, "📭 Нет товаров")

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    products = get_all_products()
    bot.send_message(message.chat.id, f"📊 *Статистика*\n\n📦 Товаров: {len(products)}\n⏳ Ожидают оплаты: {len(pending_payments)}", parse_mode="Markdown")

# ===== ЗАПУСК =====
print("🚀 БОТ ЗАПУЩЕН с Google Sheets!")
print(f"👨‍💼 Админ ID: {ADMIN_ID}")
bot.infinity_polling()
