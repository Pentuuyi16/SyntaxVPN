from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from database.db import add_user
from keyboards.main_kb import get_main_keyboard, get_plans_keyboard
from utils.texts import WELCOME_TEXT, PLANS_TEXT

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    await add_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    await message.answer(
        text=WELCOME_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "connect_vpn")
async def on_connect_vpn(callback: CallbackQuery):
    """Обработчик кнопки 'Подключить VPN'."""
    await callback.message.edit_text(
        text=PLANS_TEXT,
        reply_markup=get_plans_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def on_back_to_main(callback: CallbackQuery):
    """Возврат в главное меню."""
    await callback.message.edit_text(
        text=WELCOME_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()