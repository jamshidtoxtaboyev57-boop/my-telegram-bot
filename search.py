import html
import uuid
import time
from pathlib import Path
from math import ceil
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from core.music_search import MusicSearcher
from core.lyrics import LyricsService
from database.db import db
import json

from keyboards.inline import (
    get_search_results_keyboard,
    get_audio_action_keyboard,
)
from utils.helpers import is_url, extract_first_url, safe_remove, sanitize_filename

router = Router(name="search_router")

# Qidiruv natijalari kesh xotirasi (sahifalash uchun)
SEARCH_PAGINATION_CACHE = {}

REPLY_MENU_TEXTS = {
    "🔍 Musiqa izlash",
    "🔥 TOP Hitlar",
    "❤️ Sevimlilarim",
    "👤 Mening profilim",
    "👑 VIP Status",
    "📖 Yo'riqnoma",
}

def render_search_page(items: list, page: int, per_page: int, token: str, query: str):
    total_pages = max(1, ceil(len(items) / per_page))
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    current_items = items[start_idx:end_idx]

    lines = [
        "╭────────────────────────────╮",
        "│    🔍 <b>QIDIRUV NATIJALARI</b>        │",
        "╰────────────────────────────╯",
        f"Izlangan: <b>«{html.escape(query)}»</b>  <i>(Jami: {len(items)} ta)</i>\n"
    ]

    for i, item in enumerate(current_items, 1):
        global_idx = start_idx + i
        title = html.escape(item.get("title", "Musiqa"))
        artist = html.escape(item.get("artist", ""))
        dur = item.get("duration_str", "00:00")
        line_name = f"{artist} — {title}" if artist else title
        lines.append(f"<b>{global_idx}.</b> 🎵 <b>{line_name}</b> <code>[{dur}]</code>")

    lines.append("\n<i>Yuklab olish uchun quyidagi raqamni bosing:</i> 👇")
    text = "\n".join(lines)
    kb = get_search_results_keyboard(
        current_items,
        current_page=page,
        total_pages=total_pages,
        cache_token=token
    )
    return text, kb

# Userbot natijalarini ushlab olish uchun vaqtinchalik xotira
USERBOT_PENDING_AUDIOS = {}

@router.message(F.audio)
async def handle_userbot_audio(message: Message, bot: Bot):
    # Agar botga audio kelsa (userbot tomonidan forwarded)
    USERBOT_PENDING_AUDIOS[message.from_user.id] = message.audio.file_id

@router.message(F.text.startswith("USERBOT_RESULT:"))
async def handle_userbot_result(message: Message, bot: Bot):
    # USERBOT_RESULT:user_id:query formatida keladi
    parts = message.text.split(":", 2)
    if len(parts) == 3:
        original_user_id = int(parts[1])
        query = parts[2]
        
        file_id = USERBOT_PENDING_AUDIOS.pop(message.from_user.id, None)
        if file_id:
            try:
                # Topilgan audioni darhol egasiga yuborish (0.1s)
                await send_audio_response(
                    chat_id=original_user_id,
                    bot=bot,
                    song_id=query, # Vaqtincha query ni song_id sifatida ishlatamiz
                    title=query,
                    artist="TaronaBot",
                    duration=0,
                    file_id_or_path=file_id,
                    is_cached_file_id=True,
                    user_id=original_user_id
                )
            except Exception as e:
                print(f"[Userbot Send Error]: {e}")
    await message.delete()

@router.message(F.web_app_data)
async def handle_webapp_data(message: Message, bot: Bot):
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("action") == "download":
            query = data.get("query")
            if query:
                status_msg = await message.answer(f"⏳ <i>«{html.escape(query)}» yuklanmoqda...</i>", parse_mode="HTML")
                results = await MusicSearcher.search(query, limit=1)
                if results:
                    song_id = results[0]["id"]
                    # handle_download_callback_direct ga o'xshash mantiq
                    await bot.send_chat_action(message.chat.id, "upload_voice")
                    dl_data = await MusicSearcher.download_by_id_or_url(song_id)
                    if dl_data and dl_data.get("path"):
                        sent = await send_audio_response(
                            chat_id=message.chat.id,
                            bot=bot,
                            song_id=song_id,
                            title=dl_data.get("title", query),
                            artist=dl_data.get("artist", ""),
                            duration=dl_data.get("duration", 0),
                            file_id_or_path=dl_data["path"],
                            is_cached_file_id=False,
                            user_id=message.from_user.id,
                            cover_url=dl_data.get("cover_url") or ""
                        )
                        if sent and sent.audio:
                            db.cache_music(song_id, sent.audio.file_id, dl_data.get("title"), dl_data.get("artist"), dl_data.get("duration", 0), dl_data.get("cover_url"))
                            db.record_download(message.from_user.id, song_id)
                        safe_remove(dl_data.get("path"))
                        await status_msg.delete()
                    else:
                        await status_msg.edit_text("❌ Musiqani yuklash imkoni bo'lmadi.")
                else:
                    await status_msg.edit_text("❌ Musiqa topilmadi.")
    except Exception as e:
        print(f"[WebApp Error]: {e}")

