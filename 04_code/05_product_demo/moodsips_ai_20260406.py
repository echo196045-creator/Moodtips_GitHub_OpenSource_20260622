from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import httpx


class MoodSipsAIClient:
    def __init__(self) -> None:
        self.api_key = (
            os.getenv("HEKOU_AI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        ).strip()
        self.base_url = (
            os.getenv("HEKOU_AI_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.model = (
            os.getenv("HEKOU_AI_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4o-mini"
        ).strip()
        self.timeout_seconds = float(os.getenv("HEKOU_AI_TIMEOUT_SECONDS", "18"))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def choose_recommendation(
        self,
        mood_label: str,
        mood_code: str,
        filters: Dict[str, Any],
        candidates: List[Dict[str, Any]],
    ) -> Optional[Dict[str, str]]:
        if not self.enabled or not candidates:
            return None

        system_prompt = (
            "你是中文饮品推荐应用 Moodtips 的推荐文案助手。"
            "你只能从给定候选中选择 1 杯，不得创造新商品。"
            "请基于用户脑内天气与限制，给出自然口语、清爽、简洁、不鸡汤的推荐理由。"
            "推荐理由要尽量从候选的客观标签、默认喝法、价格带出发。"
            "不要使用“节奏、疗愈、处方、治愈、修复、宇宙”这类悬浮词，不要做结果承诺。"
            "输出必须是 JSON，对象字段固定为 chosen_item_id, reason, encouragement。"
            "reason 用 1 句中文，32 字内；encouragement 用 1 句中文，16 字内。"
        )
        user_prompt = {
            "mood": {"code": mood_code, "label": mood_label},
            "filters": filters,
            "candidates": [
                {
                    "item_id": item["item_id"],
                    "brand_name": item["brand_name"],
                    "item_name": item["item_name"],
                    "price": item["base_price_cny"],
                    "default_serving_note": item["default_serving_note"],
                    "tags": item["tags"],
                }
                for item in candidates
            ],
        }
        response_json = self._chat_completion(
            system_prompt=system_prompt,
            user_prompt=json.dumps(user_prompt, ensure_ascii=False),
            response_format={"type": "json_object"},
        )
        if not isinstance(response_json, dict):
            return None

        chosen_item_id = str(response_json.get("chosen_item_id") or "").strip()
        if chosen_item_id not in {item["item_id"] for item in candidates}:
            return None

        return {
            "chosen_item_id": chosen_item_id,
            "reason": str(response_json.get("reason") or "").strip(),
            "encouragement": str(response_json.get("encouragement") or "").strip(),
        }

    def summarize_month(
        self,
        month: str,
        stats: Dict[str, Any],
    ) -> Optional[Dict[str, str]]:
        if not self.enabled:
            return None

        system_prompt = (
            "你是中文情绪饮品应用 Moodtips 的月度总结助手。"
            "你只能基于输入统计做柔和润色，不得编造新数字或新事实。"
            "语言要自然口语、轻快清爽，不要写空泛比喻，不要写悬浮鸡汤。"
            "输出必须是 JSON，对象字段固定为 summary_title, summary_text, gentle_tip。"
            "summary_title 不超过 16 字，summary_text 不超过 80 字，gentle_tip 不超过 24 字。"
        )
        response_json = self._chat_completion(
            system_prompt=system_prompt,
            user_prompt=json.dumps({"month": month, "stats": stats}, ensure_ascii=False),
            response_format={"type": "json_object"},
        )
        if not isinstance(response_json, dict):
            return None
        summary_title = str(response_json.get("summary_title") or "").strip()
        summary_text = str(response_json.get("summary_text") or "").strip()
        gentle_tip = str(response_json.get("gentle_tip") or "").strip()
        if not summary_title or not summary_text or not gentle_tip:
            return None
        return {
            "summary_title": summary_title,
            "summary_text": summary_text,
            "gentle_tip": gentle_tip,
        }

    def _chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            if isinstance(content, list):
                text = "".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict)
                )
            else:
                text = str(content or "")
            return json.loads(text)
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
            return None
