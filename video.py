import html
import uuid
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from core.video_downloader import VideoDownloader
from core.media_converter import MediaConverter
from core.audio_detector import AudioDetector
from core.music_search import MusicSearcher
from database.db import db
from keyboards.inline import (
    get_video_options_keyboard,
    get_shazam_result_keyboard,
    get_search_results_keyboard,
    get_audio_action_keyboard,
)
from handlers.search import send_audio_response
from utils.helpers import is_url, extract_first_url, safe_remove, format_bytes
from config import TEMP_DIR

router = Router(name="video_router")

# Havolalarni vaqtinchalik saqlash lug'ati (Callback data 64 bayt chegarasi uchun)
URL_CACHE = {}

@router.message(F.text.func(lambda text: bool(extract_first_url(text))))
async def handle_video_url(message: Message, bot: Bot):
    url = extract_first_url(message.text)
    user_id = message.from_user.id
    db.record_search(user_id)

    status_msg = await message.reply("🔎 <i>Havola tahlil qilinmoqda...</i>", parse_mode="HTML")

    try:
        info = await VideoDownloader.get_info(url)
        if not info:
            await status_msg.edit_text("❌ Havoladan video ma'lumotlarini yuklab bo'lmadi yoki havola yaroqsiz.")
            return

        url_key = uuid.uuid4().hex[:10]
        URL_CACHE[url_key] = url

        title = html.escape(info.get("title", "Video"))
        duration = info.get("duration_str", "")
        uploader = html.escape(info.get("uploader", ""))

        text = (
            "╭────────────────────────────╮\n"
            "│    🎬 <b>VIDEO MA'LUMOTI</b>        │\n"
            "╰────────────────────────────╯\n\n"
            f"📌 <b>{title}</b>\n\n"
            f"⏱ <b>Davomiyligi:</b> {duration}\n"
            f"👤 <b>Muallif / Kanal:</b> {uploader}\n\n"
            "<i>Quyidagi variantlardan birini tanlang:</i> 👇"
        )
        kb = get_video_options_keyboard(url_key)
        await status_msg.edit_text(text, reply_markup=kb, parse_mode="HTML")

    except Exception as e:
        print(f"[Video URL Error]: {e}")
        await status_msg.edit_text("❌ Havolani qayta ishlashda xatolik yuz berdi.")

@router.callback_query(F.data.startswith("vid:"))
async def cb_download_video(callback: CallbackQuery, bot: Bot):
    url_key = callback.data.split("vid:", 1)[1]
    url = URL_CACHE.get(url_key)
    if not url:
        await callback.answer("Havola muddati o'tgan, iltimos qaytadan yuboring.", show_alert=True)
        return

    user_id = callback.from_user.id
    await callback.answer("Video yuklab olinmoqda...")
    status_msg = await callback.message.reply("⏳ <b>Video yuklab olinmoqda (bir necha soniya)...</b>", parse_mode="HTML")

    try:
        data = await VideoDownloader.download_video(url)
        if not data or not data.get("path"):
            await status_msg.edit_text("❌ Videoni yuklab bo'lmadi yoki hajmi 50MB dan katta.")
            return

        vid_path = data["path"]
        title = data.get("title", "Video")
        duration = data.get("duration", 0)
        width = data.get("width")
        height = data.get("height")

        bot_info = await bot.get_me()
        bot_username = bot_info.username or "musicyuklllabot"

        await bot.send_chat_action(callback.message.chat.id, "upload_video")
        video_file = FSInputFile(str(vid_path), filename="video.mp4")

        await callback.message.answer_video(
            video=video_file,
            caption=f"🎬 <b>{html.escape(title)}</b>\n\n⚡️ @{bot_username}",
            duration=duration,
            width=width,
            height=height,
            parse_mode="HTML"
        )
        db.record_download(user_id)
        await status_msg.delete()
        safe_remove(vid_path)

    except Exception as e:
        print(f"[Download Video Error]: {e}")
        await status_msg.edit_text("❌ Videoni yuborishda xatolik yuz berdi.")

