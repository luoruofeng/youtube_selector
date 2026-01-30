import subprocess
import os
import sys

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py = os.path.join(root_dir, "main.py")
    cmd = [sys.executable, "-u", main_py, "旅居", "--number_of_video", "2", "--lang", "cn"]
    proc = subprocess.Popen(cmd, cwd=root_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    if proc.stdout:
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
    proc.wait()
    # 读取配置中的输出目录
    try:
        import yaml
        with open(os.path.join(root_dir, "config", "settings.yaml"), "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        out_dir = (cfg.get("output", {}) or {}).get("csv_dir", os.path.join(root_dir, "data"))
    except Exception:
        out_dir = os.path.join(root_dir, "data")
    data_dir = out_dir
    candidates = []
    if os.path.isdir(data_dir):
        for name in os.listdir(data_dir):
            if name.startswith("旅居_") and name.endswith(".csv"):
                candidates.append(os.path.join(data_dir, name))
    if not candidates:
        preferred = os.path.join(data_dir, "output_bom.csv")
        fallback = os.path.join(data_dir, "output.csv")
        target = preferred if os.path.exists(preferred) else fallback
    else:
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        target = candidates[0]
    if os.path.exists(target):
        with open(target, "r", encoding="utf-8") as f:
            sys.stdout.write(f.read())
    else:
        print("CSV not found")

if __name__ == "__main__":
    main()
