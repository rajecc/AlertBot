from aiogram import Router, F, Bot
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup,KeyboardButton
import logging
from datetime import datetime
from ai_tools import analyze_production_message, process_response
from database import get_active_downtimes,get_downtime_report,delete_old_downtimes

GROUP_ID = 4643470681
TARGET_USER_ID = 1685244410

# Создаем кнопки для меню
menu_buttons = [
    [KeyboardButton(text="Активные простои")],
    [KeyboardButton(text="Простои за день")],
    [KeyboardButton(text="Простои за неделю")],
    [KeyboardButton(text="Простои за месяц")]
]

menu_kb = ReplyKeyboardMarkup(keyboard=menu_buttons, resize_keyboard=True)

router = Router()

@router.message(CommandStart())
async def process_start_command(message: Message):
    await message.answer("Бот запущен", reply_markup = menu_kb)

# Обработчик для просмотра активных простоев
@router.message(F.text == "Активные простои")
async def show_active_downtimes(message: Message):
    active_downtimes = get_active_downtimes()
    if active_downtimes:
        response = "Активные простои:\n"
        for downtime in active_downtimes:
            response += f"Цех {downtime[0]}, Агрегат {downtime[1]}, Начало: {downtime[2]}\n"
    else:
        response = "Нет активных простоев."
    await message.answer(response, reply_markup=menu_kb)

# Обработчик для просмотра простоев за день
@router.message(F.text == "Простои за день")
async def show_downtimes_day(message: Message):
    report = get_downtime_report("day")
    if report:
        response = "Простои за последний день:\n"
        for downtime in report:
            response += f"Цех {downtime[0]}, Агрегат {downtime[1]}, Начало: {downtime[2]}, Конец: {downtime[3] or 'Еще не завершен'}\n"
    else:
        response = "Нет данных о простоях за день."
    await message.answer(response, reply_markup=menu_kb)

# Обработчик для просмотра простоев за неделю
@router.message(F.text == "Простои за неделю")
async def show_downtimes_week(message: Message):
    report = get_downtime_report("week")
    if report:
        response = "Простои за последнюю неделю:\n"
        for downtime in report:
            response += f"Цех {downtime[0]}, Агрегат {downtime[1]}, Начало: {downtime[2]}, Конец: {downtime[3] or 'Еще не завершен'}\n"
    else:
        response = "Нет данных о простоях за неделю."
    await message.answer(response, reply_markup=menu_kb)

# Обработчик для просмотра простоев за месяц
@router.message(F.text == "Простои за месяц")
async def show_downtimes_month(message: Message):
    report = get_downtime_report("month")
    if report:
        response = "Простои за последний месяц:\n"
        for downtime in report:
            response += f"Цех {downtime[0]}, Агрегат {downtime[1]}, Начало: {downtime[2]}, Конец: {downtime[3] or 'Еще не завершен'}\n"
    else:
        response = "Нет данных о простоях за месяц."
    await message.answer(response, reply_markup=menu_kb)
# 📨 Обработчик всех сообщений в группе
@router.message()
async def forward_messages(message: Message, bot: Bot):
    # Формируем текст сообщения
    alert = {}
    user_input = message.text
    alert_time = datetime.now().strftime("%H:%M:%S")
    author = message.from_user.full_name
    alert = {"text": user_input, "time": alert_time, "author": author}
    message = analyze_production_message(alert)
    summary = process_response(message)
    try:
        # Пересылаем сообщение в личку указанному пользователю
        await bot.send_message(TARGET_USER_ID, summary)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")