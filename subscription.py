from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import REQUIRED_CHANNELS, ADMIN_IDS
from database.db import db

def get_subscription_keyboard(unsubscribed_channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, ch in enumerate(unsubscribed_channels, 1):
        url = ch.get("link") or f"https://t.me/{ch['id'].lstrip('@')}"
        title = ch.get("title") or f"Kanal {idx}"
        builder.row(InlineKeyboardButton(text=f"📢 {title}", url=url))

    # Tekshirish va VIP tugmalari
    builder.row(InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub"))
    builder.row(InlineKeyboardButton(text="👑 VIP status olish (Obunalarsiz)", callback_data="open_vip"))
    return builder.as_markup()

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        bot: Bot = data.get("bot")
        user = data.get("event_from_user")
        if not user or not bot:
            return await handler(event, data)

        # Foydalanuvchini bazaga kiritish / yangilash
        db.add_or_update_user(user.id, user.username, user.full_name)

        # Adminlar uchun majburiy obuna yo'q
        if user.id in ADMIN_IDS:
            return await handler(event, data)

        # Foydalanuvchi VIP bo'lsa obunani tekshirish o'tkazib yuboriladi
        if db.is_vip(user.id):
            return await handler(event, data)

        # FSM State tekshiruvi: agar foydalanuvchi chek yuborayotgan bo'lsa
        state = data.get("state")
        if state:
            current_state = await state.get_state()
            if current_state and "VipReceiptState" in current_state:
                return await handler(event, data)

        # Start, help, vip, admin, profil buyruqlari o'tkazib yuboriladi
        if isinstance(event, Message) and event.text:
            bypass_commands = (
                "/vip", "/help", "/start", "/id", "/admin", "/profile", "/me", "/cancel",
                "👑 VIP Status", "📖 Yo'riqnoma", "👤 Mening profilim"
            )
            if any(event.text.startswith(cmd) for cmd in bypass_commands):
                return await handler(event, data)

        # Callback query bypass
        if isinstance(event, CallbackQuery):
            bypass_data = (
                "check_sub", "open_vip", "show_help", "close_search", "noop", "adm_",
                "send_receipt:", "cancel_receipt", "pay_ok:", "pay_no:"
            )
            if any(event.data.startswith(prefix) for prefix in bypass_data) or event.data.startswith("buy_vip:"):
                return await handler(event, data)

        # Kanallar ro'yxati (config va DB)
        all_channels = list(REQUIRED_CHANNELS)
        db_channels = db.get_channels()
        for dc in db_channels:
            if dc["channel_id"] not in all_channels:
                all_channels.append(dc["channel_id"])

        if not all_channels:
            return await handler(event, data)

        unsubscribed = []
        for ch in all_channels:
            try:
                member = await bot.get_chat_member(chat_id=ch, user_id=user.id)
                if member.status in ("left", "kicked"):
                    unsubscribed.append({"id": ch, "title": f"Kanal: {ch}", "link": None})
            except Exception as e:
                # Agar bot kanalda admin bo'lmasa yoki kanal topilmasa xato bermasligi uchun o'tkazib yuboramiz
                print(f"[SubCheck Warning]: {ch} kanalini tekshirib bo'lmadi: {e}")

        if unsubscribed:
            kb = get_subscription_keyboard(unsubscribed)
            text = (
                "⚠️ <b>Botdan to'liq foydalanish uchun quyidagi kanallarga a'zo bo'ling:</b>\n\n"
                "A'zo bo'lgach, <b>«✅ Obunani tekshirish»</b> tugmasini bosing.\n"
                "<i>(Yoki VIP sotib olib, barcha majburiy obunalarsiz va maksimal tezlikda foydalaning)</i>"
            )
            if isinstance(event, Message):
                await event.answer(text, reply_markup=kb, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
                await event.answer()
            return

        return await handler(event, data)
