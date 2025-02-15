import asyncio
import aiosqlite
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties

# 🔑 Вставь API-токены
API_TOKEN = "ТВОЙ_ТОКЕН_БОТА"
OPENAI_API_KEY = "ТВОЙ_OPENAI_API_КЛЮЧ"

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# 🔥 Настройки AI
openai.api_key = OPENAI_API_KEY
MAX_FREE_MESSAGES = 5  # Количество бесплатных сообщений для пользователя

# 📌 Создаём базу данных
async def init_db():
    async with aiosqlite.connect("ai_bot.db") as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                free_messages INTEGER DEFAULT 0
            )"""
        )
        await db.commit()

# 🏁 Команда /start
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Привет! Я AI-бот 🤖\n\n"
                         "Задавай мне вопросы, и я постараюсь ответить. У тебя есть 5 бесплатных запросов.\n"
                         "🔹 Чтобы сбросить лимит – напиши /reset")

# 🔥 AI-Ответы
@dp.message()
async def chatgpt_reply(message: Message):
    user_id = message.from_user.id

    async with aiosqlite.connect("ai_bot.db") as db:
        cursor = await db.execute("SELECT free_messages FROM users WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()

        free_messages = result[0] if result else 0

        # Если пользователь исчерпал лимит, отправляем сообщение
        if free_messages >= MAX_FREE_MESSAGES:
            await message.answer("❌ У тебя закончились бесплатные запросы. Напиши /reset, чтобы сбросить.")
            return

        # Обновляем количество использованных сообщений
        await db.execute("INSERT OR REPLACE INTO users (user_id, free_messages) VALUES (?, ?)", 
                         (user_id, free_messages + 1))
        await db.commit()

    # Отправляем запрос в OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message.text}]
        )
        answer = response["choices"][0]["message"]["content"]
    except Exception as e:
        answer = "⚠️ Ошибка: не могу получить ответ. Попробуй позже."

    await message.answer(answer)

# 🔄 Сброс лимита сообщений
@dp.message(Command("reset"))
async def reset_messages(message: Message):
    user_id = message.from_user.id

    async with aiosqlite.connect("ai_bot.db") as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()

    await message.answer("✅ Лимит бесплатных сообщений сброшен! Ты снова можешь задавать вопросы.")

# 🚀 Запуск бота
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
