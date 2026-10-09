from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_search_results_keyboard(
    results: List[Dict[str, Any]],
    current_page: int = 1,
    total_pages: int = 1,
    cache_token: Optional[str] = None
) -> InlineKeyboardMarkup:
    """Qidiruv natijalari uchun sahifalangan va qulay raqamli tugmalar (1..8)"""
    builder = InlineKeyboardBuilder()

    # 1. Musiqa tanlash tugmalari (2 qatorda 5 tadan)
    row = []
    for i, item in enumerate(results, 1):
        idx = (current_page - 1) * 10 + i if total_pages > 1 else i
        btn = InlineKeyboardButton(
            text=f"{idx}",
            callback_data=f"dl:{item['id']}"
        )
        row.append(btn)
        if len(row) == 5:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)

    # 2. Paginatsiya tugmalari (agar bir nechta sahifa bo'lsa)
    if total_pages > 1 and cache_token:
        nav_row = []
        if current_page > 1:
            nav_row.append(
                InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"spg:{cache_token}:{current_page-1}")
            )
        nav_row.append(
            InlineKeyboardButton(text=f"📄 {current_page}/{total_pages}", callback_data="noop")
        )
        if current_page < total_pages:
            nav_row.append(
                InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"spg:{cache_token}:{current_page+1}")
            )
        builder.row(*nav_row)

    # 3. Yopish tugmasi
    builder.row(InlineKeyboardButton(text="❌ Yopish", callback_data="close_search"))
    return builder.as_markup()

def get_audio_action_keyboard(
    song_id: str,
    title: str = "",
    is_favorite: bool = False,
    bot_username: str = ""
) -> InlineKeyboardMarkup:
    """Audio yuborilganda ostidagi interaktiv tugmalar (Sevimlilar, Matni, Do'stlarga ulashish)"""
    builder = InlineKeyboardBuilder()

    fav_btn_text = "💔 Sevimlilardan o'chirish" if is_favorite else "❤️ Sevimlilarga qo'shish"
    fav_cb = f"unfav:{song_id}" if is_favorite else f"fav:{song_id}"

    # 1-qator: Sevimlilar va Qo'shiq matni (Lyrics)
    builder.row(
        InlineKeyboardButton(text=fav_btn_text, callback_data=fav_cb),
        InlineKeyboardButton(text="📜 Qo'shiq matni", callback_data=f"lyr:{song_id}")
    )

    # 2-qator: Do'stlarga ulashish (Inline query)
    share_query = title[:40] if title else ""
    builder.row(
        InlineKeyboardButton(
            text="📤 Do'stlarga ulashish",
            switch_inline_query=share_query
        )
    )

    return builder.as_markup()

def get_favorites_keyboard(
    favorites: List[Dict[str, Any]],
    page: int = 1,
    total_pages: int = 1
) -> InlineKeyboardMarkup:
    """Mening pleylistim (Sevimlilar) uchun boshqaruv tugmalari"""
    builder = InlineKeyboardBuilder()

    # Musiqalarni tinglash tugmalari
    row = []
    for i, item in enumerate(favorites, 1):
        idx = (page - 1) * 5 + i
        btn = InlineKeyboardButton(
            text=f"▶️ {idx}",
            callback_data=f"play_fav:{item['song_id']}"
        )
        row.append(btn)
        if len(row) == 5:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)

    # Sahifalash
    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"fav_pg:{page-1}"))
        nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"fav_pg:{page+1}"))
        builder.row(*nav_row)

    builder.row(
        InlineKeyboardButton(text="❌ Yopish", callback_data="close_search")
    )
    return builder.as_markup()

def get_top_songs_keyboard(songs: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """TOP Hitlar ro'yxati uchun qulay tinglash tugmalari"""
    builder = InlineKeyboardBuilder()
    row = []
    for i, song in enumerate(songs, 1):
        row.append(
            InlineKeyboardButton(text=f"🔥 {i}", callback_data=f"dl:{song['song_id']}")
        )
        if len(row) == 5:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)

    builder.row(
        InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_top"),
        InlineKeyboardButton(text="❌ Yopish", callback_data="close_search")
    )
    return builder.as_markup()

def get_video_options_keyboard(url_key: str) -> InlineKeyboardMarkup:
    """Video havolasi yuborilganda yuklash variantlari"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📹 Videoni yuklash (MP4)", callback_data=f"vid:{url_key}"),
        InlineKeyboardButton(text="🎵 Musiqasini yuklash (MP3)", callback_data=f"aud:{url_key}")
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Videodagi qo'shiqni aniqlash", callback_data=f"shaz_url:{url_key}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="close_search")
    )
    return builder.as_markup()

def get_video_file_options_keyboard(file_id_key: str) -> InlineKeyboardMarkup:
    """Video fayl yuborilganda amallar"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎵 Musiqasini ajratish (MP3)", callback_data=f"ext_mp3:{file_id_key}"),
        InlineKeyboardButton(text="🔍 Shazam orqali aniqlash", callback_data=f"shaz_vid:{file_id_key}")
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Ikkalasini ham bajarish", callback_data=f"ext_both:{file_id_key}")
    )
    return builder.as_markup()

def get_shazam_result_keyboard(query: str, shazam_url: str = "") -> InlineKeyboardMarkup:
    """Shazam topgan musiqa uchun yuklab olish tugmasi"""
    builder = InlineKeyboardBuilder()
    prefix = "dl_shaz:"
    max_text_bytes = 64 - len(prefix.encode("utf-8"))
    safe_bytes = query.encode("utf-8")[:max_text_bytes]
    safe_query = safe_bytes.decode("utf-8", errors="ignore")

    builder.row(
        InlineKeyboardButton(text="📥 Asl MP3 faylini yuklab olish", callback_data=f"{prefix}{safe_query}")
    )
    if shazam_url:
        builder.row(
            InlineKeyboardButton(text="🌐 Shazam-da ko'rish", url=shazam_url)
        )
    return builder.as_markup()

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Admin boshqaruv paneli tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Jonli statistika", callback_data="adm_stats"),
        InlineKeyboardButton(text="📢 Xabar tarqatish", callback_data="adm_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Kanallarni boshqarish", callback_data="adm_channels"),
        InlineKeyboardButton(text="👑 VIP berish", callback_data="adm_vip_help")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Yopish", callback_data="close_search")
    )
    return builder.as_markup()

def get_admin_channels_keyboard(channels: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """Admin uchun kanallar ro'yxati va o'chirish tugmalari"""
    builder = InlineKeyboardBuilder()
    for ch in channels:
        ch_id = ch["channel_id"]
        builder.row(
            InlineKeyboardButton(text=f"📢 {ch.get('title') or ch_id}", url=ch.get("invite_link") or f"https://t.me/{ch_id.lstrip('@')}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"adm_del_ch:{ch_id}")
        )
    builder.row(
        InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="adm_add_ch"),
        InlineKeyboardButton(text="◀️ Ortga", callback_data="adm_back")
    )
    return builder.as_markup()
