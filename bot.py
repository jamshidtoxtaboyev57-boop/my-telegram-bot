import asyncio
import logging
import sys
from pathlib import Path

# Windows terminal UTF-8 sozlamasi
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import BOT_TOKEN, TEMP_DIR
from utils.ffmpeg_setup import ensure_ffmpeg
from utils.helpers import cleanup_old_files
from middlewares.subscription import SubscriptionMiddleware

from handlers.common import router as common_router
from handlers.admin import router as admin_router
from handlers.vip import router as vip_router
from handlers.profile import router as profile_router
from handlers.favorites import router as favorites_router
from handlers.top_charts import router as top_charts_router
from handlers.inline_mode import router as inline_mode_router
from handlers.video import router as video_router
from handlers.voice_audio import router as voice_audio_router
from handlers.search import router as search_router

# Log tizimini sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("MusicBot")

async def periodic_cleanup():
    """Har 15 daqiqada eski yuklangan fayllarni avtomatik tozalab turadi"""
    while True:
        try:
            cleanup_old_files(TEMP_DIR, max_age_seconds=1800)
        except Exception as e:
            logger.warning(f"Kesh tozalashda xatolik: {e}")
        await asyncio.sleep(900)

async def main():
    # 1. FFmpeg tekshiruvi
    ffmpeg_path = ensure_ffmpeg()
    if ffmpeg_path:
        logger.info(f"FFmpeg aniqlandi: {ffmpeg_path}")
    else:
        logger.warning("Diqqat: FFmpeg topilmadi. Ba'zi video/audio funksiyalari cheklanishi mumkin.")

    # 2. Token tekshiruvi
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "\n" + "=" * 60 + "\n"
            "XATOLIK: BOT_TOKEN ko'rsatilmagan!\n"
            "1. Telegramda @BotFather ga kiring va /newbot buyrug'i bilan bot oching.\n"
            "2. Olingan tokenni .env faylidagi BOT_TOKEN= qatoriga yozing.\n"
            "=" * 60 + "\n"
        )
        return

    # 3. Bot va Dispatcher yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 4. Majburiy obuna middleware sozlash
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    # 5. Routerlarni tartibli ro'yxatdan o'tkazish
    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(vip_router)
    dp.include_router(profile_router)
    dp.include_router(favorites_router)
    dp.include_router(top_charts_router)
    dp.include_router(inline_mode_router)
    dp.include_router(video_router)
    dp.include_router(voice_audio_router)
    dp.include_router(search_router)

    # 6. Orqa fonda kesh tozalash vazifasini ishga tushirish
    asyncio.create_task(periodic_cleanup())

    # 7. Bot menyu buyruqlarini o'rnatish
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish 🚀"),
        BotCommand(command="top", description="🔥 TOP Hit musiqalar"),
        BotCommand(command="favorites", description="❤️ Mening pleylistim"),
        BotCommand(command="profile", description="👤 Mening profilim"),
        BotCommand(command="vip", description="👑 VIP status sotib olish"),
        BotCommand(command="help", description="📖 Botdan foydalanish yo'riqnomasi"),
        BotCommand(command="id", description="🆔 Telegram ID ni bilish"),
    ])

    # 8. Botni ishga tushirish
    bot_info = await bot.get_me()
    logger.info(f"Bot muvaffaqiyatli ishga tushdi: @{bot_info.username} ({bot_info.first_name})")

    # Eski kutilmagan yangilanishlarni tashlab yuborish
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        # Userbot vaqtincha olib tashlandi chunki u ulanishda qotib qoladi
        await dp.start_polling(bot)
    finally:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
