# YouTube 视频智能筛选工具

一个基于 Playwright + Qwen + SQLite 的命令行工具：  
自动在 YouTube 上根据**主题关键词**搜索视频，调用 **Qwen 大模型**过滤相关标题，只保留**播放量达到阈值**的视频，写入 SQLite 并导出为 **带 BOM 的 CSV 文件**（防止中文乱码）。

---

## 功能特性

- 按主题关键词自动搜索 YouTube 视频
- 使用 Qwen LLM 智能判断标题是否与主题相关
- 过滤掉已经保存过的 URL，避免重复
- 解析 YouTube 播放页的播放量（支持简写，例如 `1.2M`、`3.4万`）
- 只保留播放量大于配置阈值的视频
- 按配置的分钟区间过滤视频时长（例如 15–120 分钟）
- 将结果写入 SQLite 数据库（包含 view_count 字段）
  - 数据库字段：`view_count`、`duration_minutes`（分钟为单位）
- 导出为 UTF-8 BOM CSV 文件，避免中文标题乱码
- 全流程中文日志 + 终端进度条展示

---

## 目录结构

- `main.py`：命令行入口，整体流程控制、日志与进度条
- `src/crawler.py`：使用 Playwright 爬取 YouTube 搜索结果和播放页信息（包括播放量）
- `src/llm.py`：封装 Qwen 调用逻辑，按主题过滤标题
- `src/database.py`：SQLite 持久化与去重逻辑，包含 view_count 字段
- `src/utils.py`：
  - 日志工具（根据配置输出到控制台 + 文件）
  - CSV BOM 处理（解决中文乱码）
  - 播放量字符串解析函数
- `config/settings.yaml`：项目配置（Qwen、爬虫、日志、提示词等）
- `data/`：
  - `videos.db`：SQLite 数据库
  - `*.csv`：按主题与时间命名的 CSV 结果文件
- `tests/generate_csv_luju.py`：示例脚本，自动执行“旅居”主题测试并输出结果

---

## 环境准备

### 1. 安装依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置 Qwen 与爬虫参数

编辑 `config/settings.yaml`：

```yaml
qwen:
  api_key: "你的DashScope API Key"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen3-max"

crawler:
  batch_size: 55
  headless: true
  min_wait_seconds: 3.0000
  max_wait_seconds: 6.0000
  min_video_min: 15
  max_video_max: 120
  min_times_of_play: 33333

prompts:
  filter_template: "下面哪些标题可能是有关于{topic}主题的，响应我一个数组(数组包含标题字符串，标题字符串不能有任何修改)，不要返回任何多余的话，直接返回数组即可，如果一个都没有就返回一个空数组([])，标题如下：{titles}"

logging:
  level: "INFO"
  file_enabled: true
  file_path: "data/app.log"
```

配置说明：
- `qwen.api_key`：你的阿里云 DashScope API Key，可用环境变量 `DASHSCOPE_API_KEY` 兜底
- `crawler.headless`：是否无头浏览器（建议 true，更稳定）
- `min_wait_seconds` / `max_wait_seconds`：每次访问/滚动前的随机等待时间，降低被 YouTube 识别为爬虫的风险
- `min_times_of_play`：只保留播放量大于此值的视频（例如 `33333` 即大于 3.3 万播放量）
- `exclude_shorts`：是否默认剔除 Shorts（通过搜索页“Videos/视频/動画”芯片）
- `min_video_min` / `max_video_max`：分钟区间时长过滤，仅保留时长位于该区间内的视频
- `logging`：日志等级与输出路径
- `output.csv_video_count`：每个 CSV 文件限制的视频数量；当命令行未传入或传入非正数时使用该配置

---

## 运行方式

### 1. 通用命令行运行

在项目根目录：

```bash
python main.py "旅居"
```

参数说明：
- 第一个参数为主题字符串（可以是中文），程序会先调用 Qwen 将其翻译为英文再去 YouTube 搜索
- 每个 CSV 保存的视频数量由配置 `output.csv_video_count` 控制

