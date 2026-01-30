import click
import yaml
import csv
import os
import sys
import time
from src.crawler import YouTubeCrawler
from src.llm import QwenClient
from src.database import VideoDB
from src.utils import get_logger
 
def _bar(prefix, current, total, size=30):
    total = max(total, 1)
    ratio = current / total
    filled = int(size * ratio)
    try:
        full_char = "█"
        empty_char = "░"
        (full_char + empty_char).encode(sys.stdout.encoding or "utf-8")
    except Exception:
        full_char = "#"
        empty_char = "-"
    bar = (full_char * filled) + (empty_char * (size - filled))
    sys.stdout.write(f"\r{prefix} [{bar}] {current}/{total}")
    sys.stdout.flush()

def load_config():
    config_path = "config/settings.yaml"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@click.command()
@click.argument('topic')
@click.option('--lang', default='en', type=click.Choice(['en','cn','jp'], case_sensitive=False), help='Language filter: en/cn/jp')
def find_url(topic, lang):
    logger = get_logger("main")
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"加载配置失败：{e}")
        return

    crawler_cfg = config.get('crawler', {}) or {}
    batch_size = crawler_cfg.get('batch_size', 55)
    visible_cfg = crawler_cfg.get('visible', None)
    if visible_cfg is None:
        headless = bool(crawler_cfg.get('headless', False))
        visible = not headless
    else:
        visible = bool(visible_cfg)
        headless = not visible
    min_wait = config.get('crawler', {}).get('min_wait_seconds', 3.0000)
    max_wait = config.get('crawler', {}).get('max_wait_seconds', 6.0000)
    min_times_of_play = int(config.get('crawler', {}).get('min_times_of_play', 0))
    exclude_shorts = bool(crawler_cfg.get('exclude_shorts', True))
    min_video_min = int(crawler_cfg.get('min_video_min', 0))
    max_video_max = int(crawler_cfg.get('max_video_max', 1000000))
    
    logger.info(f"初始化组件，浏览器可见={visible}，headless={headless}，batch_size={batch_size}，等待区间=({min_wait},{max_wait})")
    try:
        db = VideoDB()
        llm = QwenClient()
        crawler = YouTubeCrawler(headless=headless, min_wait=min_wait, max_wait=max_wait, exclude_shorts=exclude_shorts)
    except Exception as e:
        logger.error(f"组件初始化失败：{e}")
        return
    
    try:
        original_topic = str(topic)
        topic = llm.translate_text(original_topic, "en") or original_topic
        lang = "en"
        logger.info(f"已将主题翻译为英文：{original_topic} -> {topic}")
    except Exception as te:
        logger.warning(f"首次英文翻译失败，使用原始主题：{te}")
        lang = "en"
    
    collected_urls_session = set()
    candidate_buffer = []
    total_saved = 0
    
    now = time.localtime()
    fname = f"{topic}_{now.tm_year}年{now.tm_mon:02d}月{now.tm_mday:02d}日-{now.tm_hour:02d}时{now.tm_min:02d}分.csv"
    output_dir = (config.get('output', {}) or {}).get('csv_dir', "data")
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception:
        pass
    csv_path = os.path.join(output_dir, fname)
    
    number_of_video = int((config.get('output', {}) or {}).get('csv_video_count', 33))
    logger.info(f"开始爬取主题：{topic}，目标数量：{number_of_video}，语言=en")
    
    try:
        crawler.start()
        crawler.search_topic(topic, lang="en")
        
        no_new_data_count = 0
        fallback_attempted = False
        
        while total_saved < number_of_video:
            crawler.scroll_down()
            visible_videos = crawler.extract_videos()
            
            new_found_in_scroll = 0
            from src.utils import detect_language
            for title, url in visible_videos:
                if url not in collected_urls_session:
                    if detect_language(title) == lang.lower():
                        collected_urls_session.add(url)
                        candidate_buffer.append((title, url))
                        new_found_in_scroll += 1
            
            logger.info(f"缓冲区：{len(candidate_buffer)}，已保存：{total_saved}/{number_of_video}，本次新发现：{new_found_in_scroll}")
            
            if new_found_in_scroll == 0:
                no_new_data_count += 1
                if no_new_data_count > 5:
                    if (total_saved == 0) and (not fallback_attempted):
                        try:
                            new_topic = llm.translate_text(topic, lang)
                            if new_topic and new_topic != topic:
                                logger.info(f"搜索不到足够结果，已将关键词翻译为 {new_topic}（目标语言：{lang}），重新搜索")
                                topic = new_topic
                                collected_urls_session.clear()
                                candidate_buffer.clear()
                                crawler.search_topic(topic, lang=lang)
                                no_new_data_count = 0
                                fallback_attempted = True
                                continue
                        except Exception as fe:
                            logger.warning(f"关键词翻译失败：{fe}")
                    logger.warning("连续多次滚动未发现新视频，停止")
                    break
            else:
                no_new_data_count = 0
            
            while len(candidate_buffer) >= batch_size:
                batch = candidate_buffer[:batch_size]
                candidate_buffer = candidate_buffer[batch_size:]
                
                saved_count = process_batch(batch, topic, llm, db, csv_path, crawler, min_times_of_play, number_of_video, total_saved, lang, min_video_min, max_video_max)
                total_saved += saved_count
                logger.info(f"累计保存：{total_saved}/{number_of_video}")
                _bar("总体进度", total_saved, number_of_video)
                
                if total_saved >= number_of_video:
                    sys.stdout.write("\n")
                    break
            
    except KeyboardInterrupt:
        logger.warning("用户中断，停止运行")
    except Exception as e:
        logger.error(f"运行时错误：{e}")
        import traceback
        traceback.print_exc()
    finally:
        crawler.stop()
        logger.info("爬虫已停止")

