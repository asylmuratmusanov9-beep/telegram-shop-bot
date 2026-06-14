import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import sqlite3
import os

BOT_TOKEN = "8699450261:AAHWOh4pVXD23O_rHXC1vpjzTl1VcjUBArg"
ADMIN_ID = 7717714437

bot = telebot.TeleBot(BOT_TOKEN)

# Подключение к БД
conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS products
                  (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price INTEGER, file_id TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS purchases
                  (user_id INTEGER, product_id INTEGER)''')
conn.commit()

# Клавиатуры
def user_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📚 Ашық сабақ"))
    markup.add(KeyboardButton("🤖 AI видеолар"))
    markup.add(KeyboardButton("🛒 Тапсырыс(24/7)"))
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("➕ Добавить товар"))
    markup.add(KeyboardButton("📊 Статистика"), KeyboardButton("📦 Список"))
    markup.add(KeyboardButton("🗑 Удалить товар"), KeyboardButton("🏠 Главное меню"))
    return markup

user_state = {}

# ===== ОСНОВНЫЕ КОМАНДЫ =====
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Қош келдіңіз!", reply_markup=user_menu())

@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "👨‍💼 Админ панелі:", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def back(message):
    bot.send_message(message.chat.id, "👋 Главное меню:", reply_markup=user_menu())

@bot.message_handler(func=lambda m: m.text == "📚 Ашық сабақ")
def show_lessons(message):
    cursor.execute("SELECT id, name, price FROM products WHERE category='Ашық сабақ'")
    products = cursor.fetchall()
    if products:
        for p in products:
            bot.send_message(message.chat.id, f"📘 {p[1]}\n💰 {p[2]} руб.\n/buy_{p[0]} - купить")
    else:
        bot.send_message(message.chat.id, "📭 Әлі өнім жоқ")

@bot.message_handler(func=lambda m: m.text == "🤖 AI видеолар")
def show_ai(message):
    cursor.execute("SELECT id, name, price FROM products WHERE category='AI видео'")
    products = cursor.fetchall()
    if products:
        for p in products:
            bot.send_message(message.chat.id, f"🎥 {p[1]}\n💰 {p[2]} руб.\n/buy_{p[0]} - купить")
    else:
        bot.send_message(message.chat.id, "📭 Әлі өнім жоқ")

@bot.message_handler(func=lambda m: m.text == "🛒 Тапсырыс(24/7)")
def order(message):
    bot.send_message(message.chat.id, "📞 Байланыс: @Vajnigoi\n24/7 доступно")

# ===== ПОКУПКА =====
@bot.message_handler(func=lambda m: m.text.startswith("/buy_"))
def buy_product(message):
    pid = int(message.text.split("_")[1])
    user_id = message.from_user.id
    
    cursor.execute("SELECT * FROM purchases WHERE user_id=? AND product_id=?", (user_id, pid))
    if cursor.fetchone():
        cursor.execute("SELECT file_id, name FROM products WHERE id=?", (pid,))
        file_id, name = cursor.fetchone()
        bot.send_message(message.chat.id, f"✅ У вас есть: {name}")
        bot.send_document(message.chat.id, file_id)
    else:
        cursor.execute("SELECT name, price, file_id FROM products WHERE id=?", (pid,))
        prod = cursor.fetchone()
        if prod:
            name, price, file_id = prod
            cursor.execute("INSERT INTO purchases VALUES (?, ?)", (user_id, pid))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Куплено: {name}\n💰 {price} руб.")
            bot.send_document(message.chat.id, file_id)
        else:
            bot.send_message(message.chat.id, "❌ Товар не найден")

# ===== АДМИН: ДОБАВЛЕНИЕ ТОВАРА (ПОШАГОВО) =====
@bot.message_handler(func=lambda m: m.text == "➕ Добавить товар")
def add_product_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    user_state[message.chat.id] = {"step": "name"}
    bot.send_message(message.chat.id, "📝 Введите НАЗВАНИЕ:")

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    pc = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    uc = cursor.execute("SELECT COUNT(DISTINCT user_id) FROM purchases").fetchone()[0]
    sc = cursor.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
    bot.send_message(message.chat.id, f"📊 Статистика:\n📦 Товаров: {pc}\n👥 Покупателей: {uc}\n💰 Продаж: {sc}")

@bot.message_handler(func=lambda m: m.text == "📦 Список")
def list_products(message):
    if message.from_user.id != ADMIN_ID:
        return
    products = cursor.execute("SELECT id, name, price FROM products").fetchall()
    if products:
        msg = "📦 Товары:\n"
        for p in products:
            msg += f"{p[0]}. {p[1]} - {p[2]} руб.\n"
        bot.send_message(message.chat.id, msg)
    else:
        bot.send_message(message.chat.id, "📭 Нет товаров")

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить товар")
def delete_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "🗑 Введите ID товара:\nПример: /del 1")

@bot.message_handler(commands=['del'])
def delete_product(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        pid = int(message.text.split()[1])
        cursor.execute("SELECT name FROM products WHERE id=?", (pid,))
        name = cursor.fetchone()
        if name:
            cursor.execute("DELETE FROM products WHERE id=?", (pid,))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Удалено: {name[0]}")
        else:
            bot.send_message(message.chat.id, "❌ Товар не найден")
    except:
        bot.send_message(message.chat.id, "❌ Используйте: /del 1")

# ===== ОБРАБОТКА ТЕКСТА (ДЛЯ ПОШАГОВОГО ДОБАВЛЕНИЯ) =====
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    chat_id = message.chat.id
    if chat_id in user_state:
        state = user_state[chat_id]
        step = state.get("step")
        
        if step == "name":
            state["name"] = message.text
            state["step"] = "category"
            bot.send_message(chat_id, "📂 Категория (Ашық сабақ / AI видео):")
        elif step == "category":
            state["category"] = message.text
            state["step"] = "price"
            bot.send_message(chat_id, "💰 Цена (только цифры):")
        elif step == "price":
            try:
                state["price"] = int(message.text)
                state["step"] = "file"
                bot.send_message(chat_id, "📎 Отправьте ФАЙЛ (документ, фото или видео):")
            except:
                bot.send_message(chat_id, "❌ Введите цифры!")
        elif step == "file":
            del user_state[chat_id]
    else:
        bot.send_message(chat_id, "❓ Отправь /start")

# ===== ОБРАБОТКА ФАЙЛОВ (ДОКУМЕНТЫ, ФОТО, ВИДЕО) =====
@bot.message_handler(content_types=['document', 'photo', 'video'])
def handle_file(message):
    chat_id = message.chat.id
    
    # Определяем тип файла и получаем file_id
    if message.document:
        file_id = message.document.file_id
        file_type = "документ"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "фото"
    elif message.video:
        file_id = message.video.file_id
        file_type = "видео"
    else:
        bot.send_message(chat_id, "❌ Неподдерживаемый тип файла")
        return
    
    # Если админ в режиме добавления товара
    if chat_id in user_state and user_state[chat_id].get("step") == "file":
        data = user_state[chat_id]
        cursor.execute("INSERT INTO products (name, category, price, file_id) VALUES (?, ?, ?, ?)",
                       (data["name"], data["category"], data["price"], file_id))
        conn.commit()
        bot.send_message(chat_id, f"✅ Товар '{data['name']}' добавлен!", reply_markup=admin_menu())
        del user_state[chat_id]
    else:
        # Если просто отправили файл - показываем file_id
        bot.send_message(
            chat_id, 
            f"✅ {file_type.upper()} получен!\n\n"
            f"🆔 FILE_ID:\n`{file_id}`\n\n"
            f"📌 Используй команду:\n"
            f"`/add |Название|Категория|Цена|{file_id}`\n\n"
            f"Или нажми «➕ Добавить товар» в админ-панели",
            parse_mode="Markdown"
        )

print("🚀 БОТ ЗАПУЩЕН!")
# ===== СИСТЕМА РУЧНОГО ПОДТВЕРЖДЕНИЯ ОПЛАТЫ =====
pending_payments = {}  # {user_id: {"product_id": id, "product_name": name, "price": price, "status": "waiting"}}

@bot.message_handler(func=lambda m: m.text.startswith("/buy_"))
def request_payment(message):
    """Обработчик покупки - просит оплатить и отправить чек"""
    try:
        product_id = int(message.text.split("_")[1])
    except:
        bot.reply_to(message, "❌ Неверная команда. Используй: /buy_1")
        return
    
    # Получаем информацию о товаре из БД
    cursor.execute("SELECT name, price, file_id FROM products WHERE id=?", (product_id,))
    product = cursor.fetchone()
    
    if not product:
        bot.reply_to(message, "❌ Товар не найден")
        return
    
    product_name, price, file_id = product
    
    # Сохраняем в ожидающие платежи
    pending_payments[message.from_user.id] = {
        "product_id": product_id,
        "product_name": product_name,
        "price": price,
        "status": "waiting"
    }
    
    # Отправляем реквизиты для оплаты
    bot.send_message(
        message.chat.id,
        f"💳 *Оплата товара:* {product_name}\n"
        f"💰 *Сумма:* {price} руб.\n\n"
        f"📌 *Реквизиты для оплаты:*\n"
        f"┌─────────────────────┐\n"
        f"│  Карта: 1234 5678 9012 3456\n"
        f"│  Получатель: Иван Иванов\n"
        f"│  Сумма: {price} руб.\n"
        f"└─────────────────────┘\n\n"
        f"✅ *После оплаты:*\n"
        f"1. Нажми кнопку «📤 Отправить чек»\n"
        f"2. Отправь СКРИНШОТ или ФОТО чека\n"
        f"3. Админ проверит и отправит файл\n\n"
        f"⏳ Ожидание подтверждения...",
        parse_mode="Markdown",
        reply_markup=telebot.types.InlineKeyboardMarkup().add(
            telebot.types.InlineKeyboardButton("📤 Отправить чек", callback_data=f"send_receipt_{product_id}")
        )
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_receipt_"))
def ask_for_receipt(call):
    """Просит пользователя отправить чек"""
    product_id = int(call.data.split("_")[2])
    
    bot.edit_message_text(
        "📸 *Отправь ФОТО или СКРИНШОТ чека:*\n\n"
        "Просто отправь мне изображение чека, и админ его проверит.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    """Пользователь отправляет чек - пересылаем админу"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username or "нет юзернейма"
    
    # Проверяем, есть ли ожидающий платеж
    if user_id not in pending_payments:
        bot.reply_to(message, "❌ У тебя нет активных платежей. Сначала отправь /buy_ID")
        return
    
    payment = pending_payments[user_id]
    
    # Получаем file_id фото
    file_id = message.photo[-1].file_id
    
    # Отправляем админу информацию + чек
    admin_text = (
        f"💰 *НОВЫЙ ПЛАТЕЖ!*\n\n"
        f"👤 Пользователь: {user_name} (@{user_username})\n"
        f"🆔 ID: `{user_id}`\n"
        f"📦 Товар: {payment['product_name']}\n"
        f"💰 Сумма: {payment['price']} руб.\n\n"
        f"✅ Подтвердить оплату: /confirm_{user_id}\n"
        f"❌ Отказать: /reject_{user_id}"
    )
    
    # Отправляем админу чек и информацию
    bot.send_photo(ADMIN_ID, file_id, caption=admin_text, parse_mode="Markdown")
    
    # Уведомляем пользователя
    bot.reply_to(
        message,
        f"✅ Чек отправлен администратору!\n"
        f"📦 Товар: {payment['product_name']}\n"
        f"💰 Сумма: {payment['price']} руб.\n\n"
        f"⏳ Ожидай подтверждения. Админ скоро проверит платеж."
    )
    
    # Обновляем статус
    payment["status"] = "checking"

@bot.message_handler(commands=['confirm'])
def confirm_payment(message):
    """Админ подтверждает оплату"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Доступ запрещен")
        return
    
    try:
        user_id = int(message.text.split()[1])
    except:
        bot.reply_to(message, "❌ Используй: /confirm 123456789")
        return
    
    if user_id not in pending_payments:
        bot.reply_to(message, f"❌ Платеж для пользователя {user_id} не найден")
        return
    
    payment = pending_payments[user_id]
    product_id = payment["product_id"]
    
    # Получаем файл товара
    cursor.execute("SELECT file_id, name FROM products WHERE id=?", (product_id,))
    file_id, product_name = cursor.fetchone()
    
    # Сохраняем покупку
    cursor.execute("INSERT INTO purchases (user_id, product_id) VALUES (?, ?)", (user_id, product_id))
    conn.commit()
    
    # Отправляем файл пользователю
    bot.send_message(user_id, f"✅ *Оплата подтверждена!*\n\n📦 Товар: {product_name}\n📎 Вот твой файл:", parse_mode="Markdown")
    bot.send_document(user_id, file_id)
    
    # Уведомляем админа
    bot.reply_to(message, f"✅ Товар '{product_name}' отправлен пользователю {user_id}")
    
    # Удаляем из ожидающих
    del pending_payments[user_id]

@bot.message_handler(commands=['reject'])
def reject_payment(message):
    """Админ отклоняет оплату"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Доступ запрещен")
        return
    
    try:
        user_id = int(message.text.split()[1])
    except:
        bot.reply_to(message, "❌ Используй: /reject 123456789")
        return
    
    if user_id not in pending_payments:
        bot.reply_to(message, f"❌ Платеж для пользователя {user_id} не найден")
        return
    
    payment = pending_payments[user_id]
    
    # Уведомляем пользователя
    bot.send_message(
        user_id,
        f"❌ *Оплата НЕ подтверждена!*\n\n"
        f"📦 Товар: {payment['product_name']}\n"
        f"💰 Сумма: {payment['price']} руб.\n\n"
        f"⚠️ Возможные причины:\n"
        f"• Чек не читается\n"
        f"• Неверная сумма\n"
        f"• Другая карта получателя\n\n"
        f"📞 Свяжись с менеджером: @manager",
        parse_mode="Markdown"
    )
    
    bot.reply_to(message, f"❌ Платеж пользователя {user_id} отклонен")
    del pending_payments[user_id]

@bot.message_handler(commands=['pending'])
def show_pending(message):
    """Админ показывает ожидающие платежи"""
    if message.from_user.id != ADMIN_ID:
        return
    
    if not pending_payments:
        bot.reply_to(message, "📭 Нет ожидающих платежей")
        return
    
    text = "💰 *Ожидающие платежи:*\n\n"
    for user_id, payment in pending_payments.items():
        text += f"👤 ID: `{user_id}`\n"
        text += f"📦 {payment['product_name']} | {payment['price']} руб.\n"
        text += f"📌 Статус: {payment['status']}\n"
        text += f"🔹 /confirm_{user_id} - подтвердить\n"
        text += f"🔸 /reject_{user_id} - отклонить\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
bot.infinity_polling()
