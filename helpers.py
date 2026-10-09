import os
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

def sanitize_filename(name: str, max_length: int = 80) -> str:
    """Fayl nomi uchun xavfsiz matn hosil qiladi"""
    # Windows/Linux uchun nojo'iz belgilarni olib tashlash
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > max_length:
        name = name[:max_length].rstrip()
    return name or "unnamed"

def format_duration(seconds: Optional[float | int]) -> str:
    """Soniyani MM:SS yoki HH:MM:SS formatiga o'tkazadi"""
    if not seconds or seconds < 0:
        return "00:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def format_bytes(size_bytes: Optional[int | float]) -> str:
    """Fayl hajmini odam o'qiy oladigan formatga (MB, KB) o'tkazadi"""
    if not size_bytes or size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    index = 0
    size = float(size_bytes)
    while size >= 1024.0 and index < len(units) - 1:
        size /= 1024.0
        index += 1
    return f"{size:.1f} {units[index]}"

def is_url(text: str) -> bool:
    """Matn veb-havola ekanligini tekshiradi"""
    if not text:
        return False
    text = text.strip()
    try:
        parsed = urlparse(text)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def extract_first_url(text: str) -> Optional[str]:
    """Matn ichidan birinchi URL manzilini ajratib oladi"""
    if not text:
        return None
    match = re.search(r"https?://[^\s]+", text)
    if match:
        url = match.group(0).rstrip(".,!?)\"'>")
        return url
    return None

def safe_remove(path: Optional[str | Path]) -> None:
    """Faylni xavfsiz o'chiradi"""
    if not path:
        return
    try:
        p = Path(path)
        if p.exists() and p.is_file():
            p.unlink(missing_ok=True)
    except Exception as e:
        print(f"Faylni o'chirishda xatolik ({path}): {e}")

def cleanup_old_files(directory: Path, max_age_seconds: int = 1800) -> None:
    """Belgilangan vaqtdan eski fayllarni tozalaydi"""
    now = time.time()
    try:
        if not directory.exists():
            return
        for file in directory.iterdir():
            if file.is_file():
                try:
                    if now - file.stat().st_mtime > max_age_seconds:
                        file.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception as e:
        print(f"Katalogni tozalashda xatolik: {e}")
