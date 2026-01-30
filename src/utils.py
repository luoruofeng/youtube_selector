import logging
import os
import yaml
import io
import re

_logger_cache = {}

def get_logger(name: str):
    if name in _logger_cache:
        return _logger_cache[name]
    logger = logging.getLogger(name)
    if not logger.handlers:
        try:
            with open("config/settings.yaml", "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception:
            cfg = {}
        level_str = str(cfg.get("logging", {}).get("level", "INFO")).upper()
        level = getattr(logging, level_str, logging.INFO)
        logger.setLevel(level)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
        if cfg.get("logging", {}).get("file_enabled", True):
            path = cfg.get("logging", {}).get("file_path", "data/app.log")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            fh = logging.FileHandler(path, encoding="utf-8")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
    _logger_cache[name] = logger
    return logger

def parse_view_count(text: str) -> int:
    s = str(text).strip().lower()
    s = s.replace(",", "").replace("次观看", "").replace("views", "").strip()
    if not s:
        return 0
    if "亿" in text or "萬億" in s:
        try:
            n = float(re.findall(r"[\d\.]+", text)[0])
            return int(n * 100000000)
        except:
            return 0
    if "万" in text:
        try:
            n = float(re.findall(r"[\d\.]+", text)[0])
            return int(n * 10000)
        except:
            return 0
    if s.endswith("k") or "k" in s:
        try:
            n = float(re.findall(r"[\d\.]+", s)[0])
            return int(n * 1000)
        except:
            return 0
    if s.endswith("m") or "m" in s:
        try:
            n = float(re.findall(r"[\d\.]+", s)[0])
            return int(n * 1000000)
        except:
            return 0
    if s.endswith("b") or "b" in s:
        try:
            n = float(re.findall(r"[\d\.]+", s)[0])
            return int(n * 1000000000)
        except:
            return 0
    try:
        return int(re.findall(r"\d+", s)[0])
    except:
        return 0

def ensure_csv_bom(path: str):
    logger = get_logger("utils")
    if not os.path.exists(path):
        return path
    try:
        with open(path, "rb") as f:
            head = f.read(3)
        if head == b"\xef\xbb\xbf":
            return path
        with open(path, "r", encoding="utf-8") as src:
            content = src.read()
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8-sig", newline="") as dst:
            dst.write(content)
        os.replace(tmp_path, path)
        logger.info(f"已转换为带BOM：{path}")
        return path
    except PermissionError:
        base, ext = os.path.splitext(path)
        new_path = base + "_bom" + ext
        with open(path, "r", encoding="utf-8") as src:
            content = src.read()
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        with open(new_path, "w", encoding="utf-8-sig", newline="") as dst:
            dst.write(content)
        logger.warning(f"无法覆盖原文件，已写入新的BOM文件：{new_path}")
        return new_path

def detect_language(text: str) -> str:
    s = str(text)
    has_cn = re.search(r"[\u4e00-\u9fff]", s) is not None
    has_hira = re.search(r"[\u3040-\u309f]", s) is not None
    has_kata = re.search(r"[\u30a0-\u30ff]", s) is not None or re.search(r"[\uff66-\uff9f]", s) is not None
    has_jp = has_hira or has_kata
    if has_jp:
        return "jp"
    if has_cn:
        return "cn"
    return "en"

def parse_duration_to_minutes(text: str) -> int:
    s = str(text).strip()
    s = s.replace("：", ":").replace(" ", "")
    if not s:
        return 0
    s2 = re.sub(r"[^0-9:]", "", s)
    if not s2:
        return 0
    if ":" in s2:
        parts = s2.split(":")
        try:
            if len(parts) == 3:
                h = int(parts[0] or 0)
                m = int(parts[1] or 0)
                return h * 60 + m
            if len(parts) == 2:
                m = int(parts[0] or 0)
                return m
        except:
            return 0
    try:
        return int(re.findall(r"\d+", s2)[0])
    except:
        return 0
