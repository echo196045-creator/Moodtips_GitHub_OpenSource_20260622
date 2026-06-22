from __future__ import annotations

import base64
import binascii
import hashlib
import mimetypes
import json
import os
import random
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from moodsips_recommendation_demo_20260404 import (
    RequestPayload,
    evaluate_request,
    load_sku_catalog,
    load_weight_matrix,
)
from moodsips_ai_20260406 import MoodSipsAIClient
from moodsips_storage_20260404 import MoodSipsStorage, SIMPLE_LIFECYCLE_LABELS


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]
PROTOTYPE_DIR = PROJECT_ROOT / "07_prototype"
if not PROTOTYPE_DIR.exists():
    bundled_prototype_dir = BASE_DIR / "07_prototype"
    if bundled_prototype_dir.exists():
        PROTOTYPE_DIR = bundled_prototype_dir


def resolve_env_path(env_name: str, default_path: Path) -> Path:
    raw_value = os.getenv(env_name, "").strip()
    if not raw_value:
        return default_path
    candidate = Path(raw_value)
    if candidate.is_absolute():
        return candidate
    return (PROJECT_ROOT / candidate).resolve()


FRONTEND_DIR = resolve_env_path("MOODSIPS_FRONTEND_DIR", BASE_DIR / "frontend")
GENERATED_DIR = resolve_env_path("MOODSIPS_GENERATED_DIR", FRONTEND_DIR / "generated")
DB_PATH = resolve_env_path("MOODSIPS_DB_PATH", BASE_DIR / "data" / "moodsips_local_demo_20260404.db")

SKU_CATALOG = load_sku_catalog(PROTOTYPE_DIR / "moodsips_v1_seed_sku_catalog_20260404.csv")
WEIGHT_MATRIX = load_weight_matrix(PROTOTYPE_DIR / "moodsips_v1_weight_matrix_20260404.csv")
PRESET_FILE = BASE_DIR / "moodsips_demo_requests_20260404.json"
PRESET_DATA: Dict[str, Dict[str, Any]] = json.loads(PRESET_FILE.read_text(encoding="utf-8"))
STORAGE = MoodSipsStorage(DB_PATH)
AI_CLIENT = MoodSipsAIClient()
SKU_BY_ID = {sku["sku_id"]: sku for sku in SKU_CATALOG}
DEFAULT_USER_ID = "local_demo_user"
DEFAULT_PROFILE_BASE: Dict[str, Any] = {
    "sweet_pref": 2.0,
    "caffeine_pref_level": 2.0,
    "usual_temp": "",
    "liked_categories": ["fruit_tea", "tea"],
    "disliked_categories": [],
}
DEFAULT_MARKET_CONTEXT: Dict[str, str] = {
    "market_name": "中国大陆",
    "default_locale": "zh-CN",
    "default_currency_code": "CNY",
    "default_ip_country_code": "CN",
    "default_city": "Shenzhen",
}
MENU_SOURCE_STANDARD: Dict[str, Any] = {
    "benchmark_policy": "消费者可见的深圳快照必须来自大陆官方商品内容。若门店价格未核实，页面应标注为参考价。",
    "official_source_policy": "仅大陆官方订购渠道可在 /api/menu/* 接口中面向用户展示。",
    "required_country_code": "CN",
    "required_currency_code": "CNY",
    "store_personalization_enabled": False,
    "official_pricing_city": "Shenzhen",
    "official_pricing_policy": "不做地理位置个性化，统一使用深圳门店价格作为大陆基准。",
    "official_channel_priority": [
        "luckin-cn-official",
        "heytea-go-cn-official",
        "nayuki-cn-official",
        "chagee-cn-official",
    ],
}
HEKOU_MOOD_META: Dict[str, Dict[str, str]] = {
    "tired": {"label": "很累", "color": "#6F7AA6", "recap_line": "你更多是在“很累”的时候打开它。"},
    "annoyed": {"label": "有点烦", "color": "#C8797B", "recap_line": "你最近更常在心里有点乱的时候来找它。"},
    "empty": {"label": "空空的", "color": "#6883A8", "recap_line": "你最近常在需要一点陪伴感时打开它。"},
    "light": {"label": "想轻一点", "color": "#7FA89B", "recap_line": "你更偏爱轻一点、清爽一点的答案。"},
    "unclear": {"label": "说不清", "color": "#9A9A93", "recap_line": "状态模糊时，你更愿意把决定交给系统。"},
}
HEKOU_PREFERENCE_LABELS: Dict[str, str] = {
    "fresh": "清新",
    "tea_forward": "茶感",
    "milky": "奶香",
    "fruity": "果香",
    "smooth": "顺口",
    "sugar_free_friendly": "无糖友好",
    "light": "轻负担",
    "comforting": "有一点满足感",
}
V2_MOOD_META: Dict[str, Dict[str, str]] = {
    "spark": {"label": "开心", "color": "#1677ff", "recap_line": "这个月你更常在想提一口气的时候点开它。"},
    "ease": {"label": "躺平", "color": "#15b8c8", "recap_line": "这个月你更常把节奏放慢一点。"},
    "cooldown": {"label": "烦躁", "color": "#2f6fed", "recap_line": "这个月你更常先把噪音降下来。"},
    "recharge": {"label": "难受", "color": "#4a8cff", "recap_line": "这个月你更常需要一口慢慢补回来的能量。"},
}
V2_FRONTEND_MOOD_TO_CANONICAL: Dict[str, str] = {
    "boosted": "spark",
    "sparked": "spark",
    "chill": "ease",
    "pleased": "ease",
    "overloaded": "cooldown",
    "frazzled": "cooldown",
    "low_power": "recharge",
    "hollow": "recharge",
    "tired": "recharge",
    "annoyed": "cooldown",
    "empty": "recharge",
    "unclear": "cooldown",
    "calm": "ease",
    "bright": "spark",
    "happy": "ease",
}
MOODTIPS_SERVICE_NAME = "Moodtips Local API"
V2_TASTE_LABELS: Dict[str, str] = {
    "fresh": "清新",
    "tea_forward": "茶感",
    "milky": "奶香",
    "fruity": "果香",
    "smooth": "顺口",
    "light": "轻盈",
    "sugar_free_friendly": "无糖友好",
}
V2_PRICE_LABELS: Dict[str, str] = {
    "any": "都可以",
    "under_15": "15元内",
    "15_20": "15-20",
    "above_20": "20元以上",
}
V2_TEMPERATURE_LABELS: Dict[str, str] = {
    "any": "都可以",
    "cold": "冷",
    "hot": "热",
    "smoothie": "冰沙",
}
V2_CAFFEINE_LABELS: Dict[str, str] = {
    "any": "都可以",
    "none": "无咖啡因",
    "low": "低咖啡因",
    "normal": "正常",
    "strong": "强咖啡因",
}
TARGET_BRAND_BONUS: Dict[str, float] = {}
V2_TASTE_TAG_CODES = tuple(V2_TASTE_LABELS.keys())
SIMPLE_TASTE_LABEL_TO_CODE = {label: code for code, label in V2_TASTE_LABELS.items()}
SIMPLE_TASTE_KEYWORDS: Dict[str, tuple[str, ...]] = {
    "fresh": ("清新", "清爽", "鲜爽", "爽口", "沁凉", "轻快", "气泡", "薄荷"),
    "tea_forward": ("茶感", "茶", "乌龙", "红茶", "绿茶", "白茶", "普洱", "茉莉", "龙井", "岩茶", "焙火"),
    "milky": ("奶香", "牛乳", "鲜奶", "奶茶", "奶绿", "厚乳", "芝士", "酸奶", "奶盖", "椰乳", "乳茶"),
    "fruity": ("果香", "水果", "柠檬", "西柚", "葡萄", "青提", "草莓", "莓", "桃", "芒果", "荔枝", "百香", "凤梨", "橙", "苹果", "柚"),
    "smooth": ("顺口", "丝滑", "绵密", "柔和", "细腻", "轻盈", "轻负担"),
    "light": ("轻盈", "轻负担", "清爽", "爽口", "轻轻"),
    "sugar_free_friendly": ("无糖", "零糖", "0糖", "少糖", "轻糖"),
}
SIMPLE_IMAGE_TRUST_LABELS: Dict[str, str] = {
    "source": "官方原图",
    "ai_illustration": "AI示意图",
    "user_uploaded": "用户上传",
    "brand_logo": "品牌Logo",
    "brand_collage": "官方合拍",
    "brand_fallback": "品牌备图",
}
COPY_BLOCKLIST = ("节奏", "疗愈", "治愈", "处方", "修复", "宇宙", "一切", "顺利过关", "马上")
MONTHLY_COPY_BLOCKLIST = ("情绪轨迹", "疗愈", "治愈", "宇宙", "修复")


class ProfilePayload(BaseModel):
    sweet_pref: Optional[float] = None
    caffeine_pref_level: Optional[float] = None
    usual_temp: Optional[str] = None
    liked_categories: List[str] = Field(default_factory=list)
    disliked_categories: List[str] = Field(default_factory=list)


class RecommendPayload(BaseModel):
    entry_mode: str = "quick"
    goal: str = "refresh"
    mood: str = "none"
    scene: str = ""
    budget_band: str = "high"
    temperature_pref: str = "any"
    caffeine_pref: str = "allow"
    dairy_avoid: bool = False
    micro_adjusts: List[str] = Field(default_factory=list)
    profile: ProfilePayload = Field(default_factory=ProfilePayload)
    top_k: int = 3


class AppliedContext(BaseModel):
    context_type: str
    context_code: str


class FollowupOption(BaseModel):
    value: str
    label: str


class FollowupQuestion(BaseModel):
    question_type: str
    title: str
    question: str
    options: List[FollowupOption]


class RecommendationCard(BaseModel):
    rank: int
    sku_id: str
    sku_name: str
    category: str
    base_price: float
    price_band: str
    score: float
    explanation_tags: List[str]
    emotional_copy: str
    order_hint: str
    debug: Optional[Dict[str, Any]] = None


class RecommendationMeta(BaseModel):
    candidate_count: int
    filtered_out_count: int
    score_gap_top1_top2: Optional[float] = None
    followup_required: bool
    confidence_score: float
    applied_contexts: List[AppliedContext]


class SelectedItem(BaseModel):
    sku_id: str
    sku_name: str
    selected_at: Optional[str] = None


class RecommendResponse(BaseModel):
    session_id: str
    created_at: str
    session_input: Dict[str, Any]
    effective_profile: Dict[str, Any] = Field(default_factory=dict)
    profile_memory_applied: bool = False
    meta: RecommendationMeta
    followup_question: Optional[FollowupQuestion] = None
    recommendations: List[RecommendationCard]
    filtered_out: List[Dict[str, Any]] = Field(default_factory=list)
    selected_item: Optional[SelectedItem] = None


class MenuRecommendationCard(RecommendationCard):
    brand_code: str
    brand_name: str
    brand_name_local: Optional[str] = None
    display_name: str
    sku_name_local: Optional[str] = None
    image_url: Optional[str] = None
    channel_name: Optional[str] = None
    source_type: Optional[str] = None
    source_status: Optional[str] = None
    source_name: Optional[str] = None
    store_name: Optional[str] = None
    currency_code: str
    original_category: Optional[str] = None
    option_group_count: int = 0
    option_summary: List[Dict[str, Any]] = Field(default_factory=list)
    profile_tags: List[str] = Field(default_factory=list)
    price_context: Dict[str, Any] = Field(default_factory=dict)


class MenuRecommendResponse(BaseModel):
    catalog_scope: str
    catalog_count: int
    session_input: Dict[str, Any]
    effective_profile: Dict[str, Any] = Field(default_factory=dict)
    profile_memory_applied: bool = False
    meta: RecommendationMeta
    followup_question: Optional[FollowupQuestion] = None
    recommendations: List[MenuRecommendationCard]
    filtered_out: List[Dict[str, Any]] = Field(default_factory=list)


