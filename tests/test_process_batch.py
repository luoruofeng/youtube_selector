import unittest
import os
import tempfile
from typing import List
from src.utils import ensure_csv_bom
from main import process_batch

class FakeLLM:
    def filter_relevant_titles(self, titles: List[str], topic: str) -> List[str]:
        return [t for t in titles if "good" in t.lower()]

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

class TestProcessBatch(unittest.TestCase):
    def test_filter_by_view_and_duration(self):
        batch = [
            ("A good title 1", "https://www.youtube.com/watch?v=a"),
            ("Bad title", "https://www.youtube.com/watch?v=b"),
            ("A good title 2", "https://www.youtube.com/watch?v=c"),
        ]
        mapping = {
            "https://www.youtube.com/watch?v=a": {"view_count": 50000, "duration_mins": 20},
            "https://www.youtube.com/watch?v=b": {"view_count": 200000, "duration_mins": 10},
            "https://www.youtube.com/watch?v=c": {"view_count": 5000, "duration_mins": 30},
        }
        crawler = FakeCrawler(mapping)
        llm = FakeLLM()
        db = FakeDB()
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "out.csv")
            ensure_csv_bom(csv_path)
            saved = process_batch(
                batch=batch,
                topic="finance",
                llm=llm,
                db=db,
                csv_path=csv_path,
                crawler=crawler,
                min_times_of_play=10000,
                number_of_video=10,
                total_saved_so_far=0,
                lang="en",
                min_video_min=15,
                max_video_max=120,
            )
            self.assertEqual(saved, 1)
            self.assertEqual(len(db.saved), 1)
            self.assertEqual(db.saved[0][1], "https://www.youtube.com/watch?v=a")

if __name__ == '__main__':
    unittest.main()