执行过程中：
- 终端会输出中文日志，说明当前爬取状态、过滤情况等
- 控制台会显示**播放量检查进度条**与**总体进度条**
- 最终结果：
  - 写入 SQLite：`data/videos.db`（包含 `url/title/topic/view_count`）
  - 导出 CSV：`data/{topic}_{年}{月}{日}-{时}{分}.csv`

示例文件名：

```text
data/旅居_2026年01月29日-16时05分.csv
```

### 2. 使用测试脚本自动生成“旅居”示例 CSV

在 `tests` 目录：

```bash
cd tests
python generate_csv_luju.py
```

脚本行为：
- 自动在项目根目录调用：
  - `python -u main.py "旅居"`
- 实时输出 main.py 的日志与进度条（不会再“憋到最后一次性喷日志”）
- 执行完成后，在 `data/` 目录中查找最新的以 `旅居_*.csv` 命名的文件并打印其内容  
  若找不到，则退回到 `output_bom.csv` / `output.csv`。

---

## 实现流程详解

### 1. 主流程（main.py）

1. **加载配置**
   - 从 `config/settings.yaml` 读取 Qwen、爬虫、日志等配置。
2. **初始化组件**
   - `VideoDB`：负责 SQLite 数据库连接、建表、去重与插入。
   - `QwenClient`：封装 Qwen API 调用。
   - `YouTubeCrawler`：封装 Playwright 的启动、搜索与解析。
3. **生成 CSV 文件名**
   - 根据 `topic` 和当前时间生成：

     ```text
     {topic}_{年}{月}{日}-{时}{分}.csv
     ```

   - 例如：`旅居_2026年01月29日-16时05分.csv`。
4. **搜索与滚动**
   - 打开 YouTube 搜索页，输入主题关键字。
   - 进入循环：
     - 向下滚动页面（每次滚动前后随机等待 3~6 秒）。
     - 解析当前页面上的 `ytd-video-renderer` 列表，获取标题和 URL。
     - 只保留本次会话中未见过的 URL 加入缓冲区。
5. **批次处理**
   - 当缓冲区中积累到 `batch_size` 条记录：
     - 取出一个批次，调用 `process_batch` 进行处理。
   - 当连续多次滚动都未发现新视频时停止。

### 2. 批次处理（process_batch）

