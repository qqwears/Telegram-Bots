import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

# 🔑 Вставь API-токен
API_TOKEN = "ТВОЙ_ТОКЕН_БОТА"

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# 📌 Создаём базу данных
async def init_db():
    async with aiosqlite.connect("hr_bot.db") as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                name TEXT,
                experience TEXT,
                skills TEXT,
                stage TEXT
            )"""
        )
        await db.commit()

# 🏁 Команда /start
@dp.message(Command("start"))
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Начать собеседование", callback_data="start_interview")]
        ]
    )
    await message.answer("Привет! Я бот-рекрутер 🤖\n\n"
                         "Я помогу провести собеседование и передам твои данные HR-менеджеру.", 
                         reply_markup=keyboard)

# 📝 Начинаем собеседование
@dp.callback_query(lambda c: c.data == "start_interview")
async def start_interview(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    async with aiosqlite.connect("hr_bot.db") as db:
        await db.execute("INSERT OR REPLACE INTO candidates (user_id, stage) VALUES (?, ?)", 
                         (user_id, "name"))
        await db.commit()

    await callback_query.message.answer("📝 Давай начнем!\nКак тебя зовут?")
    await callback_query.answer()

# 📌 Обработка ответов кандидата
@dp.message()
async def process_answers(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("hr_bot.db") as db:
        cursor = await db.execute("SELECT stage FROM candidates WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()

    if not result:
        await message.answer("❌ Ты ещё не начал собеседование. Нажми /start и начни заново.")
        return

    stage = result[0]

    async with aiosqlite.connect("hr_bot.db") as db:
        if stage == "name":
            await db.execute("UPDATE candidates SET name = ?, stage = 'experience' WHERE user_id = ?", 
                             (message.text, user_id))
            await db.commit()
            await message.answer(f"Отлично, {message.text}! 📌\nТеперь расскажи о своём опыте работы.")

        elif stage == "experience":
            await db.execute("UPDATE candidates SET experience = ?, stage = 'skills' WHERE user_id = ?", 
                             (message.text, user_id))
            await db.commit()
            await message.answer("Спасибо! 🔥 Теперь перечисли свои ключевые навыки через запятую (Python, SQL, Figma и т. д.).")

        elif stage == "skills":
            await db.execute("UPDATE candidates SET skills = ?, stage = NULL WHERE user_id = ?", 
                             (message.text, user_id))
            await db.commit()

            await message.answer("✅ Спасибо! Твои данные записаны и переданы HR-менеджеру. Мы свяжемся с тобой в ближайшее время. 📩")

# 📜 Просмотр всех кандидатов (только для HR)
@dp.message(Command("candidates"))
async def show_candidates(message: Message):
    if message.from_user.id not in [123456789, 987654321]:  # Укажи ID HR-менеджера
        await message.answer("❌ У тебя нет доступа к базе кандидатов.")
        return

    async with aiosqlite.connect("hr_bot.db") as db:
        cursor = await db.execute("SELECT name, experience, skills FROM candidates")
        candidates = await cursor.fetchall()

    if not candidates:
        await message.answer("📭 База кандидатов пуста.")
        return
    
    text = "📜 <b>Список кандидатов:</b>\n\n"
    for name, experience, skills in candidates:
        text += f"👤 {name}\n📌 Опыт: {experience}\n💡 Навыки: {skills}\n\n"

    await message.answer(text)

# 🚀 Запуск бота
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
