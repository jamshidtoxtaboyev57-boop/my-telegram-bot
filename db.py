import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from config import BASE_DIR

DB_PATH = BASE_DIR / "bot.db"

class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = str(db_path)
        self.init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=25.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self._get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()

            # 1. Foydalanuvchilar jadvali
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    is_vip INTEGER DEFAULT 0,
                    vip_until TIMESTAMP,
                    downloads_count INTEGER DEFAULT 0,
                    searches_count INTEGER DEFAULT 0,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Mavjud users jadvalida yangi ustunlar bormi-yo'qligini tekshirish (migratsiya)
            user_cols = [r[1] for r in cursor.execute("PRAGMA table_info(users)").fetchall()]
            if "downloads_count" not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN downloads_count INTEGER DEFAULT 0")
            if "searches_count" not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN searches_count INTEGER DEFAULT 0")
            if "last_active" not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN last_active TIMESTAMP")

            # 2. Musiqalar kesh jadvali (Telegram file_id saqlanadi, qayta yuklanmaydi!)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS music_cache (
                    song_id TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    title TEXT,
                    performer TEXT,
                    duration INTEGER,
                    download_count INTEGER DEFAULT 1,
                    cover_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Musiqalar kesh jadvalida yangi ustunlarni tekshirish
            cache_cols = [r[1] for r in cursor.execute("PRAGMA table_info(music_cache)").fetchall()]
            if "download_count" not in cache_cols:
                cursor.execute("ALTER TABLE music_cache ADD COLUMN download_count INTEGER DEFAULT 1")
            if "cover_url" not in cache_cols:
                cursor.execute("ALTER TABLE music_cache ADD COLUMN cover_url TEXT")

            # 3. Sevimlilar jadvali (Mening Pleylistim)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    song_id TEXT NOT NULL,
                    title TEXT,
                    performer TEXT,
                    duration INTEGER,
                    file_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, song_id)
                )
            """)

            # 4. Majburiy obuna kanallari
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id TEXT PRIMARY KEY,
                    title TEXT,
                    invite_link TEXT
                )
            """)

            # 5. To'lovlar va cheklar jadvali
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    tariff_key TEXT NOT NULL,
                    tariff_title TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    days INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    # --- To'lovlar va Cheklar ---
    def create_payment(
        self, user_id: int, tariff_key: str, tariff_title: str, amount: int, days: int, file_id: str, file_type: str = "photo"
    ) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO payments (user_id, tariff_key, tariff_title, amount, days, file_id, file_type, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (user_id, tariff_key, tariff_title, amount, days, file_id, file_type))
            conn.commit()
            return cursor.lastrowid

    def get_payment(self, payment_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_payment_status(self, payment_id: int, status: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment_id))
            conn.commit()
            return cursor.rowcount > 0

    # --- Foydalanuvchilar ---
    def add_or_update_user(self, user_id: int, username: Optional[str], full_name: str):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, last_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    last_active = CURRENT_TIMESTAMP
            """, (user_id, username, full_name))
            conn.commit()

    def record_search(self, user_id: int):
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE users
                SET searches_count = searches_count + 1, last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

    def record_download(self, user_id: int, song_id: Optional[str] = None):
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE users
                SET downloads_count = downloads_count + 1, last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            if song_id:
                conn.execute("""
                    UPDATE music_cache
                    SET download_count = download_count + 1
                    WHERE song_id = ?
                """, (song_id,))
            conn.commit()

    def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["favorites_count"] = self.get_favorites_count(user_id)
            return data

    def get_all_user_ids(self) -> List[int]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            return [r[0] for r in cursor.fetchall()]

    def is_vip(self, user_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_vip, vip_until FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return False
            is_vip = bool(row["is_vip"])
            vip_until = row["vip_until"]
            if not is_vip:
                return False
            if vip_until:
                try:
                    expiry = datetime.fromisoformat(vip_until)
                    if datetime.now() > expiry:
                        # VIP muddati tugagan
                        cursor.execute("UPDATE users SET is_vip = 0 WHERE user_id = ?", (user_id,))
                        conn.commit()
                        return False
                except Exception:
                    pass
            return True

    def set_vip(self, user_id: int, days: int) -> datetime:
        expiry = datetime.now() + timedelta(days=days)
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET is_vip = 1, vip_until = ?
                WHERE user_id = ?
            """, (expiry.isoformat(), user_id))
            conn.commit()
        return expiry

    def remove_vip(self, user_id: int):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_vip = 0, vip_until = NULL WHERE user_id = ?", (user_id,))
            conn.commit()

    def get_detailed_stats(self) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
            vip_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')")
            today_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM music_cache")
            cached_songs = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(SUM(downloads_count), 0) FROM users")
            total_downloads = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(SUM(searches_count), 0) FROM users")
            total_searches = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM favorites")
            total_favorites = cursor.fetchone()[0]

            return {
                "total_users": total_users,
                "today_users": today_users,
                "vip_users": vip_users,
                "cached_songs": cached_songs,
                "total_downloads": total_downloads,
                "total_searches": total_searches,
                "total_favorites": total_favorites,
            }

    # Eski get_user_stats bilan moslik
    def get_user_stats(self) -> Dict[str, int]:
        stats = self.get_detailed_stats()
        return {
            "total_users": stats["total_users"],
            "vip_users": stats["vip_users"],
            "cached_songs": stats["cached_songs"],
        }

    # --- Musiqa Keshi (Turbo tezlik uchun) ---
    def get_cached_music(self, song_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM music_cache WHERE song_id = ?", (song_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def search_cached_music_by_title(self, query: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            search_query = f"%{query}%"
            cursor.execute("""
                SELECT * FROM music_cache 
                WHERE title LIKE ? OR performer LIKE ?
                ORDER BY download_count DESC
                LIMIT 1
            """, (search_query, search_query))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def cache_music(
        self, song_id: str, file_id: str, title: str, performer: str, duration: int, cover_url: Optional[str] = None
    ):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO music_cache (song_id, file_id, title, performer, duration, cover_url)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(song_id) DO UPDATE SET
                    file_id = excluded.file_id,
                    title = excluded.title,
                    performer = excluded.performer,
                    duration = excluded.duration,
                    cover_url = COALESCE(excluded.cover_url, music_cache.cover_url),
                    download_count = music_cache.download_count + 1
            """, (song_id, file_id, title, performer, duration, cover_url))
            conn.commit()

    def get_top_songs(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT song_id, title, performer, duration, file_id, download_count
                FROM music_cache
                ORDER BY download_count DESC, created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    # --- Sevimlilar (Mening Pleylistim) ---
    def add_favorite(
        self, user_id: int, song_id: str, title: str, performer: str, duration: int, file_id: Optional[str] = None
    ) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO favorites (user_id, song_id, title, performer, duration, file_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, song_id, title, performer, duration, file_id))
                conn.commit()
                return True
            except Exception:
                return False

    def remove_favorite(self, user_id: int, song_id: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM favorites WHERE user_id = ? AND song_id = ?", (user_id, song_id))
            conn.commit()
            return cursor.rowcount > 0

    def is_favorite(self, user_id: int, song_id: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM favorites WHERE user_id = ? AND song_id = ?", (user_id, song_id))
            return cursor.fetchone() is not None

    def get_user_favorites(self, user_id: int, limit: int = 5, offset: int = 0) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, song_id, title, performer, duration, file_id, created_at
                FROM favorites
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset))
            return [dict(r) for r in cursor.fetchall()]

    def get_favorites_count(self, user_id: int) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM favorites WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

    # --- Kanallar ---
    def get_channels(self) -> List[Dict[str, str]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM channels")
            return [dict(r) for r in cursor.fetchall()]

    def add_channel(self, channel_id: str, title: str, invite_link: str):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO channels (channel_id, title, invite_link)
                VALUES (?, ?, ?)
            """, (channel_id, title, invite_link))
            conn.commit()

    def delete_channel(self, channel_id: str):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
            conn.commit()

db = Database()

