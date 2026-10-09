import asyncio
import sys

# Pyrogram Python 3.10+ (xususan 3.14) uchun fix:
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import Client
from dotenv import load_dotenv
import os

load_dotenv(override=True)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

async def login():
    print("="*50)
    print("Userbot (Pyrogram) ni sozlash va tizimga kirish")
    print("="*50)
    
    if not API_ID or not API_HASH:
        print("XATOLIK: .env faylida API_ID va API_HASH kiritilmagan!")
        print("Iltimos, my.telegram.org saytidan o'z API_ID va HASH ingizni oling va .env ga qo'shing.")
        return

    print("Iltimos, ishlayotgan botga ulamoqchi bo'lgan Telegram raqamingizni kiriting.")
    print("Masalan: +998901234567\n")
    
    # Eskirgan yoki noto'g'ri sessiya faylini tozalash
    session_file = "core/userbot_session.session"
    if os.path.exists(session_file):
        try:
            os.remove(session_file)
        except Exception:
            pass
            
    # Xatoliklarni oldini olish uchun faqat raqamlarni ajratib olamiz
    clean_api_id = "".join([c for c in str(API_ID) if c.isdigit()])
    clean_api_hash = str(API_HASH).split()[0].strip()
    
    if not clean_api_id:
        print("XATOLIK: API_ID noto'g'ri kiritilgan!")
        return
        
    app = Client("core/userbot_session", api_id=int(clean_api_id), api_hash=clean_api_hash)
    
    await app.start()
    
    print("\n✅ Muvaffaqiyatli tizimga kirdingiz!")
    print("Sizning akkauntingiz endi qidiruvlar uchun ishlatiladi.")
    print("Endi bu oynani yopib, asosiy botni (python bot.py) ishga tushirishingiz mumkin.")
    
    await app.stop()

if __name__ == "__main__":
    asyncio.run(login())
