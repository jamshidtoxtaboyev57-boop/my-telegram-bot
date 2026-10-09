import html
import uuid
from aiogram import Router, F, Bot
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultAudio,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from core.music_search import MusicSearcher
from database.db import db

router = Router(name="inline_mode_router")

@router.inline_query()
async def inline_music_search(inline_query: InlineQuery, bot: Bot):
    query = inline_query.query.strip()
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "musicyuklllabot"

    results = []

    # 1. Agar so'rov bo'sh bo'lsa, TOP hitlar yoki keshdagi musiqalarni chiqaramiz
    if not query:
        top_songs = db.get_top_songs(limit=15)
        for s in top_songs:
            if s.get("file_id"):
                results.append(
                    InlineQueryResultAudio(
                        id=f"top_{s['song_id']}",
                        audio_file_id=s["file_id"],
                        caption=f"🔥 <b>{html.escape(s.get('title', 'Musiqa'))}</b>\n🎧 @{bot_username}",
                        parse_mode="HTML"
                    )
                )
        await inline_query.answer(results, cache_time=60, is_personal=True)
        return

    # 2. Matn bo'yicha qidiruv
    try:
        search_items = await MusicSearcher.search(query, limit=10)
        for item in search_items:
            song_id = item["id"]
            title = item["title"]
            artist = item.get("artist") or ""
            duration_str = item.get("duration_str", "")

            cached = db.get_cached_music(song_id)
            if cached and cached.get("file_id"):
                results.append(
                    InlineQueryResultAudio(
                        id=f"aud_{song_id}",
                        audio_file_id=cached["file_id"],
                        caption=f"🎵 <b>{html.escape(title)}</b>\n🎧 @{bot_username} (Turbo)",
                        parse_mode="HTML"
                    )
                )
            else:
                results.append(
                    InlineQueryResultArticle(
                        id=f"art_{song_id}",
                        title=f"🎵 {title[:60]}",
                        description=f"👤 {artist[:30]} | ⏱ {duration_str}",
                        input_message_content=InputTextMessageContent(
                            message_text=(
                                f"🎵 <b>{html.escape(title)}</b>\n"
                                f"👤 <b>Ijrochi:</b> {html.escape(artist)}\n"
                                f"⏱ <b>Davomiyligi:</b> {duration_str}\n\n"
                                f"🎧 Ushbu musiqani yuklab olish uchun pastdagi tugmani bosing:"
                            ),
                            parse_mode="HTML"
                        ),
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="📥 Musiqani yuklab olish",
                                        url=f"https://t.me/{bot_username}?start=dl_{song_id}"
                                    )
                                ]
                            ]
                        )
                    )
                )
    except Exception as e:
        print(f"[Inline Query Error]: {e}")

    await inline_query.answer(results, cache_time=120, is_personal=True)