@router.message(F.text, ~F.text.startswith("/"))
async def handle_text_search(message: Message, bot: Bot):
    text = message.text.strip()

    # Reply tugmalar bosilgan bo'lsa qidiruvga olmaslik
    if text in REPLY_MENU_TEXTS:
        return

    # Agar havola bo'lsa, uni video yuklovchi handlerga o'tkazamiz
    if extract_first_url(text):
        return

    db.record_search(message.from_user.id)
    status_msg = await message.answer(f"🔍 <i>«{html.escape(text)}» qidirilmoqda...</i>", parse_mode="HTML")

    try:
        results = await MusicSearcher.search(text, limit=20)
        if not results:
            await status_msg.edit_text(
                "❌ <b>Kechirasiz, hech narsa topilmadi!</b>\n\n"
                "💡 <i>Maslahat:</i>\n"
                "• Qo'shiq yoki ijrochi nomini boshqacharoq yozib ko'ring;\n"
                "• Yoki atrofda yangrayotgan bo'lsa ovozli xabar (voice) qilib yuboring 🎙",
                parse_mode="HTML"
            )
            return

        token = uuid.uuid4().hex[:10]
        SEARCH_PAGINATION_CACHE[token] = {
            "items": results,
            "query": text,
            "time": time.time()
        }

        # Eskirgan sahifalarni tozalash (30 daqiqadan oshgan)
        now = time.time()
        expired = [k for k, v in SEARCH_PAGINATION_CACHE.items() if now - v.get("time", 0) > 1800]
        for k in expired:
            SEARCH_PAGINATION_CACHE.pop(k, None)

        msg_text, kb = render_search_page(results, page=1, per_page=10, token=token, query=text)
        await status_msg.edit_text(msg_text, reply_markup=kb, parse_mode="HTML")

    except Exception as e:
        print(f"[Search Handler Error]: {e}")
        await status_msg.edit_text("❌ Qidiruvda xatolik yuz berdi. Qayta urinib ko'ring.")

@router.callback_query(F.data.startswith("spg:"))
async def cb_search_pagination(callback: CallbackQuery):
    parts = callback.data.split(":")
    token = parts[1]
    page = int(parts[2])

    data = SEARCH_PAGINATION_CACHE.get(token)
    if not data:
        await callback.answer("Qidiruv muddati tugagan, iltimos qaytadan qidiring.", show_alert=True)
        return

    text, kb = render_search_page(data["items"], page=page, per_page=10, token=token, query=data["query"])
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()

