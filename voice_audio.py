import html
import uuid
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message
from core.audio_detector import AudioDetector
from core.music_search import MusicSearcher
from database.db import db
from keyboards.inline import get_shazam_result_keyboard, get_search_results_keyboard
from handlers.search import send_audio_response
from utils.helpers import safe_remove
from config import TEMP_DIR

router = Router(name="voice_audio_router")

@router.message(F.voice | F.audio)
async def handle_voice_or_audio(message: Message, bot: Bot):
    user_id = message.from_user.id
    db.record_search(user_id)

    status_msg = await message.reply("🎙 <b>Ovoz tahlil qilinmoqda va musiqa aniqlanmoqda (Shazam)...</b>", parse_mode="HTML")

    file_id = message.voice.file_id if message.voice else message.audio.file_id
    file_ext = ".oga" if message.voice else (Path(message.audio.file_name or "audio.mp3").suffix or ".mp3")
    temp_path = TEMP_DIR / f"rec_{uuid.uuid4().hex[:8]}{file_ext}"

    try:
        # Faylni yuklab olish
        file_obj = await bot.get_file(file_id)
        await bot.download_file(file_obj.file_path, destination=str(temp_path))

        # Musiqani aniqlash (Shazam)
        result = await AudioDetector.recognize(temp_path)

        if not result:
            await status_msg.edit_text(
                "❌ <b>Musiqani aniqlab bo'lmadi.</b>\n\n"
                "💡 <i>Maslahat:</i>\n"
                "• Ovozli xabarni kamida 5-10 soniya davomida yozib yuboring;\n"
                "• Fon shovqini kamroq bo'lishiga e'tibor bering;\n"
                "• Yoki qo'shiq matnini / so'zlarini botga yozib izlang.",
                parse_mode="HTML"
            )
            return

        title = html.escape(result.get("title", ""))
        artist = html.escape(result.get("artist", ""))
        full_title = f"{result.get('artist', '')} - {result.get('title', '')}".strip(" -")
        album = html.escape(result.get("album", ""))
        genre = html.escape(result.get("genre", ""))
        cover_url = result.get("cover_url", "")

        # Asl qo'shiqning bir nechta variantlarini qidiramiz
        variants = await MusicSearcher.search(full_title, limit=6)

        text_lines = [
            "╭────────────────────────────╮",
            "│  🎉 <b>MUSIQA ANIQLANDI (SHAZAM)</b> │",
            "╰────────────────────────────╯\n",
            f"🎵 <b>Qo'shiq:</b> {title}",
            f"👤 <b>Ijrochi:</b> {artist}",
        ]
        if album:
            text_lines.append(f"💿 <b>Albom:</b> {album}")
        if genre:
            text_lines.append(f"🎼 <b>Janr:</b> {genre}")

        if variants:
            text_lines.append("\n🎶 <b>Topilgan variantlar:</b>")
            for i, v in enumerate(variants, 1):
                text_lines.append(f"<b>{i}.</b> {html.escape(v['title'])} <code>[{v['duration_str']}]</code>")
            text_lines.append("\n<i>Boshqa variantini yuklash uchun raqamni bosing:</i> 👇")
            kb = get_search_results_keyboard(variants)
        else:
            kb = get_shazam_result_keyboard(full_title, result.get("shazam_url", ""))

        caption_text = "\n".join(text_lines)

        # Cover rasmi bo'lsa rasm bilan, aks holda matn qilib yuboramiz
        if cover_url:
            await status_msg.delete()
            await message.answer_photo(
                photo=cover_url,
                caption=caption_text,
                reply_markup=kb,
                parse_mode="HTML"
            )
        else:
            await status_msg.edit_text(
                caption_text,
                reply_markup=kb,
                parse_mode="HTML"
            )

        # Asl toza audio studiya trekini (Variant 1) avtomatik yuborish
        best_id = variants[0]["id"] if variants else full_title
        dl_data = await MusicSearcher.download_by_id_or_url(best_id, title=title, artist=artist, cover_url=cover_url)
        if dl_data:
            if dl_data.get("cached") and dl_data.get("file_id"):
                await send_audio_response(
                    chat_id=message.chat.id,
                    bot=bot,
                    song_id=best_id,
                    title=result.get("title") or title,
                    artist=result.get("artist") or artist,
                    duration=dl_data.get("duration", 0),
                    file_id_or_path=dl_data["file_id"],
                    is_cached_file_id=True,
                    user_id=user_id,
                    cover_url=cover_url
                )
                db.record_download(user_id, best_id)
            elif dl_data.get("path"):
                mp3_path = dl_data["path"]
                sent_audio = await send_audio_response(
                    chat_id=message.chat.id,
                    bot=bot,
                    song_id=best_id,
                    title=result.get("title") or title,
                    artist=result.get("artist") or artist,
                    duration=dl_data.get("duration", 0),
                    file_id_or_path=mp3_path,
                    is_cached_file_id=False,
                    user_id=user_id,
                    cover_url=cover_url
                )
                if sent_audio and sent_audio.audio:
                    db.cache_music(best_id, sent_audio.audio.file_id, title, artist, dl_data.get("duration", 0), cover_url)
                    db.record_download(user_id, best_id)
                safe_remove(mp3_path)

    except Exception as e:
        print(f"[Voice/Audio Handler Error]: {e}")
        try:
            await status_msg.edit_text("❌ Ovozni qayta ishlashda xatolik yuz berdi.")
        except Exception:
            await message.answer("❌ Ovozni qayta ishlashda xatolik yuz berdi.")
    finally:
        safe_remove(temp_path)
