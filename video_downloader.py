import asyncio
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import yt_dlp

from config import TEMP_DIR, MAX_DOWNLOAD_SIZE_BYTES
from utils.helpers import format_duration
from utils.ffmpeg_setup import get_ffmpeg_path, ensure_ffmpeg

class VideoDownloader:
    """Ijtimoiy tarmoqlar (YouTube, TikTok, Instagram va b.) dan video va audio yuklovchi xizmat"""

    @classmethod
    def _get_base_ydl_opts(cls) -> dict:
        ffmpeg_path = get_ffmpeg_path() or ensure_ffmpeg()
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "concurrent_fragment_downloads": 5,
            "retries": 5,
            "fragment_retries": 5,
            "buffersize": 1024 * 64,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"],
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }
        if ffmpeg_path:
            opts["ffmpeg_location"] = ffmpeg_path
        return opts

    @classmethod
    async def get_info(cls, url: str) -> Optional[Dict[str, Any]]:
        """Video haqida umumiy ma'lumot olish"""
        def _sync_info():
            opts = cls._get_base_ydl_opts()
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        return None
                    return {
                        "id": info.get("id"),
                        "title": info.get("title", "Video"),
                        "duration": info.get("duration") or 0,
                        "duration_str": format_duration(info.get("duration")),
                        "thumbnail": info.get("thumbnail"),
                        "uploader": info.get("uploader") or info.get("channel") or "",
                        "url": url,
                    }
                except Exception as e:
                    print(f"[VideoInfo Error]: {e}")
                    return None

        return await asyncio.to_thread(_sync_info)

    @classmethod
    async def download_video(cls, url: str) -> Optional[Dict[str, Any]]:
        """Videoni MP4 formatida yuklab olish (50MB gacha moslashtirilgan)"""
        def _sync_download():
            file_uid = uuid.uuid4().hex[:8]
            output_template = str(TEMP_DIR / f"vid_{file_uid}.%(ext)s")

            opts = cls._get_base_ydl_opts()
            # Telegram bot limiti 50MB bo'lgani uchun 50MB dan oshmaydigan eng yaxshi formatni tanlaymiz
            opts.update({
                "format": (
                    f"bestvideo[filesize<?{MAX_DOWNLOAD_SIZE_BYTES}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"best[filesize<?{MAX_DOWNLOAD_SIZE_BYTES}][ext=mp4]/"
                    f"bestvideo+bestaudio/best"
                ),
                "outtmpl": output_template,
                "merge_output_format": "mp4",
                "max_filesize": MAX_DOWNLOAD_SIZE_BYTES,
            })

            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                    video_path = TEMP_DIR / f"vid_{file_uid}.mp4"

                    if not video_path.exists():
                        for f in TEMP_DIR.glob(f"vid_{file_uid}.*"):
                            if f.suffix.lower() in (".mp4", ".mkv", ".webm"):
                                video_path = f
                                break

                    if not video_path.exists() or video_path.stat().st_size == 0:
                        return None

                    return {
                        "path": video_path,
                        "title": info.get("title", "Video"),
                        "duration": int(info.get("duration") or 0),
                        "width": info.get("width"),
                        "height": info.get("height"),
                        "file_size": video_path.stat().st_size,
                        "thumbnail": info.get("thumbnail"),
                    }
                except Exception as e:
                    print(f"[VideoDownload Error]: {e}")
                    return None

        return await asyncio.to_thread(_sync_download)

    @classmethod
    async def download_audio_from_url(cls, url: str) -> Optional[Dict[str, Any]]:
        """Video havolasidan faqat audioni (MP3) yuklab olish"""
        def _sync_audio_download():
            file_uid = uuid.uuid4().hex[:8]
            output_template = str(TEMP_DIR / f"vid_audio_{file_uid}.%(ext)s")

            opts = cls._get_base_ydl_opts()
            opts.update({
                "format": "bestaudio/140/ba/b/best",
                "outtmpl": output_template,
                "max_filesize": MAX_DOWNLOAD_SIZE_BYTES,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    },
                    {
                        "key": "FFmpegMetadata",
                        "add_metadata": True,
                    },
                ],
            })

            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                    mp3_path = TEMP_DIR / f"vid_audio_{file_uid}.mp3"

                    if not mp3_path.exists():
                        for f in TEMP_DIR.glob(f"vid_audio_{file_uid}.*"):
                            if f.suffix.lower() == ".mp3":
                                mp3_path = f
                                break

                    if not mp3_path.exists() or mp3_path.stat().st_size == 0:
                        return None

                    return {
                        "path": mp3_path,
                        "title": info.get("title", "Audio"),
                        "artist": info.get("uploader") or info.get("channel") or "",
                        "duration": int(info.get("duration") or 0),
                        "file_size": mp3_path.stat().st_size,
                    }
                except Exception as e:
                    print(f"[VideoAudioDownload Error]: {e}")
                    return None

        return await asyncio.to_thread(_sync_audio_download)