@router.callback_query(F.data.startswith("aud:"))
async def cb_download_audio(callback: CallbackQuery, bot: Bot):
    url_key = callback.data.split("aud:", 1)[1]
    url = URL_CACHE.get(url_key)
    if not url:
        await callback.answer("Havola muddati o'tgan, iltimos qaytadan yuboring.", show_alert=True)
        return

    user_id = callback.from_user.id
    await callback.answer("Audio ajratib olinmoqda...")
    status_msg = await callback.message.reply("⏳ <b>Videodan MP3 audio ajratib olinmoqda...</b>", parse_mode="HTML")

    try:
        data = await VideoDownloader.download_audio_from_url(url)
        if not data or not data.get("path"):
            await status_msg.edit_text("❌ Musiqani yuklab olish imkoni bo'lmadi.")
            return

        mp3_path = data["path"]
        title = data.get("title", "Musiqa")
        artist = data.get("artist", "")
        duration = data.get("duration", 0)

        sent_msg = await send_audio_response(
            chat_id=callback.message.chat.id,
            bot=bot,
            song_id=url_key,
            title=title,
            artist=artist,
            duration=duration,
            file_id_or_path=mp3_path,
            is_cached_file_id=False,
            user_id=user_id,
        )
        await status_msg.delete()

        if sent_msg and sent_msg.audio:
            db.cache_music(url_key, sent_msg.audio.file_id, title, artist, duration)
            db.record_download(user_id, url_key)

        safe_remove(mp3_path)

    except Exception as e:
        print(f"[Download Video Audio Error]: {e}")
        await status_msg.edit_text("❌ Musiqani yuklab yuborishda xatolik yuz berdi.")

@router.callback_query(F.data.startswith("shaz_url:"))
async def cb_shazam_video_url(callback: CallbackQuery, bot: Bot):
    url_key = callback.data.split("shaz_url:", 1)[1]
    url = URL_CACHE.get(url_key)
    if not url:
        await callback.answer("Havola muddati o'tgan, qaytadan yuboring.", show_alert=True)
        return

    user_id = callback.from_user.id
    await callback.answer("Musiqa aniqlanmoqda...")
    status_msg = await callback.message.reply("🔍 <b>Videodagi asl musiqa aniqlanmoqda (Shazam)...</b>", parse_mode="HTML")

    try:
        data = await VideoDownloader.download_audio_from_url(url)
        if not data or not data.get("path"):
            await status_msg.edit_text("❌ Videodan audio ajratib olinmadi.")
            return

        mp3_path = data["path"]
        shaz_res = await AudioDetector.recognize(mp3_path)
        safe_remove(mp3_path)

        if not shaz_res:
            await status_msg.edit_text("❌ Videodagi musiqa aniqlanmadi.")
            return

        title = html.escape(shaz_res.get("title", ""))
        artist = html.escape(shaz_res.get("artist", ""))
        full_title = f"{shaz_res.get('artist', '')} - {shaz_res.get('title', '')}".strip(" -")
        album = html.escape(shaz_res.get("album", ""))
        cover_url = shaz_res.get("cover_url", "")

        await status_msg.edit_text(f"⚡️ <i>«{full_title}» variantlari qidirilmoqda...</i>", parse_mode="HTML")
        variants = await MusicSearcher.search(full_title, limit=6)

        info_lines = [
            "╭────────────────────────────╮",
            "│  🎉 <b>VIDEODAGI MUSIQA ANIQLANDI</b> │",
            "╰────────────────────────────╯\n",
            f"🎵 <b>Qo'shiq:</b> {title}",
            f"👤 <b>Ijrochi:</b> {artist}",
        ]
        if album:
            info_lines.append(f"💿 <b>Albom:</b> {album}")

        if variants:
            info_lines.append("\n🎶 <b>Topilgan variantlar:</b>")
            for i, v in enumerate(variants, 1):
                info_lines.append(f"<b>{i}.</b> {html.escape(v['title'])} <code>[{v['duration_str']}]</code>")
            info_lines.append("\n<i>Boshqa variantini yuklash uchun raqamni bosing:</i> 👇")
            kb = get_search_results_keyboard(variants)
        else:
            kb = get_shazam_result_keyboard(full_title, shaz_res.get("shazam_url", ""))

        caption = "\n".join(info_lines)

        if cover_url:
            await status_msg.delete()
            await callback.message.answer_photo(photo=cover_url, caption=caption, reply_markup=kb, parse_mode="HTML")
        else:
            await status_msg.edit_text(caption, reply_markup=kb, parse_mode="HTML")

        # Asl toza audio studiya trekini avtomatik yuborish
        best_id = variants[0]["id"] if variants else full_title
        dl_data = await MusicSearcher.download_by_id_or_url(best_id, title=title, artist=artist, cover_url=cover_url)
        if dl_data:
            if dl_data.get("cached") and dl_data.get("file_id"):
                await send_audio_response(
                    chat_id=callback.message.chat.id,
                    bot=bot,
                    song_id=best_id,
                    title=shaz_res.get("title") or title,
                    artist=shaz_res.get("artist") or artist,
                    duration=dl_data.get("duration", 0),
                    file_id_or_path=dl_data["file_id"],
                    is_cached_file_id=True,
                    user_id=user_id,
                    cover_url=cover_url
                )
                db.record_download(user_id, best_id)
            elif dl_data.get("path"):
                original_mp3 = dl_data["path"]
                sent_audio = await send_audio_response(
                    chat_id=callback.message.chat.id,
                    bot=bot,
                    song_id=best_id,
                    title=shaz_res.get("title") or title,
                    artist=shaz_res.get("artist") or artist,
                    duration=dl_data.get("duration", 0),
                    file_id_or_path=original_mp3,
                    is_cached_file_id=False,
                    user_id=user_id,
                    cover_url=cover_url
                )
                if sent_audio and sent_audio.audio:
                    db.cache_music(best_id, sent_audio.audio.file_id, title, artist, dl_data.get("duration", 0), cover_url)
                    db.record_download(user_id, best_id)
                safe_remove(original_mp3)

    except Exception as e:
        print(f"[Shazam Video URL Error]: {e}")
        try:
            await status_msg.edit_text("❌ Musiqani aniqlashda xatolik yuz berdi.")
        except Exception:
            await callback.message.answer("❌ Musiqani aniqlashda xatolik yuz berdi.")

