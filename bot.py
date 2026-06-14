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
    bot.send_message(message.chat.id, "📞 Байланыс: @manager\n24/7 доступно")

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
bot.infinity_polling()
