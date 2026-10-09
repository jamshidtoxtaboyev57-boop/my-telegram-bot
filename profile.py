import html
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import db

router = Router(name="profile_router")

def render_profile_text_and_kb(user_id: int, full_name: str, username: str = ""):
    user_info = db.get_user_info(user_id)
    if not user_info:
        user_info = {
            "downloads_count": 0,
            "searches_count": 0,
            "favorites_count": 0,
            "is_vip": 0,
            "vip_until": None,
            "created_at": "Noma'lum"
        }

    is_vip = db.is_vip(user_id)
    if is_vip and user_info.get("vip_until"):
        try:
            exp = datetime.fromisoformat(user_info["vip_until"])
            now = datetime.now()
            diff = exp - now
            days_left = diff.days
            hours_left = diff.seconds // 3600
            vip_str = f"👑 <b>VIP Status (Faol)</b>\n⏱ <b>Muddati:</b> <code>{exp.strftime('%Y-%m-%d %H:%M')}</code> <i>({days_left} kun {hours_left} soat qoldi)</i>"
        except Exception:
            vip_str = "👑 <b>VIP Status (Faol)</b>"
    else:
        vip_str = "⚪️ <b>Standart foydalanuvchi</b>\n<i>(VIP sotib olib, barcha obunalardan va cheklovlardan ozod bo'ling)</i>"

    reg_date = user_info.get("created_at") or "Yaqinda"
    if isinstance(reg_date, str) and len(reg_date) >= 10:
        reg_date = reg_date[:10]

    text = (
        "╭────────────────────────────╮\n"
        "│    👤 <b>SHAXSIY PROFILINGIZ</b>       │\n"
        "╰────────────────────────────╯\n\n"
        f"👤 <b>Ism:</b> {html.escape(full_name)}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"💎 <b>Status:</b> {vip_str}\n\n"
        "📊 <b>FAOLIYAT STATISTIKASI:</b>\n"
        f"• 🔍 Izlangan qo'shiqlar: <b>{user_info.get('searches_count', 0)}</b> ta\n"
        f"• 📥 Yuklangan musiqalar: <b>{user_info.get('downloads_count', 0)}</b> ta\n"
        f"• ❤️ Sevimli musiqalar: <b>{user_info.get('favorites_count', 0)}</b> ta\n"
        f"• 📅 Botga qo'shilgan sana: <b>{reg_date}</b>"
    )

    builder = InlineKeyboardBuilder()
    if not is_vip:
        builder.row(
            InlineKeyboardButton(text="👑 VIP status olish", callback_data="open_vip")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="👑 VIP muddatini uzaytirish", callback_data="open_vip")
        )

    builder.row(
        InlineKeyboardButton(text="❤️ Sevimlilarim", callback_data="open_favs_from_profile"),
        InlineKeyboardButton(text="🔥 TOP Hitlar", callback_data="refresh_top")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Yopish", callback_data="close_search")
    )

    return text, builder.as_markup()

@router.message(F.text == "👤 Mening profilim")
@router.message(F.text == "/profile")
@router.message(F.text == "/me")
async def show_profile(message: Message):
    text, kb = render_profile_text_and_kb(
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.username or ""
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "open_favs_from_profile")
async def cb_favs_from_profile(callback: CallbackQuery):
    from handlers.favorites import render_favorites_page
    text, kb = await render_favorites_page(callback.from_user.id, page=1)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()
