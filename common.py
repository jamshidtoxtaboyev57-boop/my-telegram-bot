import html
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from keyboards.reply import get_main_reply_keyboard
from database.db import db

router = Router(name="common_router")

def get_start_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔥 TOP Hitlar", callback_data="refresh_top"),
                InlineKeyboardButton(text="👑 VIP Status", callback_data="open_vip"),
            ],
            [
                InlineKeyboardButton(text="❤️ Mening Pleylistim", callback_data="open_favs_from_profile"),
                InlineKeyboardButton(text="📖 Yo'riqnoma", callback_data="show_help"),
            ]
        ]
    )

HELP_TEXT = (
    "╭────────────────────────────╮\n"
    "│   📖 <b>FOYDALANISH YO'RIQNOMASI</b>    │\n"
    "╰────────────────────────────╯\n\n"
    "1️⃣ <b>Qo'shiq nomi orqali:</b>\n"
    "Shunchaki ijrochi yoki musiqa nomini yozib yuboring (masalan: <i>Konsta</i> yoki <i>Vorona</i>).\n\n"
    "2️⃣ <b>Ovozli xabar (Shazam):</b>\n"
    "Atrofda yangrayotgan musiqani 5-10 soniya ovozli xabar (voice) qilib yuborsangiz, bot darhol aniqlab beradi.\n\n"
    "3️⃣ <b>Videolardan musiqa ajratish:</b>\n"
    "Telegramdagi ixtiyoriy video yoki dumaloq video (video note) yuboring — bot undan audioni ajratadi va asl studiya trekini topadi.\n\n"
    "4️⃣ <b>Video yuklab olish:</b>\n"
    "YouTube, TikTok, Instagram havolalarini yuboring va MP4 video yoki MP3 formatda yuklab oling.\n\n"
    "5️⃣ <b>Inline qidiruv (Har qanday chatda):</b>\n"
    "Istalgan chatda yoki guruhda <code>@bot_nomi qo'shiq</code> deb yozsangiz, to'g'ridan-to'g'ri musiqa yuborishingiz mumkin!\n\n"
    "6️⃣ <b>Sevimlilar (❤️):</b>\n"
    "Yoqtirgan qo'shiqlaringizni pleylistingizga saqlab, bir joydan eshiting.\n\n"
    "7️⃣ <b>VIP Status (/vip):</b>\n"
    "Barcha majburiy obunalarsiz, reklamasiz va maksimal turbo tezlikda foydalaning!"
)

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user = message.from_user
    db.add_or_update_user(user.id, user.username, user.full_name)

    # 1. Agar deep-link parametri bo'lsa (masalan /start dl_xyz)
    text_args = message.text.split()
    if len(text_args) > 1 and text_args[1].startswith("dl_"):
        song_id = text_args[1].split("dl_", 1)[1]
        # Uni qidiruv/yuklash handleriga o'tkazish
        from handlers.search import handle_download_callback_direct
        await handle_download_callback_direct(message, song_id, bot)
        return

    bot_info = await bot.get_me()
    bot_username = bot_info.username or "musicyuklllabot"

    start_text = (
        "╭────────────────────────────╮\n"
        "│  🎧 <b>PREMIUM MUSIC & VIDEO BOT</b>   │\n"
        "╰────────────────────────────╯\n\n"
        f"Assalomu alaykum, <b>{html.escape(user.first_name)}</b>! ✨\n\n"
        "Musiqa ixlosmandlari uchun eng ilg'or, qulay va tezkor botga xush kelibsiz!\n\n"
        "⚡️ <b>Imkoniyatlar:</b>\n"
        "• 🔍 <b>Tezkor qidiruv</b> — nom yoki ijrochi bo'yicha\n"
        "• 🎙 <b>Shazam</b> — ovozli xabar (voice) orqali musiqa topish\n"
        "• 🎬 <b>Videolardan audio ajratish</b> — toza MP3 formatda\n"
        "• 🔗 <b>Video yuklash</b> — YouTube, TikTok, Instagram\n"
        "• 📜 <b>Qo'shiq matnlari (Lyrics)</b> — bir bosishda\n"
        "• ❤️ <b>Mening Pleylistim</b> — sevimli musiqalarni to'plash\n"
        f"• 🚀 <b>Inline rejim</b> — istalgan chatda <code>@{bot_username}</code> orqali\n\n"
        "<i>Boshlash uchun qo'shiq nomini yozing yoki quyidagi menyudan foydalaning:</i> 👇"
    )

    await message.answer(
        start_text,
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )
    await message.answer(
        "⚡️ <b>Tezkor amallar:</b>",
        reply_markup=get_start_inline_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.text == "🔍 Musiqa izlash")
async def msg_music_search_prompt(message: Message):
    text = (
        "🔍 <b>Musiqa izlash uchun:</b>\n\n"
        "• Qo'shiq nomi yoki ijrochisini yozib yuboring (masalan: <code>Vorona</code>, <code>Konsta</code>, <code>Billie Eilish</code>);\n"
        "• Atrofda yangrayotgan musiqani <b>ovozli xabar (voice)</b> qilib yuboring;\n"
        "• Yoki <b>video / havola</b> yuboring — bot darhol tayyorlab beradi! 🎧"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "👑 VIP Status")
async def msg_vip_prompt(message: Message):
    from handlers.vip import VIP_INFO_TEXT, get_vip_tariffs_keyboard
    is_vip = db.is_vip(message.from_user.id)
    status_str = "✅ Sizda VIP status faol!" if is_vip else "❌ Sizda hozircha VIP status yo'q."
    text = f"{VIP_INFO_TEXT}\n\n<i>Sizning holatingiz:</i> {status_str}"
    await message.answer(text, reply_markup=get_vip_tariffs_keyboard(), parse_mode="HTML")

@router.message(F.text == "📖 Yo'riqnoma")
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML")

@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(f"🆔 <b>Sizning Telegram ID:</b> <code>{message.from_user.id}</code>", parse_mode="HTML")

@router.callback_query(F.data == "show_help")
async def cb_help(callback: CallbackQuery):
    await callback.message.answer(HELP_TEXT, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(F.data == "close_search")
async def cb_close(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        await callback.answer("Yopildi", show_alert=False)
