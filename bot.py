import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import time

BOT_TOKEN = "8699450261:AAHWOh4pVXD23O_rHXC1vpjzTl1VcjUBArg"
ADMIN_ID = 7717714437
MANAGER_USERNAME = "Vajnigoi"

bot = telebot.TeleBot(BOT_TOKEN)

conn = sqlite3.connect('shop.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS products
                  (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price INTEGER, file_id TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS purchases
                  (user_id INTEGER, product_id INTEGER)''')
conn.commit()

def user_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📚 Ашық сабақ"), KeyboardButton("🤖 AI видеолар"))
    markup.add(KeyboardButton("🛒 Тапсырыс(24/7)"))
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("➕ Добавить товар"))
    markup.add(KeyboardButton("📊 Статистика"), KeyboardButton("📦 Список товаров"))
    markup.add(KeyboardButton("🗑 Удалить товар"))
    markup.add(KeyboardButton("🏠 Главное меню"))
    return markup

# ===== КОМАНДЫ =====
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Қош келдіңіз!", reply_markup=user_menu())

@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "👨‍💼 Админ панелі:", reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, "⛔ Доступ запрещен!")

@bot.message_handler(commands=['lista'])
def lista(message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT id, name, price FROM products")
    products = cursor.fetchall()
    if products:
        text = "📦 Товары:\n"
        for p in products:
            text += f"🔹 {p[0]}. {p[1]} - {p[2]} руб.\n"
        bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, "📭 Нет товаров")

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
            bot.send_message(message.chat.id, "❌ Не найден")
    except:
        bot.send_message(message.chat.id, "❌ /del 1")

@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def back(message):
    bot.send_message(message.chat.id, "👋 Главное меню:", reply_markup=user_menu())

@bot.message_handler(func=lambda m: m.text == "📚 Ашық сабақ")
def show_lessons(message):
    cursor.execute("SELECT id, name, price FROM products WHERE category='Ашық сабақ'")
    products = cursor.fetchall()
    if products:
        for p in products:
            markup = InlineKeyboardMarkup()
            btn = InlineKeyboardButton(f"💳 Купить {p[2]} руб", callback_data=f"buy_{p[0]}")
            markup.add(btn)
            bot.send_message(message.chat.id, f"📘 {p[1]}\n💰 {p[2]} руб.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "📭 Әлі өнім жоқ")

@bot.message_handler(func=lambda m: m.text == "🤖 AI видеолар")
def show_ai(message):
    cursor.execute("SELECT id, name, price FROM products WHERE category='AI видео'")
    products = cursor.fetchall()
    if products:
        for p in products:
            markup = InlineKeyboardMarkup()
            btn = InlineKeyboardButton(f"💳 Купить {p[2]} руб", callback_data=f"buy_{p[0]}")
            markup.add(btn)
            bot.send_message(message.chat.id, f"🎥 {p[1]}\n💰 {p[2]} руб.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "📭 Әлі өнім жоқ")

@bot.message_handler(func=lambda m: m.text == "🛒 Тапсырыс(24/7)")
def order(message):
    bot.send_message(message.chat.id, f"📞 Менеджер: @{MANAGER_USERNAME}\n24/7")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy(call):
    pid = int(call.data.split("_")[1])
    user_id = call.from_user.id
    
    cursor.execute("SELECT * FROM purchases WHERE user_id=? AND product_id=?", (user_id, pid))
    if cursor.fetchone():
        cursor.execute("SELECT file_id, name FROM products WHERE id=?", (pid,))
        file_id, name = cursor.fetchone()
        bot.send_message(call.message.chat.id, f"✅ У вас есть: {name}")
        bot.send_document(call.message.chat.id, file_id)
    else:
        cursor.execute("SELECT name, price, file_id FROM products WHERE id=?", (pid,))
        prod = cursor.fetchone()
        if prod:
            name, price, file_id = prod
            cursor.execute("INSERT INTO purchases VALUES (?, ?)", (user_id, pid))
            conn.commit()
            bot.send_message(call.message.chat.id, f"✅ Куплено: {name}\n💰 {price} руб.")
            bot.send_document(call.message.chat.id, file_id)
        else:
            bot.send_message(call.message.chat.id, "❌ Не найден")
    bot.answer_callback_query(call.id)

# ===== АДМИН КНОПКИ =====
@bot.message_handler(func=lambda m: m.text == "➕ Добавить товар")
def add_product_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "📝 Отправь командой:\n`/add |Название|Категория|Цена|file_id`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text.startswith("/add"))
def add_product(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split("|")
        if len(parts) >= 5:
            _, name, category, price, file_id = parts[:5]
            cursor.execute("INSERT INTO products (name, category, price, file_id) VALUES (?, ?, ?, ?)",
                           (name, category, int(price), file_id))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Товар '{name}' добавлен!")
        else:
            bot.send_message(message.chat.id, "❌ Формат: `/add |Название|Категория|Цена|file_id`", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    pc = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    uc = cursor.execute("SELECT COUNT(DISTINCT user_id) FROM purchases").fetchone()[0]
    sc = cursor.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
    bot.send_message(message.chat.id, f"📊 Статистика:\n📦 {pc}\n👥 {uc}\n💰 {sc}")

@bot.message_handler(func=lambda m: m.text == "📦 Список товаров")
def list_products(message):
    if message.from_user.id != ADMIN_ID:
        return
    products = cursor.execute("SELECT id, name, price FROM products").fetchall()
    if products:
        text = "📦 Товары:\n"
        for p in products:
            text += f"{p[0]}. {p[1]} - {p[2]} руб.\n"
        bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, "📭 Нет товаров")

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить товар")
def delete_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "🗑 /del 1")

print("🚀 БОТ ЗАПУЩЕН!")
bot.infinity_polling()
