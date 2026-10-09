import os
from pathlib import Path
from dotenv import load_dotenv

# .env faylni yuklash
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Bot tokeni
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Adminlar Telegram ID lari (vergul bilan ajratilgan, masalan: 1234567,9876543)
ADMIN_IDS = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
]
if not ADMIN_IDS:
    ADMIN_IDS = [6962408184]


# Majburiy a'zo bo'linishi kerak bo'lgan kanallar (@kanal_username yoki kanal ID)
# Masalan: REQUIRED_CHANNELS=@musictop,@music_hit
REQUIRED_CHANNELS = [
    ch.strip() for ch in os.getenv("REQUIRED_CHANNELS", "").split(",") if ch.strip()
]

# Maksimal yuklash hajmi (Telegram botlar uchun 50 MB)
MAX_DOWNLOAD_SIZE_MB = int(os.getenv("MAX_DOWNLOAD_SIZE_MB", "50"))
MAX_DOWNLOAD_SIZE_BYTES = MAX_DOWNLOAD_SIZE_MB * 1024 * 1024

# Vaqtinchalik fayllar katalogi
TEMP_DIR = BASE_DIR / os.getenv("TEMP_DIR", "downloads")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Bin katalogi (ffmpeg.exe uchun)
BIN_DIR = BASE_DIR / "bin"
BIN_DIR.mkdir(parents=True, exist_ok=True)

# VIP Narxlari (so'mda)
VIP_PRICES = {
    "1_month": {"title": "1 oylik VIP", "price": 15000, "days": 30},
    "3_month": {"title": "3 oylik VIP", "price": 35000, "days": 90},
    "1_year": {"title": "1 yillik VIP (Cheksiz)", "price": 80000, "days": 365},
}

# Admin kontakt yoki to'lov uchun aloqa username
ADMIN_CONTACT = os.getenv("ADMIN_CONTACT", "@Jamshid_2731")

# To'lov karta ma'lumotlari
CARD_NUMBER = os.getenv("CARD_NUMBER", "9860606756800524")
CARD_HOLDER = os.getenv("CARD_HOLDER", "Toxtaboyev.J")

