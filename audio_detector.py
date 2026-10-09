import uuid
import time
import random
from pathlib import Path
from typing import Optional, Dict, Any, List
import aiohttp
from utils.ffmpeg_setup import ensure_ffmpeg
# FFmpeg mavjudligini ta'minlash (pydub dan oldin bo'lishi shart)
ensure_ffmpeg()

from pydub import AudioSegment

from core.shazam.algorithm import SignatureGenerator
from core.shazam.user_agent import USER_AGENTS

class AudioDetector:
    """Ovozli xabar, audio yoki videolardan musiqani aniqlash tizimi (Shazam Multi-Window)"""

    @staticmethod
    async def _recognize_segment(segment: AudioSegment) -> Optional[Dict[str, Any]]:
        try:
            # Shazam formati uchun normalizatsiya (16kHz, mono, 16-bit PCM)
            segment = segment.set_sample_width(2)
            segment = segment.set_frame_rate(16000)
            segment = segment.set_channels(1)

            sig_gen = SignatureGenerator()
            sig_gen.feed_input(segment.get_array_of_samples())

            signature = None
            while True:
                sig = sig_gen.get_next_signature()
                if sig:
                    signature = sig
                    break
                if len(sig_gen.input_pending_processing) < 128:
                    break

            if not signature:
                return None

            uri = signature.encode_to_uri()
            sample_ms = int(signature.number_samples / signature.sample_rate_hz * 1000)

            url = (
                f"https://amp.shazam.com/discovery/v5/en/US/iphone/-/tag/"
                f"{str(uuid.uuid4()).upper()}/{str(uuid.uuid4()).upper()}"
                f"?sync=true&webv3=true&sampling=true&connected=&shazamapiversion=v3"
                f"&sharehub=true&hubv5minorversion=v5.1&hidelb=true&video=v3"
            )

            payload = {
                "timezone": "UTC",
                "signature": {
                    "uri": uri,
                    "samplems": sample_ms,
                },
                "timestamp": int(time.time() * 1000),
                "context": {},
                "geolocation": {},
            }

            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Content-Type": "application/json",
            }

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()

            track = data.get("track")
            if not track:
                return None

            title = track.get("title", "Noma'lum qo'shiq")
            artist = track.get("subtitle", "Noma'lum ijrochi")
            genre = track.get("genres", {}).get("primary", "")
            album = ""
            for sec in track.get("sections", []):
                if sec.get("type") == "SONG":
                    for meta in sec.get("metadata", []):
                        if meta.get("title", "").lower() == "album":
                            album = meta.get("text", "")
                            break

            images = track.get("images", {})
            cover_url = images.get("coverarthq") or images.get("coverart") or ""
            shazam_url = track.get("url", "")

            return {
                "title": title,
                "artist": artist,
                "full_title": f"{artist} - {title}",
                "album": album,
                "genre": genre,
                "cover_url": cover_url,
                "shazam_url": shazam_url,
                "raw": track,
            }
        except Exception:
            return None

    @classmethod
    async def recognize(cls, audio_path: str | Path) -> Optional[Dict[str, Any]]:
        path = Path(audio_path)
        if not path.exists():
            return None

        try:
            full_audio = AudioSegment.from_file(str(path))
            total_len = len(full_audio)

            # 1-oyna: 0 dan 15 soniyagacha
            slice_1 = full_audio[:15000]
            res = await cls._recognize_segment(slice_1)
            if res:
                return res

            # Agar 1-oynada topilmasa va video 15 soniyadan uzun bo'lsa (boshida gap yoki jimlik bo'lishi mumkin)
            # 2-oyna: 4 dan 19 soniyagacha
            if total_len > 15000:
                slice_2 = full_audio[4000:19000]
                res = await cls._recognize_segment(slice_2)
                if res:
                    return res

            # 3-oyna: 10 dan 25 soniyagacha (naqorat / avj qismi)
            if total_len > 22000:
                slice_3 = full_audio[10000:25000]
                res = await cls._recognize_segment(slice_3)
                if res:
                    return res

            return None
        except Exception as e:
            print(f"[AudioDetector Error]: {e}")
            return None
