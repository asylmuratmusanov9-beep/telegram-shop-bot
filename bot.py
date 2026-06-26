import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import re
from datetime import datetime

# ===== ТВОИ ДАННЫЕ =====
BOT_TOKEN = "8699450261:AAHaVZreEsFFM__QOBY_vrnOiy4cV_Rk9P4"
ADMIN_ID = 7717714437
MANAGER_USERNAME = "Vajnigoi"
SHEET_ID = "1CeSsvRuqrr0M8fv1Aef89vtwPLxrZGAnuxEkx4f08js"

CARD_NUMBER = "4002890035103872"
CARD_HOLDER = "Асылмурат М."
# ========================

# Подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ.get('GOOGLE_CREDS'))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1

# Создаём лист для покупок, если его нет
try:
    purchases_sheet = gc.open_by_key(SHEET_ID).worksheet("purchases")
except:
    purchases_sheet = gc.open_by_key(SHEET_ID).add_worksheet("purchases", 100, 7)
    purchases_sheet.append_row(["id", "user_id", "username", "product_name", "price", "status", "date"])

bot = telebot.TeleBot(BOT_TOKEN)

# ===== ФУНКЦИИ =====
def get_all_products():
    return sheet.get_all_records()

def get_products_by_category(category):
    products = get_all_products()
    return [p for p in products if p['category'].strip() == category.strip()]

def get_product_by_id(product_id):
    products = get_all_products()
    for p in products:
        if p['id'] == product_id:
            return p
    return None

def add_product_to_sheet(name, category, price, file_id):
    products = get_all_products()
    new_id = len(products) + 1
    sheet.append_row([new_id, name, category, price, file_id])
    return new_id

def search_products(query):
    products = get_all_products()
    query_lower = query.lower()
    results = []
    for p in products:
        if query_lower in p['name'].lower():
            results.append(p)
    return results

