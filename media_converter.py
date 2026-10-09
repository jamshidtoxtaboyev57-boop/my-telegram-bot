import asyncio
import os
import uuid
from pathlib import Path
from typing import Optional
from config import TEMP_DIR
from utils.ffmpeg_setup import get_ffmpeg_path, ensure_ffmpeg

class MediaConverter:
    """Video va ovozli fayllarni formatlash hamda audio ajratib olish xizmati"""

    @staticmethod
    def _get_ffmpeg() -> str:
        ffmpeg = get_ffmpeg_path() or ensure_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("FFmpeg topilmadi. Iltimos, ffmpeg o'rnatilganligini tekshiring.")
        return ffmpeg

    @classmethod
    async def extract_audio_from_video(
        cls, video_path: str | Path, output_mp3: Optional[str | Path] = None
    ) -> Optional[Path]:
        """Videodan audioni MP3 formatida ajratib oladi"""
        ffmpeg = cls._get_ffmpeg()
        in_path = Path(video_path)
        if not in_path.exists():
            return None

        if not output_mp3:
            output_mp3 = TEMP_DIR / f"audio_{uuid.uuid4().hex[:10]}.mp3"
        out_path = Path(output_mp3)

        cmd = [
            ffmpeg,
            "-y",               # Fayl mavjud bo'lsa ustidan yozish
            "-i", str(in_path), # Kirish fayli
            "-vn",              # Videoni tashlab yuborish
            "-acodec", "libmp3lame",
            "-q:a", "4",        # Tezkor va yuqori sifatli audio eksport
            str(out_path),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                return out_path
            else:
                print(f"[FFmpeg Video Extract Error]: {stderr.decode('utf-8', errors='ignore')}")
                return None
        except Exception as e:
            print(f"[MediaConverter Error]: {e}")
            return None

    @classmethod
    async def convert_voice_to_mp3(
        cls, voice_path: str | Path, output_mp3: Optional[str | Path] = None
    ) -> Optional[Path]:
        """Telegram ovozli xabarini (OGG Opus) standart MP3 formatiga o'tkazadi"""
        ffmpeg = cls._get_ffmpeg()
        in_path = Path(voice_path)
        if not in_path.exists():
            return None

        if not output_mp3:
            output_mp3 = TEMP_DIR / f"voice_{uuid.uuid4().hex[:10]}.mp3"
        out_path = Path(output_mp3)

        cmd = [
            ffmpeg,
            "-y",
            "-i", str(in_path),
            "-acodec", "libmp3lame",
            "-b:a", "128k",
            str(out_path),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                return out_path
            else:
                print(f"[FFmpeg Voice Convert Error]: {stderr.decode('utf-8', errors='ignore')}")
                return None
        except Exception as e:
            print(f"[MediaConverter Voice Error]: {e}")
            return None

    @classmethod
    async def extract_audio_sample(
        cls, media_path: str | Path, duration_sec: int = 15
    ) -> Optional[Path]:
        """Tanish uchun tezkor 15 soniyalik audio bo'lak ajratadi"""
        ffmpeg = cls._get_ffmpeg()
        in_path = Path(media_path)
        if not in_path.exists():
            return None

        out_path = TEMP_DIR / f"sample_{uuid.uuid4().hex[:10]}.mp3"
        cmd = [
            ffmpeg,
            "-y",
            "-t", str(duration_sec),
            "-i", str(in_path),
            "-vn",
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            str(out_path),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                return out_path
            return None
        except Exception:
            return None
