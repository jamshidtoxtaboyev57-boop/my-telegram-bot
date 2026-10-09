import asyncio
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import yt_dlp

from config import TEMP_DIR, MAX_DOWNLOAD_SIZE_BYTES
from database.db import db
from utils.helpers import format_duration, sanitize_filename
from utils.ffmpeg_setup import get_ffmpeg_path, ensure_ffmpeg

class MusicSearcher:
    """Musiqalarni tezkor qidirish va MP3 formatida yuklab olish xizmati (Turbo)"""

    @classmethod
    def _get_base_ydl_opts(cls) -> dict:
        ffmpeg_path = get_ffmpeg_path() or ensure_ffmpeg()
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "geo_bypass": True,
            "concurrent_fragment_downloads": 5, # Parallel tezkor yuklash
            "retries": 5,
            "fragment_retries": 5,
            "buffersize": 1024 * 64,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }
        if ffmpeg_path:
            opts["ffmpeg_location"] = ffmpeg_path
        return opts

    @classmethod
    async def search(cls, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Musiqa nomi yoki ijrochi bo'yicha tezkor qidiruv"""
        def _sync_search():
            opts = cls._get_base_ydl_opts()
            opts.update({
                "extract_flat": True,
                "skip_download": True,
                "lazy_playlist": True,
                "youtube_include_dash_manifest": False,
                "youtube_include_hls_manifest": False,
                "extract_flat": "in_playlist",
            })
            search_query = f"ytsearch{limit}:{query}"
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    result = ydl.extract_info(search_query, download=False)
                    if not result or "entries" not in result:
                        return []
                    
                    items = []
                    for entry in result["entries"]:
                        if not entry:
                            continue
                        duration = entry.get("duration") or 0
                        if duration > 1200:
                            continue
                        
                        items.append({
                            "id": entry.get("id"),
                            "title": entry.get("title", "Noma'lum musiqa"),
                            "artist": entry.get("uploader") or entry.get("channel") or "",
                            "duration": duration,
                            "duration_str": format_duration(duration),
                            "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                        })
                    return items
                except Exception as e:
                    print(f"[MusicSearch YTDLP Error]: {e}")
                    return []

        return await asyncio.to_thread(_sync_search)

    @classmethod
    async def download_by_id_or_url(
        cls, id_or_url: str, title: Optional[str] = None, artist: Optional[str] = None, cover_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Video ID yoki havola orqali MP3 audio yuklab oladi (Kesh tekshiruvi bilan)"""
        # 1. Keshda bormi tekshiramiz (Agar avval yuklangan bo'lsa 0.05 soniyada beradi!)
        cached = db.get_cached_music(id_or_url)
        if cached:
            return {
                "cached": True,
                "file_id": cached["file_id"],
                "title": cached.get("title") or title or "Musiqa",
                "artist": cached.get("performer") or artist or "",
                "duration": cached.get("duration") or 0,
                "duration_str": format_duration(cached.get("duration") or 0),
                "cover_url": cached.get("cover_url") or cover_url,
            }

        def _sync_download():
            ffmpeg_path = get_ffmpeg_path() or ensure_ffmpeg()
            file_uid = uuid.uuid4().hex[:8]
            output_template = str(TEMP_DIR / f"song_{file_uid}.%(ext)s")

            target_url = id_or_url
            if not id_or_url.startswith("http"):
                target_url = f"https://www.youtube.com/watch?v={id_or_url}"

            # YouTube cheklovlariga qarshi turli xil player clientlar bilan navbatma-navbat urinib ko'rish
            # yt-dlp o'zi standart clientlarni tanlashi uchun bo'sh qoldiramiz yoki oddiy urinish qilamiz
            client_attempts = [None]

            for clients in client_attempts:
                opts = cls._get_base_ydl_opts()
                opts.update({
                    "format": "bestaudio[ext=m4a]/140/bestaudio/best",
                    "outtmpl": output_template,
                    "max_filesize": MAX_DOWNLOAD_SIZE_BYTES,
                    "postprocessors": [], # Tezlik uchun re-encoding bekor qilindi
                })

                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(target_url, download=True)
                        mp3_path = None

                        for f in TEMP_DIR.glob(f"song_{file_uid}.*"):
                            if f.is_file():
                                mp3_path = f
                                break

                        if mp3_path and mp3_path.exists() and mp3_path.stat().st_size > 0:
                            final_title = title or info.get("title") or "Musiqa"
                            final_artist = artist or info.get("artist") or info.get("uploader") or ""
                            duration = info.get("duration") or 0
                            thumb = cover_url or info.get("thumbnail") or ""

                            return {
                                "cached": False,
                                "song_id": id_or_url,
                                "path": mp3_path,
                                "title": final_title,
                                "artist": final_artist,
                                "duration": int(duration),
                                "duration_str": format_duration(duration),
                                "file_size": mp3_path.stat().st_size,
                                "cover_url": thumb,
                            }
                except Exception as e:
                    print(f"[MusicDownload Turbo Attempt with {clients} Error]: {e}")
                    continue

            return None

        result = await asyncio.to_thread(_sync_download)
        return result

