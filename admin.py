import asyncio
import html
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database.db import db
from keyboards.inline import get_admin_main_keyboard, get_admin_channels_keyboard

router = Router(name="admin_router")

class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_add_channel = State()
    waiting_vip_input = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# --- ASOSIY ADMIN PANELI ---
@router.message(Command("admin"))
async def cmd_admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    text = (
        "👑 <b>ADMIN BOSHQARUV PANELI</b>\n\n"
        "Quyidagi tugmalar orqali botni to'liq boshqarishingiz mumkin:"
    )
    await message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "adm_back")
async def cb_admin_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    text = "👑 <b>ADMIN BOSHQARUV PANELI</b>\n\nBo'limni tanlang:"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()

# --- 1. JONLI STATISTIKA ---
@router.callback_query(F.data == "adm_stats")
@router.message(Command("stats"))
async def show_admin_stats(event: Message | CallbackQuery):
    user_id = event.from_user.id
    if not is_admin(user_id):
        return

    stats = db.get_detailed_stats()
    text = (
        "📊 <b>BOTNING JONLI STATISTIKASI:</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {stats['total_users']} ta\n"
        f"🆕 <b>Bugun qo'shilganlar:</b> {stats['today_users']} ta\n"
        f"👑 <b>VIP foydalanuvchilar:</b> {stats['vip_users']} ta\n"
        f"⚡️ <b>Keshdagi musiqalar (Turbo):</b> {stats['cached_songs']} ta\n"
        f"📥 <b>Jami yuklab olingan musiqalar:</b> {stats['total_downloads']} ta\n"
        f"🔍 <b>Jami qidiruvlar soni:</b> {stats['total_searches']} ta\n"
        f"❤️ <b>Sevimlilarga saqlanganlar:</b> {stats['total_favorites']} ta"
    )

    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Ortga", callback_data="adm_back")]]
    )

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
        except Exception:
            pass
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb, parse_mode="HTML")

# --- 2. XABAR TARQATISH (BROADCAST) ---
@router.callback_query(F.data == "adm_broadcast")
@router.message(Command("broadcast"))
async def start_broadcast(event: Message | CallbackQuery, state: FSMContext):
    user_id = event.from_user.id
    if not is_admin(user_id):
        return

    await state.set_state(AdminStates.waiting_broadcast)
    text = (
        "📢 <b>Xabar tarqatish bo'limi:</b>\n\n"
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring.\n"
        "<i>(Matn, rasm, video yoki havola bo'lishi mumkin)</i>\n\n"
        "Bekor qilish uchun /cancel deb yozing."
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")

@router.message(AdminStates.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    if message.text and message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Xabar tarqatish bekor qilindi.")
        return

    await state.clear()
    user_ids = db.get_all_user_ids()
    total = len(user_ids)

    status_msg = await message.answer(f"⏳ Xabar tarqatilmoqda (Jami: {total} ta foydalanuvchi)...")

    sent = 0
    blocked = 0

    for uid in user_ids:
        try:
            await message.copy_to(chat_id=uid)
            sent += 1
            await asyncio.sleep(0.04) # Telegram cheklovlariga qarshi (25-30 msg/sec)
        except Exception:
            blocked += 1

    await status_msg.edit_text(
        f"✅ <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"👥 Jami: <b>{total}</b>\n"
        f"✅ Yetkazildi: <b>{sent}</b>\n"
        f"❌ Bloklaganlar: <b>{blocked}</b>",
        parse_mode="HTML"
    )

# --- 3. KANALLARNI BOSHQARISH ---
@router.callback_query(F.data == "adm_channels")
async def show_admin_channels(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    channels = db.get_channels()
    text = (
        "📢 <b>MAJBURIY OBUNA KANALLARI RO'YXATI:</b>\n\n"
        f"Hozirda <b>{len(channels)}</b> ta kanal ulangan.\n"
        "Quyidagi tugmalar orqali kanal qo'shishingiz yoki o'chirishingiz mumkin:"
    )
    kb = get_admin_channels_keyboard(channels)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data == "adm_add_ch")
async def ask_add_channel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.waiting_add_channel)
    text = (
        "➕ <b>Yangi kanal qo'shish:</b>\n\n"
        "Quyidagi formatda yuboring:\n"
        "<code>@kanal_username | Havola | Kanal Nomi</code>\n\n"
        "Masalan:\n"
        "<code>@music_top | https://t.me/music_top | Top Musiqalar</code>\n\n"
        "Bekor qilish uchun /cancel deb yozing."
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

@router.message(AdminStates.waiting_add_channel)
async def process_add_channel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    parts = [p.strip() for p in message.text.split("|")]
    if len(parts) < 2:
        await message.answer("⚠️ Xato format! Format: <code>@username | https://t.me/link | Nomi</code>", parse_mode="HTML")
        return

    ch_id = parts[0]
    link = parts[1]
    title = parts[2] if len(parts) > 2 else ch_id

    db.add_channel(ch_id, title, link)
    await state.clear()
    await message.answer(f"✅ Kanal muvaffaqiyatli qo'shildi:\n<b>{title}</b> (<code>{ch_id}</code>)", parse_mode="HTML")

@router.callback_query(F.data.startswith("adm_del_ch:"))
async def cb_del_channel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    ch_id = callback.data.split("adm_del_ch:", 1)[1]
    db.delete_channel(ch_id)
    await callback.answer("🗑 Kanal o'chirildi!", show_alert=True)
    await show_admin_channels(callback)

# --- 4. VIP BOSHQARUV TUGMALARI ---
@router.callback_query(F.data == "adm_vip_help")
async def show_vip_help(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    text = (
        "👑 <b>VIP STATUS BOSHQARUVI:</b>\n\n"
        "Foydalanuvchiga VIP berish uchun quyidagi buyruqni yozing:\n"
        "<code>/addvip USER_ID KUN</code>\n"
        "Masalan: <code>/addvip 123456789 30</code>\n\n"
        "VIP statusni olib tashlash uchun:\n"
        "<code>/delvip USER_ID</code>"
    )
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Ortga", callback_data="adm_back")]]
    )
    try:
        await callback.message.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()