class PresetSummary(BaseModel):
    preset_name: str
    goal: str
    mood: str
    scene: str
    budget_band: str
    temperature_pref: str


class PresetListResponse(BaseModel):
    count: int
    presets: List[PresetSummary]


class PresetDetailResponse(BaseModel):
    preset_name: str
    payload: RecommendPayload


class HealthResponse(BaseModel):
    status: str
    service: str
    sku_count: int
    preset_count: int
    menu_brand_count: int = 0
    menu_item_count: int = 0
    market_name: str = DEFAULT_MARKET_CONTEXT["market_name"]
    default_locale: str = DEFAULT_MARKET_CONTEXT["default_locale"]
    default_currency_code: str = DEFAULT_MARKET_CONTEXT["default_currency_code"]
    default_ip_country_code: str = DEFAULT_MARKET_CONTEXT["default_ip_country_code"]
    default_city: str = DEFAULT_MARKET_CONTEXT["default_city"]
    db_path: str


class SelectionPayload(BaseModel):
    sku_id: str
    sku_name: str


class SelectionResponse(BaseModel):
    session_id: str
    selected_item: SelectedItem


class FeedbackPayload(BaseModel):
    satisfaction_label: str
    fail_reason: str = ""
    note: str = ""
    selected_sku_id: Optional[str] = None
    selected_sku_name: Optional[str] = None


class FeedbackResponse(BaseModel):
    feedback_id: str
    session_id: str
    satisfaction_label: str
    fail_reason: str = ""
    note: str = ""
    selected_item: Optional[SelectedItem] = None
    created_at: str
    profile_memory: Dict[str, Any] = Field(default_factory=dict)
    profile_summary: List[str] = Field(default_factory=list)


class RecommendationPreview(BaseModel):
    rank_no: int
    sku_id: str
    sku_name: str
    category: Optional[str] = None
    score: Optional[float] = None
    price_band: Optional[str] = None


class FeedbackSummary(BaseModel):
    label: str
    reason: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[str] = None


class HistoryItem(BaseModel):
    session_id: str
    created_at: str
    goal: str
    mood: Optional[str] = None
    scene: Optional[str] = None
    budget_band: Optional[str] = None
    temperature_pref: Optional[str] = None
    caffeine_pref: Optional[str] = None
    top_recommendation: Dict[str, Optional[str]]
    selected_item: Optional[SelectedItem] = None
    latest_feedback: Optional[FeedbackSummary] = None
    confidence_score: float
    followup_required: bool
    recommendation_preview: List[RecommendationPreview] = Field(default_factory=list)


class HistoryListResponse(BaseModel):
    count: int
    items: List[HistoryItem]


class ProfileMemoryResponse(BaseModel):
    user_id: str
    updated_at: Optional[str] = None
    profile: Dict[str, Any] = Field(default_factory=dict)
    summary_chips: List[str] = Field(default_factory=list)


class AcceptRecordPayload(BaseModel):
    session_id: Optional[str] = None
    mood_code: str
    mood_label: Optional[str] = None
    budget_band: str = ""
    temperature_pref: str = ""
    caffeine_pref: str = ""
    preference_tags: List[str] = Field(default_factory=list)
    sku_id: str
    sku_name: str
    brand_code: Optional[str] = None
    brand_name: Optional[str] = None
    image_url: Optional[str] = None
    base_price: float = 0.0
    currency_code: str = DEFAULT_MARKET_CONTEXT["default_currency_code"]
    serving_note: Optional[str] = None
    encouragement_copy: Optional[str] = None


class AcceptRecordResponse(BaseModel):
    accept_id: str
    user_id: str
    session_id: Optional[str] = None
    accepted_at: str
    accepted_date: str
    accepted_month: str
    mood_code: str
    mood_label: Optional[str] = None
    budget_band: Optional[str] = None
    temperature_pref: Optional[str] = None
    caffeine_pref: Optional[str] = None
    preference_tags: List[str] = Field(default_factory=list)
    sku_id: str
    sku_name: str
    brand_code: Optional[str] = None
    brand_name: Optional[str] = None
    image_url: Optional[str] = None
    base_price: float = 0.0
    currency_code: str = DEFAULT_MARKET_CONTEXT["default_currency_code"]
    serving_note: Optional[str] = None
    encouragement_copy: Optional[str] = None


class AcceptRecordListResponse(BaseModel):
    count: int
    items: List[AcceptRecordResponse]


class AcceptCalendarResponse(BaseModel):
    user_id: str
    month: str
    count: int
    items: List[AcceptRecordResponse]


class AcceptRecapResponse(BaseModel):
    user_id: str
    month: str
    record_count: int
    headline: str
    summary_lines: List[str] = Field(default_factory=list)
    summary_title: str = ""
    summary_text: str = ""
    gentle_tip: str = ""
    stats: Dict[str, Any] = Field(default_factory=dict)
    mood_counts: List[Dict[str, Any]] = Field(default_factory=list)
    preference_counts: List[Dict[str, Any]] = Field(default_factory=list)
    brand_counts: List[Dict[str, Any]] = Field(default_factory=list)
    longest_streak_days: int = 0
    recent_accepts: List[AcceptRecordResponse] = Field(default_factory=list)


class SimpleRecommendRequest(BaseModel):
    mood_code: str
    price_band: str = "any"
    temperature_pref: str = "any"
    caffeine_pref: str = "any"
    taste_tags: List[str] = Field(default_factory=list)
    retry_seed: int = 0
    exclude_brand_code: str = ""


class SimpleRecommendationCard(BaseModel):
    item_id: str
    brand_code: str
    brand_name: str
    item_name: str
    image_url: str
    image_source_type: str = "source"
    image_badge_text: str = ""
    image_trust: str = ""
    base_price: float
    currency_code: str = DEFAULT_MARKET_CONTEXT["default_currency_code"]
    default_temperature_text: str = ""
    default_sweetness_text: str = ""
    default_serving_note: str = ""
    temperature_type: str
    caffeine_level_code: str
    tags: List[str] = Field(default_factory=list)
    launch_date: str = ""
    lifecycle_code: str = "permanent"
    lifecycle_label: str = "常驻"
    source_url: Optional[str] = None
    explanation_sections: List[Dict[str, str]] = Field(default_factory=list)
    reason: str
    encouragement: str


class SimpleRecommendationMeta(BaseModel):
    candidate_count: int
    fallback_used: bool = False
    model_used: str = "fallback-template"
    brand_exclusion_relaxed: bool = False
    taste_constraint_relaxed: bool = False
    profile_memory_applied: bool = False
    profile_summary: List[str] = Field(default_factory=list)


class SimpleRecommendationResponse(BaseModel):
    session_id: str
    recommendation: SimpleRecommendationCard
    meta: SimpleRecommendationMeta


class SimpleVisualOverridePayload(BaseModel):
    item_id: str
    brand_code: str
    item_name: str
    image_data_url: str
    note: str = ""
    submitter_note: str = ""
    original_file_name: str = ""
    badge_text: str = "用户上传"
    image_mode: str = "user_uploaded"


class SimpleVisualOverrideResponse(BaseModel):
    item_id: str
    brand_code: str
    item_name: str
    image_url: str
    uploaded_image_url: str = ""
    image_source_type: str = "user_uploaded"
    image_badge_text: str = "用户上传"
    note: str = ""
    review_id: str = ""
    review_status: str = "pending"
    review_note: str = ""
    image_mode: str = "user_uploaded"
    rebuild_summary: Dict[str, Any] = Field(default_factory=dict)


class SimpleImageReviewItem(BaseModel):
    review_id: str
    item_id: str
    brand_code: str
    item_name: str
    uploaded_image_url: str
    uploaded_file_path: str
    mime_type: str = ""
    original_file_name: str = ""
    submitter_note: str = ""
    badge_text: str = ""
    image_mode: str = "user_uploaded"
    review_status: str = "pending"
    review_note: str = ""
    reviewed_at: str = ""
    created_at: str = ""
    updated_at: str = ""


class SimpleImageReviewListResponse(BaseModel):
    count: int
    items: List[SimpleImageReviewItem]


class SimpleImageReviewDecisionPayload(BaseModel):
    review_note: str = ""


class SimpleImageReviewDecisionResponse(BaseModel):
    item: SimpleImageReviewItem
    rebuild_summary: Dict[str, Any] = Field(default_factory=dict)


DATA_URL_PATTERN = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>[A-Za-z0-9+/=\s]+)$", re.IGNORECASE)
MAX_SIMPLE_UPLOAD_BYTES = 8 * 1024 * 1024


def slugify_name(value: str, fallback: str = "item") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "").strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-_")
    return cleaned or fallback


def decode_data_url_asset(data_url: str) -> tuple[bytes, str]:
    raw_value = str(data_url or "").strip()
    match = DATA_URL_PATTERN.match(raw_value)
    if not match:
        raise HTTPException(status_code=400, detail="image_data_url must be a base64 data URL.")
    mime_type = str(match.group("mime") or "").strip().lower()
    try:
        image_bytes = base64.b64decode(match.group("data"), validate=True)
    except (ValueError, binascii.Error) as exc:  # type: ignore[attr-defined]
        raise HTTPException(status_code=400, detail="image_data_url is not valid base64.") from exc
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    if len(image_bytes) > MAX_SIMPLE_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded image is too large.")
    return image_bytes, mime_type


