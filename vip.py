import html
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import VIP_PRICES, ADMIN_CONTACT, ADMIN_IDS, CARD_NUMBER, CARD_HOLDER
from database.db import db

router = Router(name="vip_router")

class VipReceiptState(StatesGroup):
    waiting_receipt = State()

def get_vip_tariffs_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🥉 1 oylik — 15,000 so'm", callback_data="buy_vip:1_month")
    )
    builder.row(
        InlineKeyboardButton(text="🥈 3 oylik — 35,000 so'm", callback_data="buy_vip:3_month")
    )
    builder.row(
        InlineKeyboardButton(text="🥇 1 yillik — 80,000 so'm (Cheksiz)", callback_data="buy_vip:1_year")
    )
    builder.row(
        InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", url=f"https://t.me/{ADMIN_CONTACT.lstrip('@')}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Yopish", callback_data="close_search")
    )
    return builder.as_markup()

VIP_INFO_TEXT = (
    "╭────────────────────────────╮\n"
    "│     👑 <b>VIP STATUS IMTIYOZLARI</b>     │\n"
    "╰────────────────────────────╯\n\n"
    "⚡️ <b>Turbo tezlik:</b> Musiqalar kesh orqali 0.1 soniyada yuklanadi!\n"
    "🚫 <b>Cheklovlarsiz:</b> Hech qanday majburiy kanallarga a'zo bo'lish talab etilmaydi!\n"
    "🎧 <b>Oliy sifat:</b> Eng yuqori audio va video sifati (320 kbps HQ).\n"
    "🔥 <b>Cheksiz foydalanish:</b> Hech qanday cheklov va limitlarsiz erkin foydalaning.\n\n"
    "<i>Quyidagi qulay tariflardan birini tanlang:</i> 👇"
)

@router.message(Command("vip"))
async def cmd_vip(message: Message):
    is_vip = db.is_vip(message.from_user.id)
    status_str = "✅ <b>Sizda VIP status faol!</b>" if is_vip else "⚪️ <i>Sizda hozircha VIP status faol emas.</i>"
    text = f"{VIP_INFO_TEXT}\n\n<i>Sizning holatingiz:</i> {status_str}"
    await message.answer(text, reply_markup=get_vip_tariffs_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "open_vip")
async def cb_open_vip(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_vip = db.is_vip(callback.from_user.id)
    status_str = "✅ <b>Sizda VIP status faol!</b>" if is_vip else "⚪️ <i>Sizda hozircha VIP status faol emas.</i>"
    text = f"{VIP_INFO_TEXT}\n\n<i>Sizning holatingiz:</i> {status_str}"
    try:
        await callback.message.edit_text(text, reply_markup=get_vip_tariffs_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_vip_tariffs_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("buy_vip:"))
async def cb_buy_vip(callback: CallbackQuery, state: FSMContext):
    tariff_key = callback.data.split("buy_vip:", 1)[1]
    tariff = VIP_PRICES.get(tariff_key)
    if not tariff:
        await callback.answer("Noma'lum tarif", show_alert=True)
        return

    user_id = callback.from_user.id
    price_formatted = f"{tariff['price']:,}".replace(",", " ")

    text = (
        "╭────────────────────────────╮\n"
        "│    💎 <b>TO'LOV VA VIP FAOLLASHTIRISH</b>   │\n"
        "╰────────────────────────────╯\n\n"
        f"💎 <b>Tarif:</b> {tariff['title']}\n"
        f"💰 <b>Narxi:</b> {price_formatted} so'm\n"
        f"🆔 <b>Sizning Telegram ID:</b> <code>{user_id}</code>\n\n"
        "💳 <b>To'lov uchun karta ma'lumotlari:</b>\n"
        f"💳 Karta raqam: <code>{CARD_NUMBER}</code> <i>(nusxalash uchun bosing)</i>\n"
        f"👤 Egasi: <b>{CARD_HOLDER}</b>\n\n"
        "📝 <b>To'lov yo'riqnomasi:</b>\n"
        f"1. Karta raqamini bosib nusxalang (<code>{CARD_NUMBER}</code>);\n"
        f"2. Click, Payme yoki bank ilovasi orqali <b>{price_formatted} so'm</b> o'tkazing;\n"
        "3. To'lov amalga oshirilgach, pastdagi <b>«🧾 To'lov chekini yuborish»</b> tugmasini bosing va chek skrinshotini (rasm/fayl) botga yuboring!\n"
        "4. Chek adminga yetkaziladi va tasdiqlangach VIP avtomatik yoqiladi! ⚡️"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🧾 To'lov chekini yuborish",
            callback_data=f"send_receipt:{tariff_key}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Ortga", callback_data="open_vip"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="close_search")
    )

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

# --- TO'LOV CHEKINI QABUL QILISH (FSM) ---

