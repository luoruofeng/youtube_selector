import unittest
import os
import tempfile
from typing import List
from main import process_batch
from src.utils import ensure_csv_bom

class FakeLLM:
    def filter_relevant_titles(self, titles: List[str], topic: str) -> List[str]:
        return titles

class FakeDB:
    def __init__(self):
        self.saved = []
    def filter_existing_urls(self, urls: List[str]) -> List[str]:
        return urls
    def save_videos(self, videos):
        self.saved.extend(videos)

class FakeCrawler:
    def __init__(self, mapping):
        self.mapping = mapping
    def parse_watch_page(self, url: str):
        return self.mapping.get(url, {"view_count": 0, "duration_mins": 0})

class TestQuotaLimit(unittest.TestCase):
    def test_only_save_up_to_remaining_quota(self):
        batch = [
            ("T1", "https://www.youtube.com/watch?v=1"),
            ("T2", "https://www.youtube.com/watch?v=2"),
            ("T3", "https://www.youtube.com/watch?v=3"),
        ]
        mapping = {
            "https://www.youtube.com/watch?v=1": {"view_count": 50000, "duration_mins": 20},
            "https://www.youtube.com/watch?v=2": {"view_count": 50000, "duration_mins": 20},
            "https://www.youtube.com/watch?v=3": {"view_count": 50000, "duration_mins": 20},
        }
        crawler = FakeCrawler(mapping)
        llm = FakeLLM()
        db = FakeDB()
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "out.csv")
            ensure_csv_bom(csv_path)
            saved = process_batch(
                batch=batch,
                topic="x",
                llm=llm,
                db=db,
                csv_path=csv_path,
                crawler=crawler,
                min_times_of_play=1,
                number_of_video=2,
                total_saved_so_far=0,
                lang="en",
                min_video_min=0,
                max_video_max=1000,
            )
            self.assertEqual(saved, 2)
            self.assertEqual(len(db.saved), 2)

if __name__ == '__main__':
    unittest.main()
