import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

# 🔑 Вставь API-токен
API_TOKEN = "ТВОЙ_ТОКЕН_БОТА"

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# 📌 Создаём базу данных
async def init_db():
    async with aiosqlite.connect("blogger.db") as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS keywords (
                keyword TEXT PRIMARY KEY,
                response TEXT
            )"""
        )
        await db.commit()

# 🏁 Команда /start
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id

    # Добавляем пользователя в базу (если его там нет)
    async with aiosqlite.connect("blogger.db") as db:
        await db.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
        await db.commit()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💌 Получить рассылку", callback_data="subscribe")],
            [InlineKeyboardButton(text="❌ Отписаться", callback_data="unsubscribe")]
        ]
    )

    await message.answer("Привет! Я бот-помощник блогера. 📢\n\n"
                         "📌 Подпишись на обновления, чтобы получать важные сообщения!\n"
                         "💡 Напиши ключевое слово, и я подскажу тебе информацию.", reply_markup=keyboard)

# ✅ Подписка
@dp.callback_query(lambda c: c.data == "subscribe")
async def subscribe(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    async with aiosqlite.connect("blogger.db") as db:
        await db.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
        await db.commit()

    await callback_query.message.answer("✅ Ты подписался на рассылку!")
    await callback_query.answer()

# ❌ Отписка
@dp.callback_query(lambda c: c.data == "unsubscribe")
async def unsubscribe(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    async with aiosqlite.connect("blogger.db") as db:
        await db.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
        await db.commit()

    await callback_query.message.answer("❌ Ты отписался от рассылки.")
    await callback_query.answer()

# 📢 Рассылка сообщения (только для админов)
@dp.message(Command("broadcast"))
async def broadcast(message: Message):
    if message.chat.type != "private":
        return

    # Проверяем, является ли отправитель админом
    if message.from_user.id not in [123456789, 987654321]:  # Укажи свой Telegram ID
        await message.answer("❌ У тебя нет прав на рассылку.")
        return

    try:
        text = message.text.split(" ", 1)[1]  # Получаем текст после команды
        async with aiosqlite.connect("blogger.db") as db:
            cursor = await db.execute("SELECT user_id FROM subscribers")
            subscribers = await cursor.fetchall()

        count = 0
        for user in subscribers:
            try:
                await bot.send_message(user[0], f"📢 Рассылка:\n\n{text}")
                count += 1
            except:
                pass

        await message.answer(f"✅ Сообщение отправлено {count} подписчикам!")
    except IndexError:
        await message.answer("⚠️ Использование: /broadcast <текст сообщения>")

# 📌 Автоответы по ключевым словам
@dp.message()
async def auto_reply(message: Message):
    user_text = message.text.lower()
    
    async with aiosqlite.connect("blogger.db") as db:
        cursor = await db.execute("SELECT response FROM keywords WHERE keyword = ?", (user_text,))
        response = await cursor.fetchone()

    if response:
        await message.answer(response[0])

# ➕ Добавление автоответа (только админы)
@dp.message(Command("add_reply"))
async def add_reply(message: Message):
    if message.chat.type != "private":
        return

    if message.from_user.id not in [123456789, 987654321]:  # Укажи свой Telegram ID
        await message.answer("❌ У тебя нет прав на добавление автоответов.")
        return

    try:
        _, keyword, response = message.text.split(";", 2)
        keyword = keyword.strip().lower()
        response = response.strip()

        async with aiosqlite.connect("blogger.db") as db:
            await db.execute("INSERT OR REPLACE INTO keywords (keyword, response) VALUES (?, ?)", (keyword, response))
            await db.commit()

        await message.answer(f"✅ Добавлен автоответ:\n\n🔑 {keyword}\n💡 {response}")
    except ValueError:
        await message.answer("⚠️ Использование: /add_reply <ключевое слово>; <ответ>")

# 🚀 Запуск бота
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
