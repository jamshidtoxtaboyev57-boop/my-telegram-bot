import asyncio
import os
import sys
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import Client
from pyrogram.types import Message
from dotenv import load_dotenv

load_dotenv(override=True)

# Standard Telegram API ID and HASH
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
TARGET_BOT = "@TaronaBot"

class UserbotBridge:
    def __init__(self):
        clean_api_id = "".join([c for c in str(API_ID) if c.isdigit()])
        clean_api_hash = str(API_HASH).split()[0].strip()
        
        if not clean_api_id or not clean_api_hash:
            self.app = None
            self.is_running = False
            return
            
        self.app = Client(
            "userbot_session", 
            api_id=int(clean_api_id), 
            api_hash=clean_api_hash, 
            workdir=os.path.dirname(os.path.abspath(__file__))
        )
        self.is_running = False

    async def start(self):
        if not self.app:
            print("[Userbot] API_ID yoki API_HASH kiritilmagan. Userbot o'chirilgan.")
            return
            
        try:
            await self.app.start()
            self.is_running = True
            print("[Userbot] Muvaffaqiyatli ishga tushdi va TaronaBot orqali ishlashga tayyor!")
        except Exception as e:
            print(f"[Userbot] Ishga tushishda xatolik yuz berdi. Iltimos oldin `python login.py` orqali tizimga kiring. Xato: {e}")

    async def stop(self):
        if self.is_running:
            await self.app.stop()
            self.is_running = False

    async def fetch_and_forward(self, query: str, bot_username: str, original_user_id: int, timeout: int = 15) -> bool:
        """
        TaronaBot ga so'rov yuborib, topilgan audioni asosiy botga yuboradi.
        Asosiy bot uni ushlab olib egasiga jo'natishi kerak.
        """
        if not self.is_running:
            return False

        try:
            # 1. TaronaBot ga so'rov yuborish
            sent_msg = await self.app.send_message(TARGET_BOT, query)
            
            # 2. Javobni kutish
            start_time = asyncio.get_event_loop().time()
            audio_msg = None
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                await asyncio.sleep(0.5)
                async for msg in self.app.get_chat_history(TARGET_BOT, limit=3):
                    if msg.audio and msg.id > sent_msg.id:
                        audio_msg = msg
                        break
                    
                    if msg.reply_markup and getattr(msg.reply_markup, "inline_keyboard", None) and msg.id > sent_msg.id:
                        try:
                            await msg.click(0)
                            await asyncio.sleep(1.5)
                        except Exception:
                            pass
                if audio_msg:
                    break

            if audio_msg:
                # 3. Asosiy botga audio va ma'lumotni yuborish
                await audio_msg.forward(bot_username)
                await self.app.send_message(
                    bot_username, 
                    f"USERBOT_RESULT:{original_user_id}:{query}"
                )
                return True
        except Exception as e:
            print(f"[Userbot Fetch Error]: {e}")
        return False

userbot = UserbotBridge()
