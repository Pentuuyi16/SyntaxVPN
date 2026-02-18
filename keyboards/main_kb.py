from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура после /start."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Подключить VPN", callback_data="connect_vpn")],
        [InlineKeyboardButton(text="🔐 Мой ключ", callback_data="my_key")],
        [InlineKeyboardButton(text="👥 Реферальная система", callback_data="referral")],
        [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
    ])


def get_plans_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц — 99 ₽", callback_data="plan_1")],
        [InlineKeyboardButton(text="🔥 3 месяца — 199 ₽", callback_data="plan_3")],
        [InlineKeyboardButton(text="6 месяцев — 499 ₽", callback_data="plan_6")],
        [InlineKeyboardButton(text="🔥 1 год — 999 ₽", callback_data="plan_12")],
        [InlineKeyboardButton(text="Тест — 1 ₽", callback_data="plan_test")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
    ])