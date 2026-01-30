from playwright.sync_api import sync_playwright
import time
import random
import urllib.parse
from typing import List, Dict, Tuple
from src.utils import get_logger, parse_view_count, parse_duration_to_minutes

class YouTubeCrawler:
    def __init__(self, headless: bool = True, min_wait: float = 3.0, max_wait: float = 6.0, exclude_shorts: bool = True):
        self.headless = headless
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.playwright = None
        self.browser = None
        self.page = None
        self.exclude_shorts = exclude_shorts
        self.logger = get_logger("crawler")
    
    def _random_wait(self):
        secs = round(random.uniform(self.min_wait, self.max_wait), 4)
        self.logger.debug(f"随机等待 {secs} 秒")
        time.sleep(secs)

    def start(self):
        if not self.playwright:
            self.playwright = sync_playwright().start()
            self.logger.info("Playwright 启动")
        if not self.browser:
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.logger.info(f"Chromium 启动，headless={self.headless}")
        if not self.page:
            self.page = self.browser.new_page()
            self.logger.info("新页面已创建")

    def stop(self):
        if self.page:
            self.page.close()
            self.page = None
            self.logger.info("页面已关闭")
        if self.browser:
            self.browser.close()
            self.browser = None
            self.logger.info("浏览器已关闭")
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
            self.logger.info("Playwright 已停止")

    def search_topic(self, topic: str, lang: str = "en"):
        if not self.page:
            self.start()
        
        self.logger.info("访问 YouTube 搜索页")
        self._random_wait()
        # 通过在查询中加入语言提示词来影响结果语言
        lang_hint = ""
        if lang == "en":
            lang_hint = " in English"
        elif lang == "cn":
            lang_hint = " 中文"
        elif lang == "jp":
            lang_hint = " 日本語"
        q = urllib.parse.quote(topic + lang_hint)
        self.page.goto(f"https://www.youtube.com/results?search_query={q}")
        self.logger.info(f"搜索主题：{topic}")
        try:
            self.page.wait_for_selector("ytd-video-renderer", timeout=15000)
            self.logger.info("搜索结果加载完成")
        except Exception:
            self.logger.warning("等待搜索结果超时")
        if self.exclude_shorts:
            try:
                chips = self.page.locator("yt-chip-cloud-chip-renderer").all()
                target = None
                for ch in chips:
                    txt = ch.inner_text().strip().lower()
                    if txt in ["videos", "视频", "影片", "視頻", "動画"]:
                        target = ch
                        break
                if target:
                    target.click()
                    self.logger.info("已应用“视频”过滤")
                    self.page.wait_for_selector("ytd-video-renderer", timeout=10000)
            except Exception:
                pass

    def scroll_down(self):
        self._random_wait()
        self.page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        self._random_wait()
        self.logger.debug("页面滚动到底部并等待")

    def extract_videos(self) -> List[Tuple[str, str]]:
        videos = []
        elements = self.page.locator("ytd-video-renderer").all()
        self.logger.debug(f"检测到结果元素数量：{len(elements)}")
        
        for el in elements:
            try:
                title_el = el.locator("#video-title")
                if not title_el.is_visible():
                    continue
                    
                title = title_el.inner_text().strip()
                href = title_el.get_attribute("href")
                if href and href.startswith("/watch"):
                    full_url = f"https://www.youtube.com{href}"
                    videos.append((title, full_url))
            except Exception:
                continue
        self.logger.info(f"提取到视频数量：{len(videos)}")
        return videos

    def parse_watch_page(self, url: str) -> Dict:
        if not self.page:
            self.start()
            
        self.logger.info(f"访问播放页：{url}")
        self._random_wait()
        self.page.goto(url)
        title = "Unknown"
        try:
            self.page.wait_for_selector("h1.ytd-watch-metadata", timeout=10000)
            title = self.page.locator("h1.ytd-watch-metadata").first.inner_text().strip()
            self.logger.info(f"当前视频标题：{title}")
        except Exception:
            try:
                title = self.page.title().replace(" - YouTube", "")
                self.logger.info(f"使用页面标题作为视频标题：{title}")
            except:
                pass

        view_count = 0
        try:
            self.page.wait_for_selector('xpath=//*[@id="info"]/span[1]', timeout=8000)
            txt = self.page.locator('xpath=//*[@id="info"]/span[1]').first.inner_text().strip()
            view_count = parse_view_count(txt)
        except Exception:
            try:
                el = self.page.locator('xpath=//ytd-watch-metadata//*[@id="info"]//span[1]').first
                txt = el.inner_text().strip()
                view_count = parse_view_count(txt)
            except Exception:
                try:
                    el = self.page.locator('xpath=//span[contains(text(),"views") or contains(text(),"次观看")]').first
                    txt = el.inner_text().strip()
                    view_count = parse_view_count(txt)
                except Exception:
                    view_count = 0
        
        duration_mins = 0
        try:
            self.page.wait_for_selector('#movie_player .ytp-time-duration', timeout=8000)
            dtxt = self.page.locator('#movie_player .ytp-time-duration').first.inner_text().strip()
            duration_mins = parse_duration_to_minutes(dtxt)
        except Exception:
            try:
                el = self.page.locator('xpath=//*[@id="movie_player"]/div[32]/div[2]/div[1]/div[1]/div/div/span[4]').first
                dtxt = el.inner_text().strip()
                duration_mins = parse_duration_to_minutes(dtxt)
            except Exception:
                try:
                    el = self.page.locator('xpath=//*[@id="movie_player"]//span[contains(@class,"ytp-time-duration")]').first
                    dtxt = el.inner_text().strip()
                    duration_mins = parse_duration_to_minutes(dtxt)
                except Exception:
                    duration_mins = 0

        recommendations = []
        self._random_wait()
        recs = self.page.locator("ytd-compact-video-renderer").all()
        self.logger.debug(f"推荐视频元素数量：{len(recs)}")
        for rec in recs:
            try:
                t_el = rec.locator("#video-title")
                t = t_el.inner_text().strip()
                link = rec.locator("a").first
                h = link.get_attribute("href")
                if h and h.startswith("/watch"):
                    full_h = f"https://www.youtube.com{h}"
                    recommendations.append({"title": t, "url": full_h})
            except Exception:
                continue
        self.logger.info(f"解析推荐视频数量：{len(recommendations)}")
        
        return {
            "title": title,
            "recommendations": recommendations,
            "view_count": view_count,
            "duration_mins": duration_mins
        }

    def get_view_count(self, url: str) -> int:
        data = self.parse_watch_page(url)
        return int(data.get("view_count") or 0)

    def get_duration_minutes(self, url: str) -> int:
        data = self.parse_watch_page(url)
        return int(data.get("duration_mins") or 0)
