import re
import aiohttp
from typing import Optional, Dict, Any

class LyricsService:
    """Qo'shiqlar matnini (Lyrics) topish xizmati"""

    @staticmethod
    def _clean_title(text: str) -> str:
        """Video yoki qo'shiq nomidagi ortiqcha so'zlarni tozalaydi"""
        # (Official Video), [Audio], (Clip), (Remix) va hokazo
        cleaned = re.sub(r"[\(\[\{].*?[\)\]\}]", "", text)
        cleaned = re.sub(r"(official|music|video|audio|clip|klip|remix|slowed|reverb|hq|hd|4k|lyric|lyrics)", "", cleaned, flags=re.I)
        cleaned = re.sub(r"[|_~#@!]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or text

    @classmethod
    async def get_lyrics(cls, title: str, artist: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Qo'shiq matnini qidiradi va topilgan natijani qaytaradi"""
        cleaned_title = cls._clean_title(title)
        artist_clean = cls._clean_title(artist) if artist else ""

        queries_to_try = []
        if artist_clean and cleaned_title:
            queries_to_try.append(f"{artist_clean} {cleaned_title}")
        queries_to_try.append(cleaned_title)
        if artist_clean:
            queries_to_try.append(artist_clean)

        timeout = aiohttp.ClientTimeout(total=6)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # 1. To'g'ridan-to'g'ri GET endpoint
            if artist_clean and cleaned_title:
                try:
                    params = {"track_name": cleaned_title, "artist_name": artist_clean}
                    async with session.get("https://lrclib.net/api/get", params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            lyrics = data.get("plainLyrics") or data.get("syncedLyrics")
                            if lyrics:
                                return {
                                    "track_name": data.get("trackName", title),
                                    "artist_name": data.get("artistName", artist or ""),
                                    "lyrics": lyrics.strip()
                                }
                except Exception:
                    pass

            # 2. Qidiruv orqali (Search API)
            for q in queries_to_try:
                try:
                    async with session.get("https://lrclib.net/api/search", params={"q": q}) as resp:
                        if resp.status == 200:
                            items = await resp.json()
                            if isinstance(items, list) and len(items) > 0:
                                for item in items:
                                    lyrics = item.get("plainLyrics") or item.get("syncedLyrics")
                                    if lyrics:
                                        return {
                                            "track_name": item.get("trackName", title),
                                            "artist_name": item.get("artistName", artist or ""),
                                            "lyrics": lyrics.strip()
                                        }
                except Exception:
                    continue

        return None
