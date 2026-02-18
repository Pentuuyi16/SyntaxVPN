import uuid

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from yookassa import Configuration, Payment

from config.settings import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
from utils.texts import PLAN_DETAILS, get_plan_text

router = Router()

Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY


@router.callback_query(F.data.startswith("plan_"))
async def on_select_plan(callback: CallbackQuery):
    """Выбор тарифа — сразу создаём платёж и показываем ссылку."""
    plan_id = callback.data

    if plan_id not in PLAN_DETAILS:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    plan = PLAN_DETAILS[plan_id]

    payment = Payment.create({
        "amount": {
            "value": str(plan["price"]) + ".00",
            "currency": "RUB",
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/YOUR_BOT_USERNAME",
        },
        "capture": True,
        "description": f"SyntaxVPN — {plan['name']}",
        "metadata": {
            "telegram_id": str(callback.from_user.id),
            "plan_id": plan_id,
        },
    }, uuid.uuid4())

    payment_url = payment.confirmation.confirmation_url

    await callback.message.edit_text(
        text=get_plan_text(plan_id),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="connect_vpn")],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()