from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Foydalanuvchi uchun asosiy qulay bosh menyu tugmalari"""
    keyboard = [
        [
            KeyboardButton(
                text="🔍 Zamonaviy Qidiruv (Yangi)", 
                web_app={"url": "https://nasty-towns-roll.loca.lt"}
            )
        ],
        [
            KeyboardButton(text="🔍 Musiqa izlash"),
            KeyboardButton(text="🔥 TOP Hitlar"),
        ],
        [
            KeyboardButton(text="❤️ Sevimlilarim"),
            KeyboardButton(text="👤 Mening profilim"),
        ],
        [
            KeyboardButton(text="👑 VIP Status"),
            KeyboardButton(text="📖 Yo'riqnoma"),
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Qo'shiq nomi, ijrochi yoki havola yuboring..."
    )
