import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database.db import db
from keyboards.inline import get_top_songs_keyboard
from core.music_search import MusicSearcher
from utils.helpers import format_duration

router = Router(name="top_charts_router")

DEFAULT_TRENDS = [
    {"song_id": "Xcho Vorona", "title": "Vorona", "performer": "Xcho", "duration": 195, "download_count": 520},
    {"song_id": "Konsta Odamlar nima deydi", "title": "Odamlar nima deydi", "performer": "Konsta", "duration": 210, "download_count": 480},
    {"song_id": "Billie Eilish Birds of a feather", "title": "Birds of a Feather", "performer": "Billie Eilish", "duration": 180, "download_count": 410},
    {"song_id": "Miyagi Captain", "title": "Captain", "performer": "Miyagi & Andy Panda", "duration": 220, "download_count": 395},
    {"song_id": "Lady Gaga Bruno Mars Die With A Smile", "title": "Die With A Smile", "performer": "Lady Gaga & Bruno Mars", "duration": 252, "download_count": 370},
]

def render_top_songs():
    songs = db.get_top_songs(limit=10)
    if not songs or len(songs) < 3:
        # Agar bazada hali kam musiqa bo'lsa, trenddagi tavsiya ro'yxati
        songs = DEFAULT_TRENDS

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    lines = [
        "🔥 <b>ENG OMMABOP VA TRENDDAGI HITLAR (TOP-10)</b>\n",
        "<i>Bot foydalanuvchilari tomonidan eng ko'p tinglangan va yuklab olingan saralangan taronalar:</i>\n"
    ]

    for i, s in enumerate(songs[:10]):
        medal = medals[i] if i < len(medals) else f"<b>{i+1}.</b>"
        title = html.escape(s.get("title") or "Musiqa")
        perf = html.escape(s.get("performer") or "")
        dur = format_duration(s.get("duration") or 0)
        dl_cnt = s.get("download_count", 1)
        name_str = f"{perf} — {title}" if perf else title
        lines.append(f"{medal} <b>{name_str}</b> <code>[{dur}]</code> • <i>{dl_cnt} marta</i>")

    lines.append("\n<i>Istalgan qo'shiqni yuklab olish uchun pastdagi tugmani bosing:</i>")
    text = "\n".join(lines)
    kb = get_top_songs_keyboard(songs[:10])
    return text, kb

@router.message(F.text == "🔥 TOP Hitlar")
@router.message(F.text == "/top")
async def show_top_charts(message: Message):
    text, kb = render_top_songs()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "refresh_top")
async def cb_refresh_top(callback: CallbackQuery):
    text, kb = render_top_songs()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("Top hitlar yangilandi! 🔥")
