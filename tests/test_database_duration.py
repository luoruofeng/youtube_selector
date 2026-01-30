import unittest
import os
import sqlite3
import tempfile
from src.database import VideoDB

class TestDatabaseDuration(unittest.TestCase):
    def test_insert_with_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "videos.db")
            db = VideoDB(db_path=db_path)
            videos = [
                ("Title A", "https://www.youtube.com/watch?v=a", "topicX", 123456, 22),
                ("Title B", "https://www.youtube.com/watch?v=b", "topicX", 55555, 35),
            ]
            db.save_videos(videos)
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT url,title,topic,view_count,duration_minutes FROM videos ORDER BY id ASC")
            rows = cur.fetchall()
            conn.close()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][0], "https://www.youtube.com/watch?v=a")
            self.assertEqual(rows[0][4], 22)
            self.assertEqual(rows[1][0], "https://www.youtube.com/watch?v=b")
            self.assertEqual(rows[1][4], 35)

if __name__ == '__main__':
    unittest.main()