app = FastAPI(
    title=MOODTIPS_SERVICE_NAME,
    description="Local FastAPI wrapper around Moodtips recommendations and real menu master data.",
    version="2026.04.04",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/generated", StaticFiles(directory=str(GENERATED_DIR)), name="generated")
app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend-app")


def normalize_profile_memory(memory: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    profile = dict(DEFAULT_PROFILE_BASE)
    profile.update(memory or {})
    profile["liked_categories"] = list(profile.get("liked_categories") or DEFAULT_PROFILE_BASE["liked_categories"])
    profile["disliked_categories"] = list(profile.get("disliked_categories") or [])
    profile["taste_tag_counts"] = dict(profile.get("taste_tag_counts") or {})
    profile["liked_taste_tags"] = list(profile.get("liked_taste_tags") or [])
    profile["preferred_brand_codes"] = list(profile.get("preferred_brand_codes") or [])
    profile["preferred_brand_labels"] = list(profile.get("preferred_brand_labels") or [])
    profile["preferred_temperature"] = str(profile.get("preferred_temperature") or "")
    profile["preferred_temperature_label"] = str(profile.get("preferred_temperature_label") or "")
    profile["recent_avoid_categories"] = list(profile.get("recent_avoid_categories") or [])
    profile["recent_avoid_labels"] = list(profile.get("recent_avoid_labels") or [])
    profile["brand_label_map"] = dict(profile.get("brand_label_map") or {})
    profile["temperature_counts"] = dict(profile.get("temperature_counts") or {})
    profile["brand_counts"] = dict(profile.get("brand_counts") or {})
    profile["avoid_category_counts"] = dict(profile.get("avoid_category_counts") or {})
    profile["_like_counts"] = dict(profile.get("_like_counts") or {})
    profile["_dislike_counts"] = dict(profile.get("_dislike_counts") or {})
    profile["feedback_count"] = int(profile.get("feedback_count") or 0)
    profile["last_feedback"] = dict(profile.get("last_feedback") or {})
    profile["last_accept"] = dict(profile.get("last_accept") or {})
    return profile


def profile_summary_chips(profile: Dict[str, Any]) -> List[str]:
    chips: List[str] = []
    brand_labels = profile.get("preferred_brand_labels") or []
    if brand_labels:
        chips.append("常喝 %s" % " / ".join(brand_labels[:2]))

    liked = profile.get("liked_categories") or []
    if liked:
        chips.append("偏好 %s" % " / ".join(liked[:2]))

    taste_counts = dict(profile.get("taste_tag_counts") or {})
    taste_labels = [
        V2_TASTE_LABELS.get(code, code)
        for code in _sorted_count_keys(taste_counts, limit=2)
    ]
    if taste_labels:
        chips.append("常选口味 %s" % " / ".join(taste_labels))

    sweet_pref = float(profile.get("sweet_pref", DEFAULT_PROFILE_BASE["sweet_pref"]))
    if sweet_pref <= 1.5:
        chips.append("更偏清爽低甜")
    elif sweet_pref >= 3.5:
        chips.append("更偏满足甜感")
    else:
        chips.append("甜感偏平衡")

    caffeine_pref = float(profile.get("caffeine_pref_level", DEFAULT_PROFILE_BASE["caffeine_pref_level"]))
    if caffeine_pref >= 3.5:
        chips.append("能接受更明显提神")
    elif caffeine_pref <= 1:
        chips.append("更偏低咖啡因")

    preferred_temperature_label = str(profile.get("preferred_temperature_label") or "")
    if preferred_temperature_label:
        chips.append("常选 %s" % preferred_temperature_label)
    else:
        usual_temp = str(profile.get("usual_temp") or "")
        if usual_temp == "hot":
            chips.append("最近更偏热饮")
        elif usual_temp == "cold":
            chips.append("最近更偏冷饮")

    recent_avoid = profile.get("recent_avoid_labels") or []
    if recent_avoid:
        chips.append("最近避开 %s" % " / ".join(recent_avoid[:2]))

    return chips[:4]


def merge_explicit_profile_with_memory(explicit_profile: Dict[str, Any], memory: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
    normalized_memory = normalize_profile_memory(memory)
    explicit = dict(explicit_profile or {})
    merged = dict(explicit)
    applied = False

    for field in ["sweet_pref", "caffeine_pref_level"]:
        explicit_value = explicit.get(field)
        default_value = DEFAULT_PROFILE_BASE[field]
        memory_value = normalized_memory.get(field, default_value)
        if explicit_value is None:
            merged[field] = memory_value
            applied = True
        elif float(explicit_value) == float(default_value) and float(memory_value) != float(default_value):
            merged[field] = memory_value
            applied = True

    explicit_temp = str(explicit.get("usual_temp") or "")
    memory_temp = str(normalized_memory.get("usual_temp") or "")
    if not explicit_temp and memory_temp:
        merged["usual_temp"] = memory_temp
        applied = True

    explicit_liked = list(explicit.get("liked_categories") or [])
    memory_liked = list(normalized_memory.get("liked_categories") or [])
    if explicit_liked == DEFAULT_PROFILE_BASE["liked_categories"] and memory_liked != DEFAULT_PROFILE_BASE["liked_categories"]:
        merged["liked_categories"] = memory_liked
        applied = True
    elif not explicit_liked and memory_liked:
        merged["liked_categories"] = memory_liked
        applied = True

    explicit_disliked = list(explicit.get("disliked_categories") or [])
    memory_disliked = list(normalized_memory.get("disliked_categories") or [])
    if not explicit_disliked and memory_disliked:
        merged["disliked_categories"] = memory_disliked
        applied = True

    for field in [
        "preferred_brand_codes",
        "preferred_brand_labels",
        "preferred_temperature",
        "preferred_temperature_label",
        "recent_avoid_categories",
        "recent_avoid_labels",
        "taste_tag_counts",
        "liked_taste_tags",
        "brand_label_map",
        "temperature_counts",
        "brand_counts",
        "avoid_category_counts",
        "last_accept",
    ]:
        memory_value = normalized_memory.get(field)
        explicit_value = explicit.get(field)
        if explicit_value in (None, [], {}, "") and memory_value not in (None, [], {}, ""):
            merged[field] = memory_value
            applied = True

    return merged, applied


def _sorted_count_keys(counts: Dict[str, Any], limit: int = 3) -> List[str]:
    return [
        key
        for key, _ in sorted(
            ((str(key), int(value or 0)) for key, value in counts.items() if int(value or 0) > 0),
            key=lambda item: (-item[1], item[0]),
        )[:limit]
    ]


def _sorted_count_labels(counts: Dict[str, Any], label_map: Dict[str, str], limit: int = 3) -> List[str]:
    labels: List[str] = []
    for code in _sorted_count_keys(counts, limit=limit):
        label = str(label_map.get(code) or code).strip()
        if label and label not in labels:
            labels.append(label)
    return labels


def learn_profile_from_accept(current_memory: Dict[str, Any], accept_record: Dict[str, Any]) -> Dict[str, Any]:
    profile = normalize_profile_memory(current_memory)
    brand_counts = dict(profile.get("brand_counts") or {})
    temperature_counts = dict(profile.get("temperature_counts") or {})
    taste_tag_counts = dict(profile.get("taste_tag_counts") or {})
    brand_label_map = dict(profile.get("brand_label_map") or {})

    brand_code = str(accept_record.get("brand_code") or "").strip()
    brand_name = str(accept_record.get("brand_name") or brand_code).strip()
    temp_pref = str(accept_record.get("temperature_pref") or "").strip()
    preference_tags = [str(tag or "").strip() for tag in accept_record.get("preference_tags") or [] if str(tag or "").strip()]

    if brand_code:
        brand_counts[brand_code] = int(brand_counts.get(brand_code, 0)) + 1
        if brand_name:
            brand_label_map[brand_code] = brand_name

    if temp_pref in {"hot", "cold", "smoothie"}:
        temperature_counts[temp_pref] = int(temperature_counts.get(temp_pref, 0)) + 1
        top_temperature = _sorted_count_keys(temperature_counts, limit=1)
        if top_temperature:
            profile["preferred_temperature"] = top_temperature[0]
            profile["preferred_temperature_label"] = V2_TEMPERATURE_LABELS.get(top_temperature[0], top_temperature[0])

    for tag in preference_tags:
        taste_tag_counts[tag] = int(taste_tag_counts.get(tag, 0)) + 1
    if taste_tag_counts:
        profile["taste_tag_counts"] = taste_tag_counts
        profile["liked_taste_tags"] = _sorted_count_keys(taste_tag_counts, limit=3)

    profile["brand_counts"] = brand_counts
    profile["temperature_counts"] = temperature_counts
    profile["brand_label_map"] = brand_label_map
    profile["preferred_brand_codes"] = _sorted_count_keys(brand_counts, limit=3)
    profile["preferred_brand_labels"] = _sorted_count_labels(brand_counts, brand_label_map, limit=3)
    profile["last_accept"] = {
        "brand_code": brand_code,
        "brand_name": brand_name,
        "temperature_pref": temp_pref,
        "preference_tags": preference_tags,
    }
    return profile


def learn_profile_from_feedback(
    current_memory: Dict[str, Any],
    session_input: Dict[str, Any],
    selected_sku: Dict[str, Any],
    satisfaction_label: str,
    fail_reason: str,
) -> Dict[str, Any]:
    profile = normalize_profile_memory(current_memory)
    like_counts = dict(profile.get("_like_counts") or {})
    dislike_counts = dict(profile.get("_dislike_counts") or {})
    avoid_counts = dict(profile.get("avoid_category_counts") or {})
    category = selected_sku.get("category", "")
    brand_code = str(selected_sku.get("brand_code") or "").strip()
    brand_name = str(selected_sku.get("brand_name") or brand_code).strip()

    if satisfaction_label == "很对":
        like_counts[category] = like_counts.get(category, 0) + 2
        if category in dislike_counts:
            dislike_counts[category] = max(0, dislike_counts[category] - 1)
        profile["sweet_pref"] = round((float(profile["sweet_pref"]) * 3 + float(selected_sku.get("sweetness_intensity", 2))) / 4, 2)
        profile["caffeine_pref_level"] = round((float(profile["caffeine_pref_level"]) * 3 + float(selected_sku.get("caffeine_level", 2))) / 4, 2)
    elif satisfaction_label == "一般":
        like_counts[category] = like_counts.get(category, 0) + 1
    elif satisfaction_label == "踩雷":
        dislike_counts[category] = dislike_counts.get(category, 0) + 2
        if category in like_counts:
            like_counts[category] = max(0, like_counts[category] - 1)

    if fail_reason == "太甜":
        profile["sweet_pref"] = max(1.0, round(float(profile["sweet_pref"]) - 0.7, 2))
    elif fail_reason == "不够提神":
        profile["caffeine_pref_level"] = min(5.0, round(float(profile["caffeine_pref_level"]) + 0.8, 2))
    elif fail_reason == "太腻":
        profile["sweet_pref"] = max(1.0, round(float(profile["sweet_pref"]) - 0.4, 2))
        dislike_counts[category] = dislike_counts.get(category, 0) + 1

    if satisfaction_label == "踩雷" or fail_reason in {"太甜", "不够提神", "太腻"}:
        avoid_counts[category] = avoid_counts.get(category, 0) + 1

    temp_pref = str(session_input.get("temperature_pref") or "")
    if temp_pref in {"hot", "cold"} and satisfaction_label in {"很对", "一般"}:
        profile["usual_temp"] = temp_pref

    sorted_likes = sorted(
        ((key, value) for key, value in like_counts.items() if value > 0),
        key=lambda item: (-item[1], item[0]),
    )
    sorted_dislikes = sorted(
        ((key, value) for key, value in dislike_counts.items() if value > 0),
        key=lambda item: (-item[1], item[0]),
    )

    profile["_like_counts"] = like_counts
    profile["_dislike_counts"] = dislike_counts
    profile["liked_categories"] = [key for key, _ in sorted_likes[:4]]
    profile["disliked_categories"] = [key for key, _ in sorted_dislikes[:4] if key not in profile["liked_categories"]]
    profile["feedback_count"] = int(profile.get("feedback_count", 0)) + 1
    profile["last_feedback"] = {
        "label": satisfaction_label,
        "reason": fail_reason,
        "selected_category": category,
    }
    return profile


def to_engine_payload(payload: RecommendPayload) -> RequestPayload:
    data = payload.model_dump()
    return RequestPayload(
        entry_mode=str(data.get("entry_mode", "quick")),
        goal=str(data.get("goal", "refresh")),
        mood=str(data.get("mood", "none")),
        scene=str(data.get("scene", "")),
        budget_band=str(data.get("budget_band", "high")),
        temperature_pref=str(data.get("temperature_pref", "any")),
        caffeine_pref=str(data.get("caffeine_pref", "allow")),
        dairy_avoid=bool(data.get("dairy_avoid", False)),
        micro_adjusts=list(data.get("micro_adjusts", [])),
        profile=dict(data.get("profile", {})),
        top_k=int(data.get("top_k", 3)),
    )


def get_preset_payload_or_404(preset_name: str) -> RecommendPayload:
    if preset_name not in PRESET_DATA:
        raise HTTPException(status_code=404, detail="Preset '%s' was not found." % preset_name)
    return RecommendPayload.model_validate(PRESET_DATA[preset_name])


def build_effective_payload(payload: RecommendPayload) -> tuple[RecommendPayload, Dict[str, Any], bool]:
    memory_record = STORAGE.get_profile_memory_record(DEFAULT_USER_ID)
    effective_profile, applied = merge_explicit_profile_with_memory(
        payload.profile.model_dump(),
        memory_record["profile"] if memory_record else {},
    )
    effective_payload = payload.model_copy(update={"profile": ProfilePayload.model_validate(effective_profile)})
    return effective_payload, effective_profile, applied


def persist_and_build_response(
    payload: RecommendPayload,
    result: Dict[str, Any],
    effective_profile: Dict[str, Any],
    profile_memory_applied: bool,
) -> RecommendResponse:
    payload_dict = payload.model_dump()
    payload_dict["profile"] = effective_profile
    session_ref = STORAGE.save_recommendation_session(payload_dict, result)
    result["session_id"] = session_ref["session_id"]
    result["created_at"] = session_ref["created_at"]
    result["selected_item"] = None
    result["effective_profile"] = effective_profile
    result["profile_memory_applied"] = profile_memory_applied
    return RecommendResponse.model_validate(result)


def build_live_menu_response(
    payload: RecommendPayload,
    brand_code: Optional[str],
    debug: bool,
) -> MenuRecommendResponse:
    effective_payload, effective_profile, applied = build_effective_payload(payload)
    catalog = STORAGE.get_recommendable_menu_items(brand_code=brand_code, consumer_visible=True)
    if not catalog:
        raise HTTPException(
            status_code=404,
            detail="No consumer-visible menu items were found under the mainland-official source policy.",
        )

    result = evaluate_request(catalog, WEIGHT_MATRIX, to_engine_payload(effective_payload), debug=debug)
    lookup = {item["sku_id"]: item for item in catalog}

    decorated_cards: List[Dict[str, Any]] = []
    for card in result.get("recommendations", []):
        catalog_item = lookup.get(card["sku_id"], {})
        decorated_cards.append(
            {
                **card,
                "brand_code": catalog_item.get("brand_code", ""),
                "brand_name": catalog_item.get("brand_name", ""),
                "brand_name_local": catalog_item.get("brand_name_local"),
                "display_name": catalog_item.get("display_name", card.get("sku_name", "")),
                "sku_name_local": catalog_item.get("sku_name_local"),
                "image_url": catalog_item.get("image_url"),
                "channel_name": catalog_item.get("channel_name"),
                "source_type": catalog_item.get("source_type"),
                "source_status": catalog_item.get("source_status"),
                "source_name": catalog_item.get("source_name"),
                "store_name": catalog_item.get("store_name"),
                "currency_code": catalog_item.get("currency_code", DEFAULT_MARKET_CONTEXT["default_currency_code"]),
                "original_category": catalog_item.get("category_name"),
                "option_group_count": int(catalog_item.get("option_group_count", 0)),
                "option_summary": list(catalog_item.get("option_summary") or []),
                "profile_tags": list(catalog_item.get("profile_tags") or []),
                "price_context": dict(catalog_item.get("price_context") or {}),
            }
        )

    return MenuRecommendResponse.model_validate(
        {
            "catalog_scope": brand_code or "all",
            "catalog_count": len(catalog),
            "session_input": result.get("session_input", {}),
            "effective_profile": effective_profile,
            "profile_memory_applied": applied,
            "meta": result.get("meta", {}),
            "followup_question": result.get("followup_question"),
            "recommendations": decorated_cards,
            "filtered_out": result.get("filtered_out", []),
        }
    )


def menu_overview_snapshot() -> Dict[str, Any]:
    return STORAGE.get_menu_overview(consumer_visible=True)


def format_month_label(month: str) -> str:
    try:
        year_str, month_str = month.split("-", 1)
        return f"{int(year_str)} 年 {int(month_str)} 月"
    except (TypeError, ValueError):
        return month


def build_accept_recap_response(month: str, recap: Dict[str, Any]) -> Dict[str, Any]:
    record_count = int(recap.get("record_count", 0))
    mood_counts: List[Dict[str, Any]] = []
    for item in recap.get("mood_counts", []):
        mood_code = str(item.get("mood_code") or "")
        meta = V2_MOOD_META.get(mood_code, HEKOU_MOOD_META.get(mood_code, {}))
        mood_counts.append(
            {
                **item,
                "mood_label": item.get("mood_label") or meta.get("label"),
                "color": meta.get("color"),
                "recap_line": meta.get("recap_line"),
            }
        )

    preference_counts: List[Dict[str, Any]] = []
    for item in recap.get("preference_counts", []):
        tag_code = str(item.get("tag_code") or "")
        preference_counts.append(
            {
                **item,
                "tag_label": HEKOU_PREFERENCE_LABELS.get(tag_code, tag_code),
            }
        )

    month_label = format_month_label(month)
    if not record_count:
        headline = f"{month_label}信号待机中"
        summary_lines = [
            "等你第一次点下“就喝它了”，这里就会出现脑内天气。",
            "它只记录你的选择路线，不给你下诊断。",
            "先喝一口，再决定。",
        ]
    else:
        top_mood = mood_counts[0] if mood_counts else {}
        top_preferences = [item["tag_label"] for item in preference_counts[:2] if item.get("tag_label")]
        headline = (
            f"{top_mood.get('mood_label', '这个状态')}，是你这个月的高频天气。"
            if top_mood
            else "这个月，你常常带着脑内天气来找我。"
        )
        summary_lines = [
            str(top_mood.get("recap_line") or "你最近更常在需要一条饮品提示时打开 Moodtips。"),
            f"你更偏爱{'、'.join(top_preferences)}这种答案。" if top_preferences else "你通常更愿意接受简单、低负担的一杯。",
            f"这个月你已经记下了 {record_count} 次“就喝它了”。",
        ]

    return {
        "user_id": recap.get("user_id", DEFAULT_USER_ID),
        "month": month,
        "record_count": record_count,
        "headline": headline,
        "summary_lines": summary_lines,
        "mood_counts": mood_counts,
        "preference_counts": preference_counts,
        "recent_accepts": recap.get("recent_accepts", []),
    }


def build_service_meta() -> Dict[str, Any]:
    overview = menu_overview_snapshot()
    return {
        "service": MOODTIPS_SERVICE_NAME,
        "app": "/app/",
        "docs": "/docs",
        "health": "/health",
        "preset_count": len(PRESET_DATA),
        "sku_count": len(SKU_CATALOG),
        "menu_brand_count": overview["brand_count"],
        "menu_item_count": overview["item_count"],
        **DEFAULT_MARKET_CONTEXT,
        "db_path": str(STORAGE.db_path),
    }


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/app/", status_code=307)


@app.get("/api/meta", tags=["meta"])
def service_meta() -> Dict[str, Any]:
    return build_service_meta()


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    overview = menu_overview_snapshot()
    return HealthResponse(
        status="ok",
        service=MOODTIPS_SERVICE_NAME,
        sku_count=len(SKU_CATALOG),
        preset_count=len(PRESET_DATA),
        menu_brand_count=overview["brand_count"],
        menu_item_count=overview["item_count"],
        market_name=DEFAULT_MARKET_CONTEXT["market_name"],
        default_locale=DEFAULT_MARKET_CONTEXT["default_locale"],
        default_currency_code=DEFAULT_MARKET_CONTEXT["default_currency_code"],
        default_ip_country_code=DEFAULT_MARKET_CONTEXT["default_ip_country_code"],
        default_city=DEFAULT_MARKET_CONTEXT["default_city"],
        db_path=str(STORAGE.db_path),
    )


@app.get("/api/presets", response_model=PresetListResponse, tags=["presets"])
def list_presets() -> PresetListResponse:
    presets = [
        PresetSummary(
            preset_name=name,
            goal=str(payload.get("goal", "")),
            mood=str(payload.get("mood", "")),
            scene=str(payload.get("scene", "")),
            budget_band=str(payload.get("budget_band", "")),
            temperature_pref=str(payload.get("temperature_pref", "")),
        )
        for name, payload in PRESET_DATA.items()
    ]
    return PresetListResponse(count=len(presets), presets=presets)


@app.get("/api/presets/{preset_name}", response_model=PresetDetailResponse, tags=["presets"])
def get_preset(preset_name: str) -> PresetDetailResponse:
    payload = get_preset_payload_or_404(preset_name)
    return PresetDetailResponse(preset_name=preset_name, payload=payload)


@app.post("/api/recommend", response_model=RecommendResponse, tags=["recommend"])
def recommend(payload: RecommendPayload, debug: bool = Query(False)) -> RecommendResponse:
    effective_payload, effective_profile, applied = build_effective_payload(payload)
    result = evaluate_request(SKU_CATALOG, WEIGHT_MATRIX, to_engine_payload(effective_payload), debug=debug)
    return persist_and_build_response(effective_payload, result, effective_profile, applied)


@app.post("/api/recommend/preset/{preset_name}", response_model=RecommendResponse, tags=["recommend"])
def recommend_from_preset(
    preset_name: str,
    debug: bool = Query(False),
) -> RecommendResponse:
    payload = get_preset_payload_or_404(preset_name)
    effective_payload, effective_profile, applied = build_effective_payload(payload)
    result = evaluate_request(SKU_CATALOG, WEIGHT_MATRIX, to_engine_payload(effective_payload), debug=debug)
    return persist_and_build_response(effective_payload, result, effective_profile, applied)


@app.get("/api/menu/overview", tags=["menu"])
def get_menu_overview() -> Dict[str, Any]:
    return menu_overview_snapshot()


@app.get("/api/menu/source-standard", tags=["menu"])
def get_menu_source_standard() -> Dict[str, Any]:
    return MENU_SOURCE_STANDARD


@app.get("/api/menu/brands", tags=["menu"])
def get_menu_brands() -> Dict[str, Any]:
    brands = STORAGE.list_menu_brands(consumer_visible=True)
    return {"count": len(brands), "items": brands}


@app.get("/api/menu/brands/{brand_code}", tags=["menu"])
def get_menu_brand_detail(brand_code: str) -> Dict[str, Any]:
    detail = STORAGE.get_brand_detail(brand_code, consumer_visible=True)
    if detail is None:
        raise HTTPException(status_code=404, detail="Brand '%s' was not found." % brand_code)
    return detail


@app.get("/api/menu/items", tags=["menu"])
def get_menu_items(
    brand_code: Optional[str] = Query(None),
    q: str = Query("", alias="query"),
    limit: int = Query(24, ge=1, le=120),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    return STORAGE.search_menu_items(
        brand_code=brand_code,
        search=q,
        limit=limit,
        offset=offset,
        consumer_visible=True,
    )


@app.get("/api/menu/brands/{brand_code}/items", tags=["menu"])
def get_menu_brand_items(
    brand_code: str,
    q: str = Query("", alias="query"),
    limit: int = Query(24, ge=1, le=120),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    detail = STORAGE.get_brand_detail(brand_code, consumer_visible=True)
    if detail is None:
        raise HTTPException(status_code=404, detail="Brand '%s' was not found." % brand_code)
    return STORAGE.search_menu_items(
        brand_code=brand_code,
        search=q,
        limit=limit,
        offset=offset,
        consumer_visible=True,
    )


@app.get("/api/menu/items/{item_id}", tags=["menu"])
def get_menu_item(item_id: str) -> Dict[str, Any]:
    detail = STORAGE.get_menu_item_detail(item_id, consumer_visible=True)
    if detail is None:
        raise HTTPException(status_code=404, detail="Menu item '%s' was not found." % item_id)
    return detail


@app.get("/api/ops/menu-items/{item_id}", tags=["ops"])
def get_ops_menu_item(item_id: str) -> Dict[str, Any]:
    detail = STORAGE.get_menu_item_detail(item_id, consumer_visible=False)
    if detail is None:
        raise HTTPException(status_code=404, detail="Menu item '%s' was not found." % item_id)
    return detail


@app.get("/api/ops/menu-governance", tags=["ops"])
def get_menu_governance_dashboard(
    brand_code: Optional[str] = Query(None),
    review_limit: int = Query(12, ge=3, le=60),
    tag_limit: int = Query(10, ge=3, le=24),
) -> Dict[str, Any]:
    if brand_code:
        detail = STORAGE.get_brand_detail(brand_code)
        if detail is None:
            raise HTTPException(status_code=404, detail="Brand '%s' was not found." % brand_code)
    return STORAGE.get_menu_governance_dashboard(
        brand_code=brand_code,
        review_limit=review_limit,
        tag_limit=tag_limit,
    )


@app.post("/api/menu/recommend", response_model=MenuRecommendResponse, tags=["menu"])
def recommend_live_menu(
    payload: RecommendPayload,
    brand_code: Optional[str] = Query(None),
    debug: bool = Query(False),
) -> MenuRecommendResponse:
    if brand_code:
        detail = STORAGE.get_brand_detail(brand_code, consumer_visible=True)
        if detail is None:
            raise HTTPException(status_code=404, detail="Brand '%s' was not found." % brand_code)
    return build_live_menu_response(payload, brand_code=brand_code, debug=debug)


@app.post("/api/sessions/{session_id}/select", response_model=SelectionResponse, tags=["sessions"])
def select_recommendation(session_id: str, payload: SelectionPayload) -> SelectionResponse:
    selection = STORAGE.set_selected_sku(session_id, payload.sku_id, payload.sku_name)
    if selection is None:
        raise HTTPException(status_code=404, detail="Session '%s' was not found." % session_id)
    return SelectionResponse(
        session_id=session_id,
        selected_item=SelectedItem(
            sku_id=selection["selected_sku_id"],
            sku_name=selection["selected_sku_name"],
            selected_at=selection["selected_at"],
        ),
    )


@app.post("/api/accept-records", response_model=AcceptRecordResponse, tags=["accept"])
def create_accept_record(payload: AcceptRecordPayload) -> AcceptRecordResponse:
    normalized = payload.model_dump()
    normalized["mood_code"] = canonical_mood_code(str(normalized.get("mood_code") or ""))
    if not normalized.get("mood_label"):
        normalized["mood_label"] = V2_MOOD_META.get(normalized["mood_code"], {}).get("label")
    record = STORAGE.save_accept_record(DEFAULT_USER_ID, normalized)
    current_memory = STORAGE.get_profile_memory(DEFAULT_USER_ID)
    updated_memory = learn_profile_from_accept(current_memory, record)
    STORAGE.save_profile_memory(DEFAULT_USER_ID, updated_memory)
    return AcceptRecordResponse.model_validate(record)


@app.get("/api/accept-records", response_model=AcceptRecordListResponse, tags=["accept"])
def list_accept_records(limit: int = Query(300, ge=1, le=1000)) -> AcceptRecordListResponse:
    items = [canonicalize_accept_record(item) for item in STORAGE.list_accept_records(DEFAULT_USER_ID, limit=limit)]
    return AcceptRecordListResponse.model_validate({"count": len(items), "items": items})


@app.get("/api/accept-records/calendar", response_model=AcceptCalendarResponse, tags=["accept"])
def get_accept_calendar(month: str = Query(..., min_length=7, max_length=7)) -> AcceptCalendarResponse:
    items = [canonicalize_accept_record(item) for item in STORAGE.get_accept_records_for_month(DEFAULT_USER_ID, month=month)]
    return AcceptCalendarResponse.model_validate(
        {
            "user_id": DEFAULT_USER_ID,
            "month": month,
            "count": len(items),
            "items": items,
        }
    )


@app.get("/api/accept-records/recap", response_model=AcceptRecapResponse, tags=["accept"])
def get_accept_recap(month: str = Query(..., min_length=7, max_length=7), recent_limit: int = Query(6, ge=1, le=24)) -> AcceptRecapResponse:
    recap = STORAGE.get_accept_recap(DEFAULT_USER_ID, month=month, recent_limit=recent_limit)
    return AcceptRecapResponse.model_validate(build_accept_recap_response(month, recap))


@app.post("/api/sessions/{session_id}/feedback", response_model=FeedbackResponse, tags=["sessions"])
def submit_feedback(session_id: str, payload: FeedbackPayload) -> FeedbackResponse:
    feedback = STORAGE.save_feedback(
        session_id=session_id,
        satisfaction_label=payload.satisfaction_label,
        fail_reason=payload.fail_reason,
        note=payload.note,
        selected_sku_id=payload.selected_sku_id,
        selected_sku_name=payload.selected_sku_name,
    )
    if feedback is None:
        raise HTTPException(status_code=404, detail="Session '%s' was not found." % session_id)

    session_detail = STORAGE.get_session_detail(session_id)
    profile_memory: Dict[str, Any] = {}
    if session_detail is not None:
        selected_sku_id = payload.selected_sku_id or (session_detail.get("selected_item") or {}).get("sku_id")
        selected_sku = SKU_BY_ID.get(selected_sku_id) if selected_sku_id else None
        if selected_sku is not None:
            current_memory = STORAGE.get_profile_memory(DEFAULT_USER_ID)
            profile_memory = learn_profile_from_feedback(
                current_memory=current_memory,
                session_input=session_detail.get("session_input", {}),
                selected_sku=selected_sku,
                satisfaction_label=payload.satisfaction_label,
                fail_reason=payload.fail_reason,
            )
            STORAGE.save_profile_memory(DEFAULT_USER_ID, profile_memory)

    return FeedbackResponse(
        feedback_id=feedback["feedback_id"],
        session_id=session_id,
        satisfaction_label=feedback["satisfaction_label"],
        fail_reason=feedback.get("fail_reason", ""),
        note=feedback.get("note", ""),
        selected_item=SelectedItem(
            sku_id=feedback["selected_sku_id"],
            sku_name=feedback["selected_sku_name"],
        )
        if feedback.get("selected_sku_id")
        else None,
        created_at=feedback["created_at"],
        profile_memory=profile_memory,
        profile_summary=profile_summary_chips(profile_memory) if profile_memory else [],
    )


@app.get("/api/history", response_model=HistoryListResponse, tags=["history"])
def get_history(limit: int = Query(12, ge=1, le=100)) -> HistoryListResponse:
    items = STORAGE.get_history(limit=limit)
    return HistoryListResponse.model_validate({"count": len(items), "items": items})


@app.get("/api/history/{session_id}", tags=["history"])
def get_history_detail(session_id: str) -> Dict[str, Any]:
    detail = STORAGE.get_session_detail(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session '%s' was not found." % session_id)
    return detail


@app.get("/api/profile-memory", response_model=ProfileMemoryResponse, tags=["profile"])
def get_profile_memory() -> ProfileMemoryResponse:
    record = STORAGE.get_profile_memory_record(DEFAULT_USER_ID)
    if not record:
        return ProfileMemoryResponse(
            user_id=DEFAULT_USER_ID,
            updated_at=None,
            profile={},
            summary_chips=[],
        )
    profile = normalize_profile_memory(record["profile"])
    return ProfileMemoryResponse(
        user_id=DEFAULT_USER_ID,
        updated_at=record["updated_at"],
        profile=profile,
        summary_chips=profile_summary_chips(profile),
    )


def format_month_label(month: str) -> str:
    try:
        year_str, month_str = month.split("-", 1)
        return f"{int(year_str)}年{int(month_str)}月"
    except (TypeError, ValueError):
        return month


def canonical_mood_code(mood_code: str) -> str:
    raw_mood_code = str(mood_code or "").strip()
    if raw_mood_code in V2_MOOD_META:
        return raw_mood_code
    return V2_FRONTEND_MOOD_TO_CANONICAL.get(raw_mood_code, "cooldown")


def canonicalize_mood_counts(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for item in items:
        canonical_code = canonical_mood_code(str(item.get("mood_code") or ""))
        meta = V2_MOOD_META.get(canonical_code, {})
        if canonical_code not in merged:
            merged[canonical_code] = {
                "mood_code": canonical_code,
                "mood_label": meta.get("label"),
                "count": 0,
                "color": meta.get("color"),
                "recap_line": meta.get("recap_line"),
            }
        merged[canonical_code]["count"] += int(item.get("count", 0) or 0)
    return sorted(
        merged.values(),
        key=lambda item: (-int(item.get("count", 0)), str(item.get("mood_code") or "")),
    )


def canonicalize_accept_record(record: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(record)
    mood_code = canonical_mood_code(str(normalized.get("mood_code") or ""))
    normalized["mood_code"] = mood_code
    normalized["mood_label"] = V2_MOOD_META.get(mood_code, {}).get("label")
    return normalized


def normalize_copy_text(text: str, max_len: int) -> str:
    cleaned = " ".join(str(text or "").replace("\n", " ").split())
    return cleaned[:max_len].strip()


def contains_blocked_phrase(text: str, blocked_phrases: tuple[str, ...]) -> bool:
    lowered = str(text or "").lower()
    return any(phrase.lower() in lowered for phrase in blocked_phrases)


def candidate_descriptor(candidate: Dict[str, Any]) -> str:
    tags = list(candidate.get("tags") or [])
    preferred_tags = [tag for tag in tags if tag not in {"冷饮", "热饮", "冰沙", "正常咖啡因"}]
    selected = preferred_tags[:2] or tags[:2]
    if selected:
        return "、".join(selected)
    serving_note = str(candidate.get("default_serving_note") or "").strip()
    if serving_note and serving_note != "按门店默认做法":
        return serving_note.replace(" / ", "、")
    return "按默认做法"


def is_valid_reason_copy(text: str) -> bool:
    return bool(text) and 8 <= len(text) <= 40 and not contains_blocked_phrase(text, COPY_BLOCKLIST)


def is_valid_encouragement_copy(text: str) -> bool:
    return bool(text) and 4 <= len(text) <= 18 and not contains_blocked_phrase(text, COPY_BLOCKLIST)


def normalize_reason_copy(mood_code: str, candidate: Dict[str, Any], text: str) -> str:
    cleaned = normalize_copy_text(text, 40)
    return cleaned if is_valid_reason_copy(cleaned) else fallback_recommendation_reason(mood_code, candidate)


def normalize_encouragement_copy(mood_code: str, text: str) -> str:
    cleaned = normalize_copy_text(text, 18)
    return cleaned if is_valid_encouragement_copy(cleaned) else fallback_recommendation_encouragement(mood_code)


def normalize_monthly_summary(month: str, stats: Dict[str, Any], payload: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    if not payload:
        return None
    summary_title = normalize_copy_text(payload.get("summary_title", ""), 16)
    summary_text = normalize_copy_text(payload.get("summary_text", ""), 80)
    gentle_tip = normalize_copy_text(payload.get("gentle_tip", ""), 24)
    if not summary_title or not summary_text or not gentle_tip:
        return None
    if contains_blocked_phrase(summary_title, MONTHLY_COPY_BLOCKLIST):
        return None
    if contains_blocked_phrase(summary_text, MONTHLY_COPY_BLOCKLIST):
        return None
    if contains_blocked_phrase(gentle_tip, MONTHLY_COPY_BLOCKLIST):
        return None
    return {
        "summary_title": summary_title,
        "summary_text": summary_text,
        "gentle_tip": gentle_tip,
    }


def fallback_recommendation_reason(mood_code: str, candidate: Dict[str, Any]) -> str:
    descriptor = candidate_descriptor(candidate)
    templates = {
        "spark": "想提速的时候，这杯%s会把选择变得更直接。" % descriptor,
        "ease": "想松一点的时候，这杯%s适合顺手带走。" % descriptor,
        "cooldown": "脑内有点吵的时候，这杯%s能让选择轻一点。" % descriptor,
        "recharge": "电量偏低的时候，这杯%s适合慢慢补回来。" % descriptor,
    }
    return templates.get(mood_code, "先给自己一杯%s的，再决定下一步。" % descriptor)


def fallback_recommendation_encouragement(mood_code: str) -> str:
    lines = {
        "spark": "让高亮继续在线。",
        "ease": "把这点松弛留住。",
        "cooldown": "先把噪声调低。",
        "recharge": "慢慢补电就好。",
    }
    return lines.get(mood_code, "先喝一口，再决定。")


def fallback_monthly_copy(month: str, stats: Dict[str, Any]) -> Dict[str, str]:
    month_label = format_month_label(month)
    record_count = int(stats.get("record_count", 0))
    top_moods = stats.get("top_moods", []) or []
    top_preferences = stats.get("top_preferences", []) or []
    favorite_brand = stats.get("favorite_brand") or {}
    streak_days = int(stats.get("longest_streak_days", 0))
    if record_count <= 0:
        return {
            "summary_title": f"{month_label}信号待机中",
            "summary_text": "等你选下第一杯，这里就会慢慢记录脑内天气和口味信号。",
            "gentle_tip": "先点亮今天第一条提示。",
        }

    mood_label = str((top_moods[0] or {}).get("mood_label") or "这段时间")
    preference_text = "、".join(
        item.get("tag_label", "")
        for item in top_preferences[:2]
        if item.get("tag_label")
    )
    brand_name = str(favorite_brand.get("brand_name") or "")
    if preference_text and brand_name:
        summary_text = (
            f"{month_label}你一共记下了 {record_count} 次“就喝它了”。"
            f"最常出现的是{mood_label}，最近也更常选{preference_text}，"
            f"其中{brand_name}出现得最多。"
        )
    elif preference_text:
        summary_text = (
            f"{month_label}你一共记下了 {record_count} 次“就喝它了”。"
            f"最常出现的是{mood_label}，最近也更常选{preference_text}这一类。"
        )
    else:
        summary_text = f"{month_label}你一共记下了 {record_count} 次“就喝它了”，最常出现的是{mood_label}。"

    if streak_days >= 3:
        gentle_tip = f"你已经连续记了 {streak_days} 天，信号正在变清楚。"
    else:
        gentle_tip = "表达不精确也没关系，选择会自己留下线索。"

    return {
        "summary_title": f"{mood_label}，本月高频天气",
        "summary_text": summary_text,
        "gentle_tip": gentle_tip,
    }


def build_accept_recap_response(month: str, recap: Dict[str, Any]) -> Dict[str, Any]:
    record_count = int(recap.get("record_count", 0))
    mood_counts = canonicalize_mood_counts(list(recap.get("mood_counts", []) or []))

    preference_counts: List[Dict[str, Any]] = []
    for item in recap.get("preference_counts", []):
        tag_code = str(item.get("tag_code") or "")
        preference_counts.append(
            {
                **item,
                "tag_label": V2_TASTE_LABELS.get(tag_code, HEKOU_PREFERENCE_LABELS.get(tag_code, tag_code)),
            }
        )

    brand_counts = list(recap.get("brand_counts", []) or [])
    stats = {
        "record_count": record_count,
        "top_moods": mood_counts[:3],
        "top_preferences": preference_counts[:3],
        "favorite_brand": brand_counts[0] if brand_counts else None,
        "longest_streak_days": int(recap.get("longest_streak_days", 0) or 0),
    }
    ai_summary = normalize_monthly_summary(month=month, stats=stats, payload=AI_CLIENT.summarize_month(month=month, stats=stats))
    summary_copy = ai_summary or fallback_monthly_copy(month=month, stats=stats)
    summary_title = str(summary_copy.get("summary_title") or "")
    summary_text = str(summary_copy.get("summary_text") or "")
    gentle_tip = str(summary_copy.get("gentle_tip") or "")

    return {
        "user_id": recap.get("user_id", DEFAULT_USER_ID),
        "month": month,
        "record_count": record_count,
        "headline": summary_title or format_month_label(month),
        "summary_lines": [line for line in [summary_text, gentle_tip] if line],
        "summary_title": summary_title,
        "summary_text": summary_text,
        "gentle_tip": gentle_tip,
        "stats": stats,
        "mood_counts": mood_counts,
        "preference_counts": preference_counts,
        "brand_counts": brand_counts,
        "longest_streak_days": int(recap.get("longest_streak_days", 0) or 0),
        "recent_accepts": [canonicalize_accept_record(item) for item in recap.get("recent_accepts", [])],
    }


def normalize_simple_request(payload: SimpleRecommendRequest) -> Dict[str, Any]:
    price_band = payload.price_band if payload.price_band in V2_PRICE_LABELS else "any"
    temperature_pref = payload.temperature_pref if payload.temperature_pref in V2_TEMPERATURE_LABELS else "any"
    caffeine_pref = payload.caffeine_pref if payload.caffeine_pref in V2_CAFFEINE_LABELS else "any"
    raw_mood_code = str(payload.mood_code or "").strip()
    mood_code = canonical_mood_code(raw_mood_code)
    taste_tags: List[str] = []
    for tag in payload.taste_tags:
        if tag in V2_TASTE_TAG_CODES and tag not in taste_tags:
            taste_tags.append(tag)
    return {
        "mood_code": mood_code,
        "frontend_mood_code": raw_mood_code,
        "price_band": price_band,
        "temperature_pref": temperature_pref,
        "caffeine_pref": caffeine_pref,
        "taste_tags": taste_tags[:3],
        "retry_seed": int(payload.retry_seed or 0),
        "exclude_brand_code": str(payload.exclude_brand_code or "").strip(),
    }


def simple_item_taste_codes(item: Dict[str, Any]) -> List[str]:
    raw_tags = [str(tag or "").strip() for tag in item.get("tags") or [] if str(tag or "").strip()]
    text_bits = [
        str(item.get("item_name") or ""),
        str(item.get("description") or ""),
        str(item.get("normalized_category") or ""),
        str(item.get("default_serving_note") or ""),
        " ".join(raw_tags),
    ]
    text = " ".join(bit.strip() for bit in text_bits if str(bit or "").strip()).lower()
    codes: List[str] = []
    for tag in raw_tags:
        code = SIMPLE_TASTE_LABEL_TO_CODE.get(tag, "")
        if code and code not in codes:
            codes.append(code)
        if tag in V2_TASTE_LABELS and tag not in codes:
            codes.append(tag)
    for code, keywords in SIMPLE_TASTE_KEYWORDS.items():
        if code in codes:
            continue
        if any(keyword.lower() in text for keyword in keywords):
            codes.append(code)
    return codes


def simple_response_tags(item: Dict[str, Any], request_data: Dict[str, Any]) -> List[str]:
    base_tags = [str(tag or "").strip() for tag in item.get("tags") or [] if str(tag or "").strip()]
    item_taste_codes = simple_item_taste_codes(item)
    requested_codes = [str(code or "").strip() for code in request_data.get("taste_tags") or [] if str(code or "").strip()]
    matched_taste_tags = [
        V2_TASTE_LABELS.get(code, code)
        for code in requested_codes
        if code in item_taste_codes
    ]
    tags: List[str] = []
    for tag in [*matched_taste_tags, *base_tags]:
        if tag and tag not in tags:
            tags.append(tag)
    return tags[:4]


def simple_image_trust_profile(item: Dict[str, Any]) -> Dict[str, str]:
    source_type = str(item.get("image_source_type") or "source").strip() or "source"
    label = SIMPLE_IMAGE_TRUST_LABELS.get(source_type, "官方原图" if item.get("source_url") else "待核图")
    level_map = {
        "source": "high",
        "user_uploaded": "high",
        "brand_logo": "medium",
        "brand_collage": "medium",
        "brand_fallback": "medium",
        "ai_illustration": "low",
    }
    detail_map = {
        "source": "来自官方原始菜单或官方页面链接。",
        "user_uploaded": "你后续上传的图片会优先覆盖原图。",
        "brand_logo": "原图不稳时先用品牌官方 Logo 占位。",
        "brand_collage": "来自品牌官方合拍或官方组合图。",
        "brand_fallback": "官方图缺失时先用品牌备图。",
        "ai_illustration": "这是 AI 示意图，适合过渡展示。",
    }
    return {
        "source_type": source_type,
        "label": label,
        "level": level_map.get(source_type, "medium"),
        "detail": detail_map.get(source_type, "优先待人工核图。"),
    }


def build_simple_explanation_sections(
    request_data: Dict[str, Any],
    item: Dict[str, Any],
    profile_memory: Dict[str, Any],
    profile_summary: List[str],
    taste_constraint_relaxed: bool,
    recent_avoid_relaxed: bool,
) -> List[Dict[str, str]]:
    mood_code = str(request_data.get("mood_code") or "")
    mood_label = V2_MOOD_META.get(mood_code, {}).get("label", mood_code)
    item_mood_code = str(item.get("mood_tag_code") or "")
    item_mood_label = V2_MOOD_META.get(item_mood_code, {}).get("label", item_mood_code or "未标记")
    requested_taste_labels = [V2_TASTE_LABELS.get(code, code) for code in request_data.get("taste_tags") or []]
    item_taste_codes = simple_item_taste_codes(item)
    matched_taste_labels = [
        V2_TASTE_LABELS.get(code, code)
        for code in request_data.get("taste_tags") or []
        if code in item_taste_codes
    ]
    profile_summary = list(profile_summary or [])
    lifecycle_code = str(item.get("lifecycle_code") or "permanent")
    lifecycle_label = str(item.get("lifecycle_label") or SIMPLE_LIFECYCLE_LABELS.get(lifecycle_code, "常驻"))
    image_trust = simple_image_trust_profile(item)
    temperature_type = str(item.get("temperature_type") or "")
    serving_note = str(item.get("default_serving_note") or "").strip()
    price_text = f'{float(item.get("base_price_cny", 0.0)):.0f}元'

    mood_text = f'你选的是「{mood_label}」，这杯标成「{item_mood_label}」，先把节奏往同一边拢。'
    if item_mood_code and item_mood_code != mood_code:
        mood_text = f'你选的是「{mood_label}」，这杯更靠近「{item_mood_label}」，作为同类情绪里的稳妥选项。'

    if matched_taste_labels:
        taste_text = f'口味命中「{" / ".join(matched_taste_labels)}」，没有把茶感硬塞进来。'
    elif requested_taste_labels:
        taste_text = f'本次没有完全命中「{" / ".join(requested_taste_labels)}」，先按相近口味做了放宽。'
    else:
        taste_text = f'当前没有额外口味筛选，系统主要看这杯本身的口感结构。'

    constraint_bits = [price_text]
    if serving_note:
        constraint_bits.append(serving_note)
    if lifecycle_label:
        constraint_bits.append(lifecycle_label)
    if profile_summary:
        constraint_bits.append(" / ".join(profile_summary[:2]))
    if recent_avoid_relaxed:
        constraint_bits.append("最近避开的品类已放宽")
    elif profile_memory.get("recent_avoid_labels"):
        constraint_bits.append("先绕开了近期常避的品类")
    if taste_constraint_relaxed:
        constraint_bits.append("口味筛选临时放宽")
    constraint_text = "；".join(bit for bit in constraint_bits if bit)
    if temperature_type:
        constraint_text = f"{constraint_text}；温度是 {V2_TEMPERATURE_LABELS.get(temperature_type, temperature_type)}"

    image_text = f'{image_trust["label"]}，{image_trust["detail"]}'
    if image_trust["level"] == "high":
        image_text += " 可信度高。"
    elif image_trust["level"] == "low":
        image_text += " 建议后续优先核图。"
    else:
        image_text += " 适合先看后核。"

    return [
        {"code": "mood", "title": "情绪匹配", "text": mood_text},
        {"code": "taste", "title": "口味匹配", "text": taste_text},
        {"code": "constraint", "title": "约束匹配", "text": constraint_text},
        {"code": "image", "title": "图片来源可信度", "text": image_text},
    ]


def price_matches(value: float, price_band: str) -> bool:
    if price_band == "under_15":
        return value <= 15.0
    if price_band == "15_20":
        return 15.0 <= value <= 20.0
    if price_band == "above_20":
        return value > 20.0
    return True


def temperature_matches(item: Dict[str, Any], pref: str) -> bool:
    item_type = str(item.get("temperature_type") or "cold")
    if pref == "hot":
        return item_type in {"hot", "multi"}
    if pref == "cold":
        return item_type in {"cold", "multi"}
    if pref == "smoothie":
        return item_type == "smoothie"
    return True


def caffeine_matches(item: Dict[str, Any], pref: str) -> bool:
    level = str(item.get("caffeine_level_code") or "none")
    allowed_map = {
        "none": {"none"},
        "low": {"none", "low"},
        "normal": {"low", "normal"},
        "strong": {"strong"},
        "any": {"none", "low", "normal", "strong"},
    }
    return level in allowed_map.get(pref, allowed_map["any"])


def score_simple_candidate(
    item: Dict[str, Any],
    request_data: Dict[str, Any],
    recent_brands: List[str],
    profile_memory: Dict[str, Any],
) -> Dict[str, Any]:
    requested_codes = list(request_data["taste_tags"] or [])
    item_taste_codes = simple_item_taste_codes(item)
    taste_overlap = len(set(requested_codes) & set(item_taste_codes))
    serving_note = str(item.get("default_serving_note") or "")
    serving_match = 0
    temperature_type = str(item.get("temperature_type") or "")
    if request_data["temperature_pref"] == "cold" and temperature_type in {"cold", "multi"}:
        serving_match += 1
    elif request_data["temperature_pref"] == "hot" and temperature_type in {"hot", "multi"}:
        serving_match += 1
    elif request_data["temperature_pref"] == "smoothie" and temperature_type == "smoothie":
        serving_match += 1
    if "sugar_free_friendly" in requested_codes and any(token in serving_note for token in ["??", "??", "0?"]):
        serving_match += 1

    brand_code = str(item.get("brand_code") or "")
    brand_bonus = float(TARGET_BRAND_BONUS.get(brand_code, 0.0))
    preferred_brand_codes = list(profile_memory.get("preferred_brand_codes") or [])
    if brand_code in preferred_brand_codes:
        brand_bonus += max(0.04, 0.12 - 0.03 * preferred_brand_codes.index(brand_code))

    preferred_temperature = str(profile_memory.get("preferred_temperature") or "")
    temperature_bonus = 0.08 if preferred_temperature and temperature_type == preferred_temperature else 0.0

    taste_memory_bonus = 0.0
    liked_taste_tags = list(profile_memory.get("liked_taste_tags") or [])
    if liked_taste_tags and set(liked_taste_tags) & set(item_taste_codes):
        taste_memory_bonus = 0.05

    recent_avoid_categories = {
        str(value or "").strip()
        for value in profile_memory.get("recent_avoid_categories") or []
        if str(value or "").strip()
    }
    current_category = str(item.get("normalized_category") or "").strip()
    recent_avoid_penalty = 0.45 if current_category and current_category in recent_avoid_categories else 0.0

    disliked_categories = {
        str(value or "").strip()
        for value in profile_memory.get("disliked_categories") or []
        if str(value or "").strip()
    }
    disliked_penalty = 0.18 if current_category and current_category in disliked_categories else 0.0
    recent_brand_penalty = 0.05 if brand_code in recent_brands else 0.0

    mood_match = 1 if str(item.get("mood_tag_code") or "") == request_data["mood_code"] else 0
    lifecycle_code = str(item.get("lifecycle_code") or "permanent")
    launch_date = str(item.get("launch_date") or "").strip()
    lifecycle_bonus = 0.0
    if lifecycle_code in {"seasonal", "limited"}:
        lifecycle_bonus += 0.04
    if launch_date:
        try:
            launch_dt = datetime.fromisoformat(launch_date).date()
            age_days = max((datetime.now().date() - launch_dt).days, 0)
            if age_days <= 90:
                lifecycle_bonus += 0.02
        except ValueError:
            pass

    score = (
        1.0
        + mood_match * 0.12
        + taste_overlap * 0.55
        + serving_match * 0.06
        + brand_bonus
        + temperature_bonus
        + taste_memory_bonus
        + lifecycle_bonus
        - recent_avoid_penalty
        - disliked_penalty
        - recent_brand_penalty
    )
    rng = random.Random(f"uniform-score::{request_data['retry_seed']}::{item['item_id']}")
    score += rng.random() * 0.001
    return {
        **item,
        "_score": round(score, 4),
        "_taste_overlap": taste_overlap,
        "_serving_match": serving_match,
        "_mood_match": mood_match,
        "_brand_bonus": brand_bonus,
        "_temperature_bonus": temperature_bonus,
        "_taste_memory_bonus": taste_memory_bonus,
        "_recent_avoid_penalty": recent_avoid_penalty,
        "_disliked_penalty": disliked_penalty,
        "_recent_brand_penalty": recent_brand_penalty,
        "_lifecycle_bonus": lifecycle_bonus,
    }


def sample_candidate_pool(items: List[Dict[str, Any]], retry_seed: int, limit: int = 8) -> List[Dict[str, Any]]:
    if len(items) <= limit:
        return items

    rng = random.Random(f"pool::{retry_seed}")
    remaining = list(items[: max(limit * 2, limit)])
    picked: List[Dict[str, Any]] = []
    while remaining and len(picked) < limit:
        weights = [max(float(item.get("_score", 1.0)), 0.1) for item in remaining]
        total = sum(weights)
        cursor = rng.random() * total
        running = 0.0
        chosen_index = 0
        for index, weight in enumerate(weights):
            running += weight
            if running >= cursor:
                chosen_index = index
                break
        picked.append(remaining.pop(chosen_index))
    return picked


def filter_taste_preferred_candidates(
    items: List[Dict[str, Any]],
    request_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not request_data["taste_tags"]:
        return items
    preferred = [item for item in items if int(item.get("_taste_overlap", 0)) > 0]
    return preferred or items


def ordered_uniform_candidates(items: List[Dict[str, Any]], retry_seed: int) -> List[Dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            -float(item.get("_score", 0.0)),
            -int(item.get("_taste_overlap", 0)),
            -int(item.get("_mood_match", 0)),
            str(item.get("brand_code") or ""),
            str(item.get("item_id") or ""),
        ),
    )


def build_uniform_candidate_pool(
    items: List[Dict[str, Any]],
    retry_seed: int,
    chosen_item_id: str,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    ordered = ordered_uniform_candidates(items, retry_seed=retry_seed)
    chosen = next((item for item in ordered if item["item_id"] == chosen_item_id), None)
    if chosen is not None:
        ordered = [chosen] + [item for item in ordered if item["item_id"] != chosen_item_id]
    return ordered[:limit]


def build_simple_session_result(
    request_data: Dict[str, Any],
    catalog_count: int,
    filtered_items: List[Dict[str, Any]],
    pool: List[Dict[str, Any]],
    chosen_item: Dict[str, Any],
    reason: str,
    encouragement: str,
    profile_memory: Dict[str, Any],
    profile_summary: List[str],
    taste_constraint_relaxed: bool,
    recent_avoid_relaxed: bool,
) -> Dict[str, Any]:
    recommendations: List[Dict[str, Any]] = []
    ordered_pool = [chosen_item] + [item for item in pool if item["item_id"] != chosen_item["item_id"]]
    for index, item in enumerate(ordered_pool, start=1):
        image_trust = simple_image_trust_profile(item)
        explanation_sections = []
        if item["item_id"] == chosen_item["item_id"]:
            explanation_sections = build_simple_explanation_sections(
                request_data=request_data,
                item=item,
                profile_memory=profile_memory,
                profile_summary=profile_summary,
                taste_constraint_relaxed=taste_constraint_relaxed,
                recent_avoid_relaxed=recent_avoid_relaxed,
            )
        recommendations.append(
            {
                "rank": index,
                "sku_id": item["item_id"],
                "sku_name": item["item_name"],
                "category": item.get("normalized_category") or "other",
                "base_price": item["base_price_cny"],
                "price_band": (
                    "low"
                    if item["base_price_cny"] <= 15
                    else "mid"
                    if item["base_price_cny"] <= 20
                    else "high"
                ),
                "score": float(item.get("_score", 0.0)),
                "explanation_tags": simple_response_tags(item, request_data)[:3],
                "emotional_copy": reason if item["item_id"] == chosen_item["item_id"] else "",
                "order_hint": item.get("default_serving_note", ""),
                "image_source_type": item.get("image_source_type", "source"),
                "image_badge_text": item.get("image_badge_text", ""),
                "image_trust": image_trust["label"],
                "launch_date": str(item.get("launch_date") or ""),
                "lifecycle_code": str(item.get("lifecycle_code") or "permanent"),
                "lifecycle_label": str(item.get("lifecycle_label") or SIMPLE_LIFECYCLE_LABELS.get(str(item.get("lifecycle_code") or "permanent"), "??")),
                "source_url": item.get("source_url"),
                "explanation_sections": explanation_sections,
                "debug": {
                    "taste_overlap": int(item.get("_taste_overlap", 0)),
                    "mood_match": int(item.get("_mood_match", 0)),
                    "temperature_bonus": float(item.get("_temperature_bonus", 0.0)),
                    "taste_memory_bonus": float(item.get("_taste_memory_bonus", 0.0)),
                    "lifecycle_bonus": float(item.get("_lifecycle_bonus", 0.0)),
                },
            }
        )

    confidence = 0.52
    if ordered_pool:
        confidence += min(float(ordered_pool[0].get("_taste_overlap", 0)) * 0.12, 0.3)
    if len(filtered_items) <= 3:
        confidence += 0.05

    return {
        "session_input": request_data,
        "recommendations": recommendations,
        "meta": {
            "candidate_count": len(filtered_items),
            "filtered_out_count": max(0, catalog_count - len(filtered_items)),
            "score_gap_top1_top2": (
                round(float(ordered_pool[0].get("_score", 0.0)) - float(ordered_pool[1].get("_score", 0.0)), 4)
                if len(ordered_pool) > 1
                else None
            ),
            "followup_required": False,
            "confidence_score": min(round(confidence, 3), 0.96),
            "profile_summary": profile_summary,
            "profile_memory_applied": bool(profile_summary),
            "taste_constraint_relaxed": taste_constraint_relaxed,
            "recent_avoid_relaxed": recent_avoid_relaxed,
        },
        "chosen_item_id": chosen_item["item_id"],
        "reason": reason,
        "encouragement": encouragement,
    }


@app.post("/api/recommendation/simple", response_model=SimpleRecommendationResponse, tags=["simple"])
def recommend_simple(payload: SimpleRecommendRequest) -> SimpleRecommendationResponse:
    request_data = normalize_simple_request(payload)
    profile_record = STORAGE.get_profile_memory_record(DEFAULT_USER_ID)
    profile_memory = normalize_profile_memory(profile_record["profile"] if profile_record else {})
    profile_has_signal = bool(
        profile_record
        and (
            profile_memory.get("preferred_brand_codes")
            or profile_memory.get("preferred_temperature")
            or profile_memory.get("recent_avoid_categories")
            or profile_memory.get("taste_tag_counts")
            or profile_memory.get("liked_taste_tags")
        )
    )
    profile_summary = profile_summary_chips(profile_memory) if profile_has_signal else []
    catalog = STORAGE.list_simple_drink_catalog(visible_only=True)
    if not catalog:
        raise HTTPException(status_code=503, detail="Simple catalog is empty. Please rebuild the local catalog first.")

    filtered_items = [
        item
        for item in catalog
        if price_matches(float(item.get("base_price_cny", 0.0)), request_data["price_band"])
        and temperature_matches(item, request_data["temperature_pref"])
        and caffeine_matches(item, request_data["caffeine_pref"])
    ]
    if not filtered_items:
        raise HTTPException(status_code=404, detail="No drinks matched the current filters.")

    brand_exclusion_relaxed = False
    exclude_brand_code = str(request_data.get("exclude_brand_code") or "").strip()
    candidate_source_items = filtered_items
    if exclude_brand_code:
        different_brand_items = [
            item for item in filtered_items if str(item.get("brand_code") or "").strip() != exclude_brand_code
        ]
        if different_brand_items:
            candidate_source_items = different_brand_items
        else:
            brand_exclusion_relaxed = True

    scored_items = [
        score_simple_candidate(
            item=item,
            request_data=request_data,
            recent_brands=[],
            profile_memory=profile_memory,
        )
        for item in candidate_source_items
    ]
    mood_matched_items = [item for item in scored_items if int(item.get("_mood_match", 0)) > 0]
    taste_matched_items = [item for item in scored_items if int(item.get("_taste_overlap", 0)) > 0]
    mood_taste_matched_items = [
        item for item in mood_matched_items if int(item.get("_taste_overlap", 0)) > 0
    ]
    taste_constraint_relaxed = False
    if request_data["taste_tags"]:
        if mood_taste_matched_items:
            candidate_items = mood_taste_matched_items
        elif taste_matched_items:
            candidate_items = taste_matched_items
        elif mood_matched_items:
            candidate_items = mood_matched_items
            taste_constraint_relaxed = True
        else:
            candidate_items = scored_items
            taste_constraint_relaxed = True
    else:
        candidate_items = mood_matched_items or scored_items
    candidate_items = filter_taste_preferred_candidates(candidate_items, request_data=request_data)

    recent_avoid_relaxed = False
    recent_avoid_categories = {
        str(value or "").strip()
        for value in profile_memory.get("recent_avoid_categories") or []
        if str(value or "").strip()
    }
    if recent_avoid_categories:
        avoid_filtered = [
            item
            for item in candidate_items
            if str(item.get("normalized_category") or "").strip() not in recent_avoid_categories
        ]
        if avoid_filtered:
            candidate_items = avoid_filtered
        else:
            recent_avoid_relaxed = True

    ordered_candidates = ordered_uniform_candidates(candidate_items, retry_seed=request_data["retry_seed"])
    chosen_item = ordered_candidates[0]
    pool = build_uniform_candidate_pool(
        candidate_items,
        retry_seed=request_data["retry_seed"],
        chosen_item_id=chosen_item["item_id"],
        limit=8,
    )
    mood_label = V2_MOOD_META[request_data["mood_code"]]["label"]
    ai_result = AI_CLIENT.choose_recommendation(
        mood_label=mood_label,
        mood_code=request_data["mood_code"],
        filters={
            "price_band": V2_PRICE_LABELS[request_data["price_band"]],
            "temperature_pref": V2_TEMPERATURE_LABELS[request_data["temperature_pref"]],
            "caffeine_pref": V2_CAFFEINE_LABELS[request_data["caffeine_pref"]],
            "taste_tags": [V2_TASTE_LABELS.get(code, code) for code in request_data["taste_tags"]],
        },
        candidates=[chosen_item],
    )

    fallback_used = False
    reason = ""
    encouragement = ""
    model_used = "fallback-template"
    if ai_result:
        if ai_result["chosen_item_id"] == chosen_item["item_id"]:
            reason = normalize_reason_copy(request_data["mood_code"], chosen_item, ai_result["reason"])
            encouragement = normalize_encouragement_copy(request_data["mood_code"], ai_result["encouragement"])
            model_used = AI_CLIENT.model

    if not reason:
        fallback_used = True
        reason = fallback_recommendation_reason(request_data["mood_code"], chosen_item)
        encouragement = fallback_recommendation_encouragement(request_data["mood_code"])

    session_result = build_simple_session_result(
        request_data=request_data,
        catalog_count=len(catalog),
        filtered_items=candidate_items,
        pool=pool,
        chosen_item=chosen_item,
        reason=reason,
        encouragement=encouragement,
        profile_memory=profile_memory,
        profile_summary=profile_summary,
        taste_constraint_relaxed=taste_constraint_relaxed,
        recent_avoid_relaxed=recent_avoid_relaxed,
    )
    session_ref = STORAGE.save_recommendation_session(
        payload={
            "entry_mode": "simple_v2",
            "goal": "emotion_support",
            "mood": request_data["mood_code"],
            "scene": "",
            "budget_band": request_data["price_band"],
            "temperature_pref": request_data["temperature_pref"],
            "caffeine_pref": request_data["caffeine_pref"],
            "dairy_avoid": False,
            "micro_adjusts": list(request_data["taste_tags"]),
            "profile": {"taste_tags": list(request_data["taste_tags"]), "profile_summary": profile_summary},
            "top_k": len(pool),
            "retry_seed": request_data["retry_seed"],
        },
        result=session_result,
    )
    chosen_image_trust = simple_image_trust_profile(chosen_item)
    recommendation_card = SimpleRecommendationCard(
        item_id=chosen_item["item_id"],
        brand_code=chosen_item["brand_code"],
        brand_name=chosen_item["brand_name"],
        item_name=chosen_item["item_name"],
        image_url=chosen_item["image_url"],
        image_source_type=chosen_item.get("image_source_type", "source"),
        image_badge_text=chosen_item.get("image_badge_text", ""),
        image_trust=chosen_image_trust["label"],
        base_price=float(chosen_item["base_price_cny"]),
        default_temperature_text=chosen_item.get("default_temperature_text", ""),
        default_sweetness_text=chosen_item.get("default_sweetness_text", ""),
        default_serving_note=chosen_item.get("default_serving_note", ""),
        temperature_type=chosen_item["temperature_type"],
        caffeine_level_code=chosen_item["caffeine_level_code"],
        tags=simple_response_tags(chosen_item, request_data),
        launch_date=str(chosen_item.get("launch_date") or ""),
        lifecycle_code=str(chosen_item.get("lifecycle_code") or "permanent"),
        lifecycle_label=str(chosen_item.get("lifecycle_label") or SIMPLE_LIFECYCLE_LABELS.get(str(chosen_item.get("lifecycle_code") or "permanent"), "??")),
        source_url=chosen_item.get("source_url"),
        explanation_sections=list(session_result.get("recommendations", [{}])[0].get("explanation_sections") or []),
        reason=reason,
        encouragement=encouragement,
    )
    return SimpleRecommendationResponse(
        session_id=session_ref["session_id"],
        recommendation=recommendation_card,
        meta=SimpleRecommendationMeta(
            candidate_count=len(candidate_items),
            fallback_used=fallback_used,
            model_used=model_used,
            brand_exclusion_relaxed=brand_exclusion_relaxed,
            taste_constraint_relaxed=taste_constraint_relaxed,
            profile_memory_applied=profile_has_signal,
            profile_summary=profile_summary,
        ),
    )

def store_simple_uploaded_asset(payload: SimpleVisualOverridePayload) -> Dict[str, Any]:
    catalog = STORAGE.list_simple_drink_catalog(visible_only=False)
    catalog_item = next((item for item in catalog if str(item.get("item_id") or "") == str(payload.item_id or "")), None)
    if catalog_item is None:
        raise HTTPException(status_code=404, detail="Simple catalog item was not found.")

    image_bytes, mime_type = decode_data_url_asset(payload.image_data_url)
    extension = mimetypes.guess_extension(mime_type) if mime_type else None
    if extension == ".jpe":
        extension = ".jpg"
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        extension = ".png"

    brand_slug = slugify_name(str(catalog_item.get("brand_code") or payload.brand_code or "brand"), "brand")
    item_slug = slugify_name(str(catalog_item.get("item_id") or payload.item_id or "item"), "item")
    digest = hashlib.sha1(image_bytes).hexdigest()[:16]
    upload_dir = GENERATED_DIR / "review_uploads" / brand_slug
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{item_slug}-{digest}{extension}"
    local_path = upload_dir / filename
    local_path.write_bytes(image_bytes)
    public_url = f"/generated/review_uploads/{brand_slug}/{filename}"

    image_mode = str(payload.image_mode or "user_uploaded").strip() or "user_uploaded"
    if image_mode not in {"user_uploaded", "brand_logo", "brand_collage", "brand_fallback", "ai_illustration"}:
        image_mode = "user_uploaded"
    badge_text = str(payload.badge_text or "").strip()
    if not badge_text:
        badge_text = "用户上传" if image_mode == "user_uploaded" else "品牌图"

    uploaded_file_path = local_path.relative_to(GENERATED_DIR).as_posix()
    review = STORAGE.create_sku_image_review(
        {
            "item_id": str(catalog_item.get("item_id") or payload.item_id or "").strip(),
            "brand_code": str(catalog_item.get("brand_code") or payload.brand_code or "").strip(),
            "item_name": str(catalog_item.get("item_name") or payload.item_name or "").strip(),
            "uploaded_image_url": public_url,
            "uploaded_file_path": uploaded_file_path,
            "mime_type": mime_type,
            "original_file_name": str(payload.original_file_name or "").strip(),
            "submitter_note": str(payload.submitter_note or payload.note or "").strip(),
            "badge_text": badge_text,
            "image_mode": image_mode,
            "review_status": "pending",
        }
    )

    return {
        "item_id": str(catalog_item.get("item_id") or payload.item_id or "").strip(),
        "brand_code": str(catalog_item.get("brand_code") or payload.brand_code or "").strip(),
        "item_name": str(catalog_item.get("item_name") or payload.item_name or "").strip(),
        "image_url": public_url,
        "uploaded_image_url": public_url,
        "image_source_type": "pending_review",
        "image_badge_text": badge_text,
        "note": str(payload.submitter_note or payload.note or "").strip(),
        "review_id": review["review_id"],
        "review_status": review["review_status"],
        "review_note": review.get("review_note", ""),
        "image_mode": image_mode,
        "rebuild_summary": {},
    }


@app.post("/api/simple/visual-overrides", response_model=SimpleVisualOverrideResponse, tags=["simple"])
def upload_simple_visual_override(payload: SimpleVisualOverridePayload) -> SimpleVisualOverrideResponse:
    result = store_simple_uploaded_asset(payload)
    return SimpleVisualOverrideResponse.model_validate(result)


@app.get("/api/admin/image-reviews", response_model=SimpleImageReviewListResponse, tags=["admin"])
def list_simple_image_reviews(
    review_status: str = Query("pending", description="pending, approved, rejected, or all"),
    brand_code: str = Query("", description="Optional brand code filter"),
    item_id: str = Query("", description="Optional item id filter"),
    limit: int = Query(200, ge=1, le=1000),
) -> SimpleImageReviewListResponse:
    items = STORAGE.list_sku_image_reviews(
        review_status=review_status,
        brand_code=brand_code,
        item_id=item_id,
        limit=limit,
    )
    return SimpleImageReviewListResponse(count=len(items), items=[SimpleImageReviewItem.model_validate(item) for item in items])


@app.post("/api/admin/image-reviews/{review_id}/approve", response_model=SimpleImageReviewDecisionResponse, tags=["admin"])
def approve_simple_image_review(
    review_id: str,
    payload: SimpleImageReviewDecisionPayload,
) -> SimpleImageReviewDecisionResponse:
    result = STORAGE.approve_sku_image_review(
        review_id,
        generated_dir=GENERATED_DIR,
        review_note=payload.review_note,
    )
    rebuild_summary = dict(result.pop("rebuild_summary", {}))
    return SimpleImageReviewDecisionResponse(
        item=SimpleImageReviewItem.model_validate(result),
        rebuild_summary=rebuild_summary,
    )


@app.post("/api/admin/image-reviews/{review_id}/reject", response_model=SimpleImageReviewDecisionResponse, tags=["admin"])
def reject_simple_image_review(
    review_id: str,
    payload: SimpleImageReviewDecisionPayload,
) -> SimpleImageReviewDecisionResponse:
    result = STORAGE.reject_sku_image_review(review_id, review_note=payload.review_note)
    return SimpleImageReviewDecisionResponse(
        item=SimpleImageReviewItem.model_validate(result),
        rebuild_summary={},
    )
