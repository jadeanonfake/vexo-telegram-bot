import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

SERVICES = {
    "business_card": "Визитка", "logo": "Логотип", "banner": "Баннер",
    "emoji": "Анимированные эмодзи / стикеры", "other": "Другое"
}

class OrderForm(StatesGroup):
    service = State()
    description = State()
    style = State()
    contact = State()

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Заказать дизайн", callback_data="order")],
        [InlineKeyboardButton(text="💰 Цены", callback_data="prices")],
        [InlineKeyboardButton(text="🧩 Услуги", callback_data="services")],
        [InlineKeyboardButton(text="✉️ Связаться с VEXO", url="https://t.me/anonjade")],
    ])

def service_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Визитка", callback_data="service:business_card"),
         InlineKeyboardButton(text="Логотип", callback_data="service:logo")],
        [InlineKeyboardButton(text="Баннер", callback_data="service:banner"),
         InlineKeyboardButton(text="Эмодзи / стикеры", callback_data="service:emoji")],
        [InlineKeyboardButton(text="Другое", callback_data="service:other")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")],
    ])

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Это бот заявок VEXO.\n\nЗдесь можно посмотреть услуги, узнать, как уточнить стоимость, и оставить заявку на дизайн.",
        reply_markup=main_keyboard()
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer("Выбери нужный раздел в меню ниже.", reply_markup=main_keyboard())

@dp.callback_query(F.data == "services")
async def services(callback: CallbackQuery):
    await callback.message.answer(
        "Услуги VEXO:\n• Дизайн визиток\n• Логотипы\n• Баннеры\n• Анимированные эмодзи и стикеры\n• Другие графические материалы",
        reply_markup=main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "prices")
async def prices(callback: CallbackQuery):
    await callback.message.answer(
        "💰 Стоимость зависит от сложности и объёма работы.\n\nЧтобы узнать точную цену, нажми «Заказать дизайн» и опиши задачу. Мы уточним детали.",
        reply_markup=main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "order")
async def begin_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(OrderForm.service)
    await callback.message.answer("Что нужно сделать?", reply_markup=service_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service_key = callback.data.split(":", 1)[1]
    if service_key not in SERVICES:
        await callback.answer("Неизвестная услуга", show_alert=True)
        return
    await state.update_data(service=SERVICES[service_key])
    await state.set_state(OrderForm.description)
    await callback.message.answer("Опиши, что именно нужно сделать, одним сообщением.")
    await callback.answer()

@dp.message(OrderForm.description)
async def get_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text or "(описание не указано)")
    await state.set_state(OrderForm.style)
    await message.answer("Какой стиль хочешь? Например: строгий, минимализм, киберпанк, чёрный/серебро. Если без разницы — напиши «на выбор».")

@dp.message(OrderForm.style)
async def get_style(message: Message, state: FSMContext):
    await state.update_data(style=message.text or "Не указан")
    await state.set_state(OrderForm.contact)
    await message.answer("Как с тобой связаться? Напиши свой @username в Telegram. Не отправляй пароли и коды.")

@dp.message(OrderForm.contact)
async def get_contact(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    contact = message.text or "Не указан"
    user = message.from_user
    username = f"@{user.username}" if user and user.username else "не указан"
    order_text = (
        "🆕 <b>Новая заявка VEXO</b>\n\n"
        f"<b>Услуга:</b> {data.get('service', 'Не указана')}\n"
        f"<b>Описание:</b> {data.get('description', 'Не указано')}\n"
        f"<b>Стиль:</b> {data.get('style', 'Не указан')}\n"
        f"<b>Контакт клиента:</b> {contact}\n"
        f"<b>Telegram клиента:</b> {username}\n"
        f"<b>ID клиента:</b> {user.id if user else 'неизвестен'}"
    )
    delivered = False
    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(int(ADMIN_CHAT_ID), order_text)
            delivered = True
        except Exception:
            logging.exception("Could not send order to ADMIN_CHAT_ID")
    await state.clear()
    if delivered:
        await message.answer("✅ Заявка отправлена! VEXO свяжется с тобой после просмотра деталей.", reply_markup=main_keyboard())
    else:
        await message.answer("✅ Заявка заполнена, но автоматическая отправка владельцу ещё не настроена. Напиши напрямую: @anonjade\n\nПосле настройки ADMIN_CHAT_ID заявки будут приходить автоматически.", reply_markup=main_keyboard())

@dp.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Оформление заявки отменено.", reply_markup=main_keyboard())
    await callback.answer()

async def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN. Добавь токен в переменные окружения хостинга.")
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
