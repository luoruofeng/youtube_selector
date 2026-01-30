import os
import json
import yaml
from openai import OpenAI
from typing import List
from src.utils import get_logger

class QwenClient:
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.logger = get_logger("llm")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.logger.info("加载 Qwen 配置完成")
        api_key = self.config["qwen"]["api_key"]
        if api_key == "YOUR_DASHSCOPE_API_KEY" or not api_key:
            api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = str(self.config["qwen"]["base_url"]).replace("`", "")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = self.config["qwen"]["model"]
        self.prompt_template = self.config["prompts"]["filter_template"]
        self.logger.info(f"Qwen 客户端初始化完成，模型：{self.model}")

    def filter_relevant_titles(self, titles: List[str], topic: str) -> List[str]:
        if not titles:
            return []

        titles_str = json.dumps(titles, ensure_ascii=False)
        content = self.prompt_template.format(topic=topic, titles=titles_str)
        self.logger.debug(f"构造过滤提示：主题={topic}，标题数量={len(titles)}")

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": content}
                ]
            )
            response_text = completion.choices[0].message.content.strip()
            self.logger.debug("收到 Qwen 响应")
            
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if len(lines) >= 2:
                    response_text = "\n".join(lines[1:-1])
            
            result = json.loads(response_text)
            if isinstance(result, list):
                self.logger.info(f"Qwen 过滤结果数量：{len(result)}")
                return result
            else:
                self.logger.warning("Qwen 响应不是数组，返回空列表")
                return []
        except Exception as e:
            self.logger.error(f"调用 Qwen 出错：{e}")
            return []

    def translate_text(self, text: str, target_lang: str) -> str:
        try:
            lang = str(target_lang or "").lower()
            mapping = {"en": "英语", "cn": "中文", "jp": "日语"}
            lang_name = mapping.get(lang, "英语")
            content = f"请将下面的关键词翻译为{lang_name}，只返回翻译后的词本身，不要任何其他内容：{text}"
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful translator."},
                    {"role": "user", "content": content}
                ]
            )
            result = completion.choices[0].message.content.strip()
            if result.startswith("```"):
                lines = result.splitlines()
                if len(lines) >= 2:
                    result = "\n".join(lines[1:-1]).strip()
            result = result.strip().strip("\"'`")
            self.logger.info("关键词翻译完成")
            return result or str(text)
        except Exception as e:
            self.logger.error(f"翻译失败：{e}")
            return str(text)
