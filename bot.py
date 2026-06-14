import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import time
import threading

# ===== ТВОИ ДАННЫЕ =====
BOT_TOKEN = "8699450261:AAHWOh4pVXD23O_rHXC1vpjzTl1VcjUBArg"
ADMIN_ID = 7717714437
MANAGER_USERNAME = "Vajnigoi"  # Твой юзернейм для Тапсырыс
# ========================

bot = telebot.TeleBot(BOT_TOKEN)

# База данных
conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS products
                  (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price INTEGER, file_id TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS purchases
                  (user_id INTEGER, product_id INTEGER)''')
conn.commit()

# ===== КЛАВИАТУРЫ =====
def user_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = KeyboardButton("📚 Ашық сабақ")
    btn2 = KeyboardButton("🤖 AI видеолар")
    btn3 = KeyboardButton("🛒 Тапсырыс(24/7)")
    markup.add(btn1, btn2, btn3)
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = KeyboardButton("➕ Добавить товар")
    btn2 = KeyboardButton("📊 Статистика")
    btn3 = KeyboardButton("📦 Список товаров")
    btn4 = KeyboardButton("🗑 Удалить товар")
    btn5 = KeyboardButton("✅ Подтвердить оплату")
    btn6 = KeyboardButton("🏠 Главное меню")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

# ===== ОЖИДАЮЩИЕ ПЛАТЕЖИ =====
pending_payments = {}  # {user_id: {"product_id": id, "product_name": name, "price": price, "status": "waiting"}}

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ =====
def get_products_by_category(category):
    cursor.execute("SELECT id, name, price FROM products WHERE category=?", (category,))
    return cursor.fetchall()

def get_product_by_id(product_id):
    cursor.execute("SELECT id, name, price, file_id FROM products WHERE id=?", (product_id,))
    return cursor.fetchone()

def add_purchase(user_id, product_id):
    cursor.execute("INSERT INTO purchases (user_id, product_id) VALUES (?, ?)", (user_id, product_id))
    conn.commit()

def has_purchased(user_id, product_id):
    cursor.execute("SELECT * FROM purchases WHERE user_id=? AND product_id=?", (user_id, product_id))
    return cursor.fetchone() is not None

# ===== ОСНОВНЫЕ КОМАНДЫ =====
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
                     "👋 Қош келдіңіз! / Добро пожаловать!\n\n"
                     "Төмендегі мәзірден таңдаңыз:\n"
                     "Выберите из меню ниже:",
                     reply_markup=user_menu())

@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "👨‍💼 Админ панелі:", reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, "⛔ Доступ запрещен!")

@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def back_to_menu(message):
    bot.send_message(message.chat.id, "👋 Главное меню:", reply_markup=user_menu())

# ===== КНОПКИ ПОКУПАТЕЛЯ =====
@bot.message_handler(func=lambda m: m.text == "📚 Ашық сабақ")
def show_lessons(message):
    products = get_products_by_category("Ашық сабақ")
    if not products:
        bot.send_message(message.chat.id, "📭 Әлі өнім жоқ / Пока нет товаров")
        return
    
    for p in products:
        markup = InlineKeyboardMarkup()
        btn = InlineKeyboardButton(f"💳 Купить {p[2]} руб", callback_data=f"buy_{p[0]}")
        markup.add(btn)
        bot.send_message(message.chat.id, f"📘 *{p[1]}*\n💰 Цена: {p[2]} руб.", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🤖 AI видеолар")
def show_ai(message):
    products = get_products_by_category("AI видео")
    if not products:
        bot.send_message(message.chat.id, "📭 Әлі өнім жоқ / Пока нет товаров")
        return
    
    for p in products:
        markup = InlineKeyboardMarkup()
        btn = InlineKeyboardButton(f"💳 Купить {p[2]} руб", callback_data=f"buy_{p[0]}")
        markup.add(btn)
        bot.send_message(message.chat.id, f"🎥 *{p[1]}*\n💰 Цена: {p[2]} руб.", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🛒 Тапсырыс(24/7)")
def order(message):
    bot.send_message(message.chat.id, 
                     f"📞 *Байланыс / Контакты:*\n\n"
                     f"👤 Менеджер: @{MANAGER_USERNAME}\n"
                     f"💬 24/7 қолжетімді / Доступны 24/7\n\n"
                     f"✏️ Напишите менеджеру для заказа!",
                     parse_mode="Markdown")

# ===== ПРОЦЕСС ПОКУПКИ =====
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    product_id = int(call.data.split("_")[1])
    user_id = call.from_user.id
    
    # Проверяем, покупал ли уже
    if has_purchased(user_id, product_id):
        product = get_product_by_id(product_id)
        if product:
            bot.send_message(call.message.chat.id, f"✅ У вас уже есть этот товар!")
            bot.send_document(call.message.chat.id, product[3])
        return
    
    product = get_product_by_id(product_id)
    if not product:
        bot.answer_callback_query(call.id, "❌ Товар не найден")
        return
    
    product_id, product_name, price, file_id = product
    
    # Сохраняем в ожидающие платежи
    pending_payments[user_id] = {
        "product_id": product_id,
        "product_name": product_name,
        "price": price,
        "status": "waiting"
    }
    
    # Кнопки для оплаты
    markup = InlineKeyboardMarkup()
    btn1 = InlineKeyboardButton("📤 Отправить чек", callback_data=f"receipt_{product_id}")
    btn2 = InlineKeyboardButton("❌ Отмена", callback_data="cancel_payment")
    markup.add(btn1, btn2)
    
    bot.send_message(
        call.message.chat.id,
        f"💳 *Оплата товара:* {product_name}\n"
        f"💰 *Сумма:* {price} руб.\n\n"
        f"📌 *Реквизиты для оплаты:*\n"
        f"┌─────────────────────┐\n"
        f"│  💳 Карта: 1234 5678 9012 3456\n"
        f"│  👤 Получатель: Асхат М.\n"
        f"│  💰 Сумма: {price} руб.\n"
        f"└─────────────────────┘\n\n"
        f"✅ *После оплаты:*\n"
        f"• Нажми «📤 Отправить чек»\n"
        f"• Отправь СКРИНШОТ чека\n"
        f"• Админ проверит и выдаст файл",
        parse_mode="Markdown",
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("receipt_"))
def ask_receipt(call):
    product_id = int(call.data.split("_")[1])
    user_id = call.from_user.id
    
    if user_id not in pending_payments:
        bot.answer_callback_query(call.id, "❌ Платеж не найден")
        return
    
    bot.edit_message_text(
        "📸 *Отправь ФОТО или СКРИНШОТ чека:*\n\n"
        "Просто отправь мне изображение чека, и админ его проверит.\n\n"
        "❗ Чек должен быть четким, видна сумма и дата.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_payment")
def cancel_payment(call):
    user_id = call.from_user.id
    if user_id in pending_payments:
        del pending_payments[user_id]
    bot.edit_message_text("❌ Оплата отменена.", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

# ===== ОБРАБОТКА ЧЕКА ОТ ПОЛЬЗОВАТЕЛЯ =====
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username or "нет"
    
    if user_id not in pending_payments:
        bot.reply_to(message, "❌ У тебя нет активного платежа. Нажми /start и выбери товар.")
        return
    
    payment = pending_payments[user_id]
    file_id = message.photo[-1].file_id
    
    # Кнопки для админа
    markup = InlineKeyboardMarkup()
    btn1 = InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{user_id}")
    btn2 = InlineKeyboardButton("❌ Отказать", callback_data=f"reject_{user_id}")
    markup.add(btn1, btn2)
    
    admin_text = (
        f"💰 *НОВЫЙ ПЛАТЕЖ!*\n\n"
        f"👤 Пользователь: {user_name}\n"
        f"🆔 ID: `{user_id}`\n"
        f"📸 Юзернейм: @{user_username}\n"
        f"📦 Товар: {payment['product_name']}\n"
        f"💰 Сумма: {payment['price']} руб.\n\n"
        f"📌 Чек на фото ниже"
    )
    
    bot.send_photo(ADMIN_ID, file_id, caption=admin_text, parse_mode="Markdown", reply_markup=markup)
    
    bot.reply_to(message, f"✅ Чек отправлен администратору!\n\n📦 Товар: {payment['product_name']}\n💰 {payment['price']} руб.\n\n⏳ Ожидай подтверждения...")
    
    payment["status"] = "checking"

# ===== АДМИН: ПОДТВЕРЖДЕНИЕ ОПЛАТЫ =====
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
    product_id = payment["product_id"]
    product = get_product_by_id(product_id)
    
    if product:
        # Сохраняем покупку
        add_purchase(user_id, product_id)
        
        # Отправляем файл пользователю
        bot.send_message(user_id, f"✅ *Оплата подтверждена!*\n\n📦 Товар: {payment['product_name']}\n📎 Вот твой файл:", parse_mode="Markdown")
        bot.send_document(user_id, product[3])
        
        # Удаляем из ожидающих
        del pending_payments[user_id]
        
        bot.edit_message_caption(f"✅ ПЛАТЕЖ ПОДТВЕРЖДЕН! Пользователь {user_id} получил файл.", 
                                  call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "✅ Подтверждено!")
    else:
        bot.answer_callback_query(call.id, "❌ Товар не найден")

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
    
    # Уведомляем пользователя
    bot.send_message(user_id, f"❌ *Оплата НЕ подтверждена!*\n\n📦 Товар: {payment['product_name']}\n💰 {payment['price']} руб.\n\n⚠️ Причина: чек не прошел проверку.\n\n📞 Свяжись с менеджером: @{MANAGER_USERNAME}", parse_mode="Markdown")
    
    del pending_payments[user_id]
    
    bot.edit_message_caption(f"❌ ПЛАТЕЖ ОТКЛОНЕН! Пользователь {user_id} уведомлен.", 
                              call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "❌ Отклонено")

# ===== АДМИН: ФУНКЦИИ =====
@bot.message_handler(func=lambda m: m.text == "✅ Подтвердить оплату")
def show_pending_admin(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    if not pending_payments:
        bot.send_message(message.chat.id, "📭 Нет ожидающих платежей")
        return
    
    text = "💰 *Ожидающие платежи:*\n\n"
    for user_id, payment in pending_payments.items():
        text += f"👤 ID: `{user_id}`\n"
        text += f"📦 {payment['product_name']} | {payment['price']} руб.\n"
        text += f"📌 Статус: {payment['status']}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить товар")
def add_product_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(message.chat.id, "📝 Введите НАЗВАНИЕ товара:")
    bot.register_next_step_handler(msg, get_product_name)

def get_product_name(message):
    name = message.text
    msg = bot.send_message(message.chat.id, "📂 Категория (Ашық сабақ / AI видео):")
    bot.register_next_step_handler(msg, get_product_category, name)

def get_product_category(message, name):
    category = message.text
    msg = bot.send_message(message.chat.id, "💰 Введите ЦЕНУ (только цифры):")
    bot.register_next_step_handler(msg, get_product_price, name, category)

def get_product_price(message, name, category):
    try:
        price = int(message.text)
        msg = bot.send_message(message.chat.id, "📎 Отправьте ФАЙЛ (документ, фото, видео):")
        bot.register_next_step_handler(msg, get_product_file, name, category, price)
    except:
        bot.send_message(message.chat.id, "❌ Введите цифры!")
        add_product_start(message)

def get_product_file(message, name, category, price):
    if message.document:
        file_id = message.document.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id
    elif message.video:
        file_id = message.video.file_id
    else:
        bot.send_message(message.chat.id, "❌ Отправьте файл!")
        add_product_start(message)
        return
    
    cursor.execute("INSERT INTO products (name, category, price, file_id) VALUES (?, ?, ?, ?)",
                   (name, category, price, file_id))
    conn.commit()
    bot.send_message(message.chat.id, f"✅ Товар '{name}' добавлен! (Цена: {price} руб.)", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def show_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    products_count = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    users_count = cursor.execute("SELECT COUNT(DISTINCT user_id) FROM purchases").fetchone()[0]
    sales_count = cursor.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
    pending_count = len(pending_payments)
    
    bot.send_message(message.chat.id, 
                     f"📊 *Статистика магазина*\n\n"
                     f"📦 Товаров: {products_count}\n"
                     f"👥 Покупателей: {users_count}\n"
                     f"💰 Продаж: {sales_count}\n"
                     f"⏳ Ожидают оплаты: {pending_count}",
                     parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📦 Список товаров")
def list_products(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    products = cursor.execute("SELECT id, name, category, price FROM products").fetchall()
    if not products:
        bot.send_message(message.chat.id, "📭 Нет товаров")
        return
    
    text = "📦 *Список товаров:*\n\n"
    for p in products:
        text += f"🆔 {p[0]}. {p[1]}\n   📂 {p[2]} | 💰 {p[3]} руб.\n\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить товар")
def delete_product_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(message.chat.id, "🗑 Введите ID товара для удаления:\n\n/lista - чтобы увидеть список")
    bot.register_next_step_handler(msg, delete_product)

def delete_product(message):
    try:
        product_id = int(message.text)
        cursor.execute("SELECT name FROM products WHERE id=?", (product_id,))
        product = cursor.fetchone()
        if product:
            cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Товар '{product[0]}' удален!", reply_markup=admin_menu())
        else:
            bot.send_message(message.chat.id, "❌ Товар не найден")
    except:
        bot.send_message(message.chat.id, "❌ Введите ID цифрой!")

@bot.message_handler(commands=['lista'])
def list_products_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    products = cursor.execute("SELECT id, name, price FROM products").fetchall()
    if products:
        text = "📦 ID товаров:\n"
        for p in products:
            text += f"🔹 {p[0]} - {p[1]} ({p[2]} руб.)\n"
        bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, "📭 Нет товаров")

# ===== ЗАПУСК =====
if __name__ == "__main__":
    print("🚀 БОТ ЗАПУЩЕН!")
    print(f"👨‍💼 Админ ID: {ADMIN_ID}")
    print(f"📞 Менеджер: @{MANAGER_USERNAME}")
    bot.infinity_polling()