def process_batch(batch, topic, llm, db, csv_path, crawler, min_times_of_play, number_of_video, total_saved_so_far, lang=None, min_video_min=0, max_video_max=1000000):
    titles = [v[0] for v in batch]
    logger = get_logger("main")
    logger.info(f"发送 {len(titles)} 个标题到 Qwen 进行过滤")
    
    relevant_titles = llm.filter_relevant_titles(titles, topic)
    logger.info(f"Qwen 返回相关标题数量：{len(relevant_titles)}")
    
    if not relevant_titles:
        return 0

    relevant_videos = []
    relevant_titles_set = set(relevant_titles)
    
    from src.utils import detect_language
    for t, u in batch:
        if t in relevant_titles_set:
            if (lang is None) or (detect_language(t) == str(lang).lower()):
                relevant_videos.append((t, u, topic))
    
    if not relevant_videos:
        return 0

    urls_to_check = [v[1] for v in relevant_videos]
    new_unique_urls = set(db.filter_existing_urls(urls_to_check))
    
    filtered_by_url = [v for v in relevant_videos if v[1] in new_unique_urls]
    final_videos_to_save = []
    remaining = max(0, int(number_of_video) - int(total_saved_so_far))
    for idx, (t, u, top) in enumerate(filtered_by_url):
        if remaining <= 0:
            break
        vc = 0
        dm = 0
        try:
            data = crawler.parse_watch_page(u)
            vc = int(data.get("view_count") or 0)
            dm = int(data.get("duration_mins") or 0)
        except Exception:
            vc = 0
            dm = 0
        if (vc > min_times_of_play) and (dm >= min_video_min) and (dm <= max_video_max):
            final_videos_to_save.append((t, u, top, vc, dm))
            if len(final_videos_to_save) >= remaining:
                _bar("播放量/时长检查", idx + 1, idx + 1)
                break
        _bar("播放量/时长检查", idx + 1, len(filtered_by_url))
    sys.stdout.write("\n")
    
    logger.info(f"去重后待保存数量：{len(final_videos_to_save)}")
    
    if remaining > 0 and final_videos_to_save:
        final_videos_to_save = final_videos_to_save[:remaining]
        db.save_videos(final_videos_to_save)
        from src.utils import ensure_csv_bom
        csv_path = ensure_csv_bom(csv_path)
        try:
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        except Exception:
            pass
        file_exists = os.path.exists(csv_path)
        enc = 'utf-8-sig' if not file_exists else 'utf-8'
        with open(csv_path, 'a', newline='', encoding=enc) as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Title", "URL"])
            for v in final_videos_to_save:
                writer.writerow([v[0], v[1]])
        logger.info("已写入 CSV")
                
    return len(final_videos_to_save)

if __name__ == '__main__':
    find_url()
