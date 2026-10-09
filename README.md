# 🎧 Premium Musiqa Izlovchi va Video Yuklovchi Telegram Bot (Top-Tier)

Ushbu Telegram bot musiqa ixlosmandlari uchun yaratilgan to'liq funksional, yuqori sifatli, zamonaviy va oddiy botlardan ajralib turuvchi professional botdir.

---

## 🌟 Oddiy Botlardan Ajralib Turuvchi Premium Imkoniyatlar

1. 🔍 **Aqlli va Sahifalangan Qidiruv (Pagination):**
   - Qo'shiq yoki ijrochi nomini yozing (masalan: `Xcho Vorona`, `Konsta`, `Billie Eilish`).
   - Bot natijalarni qulay sahifalarga (8 tadan) ajratadi: `◀️ Oldingi`, `Keyingi ▶️`.
   - Har bir musiqa sifati, davomiyligi va toza nomi bilan taqdim etiladi.

2. 🚀 **Telegram Inline Mode (Har qanday chatda qidirish):**
   - Istalgan shaxsiy chat, guruh yoki kanalda shunchaki `@bot_nomi qo'shiq` deb yozing.
   - Natijalar jonli chiqadi va bir zumda guruhdoshlar yoki do'stlarga yuborish mumkin!
   - Keshdagi va TOP musiqalar to'g'ridan-to'g'ri audio sifatida ulanadi.

3. 🎙 **Ovozli xabar (Voice) orqali musiqa topish (Shazam):**
   - Atrofda yangrayotgan qo'shiqni 5-10 soniya ovozli xabar (voice) qilib yuboring.
   - Bot Shazam algoritmi orqali soniyalar ichida qo'shiq nomi, ijrochi, albom, cover rasmini aniqlaydi va avtomatik ravishda asl studiya audio trekini yuboradi.

4. 🎬 **Videolardan audio ajratish va fon musiqasini aniqlash:**
   - Botga to'g'ridan-to'g'ri ixtiyoriy video yoki dumaloq video xabar (video note) yuboring.
   - Videodagi audioni yuqori sifatda ajratadi hamda Shazam orqali fon musiqasini aniqlab beradi.

5. 🔗 **Ijtimoiy tarmoqlardan video va MP3 yuklash:**
   - YouTube, TikTok, Instagram va boshqa platformalardan havola yuboring.
   - MP4 video yoki MP3 audio holida yuklab olish variantlari.

6. 📜 **Qo'shiq Matnlari (Lyrics):**
   - Har bir qo'shiq ostida **«📜 Qo'shiq matni»** tugmasi mavjud.
   - Bosganda, qo'shiqning to'liq matnini topib beradi.

7. ❤️ **Mening Pleylistim (Sevimlilar tizimi):**
   - Istalgan trek ostida **«❤️ Sevimlilarga qo'shish»** tugmasi bor.
   - Foydalanuvchi o'zining shaxsiy pleylistini yig'ib boradi va istagan paytda eshita oladi.

8. 🔥 **TOP Hitlar (Trendlar):**
   - Bot foydalanuvchilari orasida eng ko'p yuklangan va tinglangan TOP-10 musiqalar reytingi.

9. 👤 **Foydalanuvchi Shaxsiy Profili:**
   - Foydalanuvchining ID raqami, jami qidiruvlari, yuklab olgan musiqalari, pleylistidagi qo'shiqlar soni va VIP holati (qolgan kun va soatlar bilan).

10. 🏷 **ID3 Teglar va Cover Art (Muqova rasmi):**
    - Yuklangan barcha MP3 fayllarga `mutagen` orqali ijrochi, qo'shiq nomi va sifatli albom muqovasi (Cover Art) kiritiladi. Pleyerda va mashina monitorida rasmiy trekdek ko'rinadi!

11. 👑 **VIP Status va Monetizatsiya:**
    - Majburiy obunasiz, cheklovlarsiz va turbo tezlikda foydalanish.

12. 🛠 **To'liq Admin Paneli (`/admin`):**
    - 📊 Jonli statistika (Bugungi yangilar, jami foydalanuvchilar, yuklashlar)
    - 📢 Barcha foydalanuvchilarga xabar tarqatish (Broadcast)
    - 📢 Majburiy obuna kanallarini qo'shish va o'chirish
    - 👑 VIP berish va boshqarish

---

## 📁 Loyiha Strukturasi

```
bot/
├── core/
│   ├── shazam/             # Pure Python Shazam audio signature algoritmi
│   ├── audio_detector.py   # Shazam audio tahlil qiluvchi modul
│   ├── lyrics.py           # Qo'shiq matnlari (Lyrics) xizmati
│   ├── media_converter.py  # FFmpeg audio va video konvertatsiya
│   ├── music_search.py     # yt-dlp qidiruv va turbo yuklovchi
│   └── video_downloader.py # Ijtimoiy tarmoqlar yuklovchisi
├── handlers/
│   ├── admin.py            # To'liq admin paneli va statistika
│   ├── common.py           # /start, /help, navigatsiya va bosh menyu
│   ├── favorites.py        # Mening pleylistim (Sevimlilar)
│   ├── inline_mode.py      # Telegram Inline rejim (@bot so'rov)
│   ├── profile.py          # Shaxsiy profil va foydalanuvchi kabineti
│   ├── search.py           # Qidiruv, paginatsiya, yuklash va lyrics
│   ├── top_charts.py       # TOP-10 Trend musiqalar
│   ├── video.py            # Video fayllar va havolalar
│   ├── vip.py              # VIP tariflar va obuna tekshiruvi
│   └── voice_audio.py      # Ovozli xabar va audio (Shazam)
├── keyboards/
│   ├── inline.py           # Barcha zamonaviy inline tugmalar
│   └── reply.py            # Asosiy qulay reply bosh menyu
├── middlewares/
│   └── subscription.py     # Majburiy obuna va filtr middleware
├── utils/
│   ├── ffmpeg_setup.py     # FFmpeg avtomatik aniqlash va sozlash
│   ├── helpers.py          # Yordamchi funksiyalar va kesh tozalash
│   └── tagger.py           # MP3 ID3 teglar va muqova kiritish
├── bot.py                  # Botni ishga tushiruvchi markaziy fayl
├── config.py               # Sozlamalar va muhit o'zgaruvchilari
├── requirements.txt        # Kerakli Python kutubxonalari
├── bot.db                  # SQLite ma'lumotlar bazasi
└── .env                    # Bot tokeni va sozlamalar
```

---

## 🚀 Ishga Tushirish

1. **Tokenni `.env` faylida ko'rsating:**
   ```env
   BOT_TOKEN=123456789:ABC...
   ADMIN_IDS=Sizning_Telegram_ID
   ADMIN_CONTACT=@Jamshid_2731
   CARD_NUMBER=9860606756800524
   CARD_HOLDER=Toxtaboyev.J
   ```

2. **Botni ishga tushiring:**
   ```bash
   python bot.py
   ```
