import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from aiogram.utils.markdown import hbold
from aiogram.client.default import DefaultBotProperties

# 🔑 Вставь API-токен
API_TOKEN = "ТВОЙ_ТОКЕН_БОТА"

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# 📌 Создаём базу данных для автоответов
async def init_db():
    async with aiosqlite.connect("moderator.db") as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                answer TEXT
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS warnings (
                user_id INTEGER PRIMARY KEY,
                count INTEGER DEFAULT 0
            )"""
        )
        await db.commit()

# ⚠️ Чёрный список слов (мат, спам и т. д.)
BAD_WORDS = ["лох", "сука", "пидор", "казино", "http", "https"]

# 🚀 Команда /start (только в ЛС)
@dp.message(Command("start"))
async def start(message: Message):
    if message.chat.type == "private":
        await message.answer("Привет! Я бот-модератор группы. Добавь меня в чат и дай права администратора.")

# 📌 Автоответы
@dp.message(Command("faq"))
async def faq_list(message: Message):
    async with aiosqlite.connect("moderator.db") as db:
        cursor = await db.execute("SELECT question FROM faq")
        questions = await cursor.fetchall()

    if not questions:
        await message.answer("❌ В базе пока нет часто задаваемых вопросов.")
        return

    text = "📌 <b>Часто задаваемые вопросы:</b>\n\n"
    for q in questions:
        text += f"🔹 {q[0]}\n"
    text += "\nЧтобы узнать ответ, напиши: /answer <вопрос>"

    await message.answer(text)

@dp.message(Command("answer"))
async def answer(message: Message):
    try:
        question = message.text.split(" ", 1)[1].strip().lower()
        async with aiosqlite.connect("moderator.db") as db:
            cursor = await db.execute("SELECT answer FROM faq WHERE question = ?", (question,))
            result = await cursor.fetchone()

        if result:
            await message.answer(f"❓ <b>{question.capitalize()}</b>\n\n💡 {result[0]}")
        else:
            await message.answer("❌ Ответ на этот вопрос не найден.")
    except IndexError:
        await message.answer("⚠️ Использование: /answer <вопрос>")

# ➕ Добавление нового FAQ (только для админов)
@dp.message(Command("add_faq"))
async def add_faq(message: Message):
    if message.chat.type == "private":
        await message.answer("⚠️ Эту команду можно использовать только в группе.")
        return

    user = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if not user.is_chat_admin():
        await message.answer("❌ Только администратор может добавлять FAQ.")
        return

    try:
        _, question, answer = message.text.split(";", 2)
        question = question.strip().lower()
        answer = answer.strip()

        async with aiosqlite.connect("moderator.db") as db:
            await db.execute("INSERT INTO faq (question, answer) VALUES (?, ?)", (question, answer))
            await db.commit()

        await message.answer(f"✅ Добавлен новый FAQ:\n\n❓ {hbold(question)}\n💡 {answer}")
    except ValueError:
        await message.answer("⚠️ Использование: /add_faq <вопрос>; <ответ>")

# ❌ Фильтрация мата и спама
@dp.message()
async def filter_bad_words(message: Message):
    if message.chat.type == "private":
        return  # Не фильтруем ЛС

    if any(bad_word in message.text.lower() for bad_word in BAD_WORDS):
        await message.delete()
        async with aiosqlite.connect("moderator.db") as db:
            cursor = await db.execute("SELECT count FROM warnings WHERE user_id = ?", (message.from_user.id,))
            result = await cursor.fetchone()

            warnings = result[0] + 1 if result else 1
            await db.execute("INSERT OR REPLACE INTO warnings (user_id, count) VALUES (?, ?)", 
                             (message.from_user.id, warnings))
            await db.commit()

        if warnings >= 3:
            await bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await message.answer(f"🚫 {message.from_user.full_name} получил мут за спам/мат (3 предупреждения).")
        else:
            await message.answer(f"⚠️ {message.from_user.full_name}, не используй запрещённые слова! (Предупреждение {warnings}/3)")

# 🚀 Запуск бота
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
