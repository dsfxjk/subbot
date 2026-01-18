import asyncio
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import os

# Настройки
TOKEN = os.getenv("BOT_TOKEN")  # Берем токен из переменных окружения
bot = Bot(token=TOKEN)
dp = Dispatcher()


# Функции для работы с данными
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="/add"), types.KeyboardButton(text="/list")],
        [types.KeyboardButton(text="/del"), types.KeyboardButton(text="/soon")]
    ], resize_keyboard=True)

    await message.answer(
        "📅 Бот для подписок\n"
        "Команды:\n"
        "/add - добавить подписку\n"
        "/list - все подписки\n"
        "/del - удалить подписку\n"
        "/soon - ближайшие оплаты",
        reply_markup=keyboard
    )


# Добавить подписку
@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    await message.answer(
        "Введи данные в одну строку:\n"
        "<b>Название Сумма Дата(дд.мм)</b>\n\n"
        "Пример:\n"
        "<code>Netflix 399 15.01</code>",
        parse_mode="HTML"
    )


# Обработка добавления
@dp.message(lambda message: len(message.text.split()) == 3)
async def process_add(message: types.Message):
    try:
        name, amount, date_str = message.text.split()

        # Обработка даты
        day, month = map(int, date_str.split('.'))
        now = datetime.now()
        year = now.year

        # Если дата уже прошла в этом году, берем следующий год
        payment_date = datetime(year, month, day)
        if payment_date < now:
            payment_date = datetime(year + 1, month, day)

        date_formatted = payment_date.strftime("%Y-%m-%d")
        days_left = (payment_date - now).days

        # Сохранение
        data = load_data()
        user_id = str(message.from_user.id)

        if user_id not in data:
            data[user_id] = []

        data[user_id].append({
            'name': name,
            'amount': amount,
            'date': date_formatted
        })

        save_data(data)

        await message.answer(f"✅ Добавлено: {name}\n"
                             f"💳 {amount} руб.\n"
                             f"📅 {date_formatted}\n"
                             f"⏰ Через {days_left} дней")

    except Exception as e:
        await message.answer("❌ Ошибка формата. Пример: Netflix 399 15.01")


# Список подписок
@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)

    if user_id not in data or not data[user_id]:
        await message.answer("📭 Нет подписок")
        return

    text = "📋 Ваши подписки:\n\n"
    for i, sub in enumerate(data[user_id], 1):
        days = (datetime.strptime(sub['date'], "%Y-%m-%d") - datetime.now()).days
        text += f"{i}. {sub['name']} - {sub['amount']} руб.\n"
        text += f"   📅 {sub['date']} (через {days} дней)\n\n"

    await message.answer(text)


# Удалить подписку
@dp.message(Command("del"))
async def cmd_delete(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)

    if user_id not in data or not data[user_id]:
        await message.answer("📭 Нет подписок для удаления")
        return

    text = "Введи номер для удаления:\n\n"
    for i, sub in enumerate(data[user_id], 1):
        text += f"{i}. {sub['name']}\n"

    await message.answer(text)


# Обработка удаления
@dp.message(lambda message: message.text.isdigit())
async def process_delete(message: types.Message):
    num = int(message.text) - 1
    data = load_data()
    user_id = str(message.from_user.id)

    if user_id in data and 0 <= num < len(data[user_id]):
        removed = data[user_id].pop(num)
        save_data(data)
        await message.answer(f"🗑️ Удалено: {removed['name']}")
    else:
        await message.answer("❌ Неверный номер")


# Ближайшие оплаты
@dp.message(Command("soon"))
async def cmd_soon(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)

    if user_id not in data or not data[user_id]:
        await message.answer("📭 Нет подписок")
        return

    today = datetime.now()
    text = "⏰ Ближайшие оплаты:\n\n"

    for sub in data[user_id]:
        days = (datetime.strptime(sub['date'], "%Y-%m-%d") - today).days
        if 0 <= days <= 14:
            text += f"• {sub['name']} - {sub['amount']} руб.\n"
            text += f"  📅 {sub['date']} (через {days} дней)\n\n"

    if text == "⏰ Ближайшие оплаты:\n\n":
        text = "✅ В ближайшие 2 недели оплат нет"

    await message.answer(text)


# Авто-напоминания
async def check_reminders():
    while True:
        try:
            data = load_data()
            today = datetime.now()

            for user_id, subs in data.items():
                for sub in subs:
                    payment_date = datetime.strptime(sub['date'], "%Y-%m-%d")
                    days_left = (payment_date - today).days

                    if days_left in [7, 3, 1, 0]:
                        if days_left > 0:
                            msg = f"🔔 {sub['name']} - оплата через {days_left} дней"
                        else:
                            msg = f"🔔 {sub['name']} - оплатить сегодня!"

                        try:
                            await bot.send_message(int(user_id), msg)
                            await asyncio.sleep(0.5)
                        except:
                            pass

            await asyncio.sleep(3600)  # Проверка каждый час

        except Exception as e:
            print(f"Ошибка: {e}")
            await asyncio.sleep(300)


# Запуск
async def main():
    # Запускаем бота
    print("Бот запущен")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())