@router.callback_query(F.data.startswith("send_receipt:"))
async def cb_send_receipt_start(callback: CallbackQuery, state: FSMContext):
    tariff_key = callback.data.split("send_receipt:", 1)[1]
    tariff = VIP_PRICES.get(tariff_key)
    if not tariff:
        await callback.answer("Tarif topilmadi", show_alert=True)
        return

    await state.set_state(VipReceiptState.waiting_receipt)
    await state.update_data(tariff_key=tariff_key)

    price_formatted = f"{tariff['price']:,}".replace(",", " ")
    text = (
        "╭────────────────────────────╮\n"
        "│     📸 <b>TO'LOV CHEKINI YUBORISH</b>    │\n"
        "╰────────────────────────────╯\n\n"
        f"Tanlangan tarif: <b>{tariff['title']}</b> ({price_formatted} so'm)\n\n"
        "Iltimos, to'lov cheki skrinshotini (rasm) yoki PDF faylini ushbu botga yuboring.\n"
        "Chek adminga tekshirish uchun yuboriladi va tasdiqlangach sizga avtomatik ravishda VIP yoqiladi! ⚡️\n\n"
        "<i>Bekor qilish uchun: /cancel deb yozing.</i>"
    )

    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_receipt")]]
    )
    try:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "cancel_receipt")
async def cb_cancel_receipt(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ To'lov chekini yuborish bekor qilindi.\n\nVIP bo'limiga qaytish uchun /vip buyrug'ini yuboring."
    )
    await callback.answer()

@router.message(VipReceiptState.waiting_receipt, Command("cancel"))
async def msg_cancel_receipt(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ To'lov chekini yuborish bekor qilindi.\n\nVIP bo'limiga qaytish uchun /vip buyrug'ini yuboring.")

@router.message(VipReceiptState.waiting_receipt, F.photo | F.document)
async def handle_receipt_media(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    tariff_key = data.get("tariff_key") or "1_month"
    tariff = VIP_PRICES.get(tariff_key, VIP_PRICES["1_month"])
    await state.clear()

    user = message.from_user
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    else:
        file_id = message.document.file_id
        file_type = "document"

    payment_id = db.create_payment(
        user_id=user.id,
        tariff_key=tariff_key,
        tariff_title=tariff["title"],
        amount=tariff["price"],
        days=tariff["days"],
        file_id=file_id,
        file_type=file_type
    )

    price_formatted = f"{tariff['price']:,}".replace(",", " ")

    # Foydalanuvchiga tasdiq xabari
    await message.reply(
        "✅ <b>To'lov chekingiz qabul qilindi!</b>\n\n"
        "⏳ Chekingiz ko'rib chiqish uchun adminga yuborildi.\n"
        "Admin tasdiqlashi bilanoq sizga bildirishnoma keladi va VIP status avtomatik ravishda faollashadi! 🤝",
        parse_mode="HTML"
    )

    # Adminga yuborish
    admin_caption = (
        f"🔔 <b>YANGI VIP TO'LOV CHEKI! (#ID_{payment_id})</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> <a href=\"tg://user?id={user.id}\">{html.escape(user.full_name)}</a> "
        f"(@{html.escape(user.username) if user.username else 'yoq'})\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.id}</code>\n"
        f"💎 <b>Tarif:</b> {tariff['title']} ({tariff['days']} kun)\n"
        f"💰 <b>To'lov summasi:</b> {price_formatted} so'm\n"
        f"🕒 <b>Vaqt:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "<i>To'lov hisobingizga tushganini tekshirib, quyidagi tugmalar orqali tasdiqlang yoki rad eting:</i> 👇"
    )

    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_ok:{payment_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_no:{payment_id}"),
            ]
        ]
    )

    for admin_id in ADMIN_IDS:
        try:
            if file_type == "photo":
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=file_id,
                    caption=admin_caption,
                    reply_markup=admin_kb,
                    parse_mode="HTML"
                )
            else:
                await bot.send_document(
                    chat_id=admin_id,
                    document=file_id,
                    caption=admin_caption,
                    reply_markup=admin_kb,
                    parse_mode="HTML"
                )
        except Exception as err:
            print(f"[Send Receipt to Admin {admin_id} Error]: {err}")