async def send_audio_response(
    chat_id: int,
    bot: Bot,
    song_id: str,
    title: str,
    artist: str,
    duration: int,
    file_id_or_path: str,
    is_cached_file_id: bool,
    user_id: int,
    cover_url: str = ""
):
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "musicyuklllabot"
    is_fav = db.is_favorite(user_id, song_id)
    kb = get_audio_action_keyboard(song_id, title=title, is_favorite=is_fav, bot_username=bot_username)

    artist_str = f"👤 <b>Ijrochi:</b> {html.escape(artist)}\n" if artist else ""
    caption = (
        f"🎧 <b>{html.escape(title)}</b>\n"
        f"{artist_str}"
        f"⚡️ @{bot_username} (HQ Audio)"
    )

    if is_cached_file_id:
        return await bot.send_audio(
            chat_id=chat_id,
            audio=file_id_or_path,
            title=title,
            performer=artist,
            duration=duration,
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        clean_name = sanitize_filename(f"{artist} - {title}" if artist else title)
        audio_file = FSInputFile(str(file_id_or_path), filename=f"{clean_name}.mp3")
        return await bot.send_audio(
            chat_id=chat_id,
            audio=audio_file,
            title=title,
            performer=artist,
            duration=duration,
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )

# Inline query yoki /start dl_xyz orqali to'g'ridan-to'g'ri yuklash
async def handle_download_callback_direct(message: Message, song_id: str, bot: Bot):
    user_id = message.from_user.id
    cached = db.get_cached_music(song_id)

    if cached and cached.get("file_id"):
        db.record_download(user_id, song_id)
        await send_audio_response(
            chat_id=message.chat.id,
            bot=bot,
            song_id=song_id,
            title=cached.get("title") or "Musiqa",
            artist=cached.get("performer") or "",
            duration=cached.get("duration") or 0,
            file_id_or_path=cached["file_id"],
            is_cached_file_id=True,
            user_id=user_id,
            cover_url=cached.get("cover_url") or ""
        )
        return

    try:
        await bot.send_chat_action(message.chat.id, "upload_voice")
        data = await MusicSearcher.download_by_id_or_url(song_id)
        if not data or not data.get("path"):
            await message.reply("❌ Musiqani yuklab olish imkoni bo'lmadi.")
            return

        title = data.get("title", "Musiqa")
        artist = data.get("artist", "")
        duration = data.get("duration", 0)

        sent_msg = await send_audio_response(
            chat_id=message.chat.id,
            bot=bot,
            song_id=song_id,
            title=title,
            artist=artist,
            duration=duration,
            file_id_or_path=data["path"],
            is_cached_file_id=False,
            user_id=user_id,
            cover_url=data.get("cover_url") or ""
        )

        if sent_msg and sent_msg.audio:
            db.cache_music(song_id, sent_msg.audio.file_id, title, artist, duration, data.get("cover_url"))
            db.record_download(user_id, song_id)

        safe_remove(data.get("path"))
    except Exception as e:
        print(f"[Direct Download Error]: {e}")
        await message.reply("❌ Musiqani yuklashda xatolik yuz berdi.")

@router.callback_query(F.data.startswith("dl:"))
async def handle_download_callback(callback: CallbackQuery, bot: Bot):
    song_id = callback.data.split("dl:", 1)[1]
    user_id = callback.from_user.id
    await callback.answer("Yuklab olish boshlandi...")

    # 1. Keshda mavjud bo'lsa darhol yuboramiz
    cached = db.get_cached_music(song_id)
    if cached and cached.get("file_id"):
        db.record_download(user_id, song_id)
        await send_audio_response(
            chat_id=callback.message.chat.id,
            bot=bot,
            song_id=song_id,
            title=cached.get("title") or "Musiqa",
            artist=cached.get("performer") or "",
            duration=cached.get("duration") or 0,
            file_id_or_path=cached["file_id"],
            is_cached_file_id=True,
            user_id=user_id,
            cover_url=cached.get("cover_url") or ""
        )
        return

    try:
        # Userga bot hozir ishlayotganini bildirish (tepada 'uploading audio...' chiqadi)
        await bot.send_chat_action(callback.message.chat.id, "upload_voice")
        
        data = await MusicSearcher.download_by_id_or_url(song_id)
        if not data:
            await callback.message.answer("❌ Musiqani yuklab olishda xatolik yuz berdi yoki hajmi 50MB dan katta.")
            return

        title = data.get("title", "Musiqa")
        artist = data.get("artist", "")
        duration = data.get("duration", 0)

        if data.get("cached") and data.get("file_id"):
            db.record_download(user_id, song_id)
            await send_audio_response(
                chat_id=callback.message.chat.id,
                bot=bot,
                song_id=song_id,
                title=title,
                artist=artist,
                duration=duration,
                file_id_or_path=data["file_id"],
                is_cached_file_id=True,
                user_id=user_id,
                cover_url=data.get("cover_url") or ""
            )
            return

        mp3_path = data.get("path")
        if not mp3_path or not Path(mp3_path).exists():
            await callback.message.answer("❌ Musiqa fayli topilmadi.")
            return

        await bot.send_chat_action(callback.message.chat.id, "upload_voice")

        sent_msg = await send_audio_response(
            chat_id=callback.message.chat.id,
            bot=bot,
            song_id=song_id,
            title=title,
            artist=artist,
            duration=duration,
            file_id_or_path=mp3_path,
            is_cached_file_id=False,
            user_id=user_id,
            cover_url=data.get("cover_url") or ""
        )

        if sent_msg and sent_msg.audio:
            db.cache_music(song_id, sent_msg.audio.file_id, title, artist, duration, data.get("cover_url"))
            db.record_download(user_id, song_id)

        safe_remove(mp3_path)
    except Exception as e:
        print(f"[Download Callback Error]: {e}")
        await callback.message.answer("❌ Musiqani yuklab yuborishda xatolik yuz berdi.")

@router.callback_query(F.data.startswith("dl_shaz:"))
async def handle_shazam_download(callback: CallbackQuery, bot: Bot):
    query = callback.data.split("dl_shaz:", 1)[1]
    user_id = callback.from_user.id
    await callback.answer("Asl musiqa qidirilmoqda...")

    try:
        await bot.send_chat_action(callback.message.chat.id, "upload_voice")
        results = await MusicSearcher.search(query, limit=1)
        if not results:
            await callback.message.answer("❌ Asl musiqa topilmadi.")
            return

        song_id = results[0]["id"]
        data = await MusicSearcher.download_by_id_or_url(song_id, title=query)
        if not data:
            await callback.message.answer("❌ Musiqani yuklash imkoni bo'lmadi.")
            return

        title = data.get("title", query)
        artist = data.get("artist", "")
        duration = data.get("duration", 0)

        if data.get("cached") and data.get("file_id"):
            db.record_download(user_id, song_id)
            await send_audio_response(
                chat_id=callback.message.chat.id,
                bot=bot,
                song_id=song_id,
                title=title,
                artist=artist,
                duration=duration,
                file_id_or_path=data["file_id"],
                is_cached_file_id=True,
                user_id=user_id,
                cover_url=data.get("cover_url") or ""
            )
            return

        mp3_path = data.get("path")
        if not mp3_path or not Path(mp3_path).exists():
            await callback.message.answer("❌ Musiqa fayli topilmadi.")
            return

        sent_msg = await send_audio_response(
            chat_id=callback.message.chat.id,
            bot=bot,
            song_id=song_id,
            title=title,
            artist=artist,
            duration=duration,
            file_id_or_path=mp3_path,
            is_cached_file_id=False,
            user_id=user_id,
            cover_url=data.get("cover_url") or ""
        )

        if sent_msg and sent_msg.audio:
            db.cache_music(song_id, sent_msg.audio.file_id, title, artist, duration, data.get("cover_url"))
            db.record_download(user_id, song_id)

        safe_remove(mp3_path)
    except Exception as e:
        print(f"[Shazam Download Error]: {e}")
        await callback.message.answer("❌ Musiqani yuklab olishda xatolik yuz berdi.")

# --- QO'SHIQ MATNI (LYRICS) HANDLERI ---
@router.callback_query(F.data.startswith("lyr:"))
async def handle_lyrics_request(callback: CallbackQuery):
    song_id = callback.data.split("lyr:", 1)[1]
    await callback.answer("Qo'shiq matni qidirilmoqda... 📜")

    cached = db.get_cached_music(song_id)
    title = cached.get("title") if cached else song_id
    artist = cached.get("performer") if cached else None

    status_msg = await callback.message.reply("🔍 <i>Qo'shiq matni qidirilmoqda...</i>", parse_mode="HTML")

    try:
        lyrics_data = await LyricsService.get_lyrics(title, artist)
        if not lyrics_data or not lyrics_data.get("lyrics"):
            await status_msg.edit_text(
                f"ℹ️ <b>«{html.escape(title)}»</b> qo'shig'ining to'liq matni hozircha topilmadi.",
                parse_mode="HTML"
            )
            return

        song_title = html.escape(lyrics_data.get("track_name", title))
        artist_name = html.escape(lyrics_data.get("artist_name", artist or ""))
        lyrics_text = html.escape(lyrics_data["lyrics"][:3500]) # Telegram cheklovi 4096 belgi

        response = (
            f"📜 <b>«{song_title}» — QO'SHIQ MATNI:</b>\n"
            f"👤 <i>Ijrochi: {artist_name}</i>\n\n"
            f"{lyrics_text}\n\n"
            "🎧 @musicyuklllabot"
        )
        await status_msg.edit_text(response, parse_mode="HTML")
    except Exception as e:
        print(f"[Lyrics Handler Error]: {e}")
        await status_msg.edit_text("❌ Qo'shiq matnini olishda xatolik yuz berdi.")