# Telegram orqali yuborilgan to'g'ridan-to'g'ri Video yoki Dumaloq video xabarlar
@router.message(F.video | F.video_note)
async def handle_video_file(message: Message, bot: Bot):
    user_id = message.from_user.id
    db.record_search(user_id)

    file_id = message.video.file_id if message.video else message.video_note.file_id
    file_size = (message.video.file_size if message.video else message.video_note.file_size) or 0

    if file_size > 50 * 1024 * 1024:
        await message.reply("❌ Video hajmi juda katta (maksimal 50 MB).")
        return

    status_msg = await message.reply("⏳ <b>Video tahlil qilinmoqda va musiqasi aniqlanmoqda...</b>", parse_mode="HTML")
    temp_video = TEMP_DIR / f"vid_in_{uuid.uuid4().hex[:8]}.mp4"

    try:
        file_obj = await bot.get_file(file_id)
        await bot.download_file(file_obj.file_path, destination=str(temp_video))

        # 1. Videodan audioni ajratish
        await status_msg.edit_text("🎵 <b>Videodan audio ajratib olinmoqda...</b>", parse_mode="HTML")
        extracted_mp3 = await MediaConverter.extract_audio_from_video(temp_video)
        safe_remove(temp_video)

        if not extracted_mp3 or not extracted_mp3.exists():
            await status_msg.edit_text("❌ Videodan audio ajratishda xatolik yuz berdi.")
            return

        # 2. Ajratilgan audioni Shazam orqali tanish
        await status_msg.edit_text("🔍 <b>Videodagi asl musiqa aniqlanmoqda (Shazam)...</b>", parse_mode="HTML")
        shaz_res = await AudioDetector.recognize(extracted_mp3)

        if shaz_res:
            title = html.escape(shaz_res.get("title", ""))
            artist = html.escape(shaz_res.get("artist", ""))
            full_title = f"{shaz_res.get('artist', '')} - {shaz_res.get('title', '')}".strip(" -")
            cover_url = shaz_res.get("cover_url", "")
            album = html.escape(shaz_res.get("album", ""))

            # 3. Asl qo'shiqning bir nechta variantlarini qidiramiz
            await status_msg.edit_text(f"⚡️ <i>«{full_title}» variantlari qidirilmoqda...</i>", parse_mode="HTML")
            variants = await MusicSearcher.search(full_title, limit=6)

            info_lines = [
                "╭────────────────────────────╮",
                "│  🎉 <b>VIDEODAGI MUSIQA ANIQLANDI</b> │",
                "╰────────────────────────────╯\n",
                f"🎵 <b>Qo'shiq:</b> {title}",
                f"👤 <b>Ijrochi:</b> {artist}",
            ]
            if album:
                info_lines.append(f"💿 <b>Albom:</b> {album}")

            if variants:
                info_lines.append("\n🎶 <b>Topilgan variantlar:</b>")
                for i, v in enumerate(variants, 1):
                    info_lines.append(f"<b>{i}.</b> {html.escape(v['title'])} <code>[{v['duration_str']}]</code>")
                info_lines.append("\n<i>Kerakli variantni yuklab olish uchun pastdagi raqamni bosing:</i> 👇")
                kb = get_search_results_keyboard(variants)
            else:
                kb = get_shazam_result_keyboard(full_title, shaz_res.get("shazam_url", ""))

            caption_text = "\n".join(info_lines)

            if cover_url:
                await message.answer_photo(photo=cover_url, caption=caption_text, reply_markup=kb, parse_mode="HTML")
            else:
                await message.answer(caption_text, reply_markup=kb, parse_mode="HTML")

            # 4. Asl toza studio trekini avtomatik yuborish
            best_id = variants[0]["id"] if variants else full_title
            dl_data = await MusicSearcher.download_by_id_or_url(best_id, title=title, artist=artist, cover_url=cover_url)
            if dl_data:
                if dl_data.get("cached") and dl_data.get("file_id"):
                    await send_audio_response(
                        chat_id=message.chat.id,
                        bot=bot,
                        song_id=best_id,
                        title=shaz_res.get("title") or title,
                        artist=shaz_res.get("artist") or artist,
                        duration=dl_data.get("duration", 0),
                        file_id_or_path=dl_data["file_id"],
                        is_cached_file_id=True,
                        user_id=user_id,
                        cover_url=cover_url
                    )
                    db.record_download(user_id, best_id)
                elif dl_data.get("path"):
                    orig_mp3 = dl_data["path"]
                    sent_audio = await send_audio_response(
                        chat_id=message.chat.id,
                        bot=bot,
                        song_id=best_id,
                        title=shaz_res.get("title") or title,
                        artist=shaz_res.get("artist") or artist,
                        duration=dl_data.get("duration", 0),
                        file_id_or_path=orig_mp3,
                        is_cached_file_id=False,
                        user_id=user_id,
                        cover_url=cover_url
                    )
                    if sent_audio and sent_audio.audio:
                        db.cache_music(best_id, sent_audio.audio.file_id, title, artist, dl_data.get("duration", 0), cover_url)
                        db.record_download(user_id, best_id)
                    safe_remove(orig_mp3)

            # 5. Videoning o'zidagi audioni ham berish
            extracted_file = FSInputFile(str(extracted_mp3), filename="video_audio.mp3")
            await message.answer_audio(
                audio=extracted_file,
                title="Videodan ajratilgan audio",
                performer=artist or "Video Audio",
                caption="📹 <b>Videoning o'zidan ajratib olingan audio</b>",
                parse_mode="HTML"
            )

        else:
            await message.answer(
                "ℹ️ <b>Videodagi fon musiqasini Shazam orqali aniqlab bo'lmadi.</b>\n"
                "<i>(Fonda nutq/shovqin bor yoki qo'shiq juda qisqa)</i>\n\n"
                "Quyida videoning o'zidagi audio siz uchun ajratib berildi:",
                parse_mode="HTML"
            )
            extracted_file = FSInputFile(str(extracted_mp3), filename="video_audio.mp3")
            await message.answer_audio(
                audio=extracted_file,
                title="Videodan ajratilgan audio",
                performer="Video Audio",
                caption="🎵 <b>Videodan ajratib olingan audio</b>",
                parse_mode="HTML"
            )

        safe_remove(extracted_mp3)
        await status_msg.delete()

    except Exception as e:
        print(f"[Video File Handler Error]: {e}")
        try:
            await status_msg.edit_text("❌ Videoni qayta ishlashda xatolik yuz berdi.")
        except Exception:
            await message.answer("❌ Videoni qayta ishlashda xatolik yuz berdi.")
    finally:
        safe_remove(temp_video)