@router.message(VipReceiptState.waiting_receipt)
async def handle_receipt_wrong_input(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    if message.text and not message.text.startswith("/"):
        from handlers.search import handle_text_search
        await handle_text_search(message, bot)

# --- ADMIN TASDIQLASH VA RAD ETISH ---

@router.callback_query(F.data.startswith("pay_ok:"))
async def cb_admin_pay_approve(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Siz admin emassiz!", show_alert=True)
        return

    payment_id = int(callback.data.split("pay_ok:", 1)[1])
    payment = db.get_payment(payment_id)
    if not payment:
        await callback.answer("To'lov topilmadi!", show_alert=True)
        return

    if payment.get("status") != "pending":
        await callback.answer(f"Ushbu to'lov allaqachon ko'rib chiqilgan ({payment.get('status')})!", show_alert=True)
        return

    db.update_payment_status(payment_id, "approved")
    user_id = payment["user_id"]
    days = payment["days"]
    tariff_title = payment["tariff_title"]
    expiry = db.set_vip(user_id, days)

    # Foydalanuvchiga xushxabar yuborish
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>TABRIKLAYMIZ! TO'LOVINGIZ TASDIQLANDI!</b>\n\n"
                f"👑 Sizga <b>{tariff_title}</b> VIP statusi muvaffaqiyatli yoqildi!\n"
                f"⏱ <b>Amal qilish muddati:</b> <code>{expiry.strftime('%Y-%m-%d %H:%M')}</code> gacha.\n\n"
                "Endi siz uchun barcha majburiy kanallarga obuna bo'lish bekor qilindi, "
                "eng yuqori audio sifati va cheksiz qidiruv imkoniyati faollashdi! 🎧⚡️"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"[Notify User Error]: {e}")

    # Admin xabarini yangilash
    admin_name = html.escape(callback.from_user.first_name)
    price_formatted = f"{payment['amount']:,}".replace(",", " ")
    new_caption = (
        f"✅ <b>TO'LOV TASDIQLANDI VA VIP YOQILDI!</b>\n\n"
        f"🆔 Foydalanuvchi ID: <code>{user_id}</code>\n"
        f"💎 Tarif: <b>{tariff_title}</b> ({days} kun)\n"
        f"💰 Summa: {price_formatted} so'm\n"
        f"📅 VIP muddati: <code>{expiry.strftime('%Y-%m-%d %H:%M')}</code> gacha\n"
        f"👨‍💻 Tasdiqlagan admin: {admin_name} ({ADMIN_CONTACT})"
    )
    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=new_caption, parse_mode="HTML")
        else:
            await callback.message.edit_text(text=new_caption, parse_mode="HTML")
    except Exception:
        pass

    await callback.answer("✅ To'lov tasdiqlandi va foydalanuvchiga VIP yoqildi!", show_alert=True)

@router.callback_query(F.data.startswith("pay_no:"))
async def cb_admin_pay_reject(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Siz admin emassiz!", show_alert=True)
        return

    payment_id = int(callback.data.split("pay_no:", 1)[1])
    payment = db.get_payment(payment_id)
    if not payment:
        await callback.answer("To'lov topilmadi!", show_alert=True)
        return

    if payment.get("status") != "pending":
        await callback.answer(f"Ushbu to'lov allaqachon ko'rib chiqilgan ({payment.get('status')})!", show_alert=True)
        return

    db.update_payment_status(payment_id, "rejected")
    user_id = payment["user_id"]
    tariff_title = payment["tariff_title"]

    # Foydalanuvchiga rad etish xabari
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "❌ <b>TO'LOV CHEKINGIZ TASDIQLANMADI</b>\n\n"
                f"Siz yuborgan to'lov cheki admin tomonidan rad etildi.\n"
                "<i>Mumkin bo'lgan sabablar: hisobga mablag' kelib tushmagan, chek noaniq yoki xato yuborilgan.</i>\n\n"
                f"Agar to'lov qilgan bo'lsangiz, admin bilan bog'laning: {ADMIN_CONTACT}"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"[Notify User Error]: {e}")

    admin_name = html.escape(callback.from_user.first_name)
    new_caption = (
        f"❌ <b>TO'LOV RAD ETILDI!</b>\n\n"
        f"🆔 Foydalanuvchi ID: <code>{user_id}</code>\n"
        f"💎 Tarif: <b>{tariff_title}</b>\n"
        f"👨‍💻 Rad etgan admin: {admin_name} ({ADMIN_CONTACT})"
    )
    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=new_caption, parse_mode="HTML")
        else:
            await callback.message.edit_text(text=new_caption, parse_mode="HTML")
    except Exception:
        pass

    await callback.answer("❌ To'lov rad etildi.", show_alert=True)

# --- OBUNA TEKSHIRUVI ---

@router.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    from config import REQUIRED_CHANNELS
    all_channels = list(REQUIRED_CHANNELS)
    for dc in db.get_channels():
        if dc["channel_id"] not in all_channels:
            all_channels.append(dc["channel_id"])

    unsubscribed = []
    for ch in all_channels:
        try:
            m = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if m.status in ("left", "kicked"):
                unsubscribed.append(ch)
        except Exception:
            pass

    if unsubscribed:
        await callback.answer("❌ Hali barcha kanallarga a'zo bo'lmadingiz! Iltimos, a'zo bo'ling.", show_alert=True)
    else:
        await callback.answer("🎉 Tabriklaymiz! Obuna tasdiqlandi.", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "✅ <b>Obuna tasdiqlandi!</b>\n\nEndi bemalol qo'shiq nomi, ovozli xabar yoki video yuborishingiz mumkin. 🎧",
            parse_mode="HTML"
        )