def add_purchase(user_id, username, product_name, price):
    try:
        records = purchases_sheet.get_all_records()
        new_id = len(records) + 1
        purchases_sheet.append_row([
            new_id,
            user_id,
            username,
            product_name,
            price,
            "оплачено",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
    except Exception as e:
        print(f"Ошибка сохранения покупки: {e}")

# ===== КЛАВИАТУРЫ =====
def user_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📚 Ашық сабақ"), KeyboardButton("🤖 AI видеолар"))
    markup.add(KeyboardButton("🔍 Поиск"), KeyboardButton("🛒 Тапсырыс(24/7)"))
    markup.add(KeyboardButton("❓ Помощь"))
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("➕ Как добавить товар"), KeyboardButton("📊 Статистика"))
    markup.add(KeyboardButton("📦 Список товаров"), KeyboardButton("🗑 Удалить товар"))
    markup.add(KeyboardButton("✅ Подтвердить оплату"), KeyboardButton("🏠 Главное меню"))
    markup.add(KeyboardButton("📋 История покупок"))
    return markup

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
    else:
        bot.send_message(message.chat.id, "⛔ Доступ запрещен!")

@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def back_to_menu(message):
    bot.send_message(message.chat.id, "👋 Главное меню:", reply_markup=user_menu())

# ===== ПОМОЩЬ =====
@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_start(message):
    bot.send_message(
        message.chat.id,
        "📝 *Как мы можем помочь?*\n\n"
        "Напишите свой вопрос или опишите проблему.\n"
        "Мы свяжемся с вами в ближайшее время!",
        parse_mode="Markdown"
    )
    msg = bot.send_message(message.chat.id, "✍️ *Напишите ваш вопрос:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, send_help_to_admin)

def send_help_to_admin(message):
    user_id = message.from_user.id
    username = message.from_user.username or "нет"
    first_name = message.from_user.first_name
    question = message.text
    
    admin_text = (
        f"🆘 *Новый вопрос от пользователя!*\n\n"
        f"👤 Имя: {first_name}\n"
        f"🆔 ID: `{user_id}`\n"
        f"📸 Username: @{username}\n\n"
        f"📝 *Вопрос:*\n{question}"
    )
    
    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
    bot.send_message(
        message.chat.id,
        "✅ *Ваш вопрос отправлен!*\n\n"
        "Мы ответим вам в ближайшее время.",
        parse_mode="Markdown"
    )

# ===== ПОИСК =====
@bot.message_handler(func=lambda m: m.text == "🔍 Поиск")
def search_start(message):
    msg = bot.send_message(message.chat.id, "🔍 *Введите название материала:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    query = message.text
    results = search_products(query)
    
    if not results:
        bot.send_message(message.chat.id, "❌ Ничего не найдено. Попробуй другой запрос.")
        return
    
    for p in results:
        show_product(message.chat.id, p)

def show_product(chat_id, product):
    caption = f"📘 *{product['name']}*\n💰 Цена: {product['price']} ₸\n📂 Категория: {product['category']}"
    
    markup = InlineKeyboardMarkup()
    btn = InlineKeyboardButton(f"💳 Купить {product['price']} ₸", callback_data=f"buy_{product['id']}")
    markup.add(btn)
    
    if product.get('preview_url') and product['preview_url']:
        try:
            bot.send_photo(chat_id, product['preview_url'], caption=caption, parse_mode="Markdown", reply_markup=markup)
        except:
            bot.send_message(chat_id, caption + "\n\n🖼️ Превью недоступно", parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(chat_id, caption, parse_mode="Markdown", reply_markup=markup)

# ===== КНОПКИ ПОКУПАТЕЛЯ =====
@bot.message_handler(func=lambda m: m.text == "📚 Ашық сабақ")
def show_lessons(message):
    products = get_products_by_category("Ашық сабақ")
    if not products:
        bot.send_message(message.chat.id, "📭 Әлі өнім жоқ")
        return
    for p in products:
        show_product(message.chat.id, p)

@bot.message_handler(func=lambda m: m.text == "🤖 AI видеолар")
def show_ai(message):
    products = get_products_by_category("AI видео")
    if not products:
        bot.send_message(message.chat.id, "📭 Әлі өнім жоқ")
        return
    for p in products:
        show_product(message.chat.id, p)

@bot.message_handler(func=lambda m: m.text == "🛒 Тапсырыс(24/7)")
def order(message):
    bot.send_message(message.chat.id, f"📞 *Байланыс:* @{MANAGER_USERNAME}\n💬 24/7", parse_mode="Markdown")

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
    
    card_display = CARD_NUMBER
    bot.send_message(call.message.chat.id,
        f"💳 *Оплата:* {product['name']}\n💰 *Сумма:* {product['price']} ₸\n\n"
        f"📌 *Реквизиты:*\n┌─────────────────────┐\n"
        f"│  💳 Карта: {card_display}\n│  👤 Получатель: {CARD_HOLDER}\n"
        f"│  💰 Сумма: {product['price']} ₸\n└─────────────────────┘\n\n"
        f"✅ *После оплаты* нажми «Отправить чек»",
        parse_mode="Markdown", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("receipt_"))
def ask_receipt(call):
    bot.edit_message_text("📸 *Отправь ФОТО чека:*", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_payment")
def cancel_payment(call):
    user_id = call.from_user.id
    if user_id in pending_payments:
        del pending_payments[user_id]
    bot.edit_message_text("❌ Оплата отменена.", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

# ===== ОБРАБОТКА ЧЕКА =====
def handle_receipt(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username or "нет"
    
    if user_id not in pending_payments:
        bot.reply_to(message, "❌ У тебя нет активного платежа")
        return
    
    payment = pending_payments[user_id]
    file_id = message.photo[-1].file_id
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{user_id}"))
    markup.add(InlineKeyboardButton("❌ Отказать", callback_data=f"reject_{user_id}"))
    
    admin_text = (f"💰 *НОВЫЙ ПЛАТЕЖ!*\n\n👤 {user_name} (@{user_username})\n"
                  f"🆔 `{user_id}`\n📦 {payment['product_name']}\n💰 {payment['price']} ₸")
    
    bot.send_photo(ADMIN_ID, file_id, caption=admin_text, parse_mode="Markdown", reply_markup=markup)
    bot.reply_to(message, f"✅ Чек отправлен! Ожидай.")

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
    if not payment.get('file_id'):
        bot.answer_callback_query(call.id, "❌ У товара нет file_id!")
        return
    
    # Сохраняем покупку
    username = bot.get_chat(user_id).username or "нет"
    add_purchase(user_id, username, payment['product_name'], payment['price'])
    
    bot.send_message(user_id, f"✅ *Оплата подтверждена!*\n\n📦 {payment['product_name']}\n📎 Вот твой файл:", parse_mode="Markdown")
    bot.send_document(user_id, payment['file_id'])
    
    del pending_payments[user_id]
    bot.edit_message_caption(f"✅ ПЛАТЕЖ ПОДТВЕРЖДЕН", call.message.chat.id, call.message.message_id)
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
    bot.send_message(user_id, f"❌ *Оплата НЕ подтверждена!*\n\n📞 @{MANAGER_USERNAME}", parse_mode="Markdown")
    del pending_payments[user_id]
    bot.edit_message_caption(f"❌ ПЛАТЕЖ ОТКЛОНЕН", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "❌ Отклонено")

# ===== АДМИН: ФУНКЦИИ =====
@bot.message_handler(func=lambda m: m.text == "✅ Подтвердить оплату")
def show_pending(message):
    if message.from_user.id != ADMIN_ID:
        return
    if not pending_payments:
        bot.send_message(message.chat.id, "📭 Нет ожидающих платежей")
        return
    text = "💰 *Ожидающие платежи:*\n"
    for uid, p in pending_payments.items():
        text += f"\n👤 `{uid}`\n📦 {p['product_name']} | {p['price']} ₸"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    products = get_all_products()
    bot.send_message(message.chat.id, f"📊 *Статистика*\n\n📦 Товаров: {len(products)}\n⏳ Ожидают: {len(pending_payments)}", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📋 История покупок")
def purchase_history(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        records = purchases_sheet.get_all_records()
        if not records:
            bot.send_message(message.chat.id, "📭 История покупок пуста")
            return
        text = "📋 *История покупок:*\n\n"
        for r in records[-20:]:  # последние 20
            text += f"🆔 {r['id']} | {r['username']} | {r['product_name']} | {r['price']} ₸ | {r['date']}\n"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
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
        text += f"🆔 {p['id']}. {p['name']} | {p['price']} ₸\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить товар")
def delete_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "🗑 /del 1")

@bot.message_handler(commands=['del'])
def delete_product(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        pid = int(message.text.split()[1])
        products = get_all_products()
        for i, p in enumerate(products, start=2):
            if p['id'] == pid:
                sheet.delete_rows(i)
                bot.send_message(message.chat.id, f"✅ Товар {pid} удален!")
                return
        bot.send_message(message.chat.id, "❌ Не найден")
    except:
        bot.send_message(message.chat.id, "❌ /del 1")

@bot.message_handler(commands=['lista'])
def lista(message):
    if message.from_user.id != ADMIN_ID:
        return
    products = get_all_products()
    if products:
        text = "📦 ID товаров:\n"
        for p in products:
            text += f"🔹 {p['id']} - {p['name']} ({p['price']} ₸)\n"
        bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, "📭 Нет товаров")

# ===== АВТО-ДОБАВЛЕНИЕ ТОВАРА =====
@bot.message_handler(content_types=['document', 'photo', 'video'])
def handle_files(message):
    user_id = message.from_user.id
    
    caption = message.caption or ""
    is_add_command = re.match(r'^/add\s*\|\s*.+?\s*\|\s*.+?\s*\|\s*\d+\s*$', caption)
    
    if is_add_command and user_id == ADMIN_ID:
        pattern = r'^/add\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(\d+)\s*$'
        match = re.match(pattern, caption)
        
        if match:
            name = match.group(1).strip()
            category = match.group(2).strip()
            price = int(match.group(3))
            
            if message.document:
                file_id = message.document.file_id
            elif message.photo:
                file_id = message.photo[-1].file_id
            elif message.video:
                file_id = message.video.file_id
            else:
                bot.reply_to(message, "❌ Неподдерживаемый тип")
                return
            
            new_id = add_product_to_sheet(name, category, price, file_id)
            bot.reply_to(message, f"✅ Товар добавлен!\n\n📦 {name}\n📂 {category}\n💰 {price} ₸\n🆔 ID: {new_id}", parse_mode="Markdown")
        return
    
    if user_id in pending_payments:
        if message.photo:
            handle_receipt(message)
        else:
            bot.reply_to(message, "❌ Отправьте фото чека")
        return
    
    if user_id == ADMIN_ID:
        bot.reply_to(message, "❌ Неверный формат!\n\nНужно: `/add |Название|Категория|Цена`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ У тебя нет активного платежа. Нажми /start и выбери товар.")

# ===== ЗАПУСК =====
if __name__ == "__main__":
    print("🚀 БОТ ЗАПУЩЕН!")
    bot.infinity_polling()
