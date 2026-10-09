import html
from math import ceil
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from database.db import db
from keyboards.inline import (
    get_favorites_keyboard,
    get_audio_action_keyboard,
)
from core.music_search import MusicSearcher
from utils.helpers import format_duration, sanitize_filename, safe_remove
from pathlib import Path

router = Router(name="favorites_router")

PER_PAGE = 5

async def render_favorites_page(user_id: int, page: int = 1):
    total_count = db.get_favorites_count(user_id)
    if total_count == 0:
        return (
            "❤️ <b>Sizning pleylistingiz hozircha bo'sh!</b>\n\n"
            "Istalgan musiqani qidirib topganingizda yoki eshitayotganingizda "
            "<b>«❤️ Sevimlilarga qo'shish»</b> tugmasini bossangiz, "
            "u shu yerda saqlanib qoladi va istagan paytda bir zumda tinglashingiz mumkin bo'ladi! 🎧",
            None
        )

    total_pages = max(1, ceil(total_count / PER_PAGE))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * PER_PAGE

    favs = db.get_user_favorites(user_id, limit=PER_PAGE, offset=offset)

    lines = [
        "❤️ <b>MENING SEVIMLI MUSIQALARIM</b>\n",
        f"<i>Jami saqlangan musiqalar: {total_count} ta</i>\n"
    ]

    for i, item in enumerate(favs, 1):
        idx = offset + i
        title = html.escape(item.get("title") or "Noma'lum")
        performer = html.escape(item.get("performer") or "")
        dur = format_duration(item.get("duration") or 0)
        display_name = f"{performer} — {title}" if performer else title
        lines.append(f"<b>{idx}.</b> 🎵 <b>{display_name}</b> <code>[{dur}]</code>")

    lines.append("\n<i>Tinglash uchun pastdagi raqamni bosing:</i>")
    text = "\n".join(lines)
    kb = get_favorites_keyboard(favs, page=page, total_pages=total_pages)
    return text, kb

@router.message(F.text == "❤️ Sevimlilarim")
@router.message(F.text == "/favorites")
async def show_favorites(message: Message):
    text, kb = await render_favorites_page(message.from_user.id, page=1)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("fav_pg:"))
async def cb_fav_page(callback: CallbackQuery):
    page = int(callback.data.split("fav_pg:", 1)[1])
    text, kb = await render_favorites_page(callback.from_user.id, page=page)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("fav:"))
async def cb_add_favorite(callback: CallbackQuery, bot: Bot):
    song_id = callback.data.split("fav:", 1)[1]
    user_id = callback.from_user.id

    cached = db.get_cached_music(song_id)
    title = cached.get("title", "Musiqa") if cached else "Musiqa"
    performer = cached.get("performer", "") if cached else ""
    duration = cached.get("duration", 0) if cached else 0
    file_id = cached.get("file_id") if cached else None

    db.add_favorite(user_id, song_id, title, performer, duration, file_id)

    # Tugmani "O'chirish" ga yangilaymiz
    bot_info = await bot.get_me()
    try:
        new_kb = get_audio_action_keyboard(song_id, title=title, is_favorite=True, bot_username=bot_info.username)
        await callback.message.edit_reply_markup(reply_markup=new_kb)
    except Exception:
        pass

    await callback.answer("❤️ Sevimlilar ro'yxatiga qo'shildi!", show_alert=False)

@router.callback_query(F.data.startswith("unfav:"))
async def cb_remove_favorite(callback: CallbackQuery, bot: Bot):
    song_id = callback.data.split("unfav:", 1)[1]
    user_id = callback.from_user.id

    db.remove_favorite(user_id, song_id)

    cached = db.get_cached_music(song_id)
    title = cached.get("title", "Musiqa") if cached else "Musiqa"

    bot_info = await bot.get_me()
    try:
        new_kb = get_audio_action_keyboard(song_id, title=title, is_favorite=False, bot_username=bot_info.username)
        await callback.message.edit_reply_markup(reply_markup=new_kb)
    except Exception:
        pass

    await callback.answer("💔 Sevimlilardan olib tashlandi!", show_alert=False)

@router.callback_query(F.data.startswith("play_fav:"))
async def cb_play_favorite(callback: CallbackQuery, bot: Bot):
    song_id = callback.data.split("play_fav:", 1)[1]
    await callback.answer("Yuklanmoqda...")

    bot_info = await bot.get_me()
    bot_username = bot_info.username or "musicyuklllabot"

    cached = db.get_cached_music(song_id)
    if cached and cached.get("file_id"):
        db.record_download(callback.from_user.id, song_id)
        kb = get_audio_action_keyboard(song_id, title=cached.get("title", ""), is_favorite=True, bot_username=bot_username)
        caption = f"🎧 <b>{html.escape(cached.get('title', 'Musiqa'))}</b>\n⚡️ @{bot_username} (Sevimlilar)"
        await callback.message.answer_audio(
            audio=cached["file_id"],
            title=cached.get("title"),
            performer=cached.get("performer"),
            duration=cached.get("duration") or 0,
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    # Keshda bo'lmasa yuklab beramiz
    status_msg = await callback.message.reply("⏳ <i>Musiqa tayyorlanmoqda...</i>", parse_mode="HTML")
    try:
        data = await MusicSearcher.download_by_id_or_url(song_id)
        if not data or not data.get("path"):
            await status_msg.edit_text("❌ Musiqani yuklab olish imkoni bo'lmadi.")
            return

        title = data.get("title", "Musiqa")
        artist = data.get("artist", "")
        duration = data.get("duration", 0)

        kb = get_audio_action_keyboard(song_id, title=title, is_favorite=True, bot_username=bot_username)
        clean_name = sanitize_filename(f"{artist} - {title}" if artist else title)
        audio_file = FSInputFile(str(data["path"]), filename=f"{clean_name}.mp3")

        sent_msg = await callback.message.answer_audio(
            audio=audio_file,
            title=title,
            performer=artist,
            duration=duration,
            caption=f"🎧 <b>{html.escape(title)}</b>\n⚡️ @{bot_username}",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await status_msg.delete()

        if sent_msg and sent_msg.audio:
            db.cache_music(song_id, sent_msg.audio.file_id, title, artist, duration, data.get("cover_url"))
            db.record_download(callback.from_user.id, song_id)

        safe_remove(data.get("path"))
    except Exception as e:
        print(f"[Play Fav Error]: {e}")
        await status_msg.edit_text("❌ Musiqani yuklashda xatolik yuz berdi.")