函数签名见：[main.py](file:///c:/Users/luoru/Desktop/youtube_selector/main.py#L100-L142)

处理步骤：

1. **Qwen 过滤**
   - 从批次中收集标题列表，调用 `QwenClient.filter_relevant_titles`。
   - 仅保留 Qwen 判定与主题相关的标题。
2. **数据库去重**
   - 提取相关视频的 URL 列表，调用 `VideoDB.filter_existing_urls`。
   - 只保留数据库中尚不存在的 URL。
3. **播放量检查 + 进度条**
   - 对未入库的候选视频，逐个访问其 YouTube 播放页：
     - 使用 `YouTubeCrawler.get_view_count(url)` 获取播放量：
       - 首选 XPath：`//*[@id="info"]/span[1]`
       - 兼容其他结构（包括 `views`、`次观看` 等）
     - 使用 `parse_view_count` 将 `1.2M`、`3.4万` 等文本解析为整数。
   - 仅当 `view_count > min_times_of_play` 时才保留该视频。
   - 同时在终端展示“播放量检查”进度条。
4. **写入数据库与 CSV**
   - 将通过所有过滤的视频插入 SQLite：
     - 字段：`url`, `title`, `topic`, `view_count`
   - CSV 写入：
     - 先调用 `ensure_csv_bom` 保证文件带 BOM（避免 Excel 中文乱码）。
     - 若文件不存在：
       - 使用 `utf-8-sig` 编码新建文件。
       - 写入表头：`Title,URL`。
     - 然后追加写入所有视频的标题和 URL。

### 3. 播放量解析实现（parse_view_count）

位置：[utils.py](file:///c:/Users/luoru/Desktop/youtube_selector/src/utils.py#L33-L74)

支持多种格式：
- `1,234 次观看` → 1234
- `12K views` → 12000
- `1.2M views` → 1200000
- `3.4万 次观看` → 34000
- `2.1亿 次观看` → 210000000
- `1000000` → 1000000

核心思路：用正则提取数字部分，根据单位（K/M/B/万/亿）乘以相应倍数。

### 4. 数据库结构与去重

位置：[database.py](file:///c:/Users/luoru/Desktop/youtube_selector/src/database.py#L16-L54)

表结构（videos）：

- `id`：自增主键
- `url`：唯一约束，防止重复
- `title`：视频标题
- `topic`：爬取时使用的主题
- `view_count`：播放量（整数）
- `duration_minutes`：时长（分钟）
- `created_at`：插入时间

去重逻辑：
- `filter_existing_urls(urls: List[str]) -> List[str]`
  - 返回数据库中尚不存在的 URL 列表。

---

## 日志与可视化进度条

### 日志

- 所有核心模块（爬虫、LLM、数据库、主流程、工具）均使用统一的日志工具：
  - 配置文件控制日志等级与是否写入文件。
  - 控制台实时输出中文说明，方便观察流程。
- 日志示例：
  - “初始化组件，headless=...，batch_size=...，等待区间=(3.0,6.0)”
  - “缓冲区：X，已保存：Y/Z，本次新发现：N”
  - “发送 N 个标题到 Qwen 进行过滤”
  - “去重后待保存数量：K”

### 终端进度条

在 main.py 中实现了一个简易的文本进度条：

- `_bar(prefix, current, total, size=30)`
  - prefix：前缀文本，例如“总体进度”“播放量检查”
  - current / total：当前值 / 总数
  - size：进度条长度（字符数）
- 呈现效果（示意）：

```text
总体进度 [██████████░░░░░░░░░░░░░░░░] 10/50
播放量检查 [████████████████░░░░░░░░░░] 15/20
```

通过在 `process_batch` 中调用 `_bar`，在播放量检查阶段实时刷新进度；在总保存数量变化时刷新总体进度。

---

## 关于 `generate_csv_luju.py` 日志实时输出

问题现象：
- 之前使用 `subprocess.check_output` 调用 `main.py` 时，Python 缓冲机制会导致日志积压，到子进程结束才一次性输出。

当前改动：
- 改为使用 `Popen` + 流式读取：

  ```python
  cmd = [sys.executable, "-u", main_py, "旅居", "--number_of_video", "2"]
  proc = subprocess.Popen(cmd, cwd=root_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
  if proc.stdout:
      for line in proc.stdout:
          sys.stdout.write(line)
          sys.stdout.flush()
  proc.wait()
  ```

- `-u` 参数强制子进程使用无缓冲模式输出，使日志可以实时显示。
- 循环读取 `proc.stdout` 的每一行，并立即 flush 到当前终端。

效果：
- 执行 `python generate_csv_luju.py` 时，可以实时看到：
  - 初始化日志
  - Playwright 启动与页面滚动日志
  - Qwen 过滤日志
  - 播放量检查进度条
  - 最后再看到 CSV 内容。

---

## 运行测试

在项目根目录执行：

```bash
python -m unittest discover -s tests -p test*.py -v
```

包含以下测试：
- 工具函数：播放量解析、时长解析、语言检测
- 过滤流程：在批次处理中按“播放量阈值 + 分钟区间”两道条件筛选

如你有自定义测试命令，请告知以纳入项目约定。

---

## 常见问题与说明

1. **中文 CSV 乱码**
   - 已通过 `ensure_csv_bom` 处理，所有新建 CSV 使用 UTF-8 BOM。
   - 如果原文件被占用无法覆盖，会生成一个 `*_bom.csv` 副本，内容相同。

2. **播放量解析不准确**
   - 已针对常见格式（K/M/B、万/亿、带逗号的数字）做了处理。
   - 如遇到新格式，可以在 `parse_view_count` 中增加对应规则。

3. **YouTube 页面结构变动**
   - 当前使用多种 XPath/文本匹配方案获取播放量。
   - 如果 YouTube 大改版导致解析失败，可根据浏览器开发者工具调整选择器。

---

## 后续可扩展方向

- CSV 中增加播放量列，便于直接查看/排序。
- 增加命令行参数控制播放量阈值，而不是完全依赖配置文件。
- 支持多主题批次执行，一次生成多组 CSV。
- 增加失败重试与异常视频跳过策略，提升爬取稳定性。
