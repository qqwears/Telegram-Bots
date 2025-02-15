import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# 🔑 Вставь свой API-токен
API_TOKEN = "ТВОЙ_ТОКЕН_БОТА"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# 📌 Создаём базу данных
async def init_db():
    async with aiosqlite.connect("expenses.db") as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                category TEXT
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                currency TEXT DEFAULT "₽"
            )"""
        )
        await db.commit()

# 🔘 Главное меню с кнопками
def main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить расход"), KeyboardButton(text="📊 Баланс")],
            [KeyboardButton(text="📜 История"), KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True
    )
    return keyboard

# 🎛 Настройки
def settings_menu():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Валюта", callback_data="change_currency")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ]
    )
    return keyboard

# 🏁 Команда /start
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Привет! Я бот для учёта расходов 💰", reply_markup=main_menu())

# ➕ Добавление расхода
@dp.message(lambda message: message.text == "➕ Добавить расход")
async def add_expense_prompt(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍔 Еда", callback_data="add_expense_еда"),
             InlineKeyboardButton(text="🚕 Транспорт", callback_data="add_expense_транспорт")],
            [InlineKeyboardButton(text="🎉 Развлечения", callback_data="add_expense_развлечения")],
            [InlineKeyboardButton(text="🛍 Покупки", callback_data="add_expense_покупки")]
        ]
    )
    await message.answer("Выбери категорию расхода:", reply_markup=keyboard)

# Обработка выбора категории
@dp.callback_query(lambda c: c.data.startswith("add_expense_"))
async def process_add_expense(callback_query: types.CallbackQuery):
    category = callback_query.data.split("_")[2]
    await callback_query.message.answer(f"Введите сумму расхода на {category} (например: `500`)", parse_mode="Markdown")

    @dp.message()
    async def add_expense_amount(message: Message):
        try:
            amount = float(message.text)

            # Получаем текущую валюту
            async with aiosqlite.connect("expenses.db") as db:
                cursor = await db.execute("SELECT currency FROM settings WHERE user_id = ?", (message.from_user.id,))
                currency = await cursor.fetchone()
                currency = currency[0] if currency else "₽"

                await db.execute("INSERT INTO expenses (user_id, amount, category) VALUES (?, ?, ?)", 
                                 (message.from_user.id, amount, category))
                await db.commit()

            await message.answer(f"✅ Записано: {amount}{currency} на {category}")
        except ValueError:
            await message.answer("⚠️ Ошибка! Введите сумму числом.")

# 📊 Баланс
@dp.message(lambda message: message.text == "📊 Баланс")
async def balance(message: Message):
    async with aiosqlite.connect("expenses.db") as db:
        cursor = await db.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ?", (message.from_user.id,))
        total = await cursor.fetchone()

        cursor = await db.execute("SELECT currency FROM settings WHERE user_id = ?", (message.from_user.id,))
        currency = await cursor.fetchone()
        currency = currency[0] if currency else "₽"

    balance = total[0] if total[0] else 0
    await message.answer(f"💰 Твой общий расход: {balance}{currency}")

# 📜 История
@dp.message(lambda message: message.text == "📜 История")
async def history(message: Message):
    async with aiosqlite.connect("expenses.db") as db:
        cursor = await db.execute("SELECT amount, category FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 5", 
                                  (message.from_user.id,))
        expenses = await cursor.fetchall()

        cursor = await db.execute("SELECT currency FROM settings WHERE user_id = ?", (message.from_user.id,))
        currency = await cursor.fetchone()
        currency = currency[0] if currency else "₽"

    if not expenses:
        await message.answer("📭 История пуста!")
        return
    
    history_text = "📜 Последние 5 расходов:\n"
    for amount, category in expenses:
        history_text += f"💸 {amount}{currency} — {category}\n"
    
    await message.answer(history_text)

# ⚙️ Настройки
@dp.message(lambda message: message.text == "⚙️ Настройки")
async def settings(message: Message):
    await message.answer("⚙️ Настройки", reply_markup=settings_menu())

# 💰 Выбор валюты
@dp.callback_query(lambda c: c.data == "change_currency")
async def change_currency(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Рубли (₽)", callback_data="currency_₽"),
             InlineKeyboardButton(text="🇺🇸 Доллары ($)", callback_data="currency_$")],
            [InlineKeyboardButton(text="🇪🇺 Евро (€)", callback_data="currency_€")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")]
        ]
    )
    await callback_query.message.edit_text("Выбери валюту:", reply_markup=keyboard)

# Обновление валюты
@dp.callback_query(lambda c: c.data.startswith("currency_"))
async def update_currency(callback_query: types.CallbackQuery):
    currency = callback_query.data.split("_")[1]
    
    async with aiosqlite.connect("expenses.db") as db:
        await db.execute("INSERT OR REPLACE INTO settings (user_id, currency) VALUES (?, ?)", 
                         (callback_query.from_user.id, currency))
        await db.commit()

    await callback_query.message.edit_text(f"✅ Валюта изменена на {currency}")

# 🔙 Возвращение назад
@dp.callback_query(lambda c: c.data.startswith("back_to_"))
async def go_back(callback_query: types.CallbackQuery):
    if callback_query.data == "back_to_main":
        await callback_query.message.edit_text("🔙 Главное меню", reply_markup=main_menu())
    elif callback_query.data == "back_to_settings":
        await callback_query.message.edit_text("⚙️ Настройки", reply_markup=settings_menu())

# 🚀 Запуск бота
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
