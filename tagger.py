import os
from pathlib import Path
from typing import Optional
import aiohttp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, ID3NoHeaderError

async def apply_audio_tags(
    mp3_path: str | Path,
    title: str,
    artist: Optional[str] = None,
    album: Optional[str] = None,
    cover_url: Optional[str] = None,
) -> bool:
    """MP3 fayliga toza ID3 teglarini va muqova (cover art) rasmini joylaydi."""
    path = Path(mp3_path)
    if not path.exists() or path.stat().st_size == 0:
        return False

    try:
        try:
            audio = ID3(str(path))
        except ID3NoHeaderError:
            audio = ID3()

        # Nom va Ijrochi
        if title:
            audio.add(TIT2(encoding=3, text=title))
        if artist:
            audio.add(TPE1(encoding=3, text=artist))
        if album:
            audio.add(TALB(encoding=3, text=album))

        # Muqova rasmini yuklab olib APIC tagiga kiritish
        if cover_url and cover_url.startswith("http"):
            try:
                timeout = aiohttp.ClientTimeout(total=8)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(cover_url) as resp:
                        if resp.status == 200:
                            img_data = await resp.read()
                            if img_data:
                                mime = "image/jpeg" if ("jpg" in cover_url.lower() or "jpeg" in cover_url.lower()) else "image/png"
                                audio.add(
                                    APIC(
                                        encoding=3,
                                        mime=mime,
                                        type=3, # front cover
                                        desc="Cover",
                                        data=img_data
                                    )
                                )
            except Exception as img_err:
                # Muqova rasmini olishda xato bo'lsa ham qo'shiq buzilmasligi kerak
                pass

        audio.save(str(path))
        return True
    except Exception as e:
        print(f"[AudioTagger Error]: {e}")
        return False
