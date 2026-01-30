import sqlite3
import os
from typing import List, Tuple
from src.utils import get_logger

class VideoDB:
    def __init__(self, db_path: str = "data/videos.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.logger = get_logger("database")
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT,
                    topic TEXT,
                    view_count INTEGER DEFAULT 0,
                    duration_minutes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                cursor.execute("ALTER TABLE videos ADD COLUMN duration_minutes INTEGER DEFAULT 0")
            except Exception:
                pass
            conn.commit()
        self.logger.info("数据库初始化完成")

    def filter_existing_urls(self, urls: List[str]) -> List[str]:
        if not urls:
            return []
        with self._get_conn() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(urls))
            cursor.execute(f"SELECT url FROM videos WHERE url IN ({placeholders})", urls)
            existing = {row[0] for row in cursor.fetchall()}
            self.logger.info(f"数据库已存在URL数量：{len(existing)}")
            return [url for url in urls if url not in existing]

    def save_videos(self, videos: List[Tuple[str, str, str, int, int]]):
        if not videos:
            return
        
        data_to_insert = [(v[1], v[0], v[2], int(v[3]), int(v[4])) for v in videos]
        
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR IGNORE INTO videos (url, title, topic, view_count, duration_minutes) VALUES (?, ?, ?, ?, ?)
            """, data_to_insert)
            conn.commit()
        self.logger.info(f"插入新视频数量：{len(videos)}")
