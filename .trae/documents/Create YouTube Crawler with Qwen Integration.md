# Python YouTube Crawler Project Plan

I will create a complete Python command-line project to crawl YouTube videos related to a specific topic, filter them using Qwen (Aliyun), and save the results to SQLite and CSV.

## Project Structure
```text
youtube_selector/
├── config/
│   └── settings.yaml       # Configuration (API keys, prompts, batch size)
├── data/
│   ├── videos.db           # SQLite database
│   └── output.csv          # Final CSV output
├── src/
│   ├── __init__.py
│   ├── crawler.py          # Playwright crawler logic (Search & Watch page parsing)
│   ├── database.py         # SQLite database management
│   ├── llm.py              # Qwen API integration
│   └── utils.py            # CSV saving and helper functions
├── main.py                 # CLI entry point (find_url command)
└── requirements.txt        # Project dependencies
```

## Technical Implementation

### 1. Configuration (`config/settings.yaml`)
- Qwen API settings (`api_key`, `base_url`, `model`).
- Crawler settings (`batch_size`, `headless_mode`).
- Prompts (`filter_prompt`).

### 2. Crawler Module (`src/crawler.py`)
- **Library**: `playwright` (handles dynamic YouTube content).
- **Core Functions**:
  - `search_and_scroll(topic)`: Searches for the topic and scrolls to load videos.
  - `extract_video_info(page)`: Extracts titles and URLs from the search results page.
  - `parse_watch_page(url)`: **(Per requirement)** Navigates to a specific video URL, extracts the current video title and recommended video URLs (sidebar).

### 3. LLM Module (`src/llm.py`)
- **Library**: `openai` (compatible with Aliyun Qwen).
- **Function**: `filter_relevant_titles(titles, topic)`
  - Sends a batch of titles to Qwen.
  - Asks Qwen to return a JSON array of titles relevant to the topic.

### 4. Database Module (`src/database.py`)
- **Database**: `sqlite3`.
- **Functionality**:
  - Initialize table `videos` (url, title, topic, timestamp).
  - `filter_existing_urls(url_list)`: Returns only URLs that are not in the DB.
  - `save_videos(video_list)`: Inserts new videos.

### 5. CLI (`main.py`)
- **Library**: `click` or `argparse`.
- **Command**: `find_url(topic, number_of_video=33)`
- **Workflow**:
  1. Initialize Config, DB, and Browser.
  2. Search YouTube for `topic`.
  3. Loop:
     - Scroll and collect video candidates.
     - When `batch_size` (e.g., 55) is reached:
       - Call Qwen to filter relevant titles.
       - Deduplicate against SQLite.
       - Save valid videos to SQLite and CSV.
       - Check if `number_of_video` target is met.
  4. Cleanup and exit.

## Verification
- I will verify the project by running the `find_url` command with a test topic.
- I will check if the `output.csv` and SQLite database are populated correctly.
- I will ensure the Qwen API integration works (assuming a valid API key is provided or mocked).

*Note: You will need to provide your actual `DASHSCOPE_API_KEY` in the generated config file or environment variables to run the Qwen filtering.*
