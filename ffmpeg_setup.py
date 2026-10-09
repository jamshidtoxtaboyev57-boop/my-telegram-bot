import os
import sys
import shutil
import zipfile
import urllib.request
from pathlib import Path
from typing import Optional
from config import BIN_DIR

# Windows uchun ffmpeg build havolasi (yt-dlp rasmiy yoki essentials build)
FFMPEG_WIN_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

def setup_pydub_converter(ffmpeg_path: str):
    """Pydub uchun ffmpeg manzilini o'rnatish"""
    try:
        from pydub import AudioSegment
        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffmpeg = ffmpeg_path
    except Exception:
        pass

def get_ffmpeg_path() -> Optional[str]:
    """Tizimda yoki loyiha bin papkasida ffmpeg borligini aniqlaydi"""
    # 1. bin papkasida tekshirish
    local_ffmpeg = BIN_DIR / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    if local_ffmpeg.is_file():
        path_str = str(local_ffmpeg)
        if str(BIN_DIR) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{str(BIN_DIR)}{os.pathsep}{os.environ.get('PATH', '')}"
        setup_pydub_converter(path_str)
        return path_str

    # 2. Windows uchun keng tarqalgan manzillar
    if sys.platform == "win32":
        possible_paths = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Links/ffmpeg.exe",
            Path("C:/ffmpeg/bin/ffmpeg.exe"),
            Path(os.environ.get("PROGRAMDATA", "")) / "chocolatey/bin/ffmpeg.exe",
            Path(os.environ.get("USERPROFILE", "")) / "scoop/shims/ffmpeg.exe",
        ]
        for p in possible_paths:
            if p.is_file():
                path_str = str(p)
                if str(p.parent) not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = f"{str(p.parent)}{os.pathsep}{os.environ.get('PATH', '')}"
                setup_pydub_converter(path_str)
                return path_str

    # 3. Tizim PATH da tekshirish
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        setup_pydub_converter(sys_ffmpeg)
        return sys_ffmpeg

    return None

def download_and_extract_ffmpeg(progress_callback=None) -> Optional[str]:
    """Windows uchun ffmpeg-ni avtomatik yuklab olib bin papkasiga joylaydi"""
    if sys.platform != "win32":
        return None

    zip_path = BIN_DIR / "ffmpeg.zip"
    try:
        print("[FFMPEG] ffmpeg yuklab olinmoqda (bir martalik amal)...")
        if progress_callback:
            progress_callback("ffmpeg yuklab olinmoqda...")

        def _reporthook(block_num, block_size, total_size):
            if total_size > 0 and progress_callback and block_num % 100 == 0:
                percent = int(block_num * block_size * 100 / total_size)
                progress_callback(f"ffmpeg yuklanmoqda: {percent}%")

        # Yuklab olish
        import ssl
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl._create_unverified_context()

        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        opener.addheaders = [("User-Agent", "Mozilla/5.0")]
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(FFMPEG_WIN_URL, zip_path, reporthook=_reporthook)

        # Zipdan ffmpeg.exe va ffprobe.exe ni chiqarish
        print("[FFMPEG] Arxivdan chiqarilmoqda...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                filename = Path(member).name
                if filename in ("ffmpeg.exe", "ffprobe.exe"):
                    source = zf.open(member)
                    target = open(BIN_DIR / filename, "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)

        if zip_path.exists():
            zip_path.unlink()

        return get_ffmpeg_path()
    except Exception as e:
        print(f"[FFMPEG] Avtomatik yuklab olishda xatolik: {e}")
        if zip_path.exists():
            zip_path.unlink()
        return None

def ensure_ffmpeg() -> Optional[str]:
    """FFmpeg mavjudligini kafolatlaydi, agar yo'q bo'lsa get_ffmpeg_path yoki download qiladi"""
    path = get_ffmpeg_path()
    if path:
        return path
    return download_and_extract_ffmpeg()
