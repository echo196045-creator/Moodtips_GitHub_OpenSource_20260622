from __future__ import annotations

import json
import hashlib
import mimetypes
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import requests


FEATURE_FIELDS = [
    "tea_intensity",
    "milk_intensity",
    "fruit_intensity",
    "sweetness_intensity",
    "refresh_intensity",
    "comfort_intensity",
    "energy_intensity",
    "indulgence_intensity",
    "heaviness_intensity",
    "caffeine_level",
]

BENCHMARK_CHANNEL_CODE = "moodsips-cn-benchmark"
CONSUMER_VISIBLE_OFFICIAL_CN_CHANNEL_CODES = (
    "luckin-cn-official",
    "heytea-go-cn-official",
    "nayuki-cn-official",
    "chagee-cn-official",
)
CONSUMER_VISIBLE_SOURCE_TYPES = (
    "benchmark_seed",
    "brand_owned_promotional_snapshot",
    "delivery_platform_shenzhen_snapshot",
)
CONSUMER_VISIBLE_BENCHMARK_CITY = "Shenzhen"
SIMPLE_VISIBLE_STATUS = "verified_visible"
SIMPLE_HIDDEN_STATUS = "hidden_unverified"
SIMPLE_TAG_DISPLAY_LIMIT = 4
SIMPLE_TASTE_TAGS = ("清新", "茶感", "奶香", "果香", "顺口", "轻盈", "无糖友好")
SIMPLE_INGREDIENT_TAGS = ("柠檬", "茉莉", "乌龙", "酸奶", "咖啡", "椰香")
SIMPLE_SHAPE_TAGS = ("冷饮", "热饮", "冰沙")
SIMPLE_CAFFEINE_TAGS = ("无咖啡因", "低咖啡因", "正常咖啡因", "强咖啡因")
SIMPLE_MOOD_TAG_CODES = ("spark", "ease", "cooldown", "recharge")
SIMPLE_LIFECYCLE_CODES = ("permanent", "seasonal", "limited")
SIMPLE_LIFECYCLE_LABELS = {
    "permanent": "常驻",
    "seasonal": "季节限定",
    "limited": "短期限定",
}
RECENT_LAUNCH_WINDOW_DAYS = 60
LEMON_KEYWORDS = ("柠檬", "香水柠檬", "柠c", "柠汁")
JASMINE_KEYWORDS = ("茉莉", "茉香")
OOLONG_KEYWORDS = ("乌龙", "大红袍", "正山小种", "凤凰单丛")
YOGURT_KEYWORDS = ("酸奶", "优格")
COFFEE_KEYWORDS = (
    "咖啡",
    "美式",
    "拿铁",
    "浓缩",
    "冷萃",
    "冰萃",
    "dirty",
    "espresso",
    "cold brew",
    "nitro",
    "tonic",
    "澳白",
    "馥芮白",
    "玛奇朵",
    "卡布",
    "卡布奇诺",
    "摩卡",
)
COCONUT_KEYWORDS = ("椰", "椰香", "椰乳", "椰奶")
FRESH_KEYWORDS = ("清新", "清爽", "鲜爽", "爽口", "轻爽", "沁凉", "轻快")
SMOOTH_KEYWORDS = ("顺口", "丝滑", "绵密", "柔和", "细腻")
LIGHT_KEYWORDS = ("轻盈", "轻负担", "轻轻", "清爽", "爽口")
NO_SUGAR_KEYWORDS = ("无糖", "0糖", "零糖", "不另外加糖", "不加糖")
SWEETENED_DEFAULT_KEYWORDS = ("全糖", "标准糖", "常规糖", "半糖", "少糖", "微糖", "糖")
SMOOTHIE_KEYWORDS = ("冰沙", "奶昔", "思慕雪", "酸奶昔", "沙冰", "星冰乐", "frappuccino")
FRUITY_KEYWORDS = (
    "柠檬",
    "莓",
    "草莓",
    "蓝莓",
    "桃",
    "白桃",
    "黄桃",
    "橙",
    "柚",
    "葡萄柚",
    "西瓜",
    "芒果",
    "芒",
    "百香",
    "百香果",
    "葡萄",
    "荔枝",
    "凤梨",
    "菠萝",
    "青提",
    "提子",
    "苹果",
    "芭乐",
    "番石榴",
    "椰子",
    "杨梅",
    "柚子",
    "橙",
    "西柚",
    "柑橘",
    "柚柚",
)
TEA_KEYWORDS = JASMINE_KEYWORDS + OOLONG_KEYWORDS + (
    "红茶",
    "绿茶",
    "青茶",
    "白茶",
    "焙茶",
    "花草茶",
    "路易波士",
    "茶瓦纳",
    "teavana",
    "抹茶",
)
MILK_KEYWORDS = ("牛乳", "鲜奶", "奶茶", "奶绿", "奶盖", "厚乳", "拿铁", "奶昔", "芝士", "奶砖", "乳茶")
STRONG_CAFFEINE_KEYWORDS = ("浓缩", "双份", "double", "高咖啡因", "extra shot", "espresso")
PURE_COFFEE_CATEGORIES = {"coffee", "coffee_latte", "coffee_sparkling"}
TEA_FORWARD_CATEGORIES = {"tea", "milk_tea", "tea_sparkling", "tea_cheese"}
DELIVERY_PLATFORM_SOURCE_TYPE = "delivery_platform_shenzhen_snapshot"
IMAGE_QUALITY_SCORES = {
    "platform_original": 5,
    "ai_illustration": 4,
    "user_uploaded": 5,
    "brand_logo": 3,
    "brand_collage": 3,
    "brand_fallback": 3,
    "standard_remote": 4,
    "menu_card_crop": 3,
    "platform_card_crop": 3,
    "local_copy": 3,
    "generated_existing": 2,
    "brand_poster": 1,
    "missing": 0,
}
SERVING_TEXT_TRANSLATIONS = {
    "iced": "冰饮",
    "cold": "冷饮",
    "hot": "热饮",
    "warm": "热饮",
    "ice": "加冰",
    "standard ice": "标准冰",
    "regular ice": "标准冰",
    "less ice": "少冰",
    "light ice": "少冰",
    "no ice": "去冰",
    "regular sugar": "常规糖",
    "full sugar": "全糖",
    "normal sugar": "标准糖",
    "less sugar": "少糖",
    "light sugar": "微糖",
    "half sugar": "半糖",
    "no sugar": "无糖",
    "no extra sugar": "不另外加糖",
}


class MoodSipsStorage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _project_root(self) -> Path:
        return self.db_path.parent.parent

    def _resolve_project_path(self, path_value: str) -> Path:
        candidate = Path(str(path_value or "").strip())
        if candidate.is_absolute():
            return candidate
        return (self._project_root() / candidate).resolve()

    def _consumer_source_clause(self, source_alias: str = "s") -> Tuple[str, List[Any]]:
        source_type_placeholders = ", ".join("?" for _ in CONSUMER_VISIBLE_SOURCE_TYPES)
        placeholders = ", ".join("?" for _ in CONSUMER_VISIBLE_OFFICIAL_CN_CHANNEL_CODES)
        clause = f"""
            (
                (
                    {source_alias}.source_type IN ({source_type_placeholders})
                    AND {source_alias}.source_status = ?
                    AND {source_alias}.country_code = ?
                    AND {source_alias}.currency_code = ?
                    AND LOWER(COALESCE({source_alias}.city, '')) = LOWER(?)
                )
                OR (
                    {source_alias}.source_status = ?
                    AND {source_alias}.country_code = ?
                    AND {source_alias}.currency_code = ?
                    AND {source_alias}.channel_code IN ({placeholders})
                )
            )
        """
        params: List[Any] = [
            *CONSUMER_VISIBLE_SOURCE_TYPES,
            "active",
            "CN",
            "CNY",
            CONSUMER_VISIBLE_BENCHMARK_CITY,
            "active",
            "CN",
            "CNY",
            *CONSUMER_VISIBLE_OFFICIAL_CN_CHANNEL_CODES,
        ]
        return clause, params

    def init_db(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS recommendation_sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    entry_mode TEXT NOT NULL,
                    goal_code TEXT NOT NULL,
                    mood_code TEXT,
                    scene_code TEXT,
                    budget_band TEXT,
                    temperature_pref TEXT,
                    caffeine_pref TEXT,
                    dairy_avoid INTEGER NOT NULL,
                    micro_adjusts_json TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    top_k INTEGER NOT NULL,
                    candidate_count INTEGER NOT NULL,
                    filtered_out_count INTEGER NOT NULL,
                    score_gap_top1_top2 REAL,
                    followup_required INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    top_recommendation_sku_id TEXT,
                    top_recommendation_name TEXT,
                    selected_sku_id TEXT,
                    selected_sku_name TEXT,
                    selected_at TEXT,
                    latest_feedback_label TEXT,
                    latest_feedback_reason TEXT,
                    latest_feedback_note TEXT,
                    latest_feedback_at TEXT,
                    session_input_json TEXT NOT NULL,
                    response_meta_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS session_recommendations (
                    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    rank_no INTEGER NOT NULL,
                    sku_id TEXT NOT NULL,
                    sku_name TEXT NOT NULL,
                    category TEXT,
                    base_price REAL,
                    price_band TEXT,
                    score REAL,
                    explanation_tags_json TEXT NOT NULL,
                    emotional_copy TEXT,
                    order_hint TEXT,
                    debug_json TEXT,
                    FOREIGN KEY (session_id) REFERENCES recommendation_sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS feedback_events (
                    feedback_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    satisfaction_label TEXT NOT NULL,
                    fail_reason TEXT,
                    note TEXT,
                    selected_sku_id TEXT,
                    selected_sku_name TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES recommendation_sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS accepted_drink_events (
                    accept_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    accepted_at TEXT NOT NULL,
                    accepted_date TEXT NOT NULL,
                    accepted_month TEXT NOT NULL,
                    mood_code TEXT NOT NULL,
                    mood_label TEXT,
                    budget_band TEXT,
                    temperature_pref TEXT,
                    caffeine_pref TEXT,
                    preference_tags_json TEXT NOT NULL,
                    sku_id TEXT NOT NULL,
                    sku_name TEXT NOT NULL,
                    brand_code TEXT,
                    brand_name TEXT,
                    image_url TEXT,
                    base_price REAL,
                    currency_code TEXT,
                    serving_note TEXT,
                    encouragement_copy TEXT,
                    source_payload_json TEXT
                );

                CREATE TABLE IF NOT EXISTS user_profile_memory (
                    user_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS brand_master (
                    brand_code TEXT PRIMARY KEY,
                    brand_name TEXT NOT NULL,
                    brand_name_local TEXT,
                    channel_name TEXT,
                    default_currency_code TEXT,
                    brand_country_code TEXT,
                    brand_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS menu_source (
                    source_code TEXT PRIMARY KEY,
                    brand_code TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_url TEXT,
                    source_api_url TEXT,
                    store_external_id TEXT,
                    store_name TEXT,
                    address_text TEXT,
                    city TEXT,
                    region TEXT,
                    country_code TEXT,
                    currency_code TEXT,
                    channel_code TEXT,
                    imported_at TEXT NOT NULL,
                    source_status TEXT NOT NULL,
                    item_count INTEGER NOT NULL DEFAULT 0,
                    option_group_count INTEGER NOT NULL DEFAULT 0,
                    option_count INTEGER NOT NULL DEFAULT 0,
                    raw_store_json TEXT,
                    raw_menu_json TEXT,
                    FOREIGN KEY (brand_code) REFERENCES brand_master(brand_code) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS menu_category (
                    category_id TEXT PRIMARY KEY,
                    source_code TEXT NOT NULL,
                    category_name TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    raw_json TEXT,
                    FOREIGN KEY (source_code) REFERENCES menu_source(source_code) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS menu_item_master (
                    item_id TEXT PRIMARY KEY,
                    brand_code TEXT NOT NULL,
                    source_code TEXT NOT NULL,
                    category_id TEXT,
                    external_item_id TEXT NOT NULL,
                    item_code TEXT,
                    item_name TEXT NOT NULL,
                    item_name_local TEXT,
                    display_name TEXT,
                    description TEXT,
                    image_url TEXT,
                    category_name TEXT,
                    normalized_category TEXT NOT NULL,
                    base_price REAL NOT NULL,
                    currency_code TEXT NOT NULL,
                    price_band TEXT NOT NULL,
                    launch_date TEXT,
                    lifecycle_code TEXT,
                    lifecycle_label TEXT,
                    lifecycle_evidence_json TEXT,
                    available_hot INTEGER NOT NULL,
                    available_cold INTEGER NOT NULL,
                    dairy_flag INTEGER NOT NULL,
                    caffeine_level REAL NOT NULL,
                    tea_intensity REAL NOT NULL,
                    milk_intensity REAL NOT NULL,
                    fruit_intensity REAL NOT NULL,
                    sweetness_intensity REAL NOT NULL,
                    refresh_intensity REAL NOT NULL,
                    comfort_intensity REAL NOT NULL,
                    energy_intensity REAL NOT NULL,
                    indulgence_intensity REAL NOT NULL,
                    heaviness_intensity REAL NOT NULL,
                    mood_tags_json TEXT NOT NULL,
                    scene_tags_json TEXT NOT NULL,
                    profile_tags_json TEXT NOT NULL,
                    option_summary_json TEXT NOT NULL,
                    raw_json TEXT,
                    active_flag INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (brand_code) REFERENCES brand_master(brand_code) ON DELETE CASCADE,
                    FOREIGN KEY (source_code) REFERENCES menu_source(source_code) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES menu_category(category_id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS menu_option_group (
                    group_id TEXT PRIMARY KEY,
                    source_code TEXT NOT NULL,
                    external_group_id TEXT NOT NULL,
                    group_name TEXT NOT NULL,
                    required INTEGER NOT NULL,
                    limit_count INTEGER NOT NULL,
                    supports_multiple INTEGER NOT NULL,
                    group_type TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    raw_json TEXT,
                    FOREIGN KEY (source_code) REFERENCES menu_source(source_code) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS menu_item_option_group_map (
                    map_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    UNIQUE (item_id, group_id),
                    FOREIGN KEY (item_id) REFERENCES menu_item_master(item_id) ON DELETE CASCADE,
                    FOREIGN KEY (group_id) REFERENCES menu_option_group(group_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS menu_option (
                    option_id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    option_name TEXT NOT NULL,
                    external_option_code TEXT,
                    price_delta REAL NOT NULL,
                    is_default INTEGER NOT NULL,
                    sold_out INTEGER NOT NULL,
                    option_tags_json TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    raw_json TEXT,
                    FOREIGN KEY (group_id) REFERENCES menu_option_group(group_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS simple_drink_catalog (
                    item_id TEXT PRIMARY KEY,
                    brand_code TEXT NOT NULL,
                    brand_name TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    image_url TEXT,
                    base_price_cny REAL NOT NULL,
                    default_temperature_text TEXT,
                    default_sweetness_text TEXT,
                    temperature_type TEXT NOT NULL,
                    caffeine_level_code TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    source_url TEXT,
                    verification_status TEXT NOT NULL,
                    last_verified_at TEXT,
                    active_flag INTEGER NOT NULL DEFAULT 1,
                    source_code TEXT,
                    launch_date TEXT,
                    lifecycle_code TEXT,
                    lifecycle_label TEXT,
                    lifecycle_evidence_json TEXT,
                    original_image_url TEXT,
                    image_meta_json TEXT,
                    normalized_category TEXT,
                    description TEXT,
                    tag_evidence_json TEXT,
                    mood_tag_code TEXT,
                    mood_tag_evidence_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (brand_code) REFERENCES brand_master(brand_code) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS brand_coverage_registry (
                    brand_code TEXT PRIMARY KEY,
                    brand_name TEXT NOT NULL,
                    category_scope TEXT NOT NULL,
                    meituan_url TEXT,
                    eleme_url TEXT,
                    coverage_status TEXT NOT NULL,
                    exclusion_reason TEXT,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sku_attribute_overrides (
                    brand_code TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    attribute_overrides_json TEXT NOT NULL DEFAULT '{}',
                    display_tags_override_json TEXT,
                    note TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (brand_code, item_name)
                );

                CREATE TABLE IF NOT EXISTS sku_visual_overrides (
                    brand_code TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    image_mode TEXT NOT NULL DEFAULT 'source',
                    ai_image_url TEXT,
                    badge_text TEXT,
                    prompt_text TEXT,
                    prompt_version TEXT,
                    prompt_payload_json TEXT NOT NULL DEFAULT '{}',
                    note TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (brand_code, item_name)
                );

                CREATE TABLE IF NOT EXISTS sku_image_review_queue (
                    review_id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    brand_code TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    uploaded_image_url TEXT NOT NULL,
                    uploaded_file_path TEXT NOT NULL,
                    mime_type TEXT,
                    original_file_name TEXT,
                    submitter_note TEXT,
                    badge_text TEXT,
                    image_mode TEXT NOT NULL DEFAULT 'user_uploaded',
                    review_status TEXT NOT NULL DEFAULT 'pending',
                    review_note TEXT,
                    reviewed_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_session_recommendations_session
                    ON session_recommendations(session_id);
                CREATE INDEX IF NOT EXISTS idx_feedback_events_session
                    ON feedback_events(session_id);
                CREATE INDEX IF NOT EXISTS idx_accepted_drink_events_user_month
                    ON accepted_drink_events(user_id, accepted_month);
                CREATE INDEX IF NOT EXISTS idx_accepted_drink_events_user_time
                    ON accepted_drink_events(user_id, accepted_at);
                CREATE INDEX IF NOT EXISTS idx_menu_source_brand
                    ON menu_source(brand_code);
                CREATE INDEX IF NOT EXISTS idx_menu_item_brand
                    ON menu_item_master(brand_code);
                CREATE INDEX IF NOT EXISTS idx_menu_item_source
                    ON menu_item_master(source_code);
                CREATE INDEX IF NOT EXISTS idx_menu_item_price
                    ON menu_item_master(base_price);
                CREATE INDEX IF NOT EXISTS idx_menu_group_source
                    ON menu_option_group(source_code);
                CREATE INDEX IF NOT EXISTS idx_menu_option_group
                    ON menu_option(group_id);
                CREATE INDEX IF NOT EXISTS idx_simple_drink_catalog_visibility
                    ON simple_drink_catalog(verification_status, active_flag);
                CREATE INDEX IF NOT EXISTS idx_simple_drink_catalog_brand
                    ON simple_drink_catalog(brand_code);
                CREATE INDEX IF NOT EXISTS idx_brand_coverage_registry_status
                    ON brand_coverage_registry(coverage_status);
                CREATE INDEX IF NOT EXISTS idx_sku_attribute_overrides_brand
                    ON sku_attribute_overrides(brand_code);
                CREATE INDEX IF NOT EXISTS idx_sku_visual_overrides_brand
                    ON sku_visual_overrides(brand_code);
                CREATE INDEX IF NOT EXISTS idx_sku_image_review_queue_status
                    ON sku_image_review_queue(review_status);
                CREATE INDEX IF NOT EXISTS idx_sku_image_review_queue_brand
                    ON sku_image_review_queue(brand_code);
                CREATE INDEX IF NOT EXISTS idx_sku_image_review_queue_item
                    ON sku_image_review_queue(item_id);
                """
            )
            self._ensure_schema_extensions(connection)

    def _table_columns(self, connection: sqlite3.Connection, table_name: str) -> List[str]:
        rows = connection.execute("PRAGMA table_info(%s)" % table_name).fetchall()
        return [str(row["name"]) for row in rows]

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_sql: str,
    ) -> None:
        if column_name in self._table_columns(connection, table_name):
            return
        connection.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table_name, column_name, column_sql))

    def _parse_date_value(self, value: Any) -> Optional[datetime.date]:
        text = str(value or "").strip()
        if not text:
            return None
        for parser in (
            lambda value_text: datetime.strptime(value_text[:10], "%Y-%m-%d").date(),
            lambda value_text: datetime.fromisoformat(value_text).date(),
        ):
            try:
                return parser(text)
            except ValueError:
                continue
        return None

    def _derive_lifecycle_payload(
        self,
        *,
        item_name: str,
        description: str,
        normalized_category: str,
        source_code: str,
        raw_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raw_meta = raw_meta if isinstance(raw_meta, dict) else {}
        explicit_code = str(
            raw_meta.get("lifecycle_status")
            or raw_meta.get("lifecycle_code")
            or raw_meta.get("launch_lifecycle")
            or ""
        ).strip().lower()
        if explicit_code not in SIMPLE_LIFECYCLE_CODES:
            explicit_code = ""

        launch_date_text = str(raw_meta.get("launch_date") or "").strip()
        launch_date = self._parse_date_value(launch_date_text)
        source_hint = " ".join(
            str(part or "").lower()
            for part in [item_name, description, normalized_category, source_code, raw_meta.get("kind"), raw_meta.get("curation")]
        )

        lifecycle_code = explicit_code or "permanent"
        if not explicit_code and (str(source_code or "").startswith("recent_launch_") or launch_date is not None):
            if any(keyword.lower() in source_hint for keyword in ("限定", "联名", "pro", "快闪", "会员", "礼盒")):
                lifecycle_code = "limited"
            else:
                lifecycle_code = "seasonal"

        lifecycle_label = SIMPLE_LIFECYCLE_LABELS.get(lifecycle_code, "常驻")
        evidence = {
            "source_code": source_code,
            "launch_date": launch_date_text,
            "raw_lifecycle_code": explicit_code or lifecycle_code,
            "derived_lifecycle_code": lifecycle_code,
            "reason": "explicit" if explicit_code else ("recent_launch_window" if lifecycle_code != "permanent" else "default_permanent"),
        }
        if isinstance(raw_meta.get("kind"), str) and raw_meta.get("kind"):
            evidence["kind"] = raw_meta.get("kind")
        if isinstance(raw_meta.get("category_name"), str) and raw_meta.get("category_name"):
            evidence["category_name"] = raw_meta.get("category_name")
        if launch_date is not None:
            evidence["launch_age_days"] = max((datetime.now().date() - launch_date).days, 0)

        return {
            "launch_date": launch_date_text,
            "lifecycle_code": lifecycle_code,
            "lifecycle_label": lifecycle_label,
            "lifecycle_evidence_json": self._dump_json(evidence),
        }

    def _ensure_schema_extensions(self, connection: sqlite3.Connection) -> None:
        self._ensure_column(connection, "menu_item_master", "launch_date", "TEXT")
        self._ensure_column(connection, "menu_item_master", "lifecycle_code", "TEXT")
        self._ensure_column(connection, "menu_item_master", "lifecycle_label", "TEXT")
        self._ensure_column(connection, "menu_item_master", "lifecycle_evidence_json", "TEXT")
        self._ensure_column(connection, "simple_drink_catalog", "image_meta_json", "TEXT")
        self._ensure_column(connection, "simple_drink_catalog", "tag_evidence_json", "TEXT")
        self._ensure_column(connection, "simple_drink_catalog", "mood_tag_code", "TEXT")
        self._ensure_column(connection, "simple_drink_catalog", "mood_tag_evidence_json", "TEXT")
        self._ensure_column(connection, "simple_drink_catalog", "launch_date", "TEXT")
        self._ensure_column(connection, "simple_drink_catalog", "lifecycle_code", "TEXT")
        self._ensure_column(connection, "simple_drink_catalog", "lifecycle_label", "TEXT")
        self._ensure_column(connection, "simple_drink_catalog", "lifecycle_evidence_json", "TEXT")
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_simple_drink_catalog_mood_tag
                ON simple_drink_catalog(mood_tag_code);
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_simple_drink_catalog_lifecycle
                ON simple_drink_catalog(lifecycle_code);
            """
        )
        self._backfill_simple_mood_tags(connection)
        self._backfill_menu_item_lifecycle(connection)
        self._backfill_simple_lifecycle(connection)

    def _backfill_simple_mood_tags(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT item_id, item_name, description, normalized_category, temperature_type,
                   caffeine_level_code, tags_json, mood_tag_code
            FROM simple_drink_catalog
            """
        ).fetchall()
        for row in rows:
            current_code = str(row["mood_tag_code"] or "").strip()
            if current_code in SIMPLE_MOOD_TAG_CODES:
                continue
            tags = self._loads_json(row["tags_json"], [])
            mood_payload = self._derive_simple_mood_tag_payload(
                item_name=str(row["item_name"] or ""),
                description=str(row["description"] or ""),
                normalized_category=str(row["normalized_category"] or ""),
                temperature_type=str(row["temperature_type"] or ""),
                caffeine_level_code=str(row["caffeine_level_code"] or ""),
                display_tags=[str(tag) for tag in tags],
            )
            connection.execute(
                """
                UPDATE simple_drink_catalog
                SET mood_tag_code = ?, mood_tag_evidence_json = ?
                WHERE item_id = ?
                """,
                (
                    mood_payload["mood_tag_code"],
                    self._dump_json(mood_payload["evidence"]),
                    row["item_id"],
                ),
            )

    def _backfill_simple_lifecycle(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT item_id, item_name, description, normalized_category, source_code, lifecycle_code
            FROM simple_drink_catalog
            """
        ).fetchall()
        for row in rows:
            current_code = str(row["lifecycle_code"] or "").strip()
            if current_code in SIMPLE_LIFECYCLE_CODES:
                continue
            payload = self._derive_lifecycle_payload(
                item_name=str(row["item_name"] or ""),
                description=str(row["description"] or ""),
                normalized_category=str(row["normalized_category"] or ""),
                source_code=str(row["source_code"] or ""),
                raw_meta={},
            )
            connection.execute(
                """
                UPDATE simple_drink_catalog
                SET launch_date = ?,
                    lifecycle_code = ?,
                    lifecycle_label = ?,
                    lifecycle_evidence_json = ?
                WHERE item_id = ?
                """,
                (
                    payload["launch_date"],
                    payload["lifecycle_code"],
                    payload["lifecycle_label"],
                    payload["lifecycle_evidence_json"],
                    row["item_id"],
                ),
            )

    def _backfill_menu_item_lifecycle(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT item_id, item_name, description, normalized_category, source_code, raw_json, lifecycle_code
            FROM menu_item_master
            """
        ).fetchall()
        for row in rows:
            current_code = str(row["lifecycle_code"] or "").strip()
            if current_code in SIMPLE_LIFECYCLE_CODES:
                continue
            raw_meta = self._loads_json(row["raw_json"], {})
            payload = self._derive_lifecycle_payload(
                item_name=str(row["item_name"] or ""),
                description=str(row["description"] or ""),
                normalized_category=str(row["normalized_category"] or ""),
                source_code=str(row["source_code"] or ""),
                raw_meta=raw_meta if isinstance(raw_meta, dict) else {},
            )
            connection.execute(
                """
                UPDATE menu_item_master
                SET launch_date = ?,
                    lifecycle_code = ?,
                    lifecycle_label = ?,
                    lifecycle_evidence_json = ?
                WHERE item_id = ?
                """,
                (
                    payload["launch_date"],
                    payload["lifecycle_code"],
                    payload["lifecycle_label"],
                    payload["lifecycle_evidence_json"],
                    row["item_id"],
                ),
            )

    def upsert_sku_visual_overrides(self, entries: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        seen: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for entry in entries:
            brand_code = str(entry.get("brand_code") or "").strip()
            item_name = str(entry.get("item_name") or "").strip()
            if not brand_code or not item_name:
                continue
            seen[(brand_code, item_name)] = {
                "brand_code": brand_code,
                "item_name": item_name,
                "image_mode": str(entry.get("image_mode") or "source").strip() or "source",
                "ai_image_url": str(entry.get("ai_image_url") or "").strip(),
                "badge_text": str(entry.get("badge_text") or "").strip(),
                "prompt_text": str(entry.get("prompt_text") or "").strip(),
                "prompt_version": str(entry.get("prompt_version") or "").strip(),
                "prompt_payload_json": self._dump_json(entry.get("prompt_payload_json") or {}),
                "note": str(entry.get("note") or "").strip(),
                "updated_at": str(entry.get("updated_at") or self._now_iso()).strip() or self._now_iso(),
            }

        inserted_count = 0
        updated_count = 0
        with self.connect() as connection:
            existing_rows = connection.execute(
                """
                SELECT brand_code, item_name
                FROM sku_visual_overrides
                """
            ).fetchall()
            existing_keys = {
                (str(row["brand_code"] or "").strip(), str(row["item_name"] or "").strip())
                for row in existing_rows
            }
            for payload in seen.values():
                connection.execute(
                    """
                    INSERT INTO sku_visual_overrides (
                        brand_code, item_name, image_mode, ai_image_url, badge_text,
                        prompt_text, prompt_version, prompt_payload_json, note, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(brand_code, item_name) DO UPDATE SET
                        image_mode=excluded.image_mode,
                        ai_image_url=excluded.ai_image_url,
                        badge_text=excluded.badge_text,
                        prompt_text=excluded.prompt_text,
                        prompt_version=excluded.prompt_version,
                        prompt_payload_json=excluded.prompt_payload_json,
                        note=excluded.note,
                        updated_at=excluded.updated_at
                    """,
                    (
                        payload["brand_code"],
                        payload["item_name"],
                        payload["image_mode"],
                        payload["ai_image_url"],
                        payload["badge_text"],
                        payload["prompt_text"],
                        payload["prompt_version"],
                        payload["prompt_payload_json"],
                        payload["note"],
                        payload["updated_at"],
                    ),
                )
                key = (payload["brand_code"], payload["item_name"])
                if key in existing_keys:
                    updated_count += 1
                else:
                    inserted_count += 1

        return {
            "entry_count": len(seen),
            "inserted_count": inserted_count,
            "updated_count": updated_count,
        }

    def create_sku_image_review(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        brand_code = str(entry.get("brand_code") or "").strip()
        item_name = str(entry.get("item_name") or "").strip()
        item_id = str(entry.get("item_id") or "").strip()
        uploaded_image_url = str(entry.get("uploaded_image_url") or "").strip()
        uploaded_file_path = str(entry.get("uploaded_file_path") or "").strip()
        if not brand_code or not item_name or not item_id:
            raise ValueError("image review entry is missing required fields")
        if not uploaded_image_url or not uploaded_file_path:
            raise ValueError("image review entry is missing uploaded file metadata")

        review_id = str(entry.get("review_id") or f"review_{uuid.uuid4().hex}").strip()
        now = str(entry.get("now") or self._now_iso()).strip() or self._now_iso()
        review_status = str(entry.get("review_status") or "pending").strip().lower() or "pending"
        if review_status not in {"pending", "approved", "rejected"}:
            review_status = "pending"
        image_mode = str(entry.get("image_mode") or "user_uploaded").strip() or "user_uploaded"
        badge_text = str(entry.get("badge_text") or "").strip()
        submitter_note = str(entry.get("submitter_note") or entry.get("note") or "").strip()
        original_file_name = str(entry.get("original_file_name") or "").strip()
        mime_type = str(entry.get("mime_type") or "").strip()
        review_note = str(entry.get("review_note") or "").strip()
        reviewed_at = str(entry.get("reviewed_at") or "").strip()

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO sku_image_review_queue (
                    review_id, item_id, brand_code, item_name, uploaded_image_url,
                    uploaded_file_path, mime_type, original_file_name, submitter_note,
                    badge_text, image_mode, review_status, review_note, reviewed_at,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(review_id) DO UPDATE SET
                    item_id=excluded.item_id,
                    brand_code=excluded.brand_code,
                    item_name=excluded.item_name,
                    uploaded_image_url=excluded.uploaded_image_url,
                    uploaded_file_path=excluded.uploaded_file_path,
                    mime_type=excluded.mime_type,
                    original_file_name=excluded.original_file_name,
                    submitter_note=excluded.submitter_note,
                    badge_text=excluded.badge_text,
                    image_mode=excluded.image_mode,
                    review_status=excluded.review_status,
                    review_note=excluded.review_note,
                    reviewed_at=excluded.reviewed_at,
                    updated_at=excluded.updated_at
                """,
                (
                    review_id,
                    item_id,
                    brand_code,
                    item_name,
                    uploaded_image_url,
                    uploaded_file_path,
                    mime_type,
                    original_file_name,
                    submitter_note,
                    badge_text,
                    image_mode,
                    review_status,
                    review_note,
                    reviewed_at,
                    now,
                    now,
                ),
            )
            row = connection.execute(
                """
                SELECT
                    review_id, item_id, brand_code, item_name, uploaded_image_url,
                    uploaded_file_path, mime_type, original_file_name, submitter_note,
                    badge_text, image_mode, review_status, review_note, reviewed_at,
                    created_at, updated_at
                FROM sku_image_review_queue
                WHERE review_id = ?
                """,
                (review_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError("failed to persist image review queue item")
        return self._serialize_sku_image_review_row(row)

    def _serialize_sku_image_review_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "review_id": str(row["review_id"] or "").strip(),
            "item_id": str(row["item_id"] or "").strip(),
            "brand_code": str(row["brand_code"] or "").strip(),
            "item_name": str(row["item_name"] or "").strip(),
            "uploaded_image_url": str(row["uploaded_image_url"] or "").strip(),
            "uploaded_file_path": str(row["uploaded_file_path"] or "").strip(),
            "mime_type": str(row["mime_type"] or "").strip(),
            "original_file_name": str(row["original_file_name"] or "").strip(),
            "submitter_note": str(row["submitter_note"] or "").strip(),
            "badge_text": str(row["badge_text"] or "").strip(),
            "image_mode": str(row["image_mode"] or "user_uploaded").strip() or "user_uploaded",
            "review_status": str(row["review_status"] or "pending").strip() or "pending",
            "review_note": str(row["review_note"] or "").strip(),
            "reviewed_at": str(row["reviewed_at"] or "").strip(),
            "created_at": str(row["created_at"] or "").strip(),
            "updated_at": str(row["updated_at"] or "").strip(),
        }

    def list_sku_image_reviews(
        self,
        *,
        review_status: Optional[str] = "pending",
        brand_code: str = "",
        item_id: str = "",
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit or 200), 1000))
        clauses: List[str] = []
        params: List[Any] = []
        status_text = str(review_status or "").strip().lower()
        if status_text and status_text != "all":
            clauses.append("review_status = ?")
            params.append(status_text)
        brand_text = str(brand_code or "").strip()
        if brand_text:
            clauses.append("brand_code = ?")
            params.append(brand_text)
        item_text = str(item_id or "").strip()
        if item_text:
            clauses.append("item_id = ?")
            params.append(item_text)

        query = """
            SELECT
                review_id, item_id, brand_code, item_name, uploaded_image_url,
                uploaded_file_path, mime_type, original_file_name, submitter_note,
                badge_text, image_mode, review_status, review_note, reviewed_at,
                created_at, updated_at
            FROM sku_image_review_queue
        """
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC, review_id DESC LIMIT ?"
        params.append(limit)

        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._serialize_sku_image_review_row(row) for row in rows]

    def get_sku_image_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        review_text = str(review_id or "").strip()
        if not review_text:
            return None
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    review_id, item_id, brand_code, item_name, uploaded_image_url,
                    uploaded_file_path, mime_type, original_file_name, submitter_note,
                    badge_text, image_mode, review_status, review_note, reviewed_at,
                    created_at, updated_at
                FROM sku_image_review_queue
                WHERE review_id = ?
                """,
                (review_text,),
            ).fetchone()
        if row is None:
            return None
        return self._serialize_sku_image_review_row(row)

    def update_sku_image_review_status(
        self,
        review_id: str,
        *,
        review_status: str,
        review_note: str = "",
        reviewed_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        review_text = str(review_id or "").strip()
        if not review_text:
            raise ValueError("review_id is required")
        status_text = str(review_status or "").strip().lower()
        if status_text not in {"pending", "approved", "rejected"}:
            raise ValueError("review_status must be pending, approved, or rejected")
        now = str(reviewed_at or self._now_iso()).strip() or self._now_iso()
        with self.connect() as connection:
            current = connection.execute(
                """
                SELECT
                    review_id, item_id, brand_code, item_name, uploaded_image_url,
                    uploaded_file_path, mime_type, original_file_name, submitter_note,
                    badge_text, image_mode, review_status, review_note, reviewed_at,
                    created_at, updated_at
                FROM sku_image_review_queue
                WHERE review_id = ?
                """,
                (review_text,),
            ).fetchone()
            if current is None:
                raise ValueError("review item not found")
            connection.execute(
                """
                UPDATE sku_image_review_queue
                SET review_status = ?,
                    review_note = ?,
                    reviewed_at = ?,
                    updated_at = ?
                WHERE review_id = ?
                """,
                (
                    status_text,
                    str(review_note or "").strip(),
                    now if status_text in {"approved", "rejected"} else str(current["reviewed_at"] or "").strip(),
                    now,
                    review_text,
                ),
            )
        return self.get_sku_image_review(review_text) or {}

    def approve_sku_image_review(
        self,
        review_id: str,
        *,
        generated_dir: Optional[Path] = None,
        review_note: str = "",
    ) -> Dict[str, Any]:
        review = self.get_sku_image_review(review_id)
        if review is None:
            raise ValueError("review item not found")
        if str(review.get("review_status") or "").strip().lower() == "approved":
            rebuild_dir = generated_dir or self._project_root() / "frontend" / "generated"
            rebuild_summary = self.rebuild_simple_drink_catalog(rebuild_dir)
            review["rebuild_summary"] = rebuild_summary
            return review

        rebuild_dir = generated_dir or self._project_root() / "frontend" / "generated"
        stored_path = Path(str(review.get("uploaded_file_path") or ""))
        file_path = stored_path if stored_path.is_absolute() else (rebuild_dir / stored_path).resolve()
        if not file_path.exists() or not file_path.is_file():
            raise ValueError(f"uploaded file missing: {file_path}")

        now = self._now_iso()
        note_text = str(review_note or review.get("review_note") or review.get("submitter_note") or "").strip()
        self.upsert_sku_visual_overrides(
            [
                {
                    "brand_code": review["brand_code"],
                    "item_name": review["item_name"],
                    "image_mode": review.get("image_mode") or "user_uploaded",
                    "ai_image_url": review["uploaded_image_url"],
                    "badge_text": review.get("badge_text") or "用户上传",
                    "prompt_text": "approved user-uploaded drink image",
                    "prompt_version": "review_upload_v1",
                    "prompt_payload_json": {
                        "review_id": review["review_id"],
                        "item_id": review["item_id"],
                        "brand_code": review["brand_code"],
                        "item_name": review["item_name"],
                        "uploaded_image_url": review["uploaded_image_url"],
                        "uploaded_file_path": review["uploaded_file_path"],
                        "mime_type": review.get("mime_type") or "",
                        "original_file_name": review.get("original_file_name") or "",
                        "submitter_note": review.get("submitter_note") or "",
                    },
                    "note": note_text,
                    "updated_at": now,
                }
            ]
        )
        updated_review = self.update_sku_image_review_status(
            review["review_id"],
            review_status="approved",
            review_note=note_text,
            reviewed_at=now,
        )
        rebuild_summary = self.rebuild_simple_drink_catalog(rebuild_dir)
        updated_review["rebuild_summary"] = rebuild_summary
        return updated_review

    def reject_sku_image_review(
        self,
        review_id: str,
        *,
        review_note: str = "",
    ) -> Dict[str, Any]:
        return self.update_sku_image_review_status(
            review_id,
            review_status="rejected",
            review_note=review_note,
        )

    def sync_brand_coverage_registry(self, entries: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        seen: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            brand_code = str(entry.get("brand_code") or "").strip()
            if not brand_code:
                continue
            seen[brand_code] = {
                "brand_code": brand_code,
                "brand_name": str(entry.get("brand_name") or brand_code).strip(),
                "category_scope": str(entry.get("category_scope") or "drink_chain").strip() or "drink_chain",
                "meituan_url": str(entry.get("meituan_url") or "").strip(),
                "eleme_url": str(entry.get("eleme_url") or "").strip(),
                "coverage_status": str(entry.get("coverage_status") or "staged_backend_only").strip() or "staged_backend_only",
                "exclusion_reason": str(entry.get("exclusion_reason") or "").strip(),
                "last_seen_at": str(entry.get("last_seen_at") or self._now_iso()).strip() or self._now_iso(),
            }

        inserted_count = 0
        updated_count = 0
        with self.connect() as connection:
            existing_rows = connection.execute(
                """
                SELECT brand_code, brand_name, category_scope, meituan_url, eleme_url, coverage_status, exclusion_reason, last_seen_at
                FROM brand_coverage_registry
                """
            ).fetchall()
            existing_map = {str(row["brand_code"]): row for row in existing_rows}

            for brand_code, payload in seen.items():
                connection.execute(
                    """
                    INSERT INTO brand_coverage_registry (
                        brand_code, brand_name, category_scope, meituan_url, eleme_url,
                        coverage_status, exclusion_reason, last_seen_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(brand_code) DO UPDATE SET
                        brand_name=excluded.brand_name,
                        category_scope=excluded.category_scope,
                        meituan_url=excluded.meituan_url,
                        eleme_url=excluded.eleme_url,
                        coverage_status=excluded.coverage_status,
                        exclusion_reason=excluded.exclusion_reason,
                        last_seen_at=excluded.last_seen_at
                    """,
                    (
                        payload["brand_code"],
                        payload["brand_name"],
                        payload["category_scope"],
                        payload["meituan_url"],
                        payload["eleme_url"],
                        payload["coverage_status"],
                        payload["exclusion_reason"],
                        payload["last_seen_at"],
                    ),
                )
                if brand_code in existing_map:
                    updated_count += 1
                else:
                    inserted_count += 1

        return {
            "entry_count": len(seen),
            "inserted_count": inserted_count,
            "updated_count": updated_count,
        }

    def reset_menu_catalog(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM menu_option")
            connection.execute("DELETE FROM menu_item_option_group_map")
            connection.execute("DELETE FROM menu_option_group")
            connection.execute("DELETE FROM menu_item_master")
            connection.execute("DELETE FROM menu_category")
            connection.execute("DELETE FROM menu_source")
            connection.execute("DELETE FROM brand_master")

    def save_recommendation_session(self, payload: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, str]:
        session_id = str(uuid.uuid4())
        created_at = self._now_iso()
        top_card = (result.get("recommendations") or [{}])[0]

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO recommendation_sessions (
                    session_id, created_at, entry_mode, goal_code, mood_code, scene_code,
                    budget_band, temperature_pref, caffeine_pref, dairy_avoid,
                    micro_adjusts_json, profile_json, top_k, candidate_count,
                    filtered_out_count, score_gap_top1_top2, followup_required,
                    confidence_score, top_recommendation_sku_id, top_recommendation_name,
                    session_input_json, response_meta_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    created_at,
                    payload.get("entry_mode", "quick"),
                    payload.get("goal", ""),
                    payload.get("mood", ""),
                    payload.get("scene", ""),
                    payload.get("budget_band", ""),
                    payload.get("temperature_pref", ""),
                    payload.get("caffeine_pref", ""),
                    int(bool(payload.get("dairy_avoid", False))),
                    self._dump_json(payload.get("micro_adjusts", [])),
                    self._dump_json(payload.get("profile", {})),
                    int(payload.get("top_k", 3)),
                    int(result.get("meta", {}).get("candidate_count", 0)),
                    int(result.get("meta", {}).get("filtered_out_count", 0)),
                    result.get("meta", {}).get("score_gap_top1_top2"),
                    int(bool(result.get("meta", {}).get("followup_required", False))),
                    float(result.get("meta", {}).get("confidence_score", 0.0)),
                    top_card.get("sku_id"),
                    top_card.get("sku_name"),
                    self._dump_json(payload),
                    self._dump_json(result.get("meta", {})),
                ),
            )

            for card in result.get("recommendations", []):
                connection.execute(
                    """
                    INSERT INTO session_recommendations (
                        session_id, rank_no, sku_id, sku_name, category, base_price,
                        price_band, score, explanation_tags_json, emotional_copy,
                        order_hint, debug_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        int(card.get("rank", 0)),
                        card.get("sku_id"),
                        card.get("sku_name"),
                        card.get("category"),
                        float(card.get("base_price", 0.0)),
                        card.get("price_band"),
                        float(card.get("score", 0.0)),
                        self._dump_json(card.get("explanation_tags", [])),
                        card.get("emotional_copy"),
                        card.get("order_hint"),
                        self._dump_json(card.get("debug")) if card.get("debug") is not None else None,
                    ),
                )

        return {"session_id": session_id, "created_at": created_at}

    def set_selected_sku(self, session_id: str, sku_id: str, sku_name: str) -> Optional[Dict[str, Any]]:
        selected_at = self._now_iso()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE recommendation_sessions
                SET selected_sku_id = ?, selected_sku_name = ?, selected_at = ?
                WHERE session_id = ?
                """,
                (sku_id, sku_name, selected_at, session_id),
            )
            if cursor.rowcount == 0:
                return None

        return {
            "session_id": session_id,
            "selected_sku_id": sku_id,
            "selected_sku_name": sku_name,
            "selected_at": selected_at,
        }

    def save_feedback(
        self,
        session_id: str,
        satisfaction_label: str,
        fail_reason: str,
        note: str,
        selected_sku_id: Optional[str],
        selected_sku_name: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        feedback_id = str(uuid.uuid4())
        created_at = self._now_iso()

        with self.connect() as connection:
            session_row = connection.execute(
                "SELECT session_id FROM recommendation_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if session_row is None:
                return None

            connection.execute(
                """
                INSERT INTO feedback_events (
                    feedback_id, session_id, satisfaction_label, fail_reason, note,
                    selected_sku_id, selected_sku_name, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback_id,
                    session_id,
                    satisfaction_label,
                    fail_reason or None,
                    note or None,
                    selected_sku_id,
                    selected_sku_name,
                    created_at,
                ),
            )

            connection.execute(
                """
                UPDATE recommendation_sessions
                SET latest_feedback_label = ?,
                    latest_feedback_reason = ?,
                    latest_feedback_note = ?,
                    latest_feedback_at = ?,
                    selected_sku_id = COALESCE(?, selected_sku_id),
                    selected_sku_name = COALESCE(?, selected_sku_name),
                    selected_at = CASE
                        WHEN ? IS NOT NULL THEN COALESCE(selected_at, ?)
                        ELSE selected_at
                    END
                WHERE session_id = ?
                """,
                (
                    satisfaction_label,
                    fail_reason or None,
                    note or None,
                    created_at,
                    selected_sku_id,
                    selected_sku_name,
                    selected_sku_id,
                    created_at,
                    session_id,
                ),
            )

        return {
            "feedback_id": feedback_id,
            "session_id": session_id,
            "satisfaction_label": satisfaction_label,
            "fail_reason": fail_reason,
            "note": note,
            "selected_sku_id": selected_sku_id,
            "selected_sku_name": selected_sku_name,
            "created_at": created_at,
        }

    def save_accept_record(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        accept_id = str(uuid.uuid4())
        accepted_at = self._now_iso()
        accepted_date = accepted_at[:10]
        accepted_month = accepted_date[:7]

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO accepted_drink_events (
                    accept_id, user_id, session_id, accepted_at, accepted_date, accepted_month,
                    mood_code, mood_label, budget_band, temperature_pref, caffeine_pref,
                    preference_tags_json, sku_id, sku_name, brand_code, brand_name, image_url,
                    base_price, currency_code, serving_note, encouragement_copy, source_payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accept_id,
                    user_id,
                    payload.get("session_id"),
                    accepted_at,
                    accepted_date,
                    accepted_month,
                    payload.get("mood_code", ""),
                    payload.get("mood_label"),
                    payload.get("budget_band"),
                    payload.get("temperature_pref"),
                    payload.get("caffeine_pref"),
                    self._dump_json(payload.get("preference_tags", [])),
                    payload.get("sku_id", ""),
                    payload.get("sku_name", ""),
                    payload.get("brand_code"),
                    payload.get("brand_name"),
                    payload.get("image_url"),
                    float(payload.get("base_price", 0.0)),
                    payload.get("currency_code", "CNY"),
                    payload.get("serving_note"),
                    payload.get("encouragement_copy"),
                    self._dump_json(payload),
                ),
            )

        return {
            "accept_id": accept_id,
            "user_id": user_id,
            "session_id": payload.get("session_id"),
            "accepted_at": accepted_at,
            "accepted_date": accepted_date,
            "accepted_month": accepted_month,
            "mood_code": payload.get("mood_code", ""),
            "mood_label": payload.get("mood_label"),
            "budget_band": payload.get("budget_band"),
            "temperature_pref": payload.get("temperature_pref"),
            "caffeine_pref": payload.get("caffeine_pref"),
            "preference_tags": list(payload.get("preference_tags") or []),
            "sku_id": payload.get("sku_id", ""),
            "sku_name": payload.get("sku_name", ""),
            "brand_code": payload.get("brand_code"),
            "brand_name": payload.get("brand_name"),
            "image_url": payload.get("image_url"),
            "base_price": float(payload.get("base_price", 0.0)),
            "currency_code": payload.get("currency_code", "CNY"),
            "serving_note": payload.get("serving_note"),
            "encouragement_copy": payload.get("encouragement_copy"),
        }

    def list_accept_records(self, user_id: str, limit: int = 300) -> List[Dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM accepted_drink_events
                WHERE user_id = ?
                ORDER BY datetime(accepted_at) DESC, rowid DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._accept_record_from_row(row) for row in rows]

    def get_accept_records_for_month(self, user_id: str, month: str) -> List[Dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM accepted_drink_events
                WHERE user_id = ? AND accepted_month = ?
                ORDER BY datetime(accepted_at) DESC, rowid DESC
                """,
                (user_id, month),
            ).fetchall()
        return [self._accept_record_from_row(row) for row in rows]

    def get_accept_recap(self, user_id: str, month: str, recent_limit: int = 6) -> Dict[str, Any]:
        records = self.get_accept_records_for_month(user_id=user_id, month=month)
        mood_counts: Dict[str, Dict[str, Any]] = {}
        preference_counts: Dict[str, int] = {}
        brand_counts: Dict[str, Dict[str, Any]] = {}
        accepted_days: List[str] = []

        for record in records:
            mood_code = str(record.get("mood_code") or "")
            if mood_code not in mood_counts:
                mood_counts[mood_code] = {
                    "mood_code": mood_code,
                    "mood_label": record.get("mood_label"),
                    "count": 0,
                }
            mood_counts[mood_code]["count"] += 1

            for tag in record.get("preference_tags") or []:
                preference_counts[tag] = preference_counts.get(tag, 0) + 1

            brand_code = str(record.get("brand_code") or "")
            if brand_code:
                if brand_code not in brand_counts:
                    brand_counts[brand_code] = {
                        "brand_code": brand_code,
                        "brand_name": record.get("brand_name") or brand_code,
                        "count": 0,
                    }
                brand_counts[brand_code]["count"] += 1

            accepted_date = str(record.get("accepted_date") or "")
            if accepted_date:
                accepted_days.append(accepted_date)

        sorted_moods = sorted(
            mood_counts.values(),
            key=lambda item: (-int(item.get("count", 0)), str(item.get("mood_code") or "")),
        )
        sorted_preferences = sorted(
            (
                {"tag_code": tag_code, "count": count}
                for tag_code, count in preference_counts.items()
            ),
            key=lambda item: (-int(item["count"]), item["tag_code"]),
        )
        sorted_brands = sorted(
            brand_counts.values(),
            key=lambda item: (-int(item.get("count", 0)), str(item.get("brand_name") or "")),
        )

        longest_streak = 0
        current_streak = 0
        last_date: Optional[datetime.date] = None
        for day_str in sorted(set(accepted_days)):
            try:
                day = datetime.strptime(day_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if last_date is not None and (day - last_date).days == 1:
                current_streak += 1
            else:
                current_streak = 1
            longest_streak = max(longest_streak, current_streak)
            last_date = day

        return {
            "user_id": user_id,
            "month": month,
            "record_count": len(records),
            "mood_counts": sorted_moods,
            "preference_counts": sorted_preferences,
            "brand_counts": sorted_brands,
            "longest_streak_days": longest_streak,
            "recent_accepts": records[:recent_limit],
        }

    def list_recent_accepted_brands(self, user_id: str, limit: int = 3) -> List[str]:
        items = self.list_accept_records(user_id=user_id, limit=max(limit, 1))
        brand_codes: List[str] = []
        for item in items:
            brand_code = str(item.get("brand_code") or "").strip()
            if brand_code and brand_code not in brand_codes:
                brand_codes.append(brand_code)
            if len(brand_codes) >= limit:
                break
        return brand_codes

    def get_simple_catalog_overview(self) -> Dict[str, Any]:
        with self.connect() as connection:
            visible_row = connection.execute(
                """
                SELECT COUNT(*) AS visible_count
                FROM simple_drink_catalog
                WHERE active_flag = 1 AND verification_status = ?
                """,
                (SIMPLE_VISIBLE_STATUS,),
            ).fetchone()
            total_row = connection.execute(
                "SELECT COUNT(*) AS total_count FROM simple_drink_catalog"
            ).fetchone()
            lifecycle_rows = connection.execute(
                """
                SELECT COALESCE(lifecycle_code, 'permanent') AS lifecycle_code, COUNT(*) AS item_count
                FROM simple_drink_catalog
                WHERE active_flag = 1
                GROUP BY COALESCE(lifecycle_code, 'permanent')
                """
            ).fetchall()
        return {
            "visible_count": int(visible_row["visible_count"] or 0),
            "total_count": int(total_row["total_count"] or 0),
            "lifecycle_counts": [
                {
                    "lifecycle_code": str(row["lifecycle_code"] or "permanent"),
                    "lifecycle_label": SIMPLE_LIFECYCLE_LABELS.get(str(row["lifecycle_code"] or "permanent"), "常驻"),
                    "item_count": int(row["item_count"] or 0),
                }
                for row in lifecycle_rows
            ],
        }

    def list_simple_drink_catalog(
        self,
        visible_only: bool = True,
    ) -> List[Dict[str, Any]]:
        clauses = ["active_flag = 1"]
        params: List[Any] = []
        if visible_only:
            clauses.append("verification_status = ?")
            params.append(SIMPLE_VISIBLE_STATUS)
        where_sql = " AND ".join(clauses)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM simple_drink_catalog
                WHERE {where_sql}
                ORDER BY brand_name ASC, base_price_cny ASC, item_name ASC
                """,
                params,
            ).fetchall()
        return [self._simple_catalog_item_from_row(row) for row in rows]

    def _load_sku_attribute_overrides(self, connection: sqlite3.Connection) -> Dict[Tuple[str, str], Dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT brand_code, item_name, attribute_overrides_json, display_tags_override_json, note, updated_at
            FROM sku_attribute_overrides
            """
        ).fetchall()
        override_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for row in rows:
            override_map[
                (
                    str(row["brand_code"] or "").strip(),
                    self._normalize_item_name_for_match(str(row["item_name"] or "")),
                )
            ] = {
                "attribute_overrides": self._loads_json(row["attribute_overrides_json"], {}),
                "display_tags_override": self._loads_json(row["display_tags_override_json"], []),
                "note": str(row["note"] or "").strip(),
                "updated_at": str(row["updated_at"] or "").strip(),
            }
        return override_map

    def _load_sku_visual_overrides(self, connection: sqlite3.Connection) -> Dict[Tuple[str, str], Dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT
                brand_code,
                item_name,
                image_mode,
                ai_image_url,
                badge_text,
                prompt_text,
                prompt_version,
                prompt_payload_json,
                note,
                updated_at
            FROM sku_visual_overrides
            """
        ).fetchall()
        override_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for row in rows:
            override_map[
                (
                    str(row["brand_code"] or "").strip(),
                    self._normalize_item_name_for_match(str(row["item_name"] or "")),
                )
            ] = {
                "image_mode": str(row["image_mode"] or "source").strip() or "source",
                "ai_image_url": str(row["ai_image_url"] or "").strip(),
                "badge_text": str(row["badge_text"] or "").strip(),
                "prompt_text": str(row["prompt_text"] or "").strip(),
                "prompt_version": str(row["prompt_version"] or "").strip(),
                "prompt_payload": self._loads_json(row["prompt_payload_json"], {}),
                "note": str(row["note"] or "").strip(),
                "updated_at": str(row["updated_at"] or "").strip(),
            }
        return override_map

    def _resolve_generated_asset_path(self, generated_dir: Path, asset_url: str) -> Optional[Path]:
        url = str(asset_url or "").strip()
        if not url.startswith("/generated/"):
            return None
        relative_path = url[len("/generated/") :].replace("/", "\\")
        asset_path = generated_dir / Path(relative_path)
        if not asset_path.exists() or not asset_path.is_file() or asset_path.stat().st_size <= 0:
            return None
        return asset_path

    def _apply_visual_override(
        self,
        generated_dir: Path,
        brand_code: str,
        item_name: str,
        source_url: str,
        localized_image: Dict[str, Any],
        visual_override: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(visual_override, dict):
            return localized_image
        image_mode = str(visual_override.get("image_mode") or "source").strip() or "source"
        if image_mode == "source":
            return localized_image
        if image_mode not in {"ai_illustration", "user_uploaded", "brand_logo", "brand_collage", "brand_fallback"}:
            return localized_image
        image_url = str(visual_override.get("ai_image_url") or "").strip()
        if not image_url:
            return localized_image
        asset_path = self._resolve_generated_asset_path(generated_dir, image_url)
        if asset_path is None:
            return localized_image

        base_meta = dict(localized_image.get("meta") or {})
        prompt_payload = visual_override.get("prompt_payload") if isinstance(visual_override.get("prompt_payload"), dict) else {}
        badge_text_map = {
            "ai_illustration": "AI\u793a\u610f\u56fe",
            "user_uploaded": "\u7528\u6237\u4e0a\u4f20",
            "brand_logo": "\u54c1\u724cLOGO",
            "brand_collage": "\u5b98\u65b9\u5408\u62cd",
            "brand_fallback": "\u54c1\u724c\u5907\u7528\u56fe",
        }
        provenance_map = {
            "ai_illustration": "ai_generated_illustration",
            "user_uploaded": "user_uploaded",
            "brand_logo": "brand_logo",
            "brand_collage": "brand_collage",
            "brand_fallback": "brand_fallback",
        }
        quality_map = {
            "ai_illustration": "ai_illustration",
            "user_uploaded": "user_uploaded",
            "brand_logo": "brand_logo",
            "brand_collage": "brand_collage",
            "brand_fallback": "brand_fallback",
        }
        badge_text = str(visual_override.get("badge_text") or badge_text_map.get(image_mode, "AI\u793a\u610f\u56fe")).strip() or badge_text_map.get(image_mode, "AI\u793a\u610f\u56fe")
        prompt_version = str(visual_override.get("prompt_version") or "anime_product_v1").strip() or "anime_product_v1"
        updated_meta = {
            "image_provenance": provenance_map.get(image_mode, "ai_generated_illustration"),
            "source_page_url": str(base_meta.get("source_page_url") or source_url or "").strip(),
            "crop_fallback_used": False,
            "localized_at": self._now_iso(),
            "quality_tier": quality_map.get(image_mode, "ai_illustration"),
            "badge_text": badge_text,
            "prompt_version": prompt_version,
            "visual_override_applied": True,
            "visual_override_mode": image_mode,
        }
        if prompt_payload:
            updated_meta["prompt_payload"] = prompt_payload
        if str(visual_override.get("note") or "").strip():
            updated_meta["visual_override_note"] = str(visual_override.get("note") or "").strip()

        return {
            "image_url": image_url,
            "meta": updated_meta,
        }

    def rebuild_simple_drink_catalog(self, generated_dir: Path) -> Dict[str, Any]:
        generated_dir.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            default_rows = connection.execute(
                """
                SELECT
                    m.item_id,
                    g.group_type,
                    o.option_name
                FROM menu_item_option_group_map m
                JOIN menu_option_group g
                    ON g.group_id = m.group_id
                JOIN menu_option o
                    ON o.group_id = g.group_id
                WHERE o.is_default = 1 AND o.sold_out = 0
                ORDER BY m.sort_order ASC, o.sort_order ASC, o.option_name ASC
                """
            ).fetchall()
            default_map: Dict[str, Dict[str, str]] = {}
            for row in default_rows:
                item_defaults = default_map.setdefault(row["item_id"], {})
                item_defaults.setdefault(str(row["group_type"] or "unknown"), str(row["option_name"] or ""))

            item_rows = connection.execute(
                """
                SELECT
                    i.item_id,
                    i.brand_code,
                    b.brand_name,
                    i.item_name,
                    i.description,
                    i.image_url,
                    i.base_price,
                    i.currency_code,
                    i.available_hot,
                    i.available_cold,
                    i.caffeine_level,
                    i.launch_date,
                    i.lifecycle_code,
                    i.lifecycle_label,
                    i.lifecycle_evidence_json,
                    i.normalized_category,
                    i.active_flag,
                    i.raw_json,
                    i.source_code,
                    s.source_status,
                    s.source_type,
                    s.source_url,
                    s.imported_at,
                    s.country_code,
                    s.currency_code AS source_currency_code
                FROM menu_item_master i
                JOIN brand_master b
                    ON b.brand_code = i.brand_code
                JOIN menu_source s
                    ON s.source_code = i.source_code
                WHERE COALESCE(s.source_status, '') NOT LIKE 'archived_%'
                ORDER BY b.brand_name ASC, i.item_name ASC
                """
            ).fetchall()

            override_map = self._load_sku_attribute_overrides(connection)
            visual_override_map = self._load_sku_visual_overrides(connection)
            connection.execute("DELETE FROM simple_drink_catalog")

            visible_count = 0
            localized_count = 0
            brand_fallback_count = 0
            hidden_count = 0
            duplicate_group_count = 0
            now = self._now_iso()
            candidate_rows: List[Dict[str, Any]] = []
            brand_best_images: Dict[str, Dict[str, Any]] = {}
            for row in item_rows:
                defaults = default_map.get(row["item_id"], {})
                raw_meta = self._loads_json(row["raw_json"], {})
                raw_meta = dict(raw_meta) if isinstance(raw_meta, dict) else {}
                official_snapshot = raw_meta.get("official_snapshot") if isinstance(raw_meta, dict) else {}
                source_snapshot = raw_meta.get("source_snapshot") if isinstance(raw_meta, dict) else {}
                price_context = raw_meta.get("price_context") if isinstance(raw_meta, dict) else {}
                verification_meta = raw_meta.get("content_verification") if isinstance(raw_meta, dict) else {}
                lifecycle_meta = {
                    "launch_date": str(row["launch_date"] or raw_meta.get("launch_date") or "").strip(),
                    "lifecycle_code": str(row["lifecycle_code"] or raw_meta.get("lifecycle_code") or "").strip(),
                    "lifecycle_label": str(row["lifecycle_label"] or raw_meta.get("lifecycle_label") or "").strip(),
                    "lifecycle_evidence_json": str(row["lifecycle_evidence_json"] or raw_meta.get("lifecycle_evidence_json") or "").strip(),
                }
                image_meta_hint = {}
                if isinstance(official_snapshot, dict):
                    image_meta_hint = official_snapshot.get("image_meta") or {}
                if not image_meta_hint and isinstance(source_snapshot, dict):
                    image_meta_hint = source_snapshot.get("image_meta") or {}
                source_url = (
                    (official_snapshot or {}).get("source_url")
                    or (source_snapshot or {}).get("source_url")
                    or (price_context or {}).get("source_url")
                    or (verification_meta or {}).get("source_url")
                    or row["source_url"]
                )
                verified_at = (verification_meta or {}).get("verified_at") or row["imported_at"]
                original_image_url = (
                    (official_snapshot or {}).get("image_url")
                    or (source_snapshot or {}).get("image_url")
                    or row["image_url"]
                    or ""
                )
                localized_image = self._localize_image(
                    image_url=original_image_url,
                    generated_dir=generated_dir,
                    brand_code=str(row["brand_code"] or "brand"),
                    item_id=str(row["item_id"] or ""),
                    image_meta_hint=image_meta_hint,
                    source_url=str(source_url or ""),
                )
                visual_override_key = (
                    str(row["brand_code"] or ""),
                    self._normalize_item_name_for_match(str(row["item_name"] or "")),
                )
                localized_image = self._apply_visual_override(
                    generated_dir=generated_dir,
                    brand_code=str(row["brand_code"] or ""),
                    item_name=str(row["item_name"] or ""),
                    source_url=str(source_url or ""),
                    localized_image=localized_image,
                    visual_override=visual_override_map.get(visual_override_key),
                )
                temperature_type = self._derive_temperature_type(
                    item_name=str(row["item_name"] or ""),
                    normalized_category=str(row["normalized_category"] or ""),
                    available_hot=bool(row["available_hot"]),
                    available_cold=bool(row["available_cold"]),
                )
                lifecycle_payload = self._derive_lifecycle_payload(
                    item_name=str(row["item_name"] or ""),
                    description=str(row["description"] or ""),
                    normalized_category=str(row["normalized_category"] or ""),
                    source_code=str(row["source_code"] or ""),
                    raw_meta={
                        **raw_meta,
                        "launch_date": lifecycle_meta["launch_date"],
                        "lifecycle_code": lifecycle_meta["lifecycle_code"],
                        "lifecycle_label": lifecycle_meta["lifecycle_label"],
                        "lifecycle_evidence_json": lifecycle_meta["lifecycle_evidence_json"],
                    },
                )
                default_temperature_text = self._derive_default_temperature_text(
                    temperature_type=temperature_type,
                    default_temperature=defaults.get("temperature", ""),
                    default_ice=defaults.get("ice_level", ""),
                )
                default_sweetness_text = self._derive_default_sweetness_text(defaults.get("sugar_level", ""))
                caffeine_level_code = self._derive_caffeine_level_code(
                    item_name=str(row["item_name"] or ""),
                    description=str(row["description"] or ""),
                    normalized_category=str(row["normalized_category"] or ""),
                    caffeine_level=float(row["caffeine_level"] or 0.0),
                )
                override_key = (
                    str(row["brand_code"] or ""),
                    self._normalize_item_name_for_match(str(row["item_name"] or "")),
                )
                tag_payload = self._derive_simple_tag_payload(
                    item_name=str(row["item_name"] or ""),
                    description=str(row["description"] or ""),
                    normalized_category=str(row["normalized_category"] or ""),
                    temperature_type=temperature_type,
                    caffeine_level_code=caffeine_level_code,
                    default_sweetness_text=default_sweetness_text,
                    default_temperature_text=default_temperature_text,
                    overrides=override_map.get(override_key, {}),
                )
                mood_payload = self._derive_simple_mood_tag_payload(
                    item_name=str(row["item_name"] or ""),
                    description=str(row["description"] or ""),
                    normalized_category=str(row["normalized_category"] or ""),
                    temperature_type=temperature_type,
                    caffeine_level_code=caffeine_level_code,
                    display_tags=tag_payload["display_tags"],
                )
                verification_status = self._derive_simple_verification_status(
                    active_flag=bool(row["active_flag"]),
                    source_status=str(row["source_status"] or ""),
                    source_type=str(row["source_type"] or ""),
                    country_code=str(row["country_code"] or ""),
                    currency_code=str(row["source_currency_code"] or row["currency_code"] or ""),
                    image_url=localized_image["image_url"],
                    source_url=str(source_url or ""),
                    image_meta=localized_image["meta"],
                )
                candidate_row = {
                    "item_id": row["item_id"],
                    "brand_code": row["brand_code"],
                    "brand_name": row["brand_name"],
                    "item_name": row["item_name"],
                    "image_url": localized_image["image_url"],
                    "base_price_cny": float(row["base_price"] or 0.0),
                    "default_temperature_text": default_temperature_text,
                    "default_sweetness_text": default_sweetness_text,
                    "temperature_type": temperature_type,
                    "caffeine_level_code": caffeine_level_code,
                    "launch_date": lifecycle_payload["launch_date"],
                    "lifecycle_code": lifecycle_payload["lifecycle_code"],
                    "lifecycle_label": lifecycle_payload["lifecycle_label"],
                    "lifecycle_evidence_json": lifecycle_payload["lifecycle_evidence_json"],
                    "tags_json": self._dump_json(tag_payload["display_tags"]),
                    "source_url": source_url,
                    "verification_status": verification_status,
                    "last_verified_at": verified_at,
                    "active_flag": int(bool(row["active_flag"])),
                    "source_code": row["source_code"],
                    "original_image_url": original_image_url,
                    "image_meta_json": self._dump_json(localized_image["meta"]),
                    "normalized_category": row["normalized_category"],
                    "description": row["description"],
                    "tag_evidence_json": self._dump_json(tag_payload["evidence"]),
                    "mood_tag_code": mood_payload["mood_tag_code"],
                    "mood_tag_evidence_json": self._dump_json(mood_payload["evidence"]),
                    "created_at": now,
                    "updated_at": now,
                    "_dedupe_key": self._build_simple_dedupe_key(
                        brand_code=str(row["brand_code"] or ""),
                        item_name=str(row["item_name"] or ""),
                        temperature_type=temperature_type,
                    ),
                    "_rank": self._rank_simple_catalog_candidate(
                        verification_status=verification_status,
                        source_type=str(row["source_type"] or ""),
                        image_meta=localized_image["meta"],
                        description=str(row["description"] or ""),
                        imported_at=str(row["imported_at"] or ""),
                    ),
                }
                candidate_rows.append(candidate_row)
                if candidate_row["image_url"]:
                    localized_count += 1
                    image_meta_for_fallback = localized_image.get("meta") if isinstance(localized_image.get("meta"), dict) else {}
                    image_provenance_for_fallback = str(image_meta_for_fallback.get("image_provenance") or "").strip()
                    if image_provenance_for_fallback not in {
                        "user_uploaded",
                        "brand_fallback",
                        "brand_logo",
                        "brand_collage",
                        "ai_generated_illustration",
                    }:
                        brand_code_key = str(candidate_row["brand_code"] or "").strip()
                        current_best = brand_best_images.get(brand_code_key)
                        if current_best is None or candidate_row["_rank"] > current_best["_rank"]:
                            brand_best_images[brand_code_key] = dict(candidate_row)

            deduped_rows: List[Dict[str, Any]] = []
            grouped_candidates: Dict[str, List[Dict[str, Any]]] = {}
            for candidate in candidate_rows:
                grouped_candidates.setdefault(candidate["_dedupe_key"], []).append(candidate)

            for dedupe_key, grouped in grouped_candidates.items():
                if len(grouped) > 1:
                    duplicate_group_count += 1
                grouped.sort(key=lambda item: item["_rank"], reverse=True)
                chosen = dict(grouped[0])
                chosen.pop("_dedupe_key", None)
                chosen.pop("_rank", None)
                deduped_rows.append(chosen)

            self._disambiguate_simple_catalog_names(deduped_rows)

            for row in deduped_rows:
                if row.get("image_url"):
                    continue
                fallback = brand_best_images.get(str(row.get("brand_code") or "").strip())
                fallback_image_url = str((fallback or {}).get("image_url") or "").strip()
                if not fallback or not fallback_image_url or fallback.get("item_id") == row.get("item_id"):
                    continue
                fallback_meta = self._loads_json(fallback.get("image_meta_json"), {})
                if not isinstance(fallback_meta, dict):
                    fallback_meta = {}
                fallback_meta.update(
                    {
                        "image_provenance": "brand_fallback",
                        "quality_tier": "brand_fallback",
                        "source_page_url": str(fallback.get("source_url") or "").strip(),
                        "localized_at": self._now_iso(),
                        "brand_fallback_source_item_id": fallback.get("item_id"),
                        "brand_fallback_source_item_name": fallback.get("item_name"),
                    }
                )
                row["image_url"] = fallback_image_url
                row["original_image_url"] = str(fallback.get("original_image_url") or fallback_image_url).strip()
                row["source_url"] = str(row.get("source_url") or fallback.get("source_url") or "").strip()
                row["image_meta_json"] = self._dump_json(fallback_meta)
                brand_fallback_count += 1

            for row in deduped_rows:
                if row["verification_status"] == SIMPLE_VISIBLE_STATUS:
                    visible_count += 1
                else:
                    hidden_count += 1

                connection.execute(
                    """
                    INSERT INTO simple_drink_catalog (
                        item_id, brand_code, brand_name, item_name, image_url, base_price_cny,
                        default_temperature_text, default_sweetness_text, temperature_type,
                        caffeine_level_code, tags_json, source_url, verification_status,
                        last_verified_at, active_flag, source_code, launch_date,
                        lifecycle_code, lifecycle_label, lifecycle_evidence_json,
                        original_image_url, image_meta_json, normalized_category, description, tag_evidence_json,
                        mood_tag_code, mood_tag_evidence_json,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["item_id"],
                        row["brand_code"],
                        row["brand_name"],
                        row["item_name"],
                        row["image_url"],
                        row["base_price_cny"],
                        row["default_temperature_text"],
                        row["default_sweetness_text"],
                        row["temperature_type"],
                        row["caffeine_level_code"],
                        row["tags_json"],
                        row["source_url"],
                        row["verification_status"],
                        row["last_verified_at"],
                        row["active_flag"],
                        row["source_code"],
                        row["launch_date"],
                        row["lifecycle_code"],
                        row["lifecycle_label"],
                        row["lifecycle_evidence_json"],
                        row["original_image_url"],
                        row["image_meta_json"],
                        row["normalized_category"],
                        row["description"],
                        row["tag_evidence_json"],
                        row["mood_tag_code"],
                        row["mood_tag_evidence_json"],
                        row["created_at"],
                        row["updated_at"],
                    ),
                )

        return {
            "total_count": len(item_rows),
            "deduped_count": len(deduped_rows),
            "visible_count": visible_count,
            "hidden_count": hidden_count,
            "localized_count": localized_count,
            "brand_fallback_count": brand_fallback_count,
            "duplicate_group_count": duplicate_group_count,
            "duplicates_removed_count": max(len(candidate_rows) - len(deduped_rows), 0),
        }

    def get_history(self, limit: int = 12) -> List[Dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    session_id,
                    created_at,
                    goal_code,
                    mood_code,
                    scene_code,
                    budget_band,
                    temperature_pref,
                    caffeine_pref,
                    top_recommendation_sku_id,
                    top_recommendation_name,
                    selected_sku_id,
                    selected_sku_name,
                    latest_feedback_label,
                    latest_feedback_reason,
                    latest_feedback_note,
                    latest_feedback_at,
                    confidence_score,
                    followup_required
                FROM recommendation_sessions
                ORDER BY datetime(created_at) DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            history: List[Dict[str, Any]] = []
            for row in rows:
                recommendations = connection.execute(
                    """
                    SELECT rank_no, sku_id, sku_name, category, score, price_band
                    FROM session_recommendations
                    WHERE session_id = ?
                    ORDER BY rank_no ASC
                    LIMIT 3
                    """,
                    (row["session_id"],),
                ).fetchall()

                history.append(
                    {
                        "session_id": row["session_id"],
                        "created_at": row["created_at"],
                        "goal": row["goal_code"],
                        "mood": row["mood_code"],
                        "scene": row["scene_code"],
                        "budget_band": row["budget_band"],
                        "temperature_pref": row["temperature_pref"],
                        "caffeine_pref": row["caffeine_pref"],
                        "top_recommendation": {
                            "sku_id": row["top_recommendation_sku_id"],
                            "sku_name": row["top_recommendation_name"],
                        },
                        "selected_item": {
                            "sku_id": row["selected_sku_id"],
                            "sku_name": row["selected_sku_name"],
                        }
                        if row["selected_sku_id"]
                        else None,
                        "latest_feedback": {
                            "label": row["latest_feedback_label"],
                            "reason": row["latest_feedback_reason"],
                            "note": row["latest_feedback_note"],
                            "created_at": row["latest_feedback_at"],
                        }
                        if row["latest_feedback_label"]
                        else None,
                        "confidence_score": row["confidence_score"],
                        "followup_required": bool(row["followup_required"]),
                        "recommendation_preview": [dict(item) for item in recommendations],
                    }
                )
            return history

    def get_session_detail(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as connection:
            session = connection.execute(
                """
                SELECT *
                FROM recommendation_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if session is None:
                return None

            recommendations = connection.execute(
                """
                SELECT rank_no, sku_id, sku_name, category, base_price, price_band, score,
                       explanation_tags_json, emotional_copy, order_hint, debug_json
                FROM session_recommendations
                WHERE session_id = ?
                ORDER BY rank_no ASC
                """,
                (session_id,),
            ).fetchall()

            return {
                "session_id": session["session_id"],
                "created_at": session["created_at"],
                "session_input": self._loads_json(session["session_input_json"], {}),
                "response_meta": self._loads_json(session["response_meta_json"], {}),
                "selected_item": {
                    "sku_id": session["selected_sku_id"],
                    "sku_name": session["selected_sku_name"],
                    "selected_at": session["selected_at"],
                }
                if session["selected_sku_id"]
                else None,
                "latest_feedback": {
                    "label": session["latest_feedback_label"],
                    "reason": session["latest_feedback_reason"],
                    "note": session["latest_feedback_note"],
                    "created_at": session["latest_feedback_at"],
                }
                if session["latest_feedback_label"]
                else None,
                "recommendations": [
                    {
                        "rank": row["rank_no"],
                        "sku_id": row["sku_id"],
                        "sku_name": row["sku_name"],
                        "category": row["category"],
                        "base_price": row["base_price"],
                        "price_band": row["price_band"],
                        "score": row["score"],
                        "explanation_tags": self._loads_json(row["explanation_tags_json"], []),
                        "emotional_copy": row["emotional_copy"],
                        "order_hint": row["order_hint"],
                        "debug": self._loads_json(row["debug_json"], None) if row["debug_json"] else None,
                    }
                    for row in recommendations
                ],
            }

    def get_profile_memory(self, user_id: str) -> Dict[str, Any]:
        record = self.get_profile_memory_record(user_id)
        return record["profile"] if record else {}

    def get_profile_memory_record(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT profile_json, updated_at FROM user_profile_memory WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "user_id": user_id,
                "updated_at": row["updated_at"],
                "profile": self._loads_json(row["profile_json"], {}),
            }

    def save_profile_memory(self, user_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        updated_at = self._now_iso()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO user_profile_memory (user_id, profile_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    profile_json = excluded.profile_json,
                    updated_at = excluded.updated_at
                """,
                (user_id, self._dump_json(profile), updated_at),
            )
        return {
            "user_id": user_id,
            "updated_at": updated_at,
            "profile": profile,
        }

    def replace_menu_source_import(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        brand = dict(payload.get("brand") or {})
        source = dict(payload.get("source") or {})
        categories = list(payload.get("categories") or [])
        items = list(payload.get("items") or [])
        option_groups = list(payload.get("option_groups") or [])
        item_group_maps = list(payload.get("item_group_maps") or [])

        brand_code = str(brand.get("brand_code") or "").strip()
        source_code = str(source.get("source_code") or "").strip()
        if not brand_code or not source_code:
            raise ValueError("Both brand_code and source_code are required for menu imports.")

        imported_at = str(source.get("imported_at") or self._now_iso())
        option_count = sum(len(group.get("options") or []) for group in option_groups)
        now = self._now_iso()

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO brand_master (
                    brand_code, brand_name, brand_name_local, channel_name,
                    default_currency_code, brand_country_code, brand_notes,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(brand_code) DO UPDATE SET
                    brand_name = excluded.brand_name,
                    brand_name_local = excluded.brand_name_local,
                    channel_name = excluded.channel_name,
                    default_currency_code = excluded.default_currency_code,
                    brand_country_code = excluded.brand_country_code,
                    brand_notes = excluded.brand_notes,
                    updated_at = excluded.updated_at
                """,
                (
                    brand_code,
                    brand.get("brand_name", brand_code),
                    brand.get("brand_name_local"),
                    brand.get("channel_name"),
                    brand.get("default_currency_code"),
                    brand.get("brand_country_code"),
                    brand.get("brand_notes"),
                    now,
                    now,
                ),
            )

            connection.execute("DELETE FROM menu_item_master WHERE source_code = ?", (source_code,))
            connection.execute("DELETE FROM menu_option_group WHERE source_code = ?", (source_code,))
            connection.execute("DELETE FROM menu_category WHERE source_code = ?", (source_code,))
            connection.execute("DELETE FROM menu_source WHERE source_code = ?", (source_code,))

            connection.execute(
                """
                INSERT INTO menu_source (
                    source_code, brand_code, source_type, source_name, source_url, source_api_url,
                    store_external_id, store_name, address_text, city, region, country_code,
                    currency_code, channel_code, imported_at, source_status, item_count,
                    option_group_count, option_count, raw_store_json, raw_menu_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_code,
                    brand_code,
                    source.get("source_type", "api"),
                    source.get("source_name", source_code),
                    source.get("source_url"),
                    source.get("source_api_url"),
                    source.get("store_external_id"),
                    source.get("store_name"),
                    source.get("address_text"),
                    source.get("city"),
                    source.get("region"),
                    source.get("country_code"),
                    source.get("currency_code", brand.get("default_currency_code") or "USD"),
                    source.get("channel_code"),
                    imported_at,
                    source.get("source_status", "active"),
                    len(items),
                    len(option_groups),
                    option_count,
                    self._dump_json(source.get("raw_store_json"))
                    if source.get("raw_store_json") is not None
                    else None,
                    self._dump_json(source.get("raw_menu_json"))
                    if source.get("raw_menu_json") is not None
                    else None,
                ),
            )

            for category in categories:
                connection.execute(
                    """
                    INSERT INTO menu_category (
                        category_id, source_code, category_name, sort_order, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        category["category_id"],
                        source_code,
                        category["category_name"],
                        int(category.get("sort_order", 0)),
                        self._dump_json(category.get("raw_json")) if category.get("raw_json") is not None else None,
                    ),
                )

            for item in items:
                raw_meta = dict(item.get("raw_json") or {})
                launch_date = str(item.get("launch_date") or raw_meta.get("launch_date") or "").strip()
                raw_meta.setdefault("launch_date", launch_date)
                if item.get("lifecycle_code"):
                    raw_meta.setdefault("lifecycle_code", item.get("lifecycle_code"))
                if item.get("lifecycle_status"):
                    raw_meta.setdefault("lifecycle_status", item.get("lifecycle_status"))
                if item.get("lifecycle_label"):
                    raw_meta.setdefault("lifecycle_label", item.get("lifecycle_label"))
                lifecycle_payload = self._derive_lifecycle_payload(
                    item_name=str(item.get("item_name") or ""),
                    description=str(item.get("description") or ""),
                    normalized_category=str(item.get("normalized_category") or ""),
                    source_code=source_code,
                    raw_meta=raw_meta,
                )
                connection.execute(
                    """
                    INSERT INTO menu_item_master (
                        item_id, brand_code, source_code, category_id, external_item_id, item_code,
                        item_name, item_name_local, display_name, description, image_url, category_name,
                        normalized_category, base_price, currency_code, price_band, launch_date,
                        lifecycle_code, lifecycle_label, lifecycle_evidence_json, available_hot,
                        available_cold, dairy_flag, caffeine_level, tea_intensity, milk_intensity,
                        fruit_intensity, sweetness_intensity, refresh_intensity, comfort_intensity,
                        energy_intensity, indulgence_intensity, heaviness_intensity, mood_tags_json,
                        scene_tags_json, profile_tags_json, option_summary_json, raw_json, active_flag,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["item_id"],
                        brand_code,
                        source_code,
                        item.get("category_id"),
                        item["external_item_id"],
                        item.get("item_code"),
                        item["item_name"],
                        item.get("item_name_local"),
                        item.get("display_name"),
                        item.get("description"),
                        item.get("image_url"),
                        item.get("category_name"),
                        item.get("normalized_category", "tea"),
                        float(item.get("base_price", 0.0)),
                        item.get("currency_code", source.get("currency_code", "USD")),
                        item.get("price_band", "mid"),
                        lifecycle_payload["launch_date"],
                        lifecycle_payload["lifecycle_code"],
                        lifecycle_payload["lifecycle_label"],
                        lifecycle_payload["lifecycle_evidence_json"],
                        int(bool(item.get("available_hot", False))),
                        int(bool(item.get("available_cold", True))),
                        int(bool(item.get("dairy_flag", False))),
                        float(item.get("caffeine_level", 0.0)),
                        float(item.get("tea_intensity", 0.0)),
                        float(item.get("milk_intensity", 0.0)),
                        float(item.get("fruit_intensity", 0.0)),
                        float(item.get("sweetness_intensity", 0.0)),
                        float(item.get("refresh_intensity", 0.0)),
                        float(item.get("comfort_intensity", 0.0)),
                        float(item.get("energy_intensity", 0.0)),
                        float(item.get("indulgence_intensity", 0.0)),
                        float(item.get("heaviness_intensity", 0.0)),
                        self._dump_json(item.get("mood_tags", [])),
                        self._dump_json(item.get("scene_tags", [])),
                        self._dump_json(item.get("profile_tags", [])),
                        self._dump_json(item.get("option_summary", [])),
                        self._dump_json(item.get("raw_json")) if item.get("raw_json") is not None else None,
                        int(bool(item.get("active_flag", True))),
                        now,
                        now,
                    ),
                )

            for group in option_groups:
                connection.execute(
                    """
                    INSERT INTO menu_option_group (
                        group_id, source_code, external_group_id, group_name,
                        required, limit_count, supports_multiple, group_type,
                        sort_order, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        group["group_id"],
                        source_code,
                        group["external_group_id"],
                        group["group_name"],
                        int(bool(group.get("required", False))),
                        int(group.get("limit_count", 0)),
                        int(bool(group.get("supports_multiple", False))),
                        group.get("group_type"),
                        int(group.get("sort_order", 0)),
                        self._dump_json(group.get("raw_json")) if group.get("raw_json") is not None else None,
                    ),
                )

                for option in group.get("options") or []:
                    connection.execute(
                        """
                        INSERT INTO menu_option (
                            option_id, group_id, option_name, external_option_code,
                            price_delta, is_default, sold_out, option_tags_json,
                            sort_order, raw_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            option["option_id"],
                            group["group_id"],
                            option["option_name"],
                            option.get("external_option_code"),
                            float(option.get("price_delta", 0.0)),
                            int(bool(option.get("is_default", False))),
                            int(bool(option.get("sold_out", False))),
                            self._dump_json(option.get("option_tags", [])),
                            int(option.get("sort_order", 0)),
                            self._dump_json(option.get("raw_json")) if option.get("raw_json") is not None else None,
                        ),
                    )

            for item_group_map in item_group_maps:
                connection.execute(
                    """
                    INSERT INTO menu_item_option_group_map (item_id, group_id, sort_order)
                    VALUES (?, ?, ?)
                    """,
                    (
                        item_group_map["item_id"],
                        item_group_map["group_id"],
                        int(item_group_map.get("sort_order", 0)),
                    ),
                )

        return {
            "brand_code": brand_code,
            "source_code": source_code,
            "item_count": len(items),
            "option_group_count": len(option_groups),
            "option_count": option_count,
            "imported_at": imported_at,
        }

    def get_menu_overview(self, consumer_visible: bool = False) -> Dict[str, Any]:
        with self.connect() as connection:
            if consumer_visible:
                source_clause, source_params = self._consumer_source_clause("s")
                row = connection.execute(
                    f"""
                    SELECT
                        COUNT(DISTINCT b.brand_code) AS brand_count,
                        COUNT(DISTINCT s.source_code) AS source_count,
                        COUNT(DISTINCT CASE WHEN i.active_flag = 1 THEN i.item_id END) AS item_count,
                        COUNT(DISTINCT g.group_id) AS option_group_count,
                        COUNT(DISTINCT o.option_id) AS option_count,
                        MAX(s.imported_at) AS latest_imported_at
                    FROM brand_master b
                    JOIN menu_source s
                        ON s.brand_code = b.brand_code
                    LEFT JOIN menu_item_master i
                        ON i.source_code = s.source_code
                    LEFT JOIN menu_option_group g
                        ON g.source_code = s.source_code
                    LEFT JOIN menu_option o
                        ON o.group_id = g.group_id
                    WHERE {source_clause}
                    """,
                    source_params,
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM brand_master) AS brand_count,
                        (SELECT COUNT(*) FROM menu_source) AS source_count,
                        (SELECT COUNT(*) FROM menu_item_master WHERE active_flag = 1) AS item_count,
                        (SELECT COUNT(*) FROM menu_option_group) AS option_group_count,
                        (SELECT COUNT(*) FROM menu_option) AS option_count,
                        (SELECT MAX(imported_at) FROM menu_source) AS latest_imported_at
                    """
                ).fetchone()

        return {
            "brand_count": int(row["brand_count"] or 0),
            "source_count": int(row["source_count"] or 0),
            "item_count": int(row["item_count"] or 0),
            "option_group_count": int(row["option_group_count"] or 0),
            "option_count": int(row["option_count"] or 0),
            "latest_imported_at": row["latest_imported_at"],
            "brands": self.list_menu_brands(consumer_visible=consumer_visible),
        }

    def list_menu_brands(self, consumer_visible: bool = False) -> List[Dict[str, Any]]:
        with self.connect() as connection:
            if consumer_visible:
                source_clause, source_params = self._consumer_source_clause("s")
                rows = connection.execute(
                    f"""
                    SELECT
                        b.brand_code,
                        b.brand_name,
                        b.brand_name_local,
                        b.channel_name,
                        b.default_currency_code,
                        b.brand_country_code,
                        b.brand_notes,
                        COUNT(DISTINCT s.source_code) AS source_count,
                        COUNT(DISTINCT CASE WHEN i.active_flag = 1 THEN i.item_id END) AS item_count,
                        COUNT(DISTINCT g.group_id) AS option_group_count,
                        COUNT(DISTINCT o.option_id) AS option_count,
                        MIN(CASE WHEN i.active_flag = 1 THEN i.base_price END) AS min_price,
                        MAX(CASE WHEN i.active_flag = 1 THEN i.base_price END) AS max_price,
                        MAX(s.imported_at) AS latest_imported_at
                    FROM brand_master b
                    JOIN menu_source s
                        ON s.brand_code = b.brand_code
                    LEFT JOIN menu_item_master i
                        ON i.source_code = s.source_code
                    LEFT JOIN menu_option_group g
                        ON g.source_code = s.source_code
                    LEFT JOIN menu_option o
                        ON o.group_id = g.group_id
                    WHERE {source_clause}
                    GROUP BY
                        b.brand_code, b.brand_name, b.brand_name_local, b.channel_name,
                        b.default_currency_code, b.brand_country_code, b.brand_notes
                    ORDER BY item_count DESC, b.brand_name ASC
                    """,
                    source_params,
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT
                        b.brand_code,
                        b.brand_name,
                        b.brand_name_local,
                        b.channel_name,
                        b.default_currency_code,
                        b.brand_country_code,
                        b.brand_notes,
                        COUNT(DISTINCT s.source_code) AS source_count,
                        COUNT(DISTINCT CASE WHEN i.active_flag = 1 THEN i.item_id END) AS item_count,
                        COUNT(DISTINCT g.group_id) AS option_group_count,
                        COUNT(DISTINCT o.option_id) AS option_count,
                        MIN(CASE WHEN i.active_flag = 1 THEN i.base_price END) AS min_price,
                        MAX(CASE WHEN i.active_flag = 1 THEN i.base_price END) AS max_price,
                        MAX(s.imported_at) AS latest_imported_at
                    FROM brand_master b
                    LEFT JOIN menu_source s
                        ON s.brand_code = b.brand_code
                    LEFT JOIN menu_item_master i
                        ON i.brand_code = b.brand_code
                    LEFT JOIN menu_option_group g
                        ON g.source_code = s.source_code
                    LEFT JOIN menu_option o
                        ON o.group_id = g.group_id
                    GROUP BY
                        b.brand_code, b.brand_name, b.brand_name_local, b.channel_name,
                        b.default_currency_code, b.brand_country_code, b.brand_notes
                    ORDER BY item_count DESC, b.brand_name ASC
                    """
                ).fetchall()

        return [
            {
                "brand_code": row["brand_code"],
                "brand_name": row["brand_name"],
                "brand_name_local": row["brand_name_local"],
                "channel_name": row["channel_name"],
                "default_currency_code": row["default_currency_code"],
                "brand_country_code": row["brand_country_code"],
                "brand_notes": row["brand_notes"],
                "source_count": int(row["source_count"] or 0),
                "item_count": int(row["item_count"] or 0),
                "option_group_count": int(row["option_group_count"] or 0),
                "option_count": int(row["option_count"] or 0),
                "min_price": row["min_price"],
                "max_price": row["max_price"],
                "latest_imported_at": row["latest_imported_at"],
            }
            for row in rows
        ]

    def get_brand_detail(self, brand_code: str, consumer_visible: bool = False) -> Optional[Dict[str, Any]]:
        with self.connect() as connection:
            brand = connection.execute(
                "SELECT * FROM brand_master WHERE brand_code = ?",
                (brand_code,),
            ).fetchone()
            if brand is None:
                return None

            if consumer_visible:
                source_clause, source_params = self._consumer_source_clause("s")
                stats = connection.execute(
                    f"""
                    SELECT
                        COUNT(*) AS item_count,
                        MIN(i.base_price) AS min_price,
                        MAX(i.base_price) AS max_price
                    FROM menu_item_master i
                    JOIN menu_source s
                        ON s.source_code = i.source_code
                    WHERE i.brand_code = ? AND i.active_flag = 1 AND {source_clause}
                    """,
                    [brand_code, *source_params],
                ).fetchone()

                sources = connection.execute(
                    f"""
                    SELECT
                        source_code, source_type, source_name, source_url, source_api_url,
                        store_name, address_text, city, region, country_code, currency_code,
                        imported_at, source_status, item_count, option_group_count, option_count
                    FROM menu_source s
                    WHERE brand_code = ? AND {source_clause}
                    ORDER BY datetime(imported_at) DESC, source_name ASC
                    """,
                    [brand_code, *source_params],
                ).fetchall()

                categories = connection.execute(
                    f"""
                    SELECT i.category_name, COUNT(*) AS item_count
                    FROM menu_item_master i
                    JOIN menu_source s
                        ON s.source_code = i.source_code
                    WHERE i.brand_code = ? AND i.active_flag = 1 AND {source_clause}
                    GROUP BY i.category_name
                    ORDER BY item_count DESC, i.category_name ASC
                    """,
                    [brand_code, *source_params],
                ).fetchall()
            else:
                stats = connection.execute(
                    """
                    SELECT COUNT(*) AS item_count, MIN(base_price) AS min_price, MAX(base_price) AS max_price
                    FROM menu_item_master
                    WHERE brand_code = ? AND active_flag = 1
                    """,
                    (brand_code,),
                ).fetchone()

                sources = connection.execute(
                    """
                    SELECT
                        source_code, source_type, source_name, source_url, source_api_url,
                        store_name, address_text, city, region, country_code, currency_code,
                        imported_at, source_status, item_count, option_group_count, option_count
                    FROM menu_source
                    WHERE brand_code = ?
                    ORDER BY datetime(imported_at) DESC, source_name ASC
                    """,
                    (brand_code,),
                ).fetchall()

                categories = connection.execute(
                    """
                    SELECT category_name, COUNT(*) AS item_count
                    FROM menu_item_master
                    WHERE brand_code = ? AND active_flag = 1
                    GROUP BY category_name
                    ORDER BY item_count DESC, category_name ASC
                    """,
                    (brand_code,),
                ).fetchall()

        if consumer_visible and not sources:
            return None

        return {
            "brand_code": brand["brand_code"],
            "brand_name": brand["brand_name"],
            "brand_name_local": brand["brand_name_local"],
            "channel_name": brand["channel_name"],
            "default_currency_code": brand["default_currency_code"],
            "brand_country_code": brand["brand_country_code"],
            "brand_notes": brand["brand_notes"],
            "item_count": int(stats["item_count"] or 0),
            "min_price": stats["min_price"],
            "max_price": stats["max_price"],
            "sources": [dict(source) for source in sources],
            "category_breakdown": [
                {
                    "category_name": row["category_name"],
                    "item_count": int(row["item_count"] or 0),
                }
                for row in categories
            ],
        }

    def search_menu_items(
        self,
        brand_code: Optional[str] = None,
        search: str = "",
        limit: int = 24,
        offset: int = 0,
        consumer_visible: bool = False,
    ) -> Dict[str, Any]:
        clauses = ["i.active_flag = 1"]
        params: List[Any] = []

        if brand_code:
            clauses.append("i.brand_code = ?")
            params.append(brand_code)

        if consumer_visible:
            source_clause, source_params = self._consumer_source_clause("s")
            clauses.append(source_clause)
            params.extend(source_params)

        search_term = search.strip().lower()
        if search_term:
            like = f"%{search_term}%"
            clauses.append(
                """
                (
                    LOWER(i.item_name) LIKE ?
                    OR LOWER(COALESCE(i.item_name_local, '')) LIKE ?
                    OR LOWER(COALESCE(i.description, '')) LIKE ?
                    OR LOWER(COALESCE(i.category_name, '')) LIKE ?
                )
                """
            )
            params.extend([like, like, like, like])

        where_sql = " AND ".join(clauses)

        with self.connect() as connection:
            count_row = connection.execute(
                f"""
                SELECT COUNT(*) AS total_count
                FROM menu_item_master i
                JOIN menu_source s
                    ON s.source_code = i.source_code
                WHERE {where_sql}
                """,
                params,
            ).fetchone()

            rows = connection.execute(
                f"""
                SELECT
                    i.*,
                    b.brand_name,
                    b.brand_name_local,
                    b.channel_name,
                    s.source_name,
                    s.source_type,
                    s.source_status,
                    s.store_name,
                    (
                        SELECT COUNT(*)
                        FROM menu_item_option_group_map m
                        WHERE m.item_id = i.item_id
                    ) AS option_group_count
                FROM menu_item_master i
                JOIN brand_master b
                    ON b.brand_code = i.brand_code
                JOIN menu_source s
                    ON s.source_code = i.source_code
                WHERE {where_sql}
                ORDER BY b.brand_name ASC, i.base_price ASC, i.item_name ASC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()

        return {
            "count": int(count_row["total_count"] or 0),
            "items": [self._menu_item_summary_from_row(row) for row in rows],
        }

    def get_menu_item_detail(self, item_id: str, consumer_visible: bool = False) -> Optional[Dict[str, Any]]:
        source_sql = ""
        params: List[Any] = [item_id]
        if consumer_visible:
            source_clause, source_params = self._consumer_source_clause("s")
            source_sql = f" AND {source_clause}"
            params.extend(source_params)

        with self.connect() as connection:
            item_row = connection.execute(
                f"""
                SELECT
                    i.*,
                    b.brand_name,
                    b.brand_name_local,
                    b.channel_name,
                    s.source_name,
                    s.source_type,
                    s.source_status,
                    s.source_url,
                    s.source_api_url,
                    s.store_name,
                    s.address_text
                FROM menu_item_master i
                JOIN brand_master b
                    ON b.brand_code = i.brand_code
                JOIN menu_source s
                    ON s.source_code = i.source_code
                WHERE i.item_id = ?
                {source_sql}
                """,
                params,
            ).fetchone()
            if item_row is None:
                return None

            group_rows = connection.execute(
                """
                SELECT
                    g.group_id,
                    g.external_group_id,
                    g.group_name,
                    g.required,
                    g.limit_count,
                    g.supports_multiple,
                    g.group_type,
                    m.sort_order
                FROM menu_item_option_group_map m
                JOIN menu_option_group g
                    ON g.group_id = m.group_id
                WHERE m.item_id = ?
                ORDER BY m.sort_order ASC, g.group_name ASC
                """,
                (item_id,),
            ).fetchall()

            option_rows = connection.execute(
                """
                SELECT
                    g.group_id,
                    o.option_id,
                    o.option_name,
                    o.external_option_code,
                    o.price_delta,
                    o.is_default,
                    o.sold_out,
                    o.option_tags_json,
                    o.sort_order
                FROM menu_item_option_group_map m
                JOIN menu_option_group g
                    ON g.group_id = m.group_id
                JOIN menu_option o
                    ON o.group_id = g.group_id
                WHERE m.item_id = ?
                ORDER BY m.sort_order ASC, o.sort_order ASC, o.option_name ASC
                """,
                (item_id,),
            ).fetchall()

        option_map: Dict[str, List[Dict[str, Any]]] = {}
        for row in option_rows:
            option_map.setdefault(row["group_id"], []).append(
                {
                    "option_id": row["option_id"],
                    "option_name": row["option_name"],
                    "external_option_code": row["external_option_code"],
                    "price_delta": row["price_delta"],
                    "is_default": bool(row["is_default"]),
                    "sold_out": bool(row["sold_out"]),
                    "option_tags": self._loads_json(row["option_tags_json"], []),
                }
            )

        detail = self._menu_item_summary_from_row(item_row)
        detail["channel_name"] = item_row["channel_name"]
        detail["source_url"] = item_row["source_url"]
        detail["source_api_url"] = item_row["source_api_url"]
        detail["address_text"] = item_row["address_text"]
        detail["customization_groups"] = [
            {
                "group_id": row["group_id"],
                "external_group_id": row["external_group_id"],
                "group_name": row["group_name"],
                "required": bool(row["required"]),
                "limit_count": int(row["limit_count"] or 0),
                "supports_multiple": bool(row["supports_multiple"]),
                "group_type": row["group_type"],
                "options": option_map.get(row["group_id"], []),
            }
            for row in group_rows
        ]
        return detail

    def get_recommendable_menu_items(
        self,
        brand_code: Optional[str] = None,
        consumer_visible: bool = False,
    ) -> List[Dict[str, Any]]:
        clauses = ["i.active_flag = 1"]
        params: List[Any] = []
        if brand_code:
            clauses.append("i.brand_code = ?")
            params.append(brand_code)
        if consumer_visible:
            source_clause, source_params = self._consumer_source_clause("s")
            clauses.append(source_clause)
            params.extend(source_params)
        where_sql = " AND ".join(clauses)

        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    i.*,
                    b.brand_name,
                    b.brand_name_local,
                    b.channel_name,
                    s.source_name,
                    s.source_type,
                    s.source_status,
                    s.store_name,
                    (
                        SELECT COUNT(*)
                        FROM menu_item_option_group_map m
                        WHERE m.item_id = i.item_id
                    ) AS option_group_count
                FROM menu_item_master i
                JOIN brand_master b
                    ON b.brand_code = i.brand_code
                JOIN menu_source s
                    ON s.source_code = i.source_code
                WHERE {where_sql}
                ORDER BY b.brand_name ASC, i.item_name ASC
                """,
                params,
            ).fetchall()

        catalog: List[Dict[str, Any]] = []
        for row in rows:
            raw_meta = self._loads_json(row["raw_json"], {})
            price_context = raw_meta.get("price_context") if isinstance(raw_meta, dict) else None
            catalog.append(
                {
                    "sku_id": row["item_id"],
                    "brand_code": row["brand_code"],
                    "brand_name": row["brand_name"],
                    "brand_name_local": row["brand_name_local"],
                    "source_code": row["source_code"],
                        "source_name": row["source_name"],
                        "channel_name": row["channel_name"],
                        "source_type": row["source_type"],
                        "source_status": row["source_status"],
                        "store_name": row["store_name"],
                        "sku_name": row["item_name"],
                        "sku_name_local": row["item_name_local"],
                    "display_name": row["display_name"] or row["item_name"],
                    "image_url": row["image_url"],
                    "description": row["description"],
                    "category": row["normalized_category"],
                    "category_name": row["category_name"],
                    "base_price": float(row["base_price"] or 0.0),
                    "currency_code": row["currency_code"],
                    "price_band": row["price_band"],
                    "available_hot": int(row["available_hot"] or 0),
                    "available_cold": int(row["available_cold"] or 0),
                    "dairy_flag": int(row["dairy_flag"] or 0),
                    "status": "active" if int(row["active_flag"] or 0) == 1 else "inactive",
                    "option_group_count": int(row["option_group_count"] or 0),
                    "option_summary": self._loads_json(row["option_summary_json"], []),
                    "profile_tags": self._loads_json(row["profile_tags_json"], []),
                    "default_scene_tags": self._loads_json(row["scene_tags_json"], []),
                    "default_mood_tags": self._loads_json(row["mood_tags_json"], []),
                    "price_context": price_context if isinstance(price_context, dict) else {},
                    **{field: float(row[field] or 0.0) for field in FEATURE_FIELDS},
                }
            )
        return catalog

    def get_menu_governance_dashboard(
        self,
        brand_code: Optional[str] = None,
        review_limit: int = 12,
        tag_limit: int = 10,
    ) -> Dict[str, Any]:
        clauses = ["i.active_flag = 1"]
        params: List[Any] = []
        if brand_code:
            clauses.append("i.brand_code = ?")
            params.append(brand_code)
        where_sql = " AND ".join(clauses)

        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    i.*,
                    b.brand_name,
                    b.brand_name_local,
                    b.channel_name,
                    s.source_name,
                    s.source_type,
                    s.source_status,
                    s.store_name,
                    (
                        SELECT COUNT(*)
                        FROM menu_item_option_group_map m
                        WHERE m.item_id = i.item_id
                    ) AS option_group_count
                FROM menu_item_master i
                JOIN brand_master b
                    ON b.brand_code = i.brand_code
                JOIN menu_source s
                    ON s.source_code = i.source_code
                WHERE {where_sql}
                ORDER BY b.brand_name ASC, i.item_name ASC
                """,
                params,
            ).fetchall()

            option_group_rows = connection.execute(
                f"""
                SELECT
                    COALESCE(NULLIF(g.group_type, ''), 'unknown') AS group_type,
                    COUNT(*) AS mapping_count,
                    COUNT(DISTINCT m.item_id) AS item_count
                FROM menu_item_option_group_map m
                JOIN menu_option_group g
                    ON g.group_id = m.group_id
                JOIN menu_item_master i
                    ON i.item_id = m.item_id
                WHERE {where_sql}
                GROUP BY COALESCE(NULLIF(g.group_type, ''), 'unknown')
                ORDER BY mapping_count DESC, item_count DESC, group_type ASC
                """,
                params,
            ).fetchall()

        items = [self._menu_item_summary_from_row(row) for row in rows]
        brand_cards = self.list_menu_brands()
        if brand_code:
            brand_cards = [brand for brand in brand_cards if brand["brand_code"] == brand_code]

        item_count = len(items)
        avg_price = round(sum(float(item["base_price"] or 0.0) for item in items) / item_count, 2) if item_count else 0.0
        described_count = sum(1 for item in items if (item.get("description") or "").strip())
        customizable_count = sum(1 for item in items if int(item.get("option_group_count") or 0) > 0)
        mood_covered_count = sum(1 for item in items if item.get("mood_tags"))
        scene_covered_count = sum(1 for item in items if item.get("scene_tags"))
        profile_covered_count = sum(1 for item in items if item.get("profile_tags"))
        hot_supported_count = sum(1 for item in items if item.get("available_hot"))
        cold_supported_count = sum(1 for item in items if item.get("available_cold"))

        category_counts: Dict[str, int] = {}
        price_band_counts: Dict[str, int] = {}
        feature_totals = {field: 0.0 for field in FEATURE_FIELDS}
        tag_counts = {"profile": {}, "mood": {}, "scene": {}}
        review_queue: List[Dict[str, Any]] = []

        for item in items:
            category = str(item.get("normalized_category") or "other")
            category_counts[category] = category_counts.get(category, 0) + 1

            price_band = str(item.get("price_band") or "unknown")
            price_band_counts[price_band] = price_band_counts.get(price_band, 0) + 1

            for field in FEATURE_FIELDS:
                feature_totals[field] += float(item["feature_profile"].get(field, 0.0) or 0.0)

            for tag_type, field_name in [
                ("profile", "profile_tags"),
                ("mood", "mood_tags"),
                ("scene", "scene_tags"),
            ]:
                for tag in item.get(field_name, []):
                    bucket = tag_counts[tag_type]
                    bucket[tag] = bucket.get(tag, 0) + 1

            reasons: List[str] = []
            if not (item.get("description") or "").strip():
                reasons.append("缺少商品描述")
            if len(item.get("profile_tags") or []) < 2:
                reasons.append("画像标签偏少")
            if not item.get("mood_tags"):
                reasons.append("缺少情绪标签")
            if not item.get("scene_tags"):
                reasons.append("缺少场景标签")
            if int(item.get("option_group_count") or 0) == 0:
                reasons.append("缺少客制组选项")
            if not item.get("available_hot") and not item.get("available_cold"):
                reasons.append("温度信息缺失")
            if str(item.get("normalized_category") or "") in {
                "coffee",
                "coffee_sparkling",
                "smoothie",
                "yogurt",
                "herbal_tea",
            }:
                reasons.append("跨品类样本建议抽检")
            if float(item.get("base_price") or 0.0) >= 25 or float(item.get("base_price") or 0.0) <= 8:
                reasons.append("价格带边界样本建议抽检")
            if int(item.get("option_group_count") or 0) >= 6:
                reasons.append("客制结构较复杂建议复核")

            if reasons:
                review_queue.append(
                    {
                        "item_id": item["item_id"],
                        "item_name": item["item_name"],
                        "brand_code": item["brand_code"],
                        "brand_name": item["brand_name"],
                        "channel_name": item.get("channel_name"),
                        "source_name": item.get("source_name"),
                        "source_type": item.get("source_type"),
                        "source_status": item.get("source_status"),
                        "normalized_category": item["normalized_category"],
                        "base_price": float(item["base_price"] or 0.0),
                        "currency_code": item["currency_code"],
                        "option_group_count": int(item.get("option_group_count") or 0),
                        "profile_tag_count": len(item.get("profile_tags") or []),
                        "mood_tag_count": len(item.get("mood_tags") or []),
                        "scene_tag_count": len(item.get("scene_tags") or []),
                        "review_reasons": reasons,
                        "priority_score": len(reasons) * 10
                        + max(0, 2 - len(item.get("profile_tags") or []))
                        + (0 if (item.get("description") or "").strip() else 2),
                    }
                )

        def ratio(count: int) -> float:
            if item_count == 0:
                return 0.0
            return round(count / item_count, 4)

        def sorted_distribution(counts: Dict[str, int], limit: Optional[int] = None) -> List[Dict[str, Any]]:
            rows = [
                {
                    "code": key,
                    "count": value,
                    "ratio": ratio(value),
                }
                for key, value in counts.items()
            ]
            rows.sort(key=lambda entry: (-entry["count"], entry["code"]))
            return rows[:limit] if limit else rows

        review_queue.sort(
            key=lambda item: (
                -int(item["priority_score"]),
                -len(item["review_reasons"]),
                item["brand_name"],
                item["item_name"],
            )
        )

        feature_averages = [
            {
                "code": field,
                "avg_score": round(feature_totals[field] / item_count, 3) if item_count else 0.0,
            }
            for field in FEATURE_FIELDS
        ]
        feature_averages.sort(key=lambda entry: (-entry["avg_score"], entry["code"]))

        option_group_distribution = [
            {
                "group_type": row["group_type"],
                "mapping_count": int(row["mapping_count"] or 0),
                "item_count": int(row["item_count"] or 0),
                "ratio": ratio(int(row["item_count"] or 0)),
            }
            for row in option_group_rows
        ]

        latest_imported_at = None
        if brand_cards:
            latest_imported_at = max(
                (brand.get("latest_imported_at") for brand in brand_cards if brand.get("latest_imported_at")),
                default=None,
            )

        return {
            "scope": brand_code or "all",
            "generated_at": self._now_iso(),
            "latest_imported_at": latest_imported_at,
            "summary": {
                "brand_count": len(brand_cards) if brand_code else len(brand_cards),
                "item_count": item_count,
                "avg_price": avg_price,
                "described_count": described_count,
                "customizable_count": customizable_count,
                "mood_covered_count": mood_covered_count,
                "scene_covered_count": scene_covered_count,
                "profile_covered_count": profile_covered_count,
                "hot_supported_count": hot_supported_count,
                "cold_supported_count": cold_supported_count,
                "review_queue_count": len(review_queue),
                "description_coverage_ratio": ratio(described_count),
                "customization_coverage_ratio": ratio(customizable_count),
                "mood_coverage_ratio": ratio(mood_covered_count),
                "scene_coverage_ratio": ratio(scene_covered_count),
                "profile_coverage_ratio": ratio(profile_covered_count),
                "hot_support_ratio": ratio(hot_supported_count),
                "cold_support_ratio": ratio(cold_supported_count),
            },
            "brands": brand_cards,
            "category_distribution": sorted_distribution(category_counts),
            "price_band_distribution": sorted_distribution(price_band_counts),
            "feature_averages": feature_averages,
            "tag_distributions": {
                "profile": sorted_distribution(tag_counts["profile"], limit=tag_limit),
                "mood": sorted_distribution(tag_counts["mood"], limit=tag_limit),
                "scene": sorted_distribution(tag_counts["scene"], limit=tag_limit),
            },
            "option_group_distribution": option_group_distribution,
            "review_queue": review_queue[:review_limit],
        }

    def _menu_item_summary_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        item = {
            "item_id": row["item_id"],
            "brand_code": row["brand_code"],
            "brand_name": row["brand_name"],
            "brand_name_local": row["brand_name_local"],
            "source_code": row["source_code"],
            "source_name": row["source_name"],
            "store_name": row["store_name"],
            "item_name": row["item_name"],
            "item_name_local": row["item_name_local"],
            "display_name": row["display_name"] or row["item_name"],
            "description": row["description"],
            "image_url": row["image_url"],
            "category_name": row["category_name"],
            "normalized_category": row["normalized_category"],
            "base_price": row["base_price"],
            "currency_code": row["currency_code"],
            "price_band": row["price_band"],
            "available_hot": bool(row["available_hot"]),
            "available_cold": bool(row["available_cold"]),
            "dairy_flag": bool(row["dairy_flag"]),
            "active_flag": bool(row["active_flag"]),
            "feature_profile": {field: float(row[field] or 0.0) for field in FEATURE_FIELDS},
            "profile_tags": self._loads_json(row["profile_tags_json"], []),
            "scene_tags": self._loads_json(row["scene_tags_json"], []),
            "mood_tags": self._loads_json(row["mood_tags_json"], []),
            "option_summary": self._loads_json(row["option_summary_json"], []),
        }
        if "raw_json" in row.keys():
            raw_meta = self._loads_json(row["raw_json"], {})
            if isinstance(raw_meta, dict):
                price_context = raw_meta.get("price_context")
                if isinstance(price_context, dict):
                    item["price_context"] = price_context
        if "launch_date" in row.keys():
            item["launch_date"] = str(row["launch_date"] or "").strip()
        if "lifecycle_code" in row.keys():
            item["lifecycle_code"] = str(row["lifecycle_code"] or "").strip()
        if "lifecycle_label" in row.keys():
            item["lifecycle_label"] = str(row["lifecycle_label"] or "").strip()
        if "lifecycle_evidence_json" in row.keys():
            item["lifecycle_evidence"] = self._loads_json(row["lifecycle_evidence_json"], {})
        if "channel_name" in row.keys():
            item["channel_name"] = row["channel_name"]
        if "source_type" in row.keys():
            item["source_type"] = row["source_type"]
        if "source_status" in row.keys():
            item["source_status"] = row["source_status"]
        if "option_group_count" in row.keys():
            item["option_group_count"] = int(row["option_group_count"] or 0)
        return item

    def _simple_catalog_item_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        default_temperature_text = str(row["default_temperature_text"] or "").strip()
        default_sweetness_text = str(row["default_sweetness_text"] or "").strip()
        serving_bits = [value for value in [default_temperature_text, default_sweetness_text] if value]
        image_meta = self._loads_json(row["image_meta_json"], {})
        image_provenance = str(image_meta.get("image_provenance") or "").strip()
        if image_provenance == "ai_generated_illustration":
            image_source_type = "ai_illustration"
        elif image_provenance in {"user_uploaded", "brand_logo", "brand_collage", "brand_fallback"}:
            image_source_type = image_provenance
        else:
            image_source_type = "source"
        return {
            "item_id": row["item_id"],
            "brand_code": row["brand_code"],
            "brand_name": row["brand_name"],
            "item_name": row["item_name"],
            "image_url": row["image_url"],
            "image_source_type": image_source_type,
            "image_badge_text": str(image_meta.get("badge_text") or "").strip(),
            "base_price_cny": float(row["base_price_cny"] or 0.0),
            "currency_code": "CNY",
            "default_temperature_text": default_temperature_text,
            "default_sweetness_text": default_sweetness_text,
            "default_serving_note": " / ".join(serving_bits) if serving_bits else "按门店默认做法",
            "temperature_type": row["temperature_type"],
            "caffeine_level_code": row["caffeine_level_code"],
            "tags": self._loads_json(row["tags_json"], []),
            "mood_tag_code": str(row["mood_tag_code"] or "").strip() if "mood_tag_code" in row.keys() else "",
            "mood_tag_evidence": self._loads_json(row["mood_tag_evidence_json"], {}) if "mood_tag_evidence_json" in row.keys() else {},
            "launch_date": str(row["launch_date"] or "").strip() if "launch_date" in row.keys() else "",
            "lifecycle_code": str(row["lifecycle_code"] or "").strip() if "lifecycle_code" in row.keys() else "",
            "lifecycle_label": str(row["lifecycle_label"] or "").strip() if "lifecycle_label" in row.keys() else "",
            "lifecycle_evidence": self._loads_json(row["lifecycle_evidence_json"], {}) if "lifecycle_evidence_json" in row.keys() else {},
            "source_url": row["source_url"],
            "verification_status": row["verification_status"],
            "last_verified_at": row["last_verified_at"],
            "active_flag": bool(row["active_flag"]),
            "normalized_category": row["normalized_category"],
            "description": row["description"] or "",
        }

    def _accept_record_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "accept_id": row["accept_id"],
            "user_id": row["user_id"],
            "session_id": row["session_id"],
            "accepted_at": row["accepted_at"],
            "accepted_date": row["accepted_date"],
            "accepted_month": row["accepted_month"],
            "mood_code": row["mood_code"],
            "mood_label": row["mood_label"],
            "budget_band": row["budget_band"],
            "temperature_pref": row["temperature_pref"],
            "caffeine_pref": row["caffeine_pref"],
            "preference_tags": self._loads_json(row["preference_tags_json"], []),
            "sku_id": row["sku_id"],
            "sku_name": row["sku_name"],
            "brand_code": row["brand_code"],
            "brand_name": row["brand_name"],
            "image_url": row["image_url"],
            "base_price": row["base_price"],
            "currency_code": row["currency_code"],
            "serving_note": row["serving_note"],
            "encouragement_copy": row["encouragement_copy"],
        }

    def _localize_image(
        self,
        image_url: str,
        generated_dir: Path,
        brand_code: str,
        item_id: str,
        image_meta_hint: Optional[Dict[str, Any]] = None,
        source_url: str = "",
    ) -> Dict[str, Any]:
        url = str(image_url or "").strip()
        image_meta_hint = image_meta_hint if isinstance(image_meta_hint, dict) else {}
        provenance_hint = str(
            image_meta_hint.get("image_provenance")
            or image_meta_hint.get("image_derivation")
            or image_meta_hint.get("provenance")
            or ""
        ).strip()
        source_page_url = str(image_meta_hint.get("source_page_url") or source_url or "").strip()
        meta = {
            "image_provenance": provenance_hint or "missing",
            "source_page_url": source_page_url,
            "crop_fallback_used": bool(
                image_meta_hint.get("crop_fallback_used")
                or image_meta_hint.get("is_crop")
                or ("crop" in provenance_hint.lower() if provenance_hint else False)
            ),
            "localized_at": "",
            "quality_tier": "missing",
        }
        if not url:
            return {"image_url": "", "meta": meta}

        if url.startswith("/generated/"):
            relative_path = url[len("/generated/") :].replace("/", "\\")
            local_path = generated_dir / Path(relative_path)
            if local_path.exists() and local_path.stat().st_size > 0:
                meta["image_provenance"] = provenance_hint or "generated_existing"
                meta["quality_tier"] = self._resolve_image_quality_tier(image_meta_hint, "generated_existing")
                meta["localized_at"] = self._now_iso()
                return {"image_url": url, "meta": meta}
            return {"image_url": "", "meta": meta}

        local_file_path: Optional[Path] = None
        if re.match(r"^[A-Za-z]:[\\/]", url) or url.startswith("\\\\"):
            candidate_path = Path(url)
            if candidate_path.exists() and candidate_path.is_file():
                local_file_path = candidate_path
        else:
            parsed_local = urlparse(url)
            if parsed_local.scheme == "file":
                candidate_path = Path(parsed_local.path.lstrip("/"))
                if candidate_path.exists() and candidate_path.is_file():
                    local_file_path = candidate_path

        subdir = generated_dir / "simple" / brand_code
        subdir.mkdir(parents=True, exist_ok=True)

        if local_file_path is not None:
            extension = local_file_path.suffix.lower()
            if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
                extension = ".jpg"
            filename = "%s%s" % (hashlib.sha1(item_id.encode("utf-8")).hexdigest()[:16], extension)
            local_target_path = subdir / filename
            public_url = "/generated/simple/%s/%s" % (brand_code, filename)
            if not local_target_path.exists() or local_target_path.stat().st_size == 0:
                local_target_path.write_bytes(local_file_path.read_bytes())
            meta["image_provenance"] = provenance_hint or "local_copy"
            meta["quality_tier"] = self._resolve_image_quality_tier(image_meta_hint, "local_copy")
            meta["localized_at"] = self._now_iso()
            return {"image_url": public_url if local_target_path.stat().st_size > 0 else "", "meta": meta}

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return {"image_url": "", "meta": meta}

        extension = Path(parsed.path).suffix.lower()
        if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
            extension = ".jpg"

        filename = "%s%s" % (hashlib.sha1(item_id.encode("utf-8")).hexdigest()[:16], extension)
        local_path = subdir / filename
        public_url = "/generated/simple/%s/%s" % (brand_code, filename)

        if local_path.exists() and local_path.stat().st_size > 0:
            meta["image_provenance"] = provenance_hint or "standard_remote"
            meta["quality_tier"] = self._resolve_image_quality_tier(image_meta_hint, "standard_remote")
            meta["localized_at"] = self._now_iso()
            return {"image_url": public_url, "meta": meta}

        try:
            host = (parsed.hostname or "").lower()
            headers = {"User-Agent": "MoodtipsSimpleCatalog/2026.04"}
            if "sinaimg.cn" in host:
                headers["Referer"] = "https://weibo.com/"
            elif any(token in host for token in ("luckincdn.com", "luckincoffee.com", "lkcoffee.com")):
                headers["Referer"] = "https://m.lkcoffee.com/"
            response = requests.get(
                url,
                timeout=20,
                headers=headers,
            )
            response.raise_for_status()
            content_type = str(response.headers.get("content-type") or "").split(";")[0].strip().lower()
            guessed_extension = mimetypes.guess_extension(content_type) if content_type else None
            if guessed_extension in {".jpg", ".jpeg", ".png", ".webp"} and guessed_extension != extension:
                filename = "%s%s" % (hashlib.sha1(item_id.encode("utf-8")).hexdigest()[:16], guessed_extension)
                local_path = subdir / filename
                public_url = "/generated/simple/%s/%s" % (brand_code, filename)
            local_path.write_bytes(response.content)
            meta["image_provenance"] = provenance_hint or "standard_remote"
            meta["quality_tier"] = self._resolve_image_quality_tier(image_meta_hint, "standard_remote")
            meta["localized_at"] = self._now_iso()
            return {"image_url": public_url if local_path.stat().st_size > 0 else "", "meta": meta}
        except requests.RequestException:
            return {"image_url": "", "meta": meta}

    def _resolve_image_quality_tier(self, image_meta_hint: Dict[str, Any], fallback: str) -> str:
        provenance = str(
            image_meta_hint.get("quality_tier")
            or image_meta_hint.get("image_provenance")
            or image_meta_hint.get("image_derivation")
            or image_meta_hint.get("provenance")
            or ""
        ).strip().lower()
        if not provenance:
            return fallback
        if "platform_original" in provenance:
            return "platform_original"
        if "card_crop" in provenance or "menu_card" in provenance:
            return "platform_card_crop"
        if "poster_crop" in provenance or "official_menu_poster_crop" in provenance or "official_site_poster_mirror" in provenance:
            return "menu_card_crop"
        if "user_upload" in provenance:
            return "user_uploaded"
        if "brand_logo" in provenance:
            return "brand_logo"
        if "brand_collage" in provenance or "brand_fallback" in provenance:
            return "brand_fallback"
        if "poster" in provenance and "crop" not in provenance and "mirror" not in provenance:
            return "brand_poster"
        if "generated" in provenance:
            return "generated_existing"
        return fallback

    def _normalize_item_name_for_match(self, item_name: str) -> str:
        normalized = str(item_name or "").strip().lower()
        normalized = normalized.replace("（", "(").replace("）", ")").replace("·", "").replace("*", "")
        normalized = re.sub(r"\s+", "", normalized)
        return normalized

    def _build_simple_dedupe_key(self, brand_code: str, item_name: str, temperature_type: str) -> str:
        return "%s|%s|%s" % (
            str(brand_code or "").strip(),
            self._normalize_item_name_for_match(item_name),
            str(temperature_type or "").strip(),
        )

    def _rank_simple_catalog_candidate(
        self,
        verification_status: str,
        source_type: str,
        image_meta: Dict[str, Any],
        description: str,
        imported_at: str,
    ) -> Tuple[int, int, int, int, int, str]:
        source_priority = {
            "official_mainland_national_snapshot": 4,
            DELIVERY_PLATFORM_SOURCE_TYPE: 3,
            "brand_owned_promotional_snapshot": 2,
            "benchmark_seed": 1,
        }.get(str(source_type or "").strip(), 0)
        quality_tier = str((image_meta or {}).get("quality_tier") or "missing")
        quality_score = IMAGE_QUALITY_SCORES.get(quality_tier, 0)
        description_text = str(description or "").strip()
        return (
            1 if verification_status == SIMPLE_VISIBLE_STATUS else 0,
            source_priority,
            quality_score,
            1 if description_text else 0,
            len(description_text),
            str(imported_at or ""),
        )

    def _disambiguate_simple_catalog_names(self, rows: List[Dict[str, Any]]) -> None:
        grouped_rows: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            grouped_rows.setdefault(
                "%s|%s" % (
                    str(row.get("brand_code") or "").strip(),
                    self._normalize_item_name_for_match(str(row.get("item_name") or "")),
                ),
                [],
            ).append(row)

        suffix_map = {
            "hot": "（热饮）",
            "cold": "（冷饮）",
            "smoothie": "（冰沙）",
            "multi": "（多温）",
        }
        for grouped in grouped_rows.values():
            if len(grouped) <= 1:
                continue
            for row in grouped:
                item_name = str(row.get("item_name") or "").strip()
                suffix = suffix_map.get(str(row.get("temperature_type") or "").strip(), "（限定）")
                if item_name.endswith(suffix):
                    continue
                row["item_name"] = "%s%s" % (item_name, suffix)

    def _derive_temperature_type(
        self,
        item_name: str,
        normalized_category: str,
        available_hot: bool,
        available_cold: bool,
    ) -> str:
        text = f"{item_name} {normalized_category}"
        if self._contains_any(text, SMOOTHIE_KEYWORDS) or normalized_category == "smoothie":
            return "smoothie"
        if available_hot and available_cold:
            return "multi"
        if available_hot:
            return "hot"
        return "cold"

    def _derive_default_temperature_text(
        self,
        temperature_type: str,
        default_temperature: str,
        default_ice: str,
    ) -> str:
        if default_temperature:
            return self._localize_serving_text(default_temperature)
        if default_ice:
            return self._localize_serving_text(default_ice)
        if temperature_type == "hot":
            return "热饮默认"
        if temperature_type == "smoothie":
            return "冰沙默认"
        return "冷饮默认"

    def _derive_default_sweetness_text(self, default_sugar: str) -> str:
        if default_sugar:
            return self._localize_serving_text(default_sugar)
        return "默认糖度"

    def _localize_serving_text(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        normalized = re.sub(r"\s+", " ", text).strip().lower()
        return SERVING_TEXT_TRANSLATIONS.get(normalized, text)

    def _derive_caffeine_level_code(
        self,
        item_name: str,
        description: str,
        normalized_category: str,
        caffeine_level: float,
    ) -> str:
        text = f"{item_name} {description} {normalized_category}"
        lowered = text.lower()
        if self._contains_any(lowered, STRONG_CAFFEINE_KEYWORDS):
            return "strong"
        if normalized_category in PURE_COFFEE_CATEGORIES or self._contains_any(text, COFFEE_KEYWORDS):
            return "normal"
        if normalized_category in TEA_FORWARD_CATEGORIES or (
            normalized_category == "latte" and self._contains_any(text, TEA_KEYWORDS) and not self._contains_any(text, COFFEE_KEYWORDS)
        ):
            if caffeine_level >= 1.5:
                return "normal"
            return "low"
        if caffeine_level >= 1.5:
            return "normal"
        if caffeine_level > 0.35:
            return "low"
        return "none"

    def _derive_simple_tags(
        self,
        item_name: str,
        description: str,
        normalized_category: str,
        temperature_type: str,
        caffeine_level_code: str,
        default_sweetness_text: str,
        default_temperature_text: str,
    ) -> List[str]:
        return self._derive_simple_tag_payload(
            item_name=item_name,
            description=description,
            normalized_category=normalized_category,
            temperature_type=temperature_type,
            caffeine_level_code=caffeine_level_code,
            default_sweetness_text=default_sweetness_text,
            default_temperature_text=default_temperature_text,
        )["display_tags"]

    def _derive_simple_tag_payload(
        self,
        item_name: str,
        description: str,
        normalized_category: str,
        temperature_type: str,
        caffeine_level_code: str,
        default_sweetness_text: str,
        default_temperature_text: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        overrides = overrides if isinstance(overrides, dict) else {}
        attribute_overrides = overrides.get("attribute_overrides") if isinstance(overrides.get("attribute_overrides"), dict) else {}
        display_tags_override = overrides.get("display_tags_override") if isinstance(overrides.get("display_tags_override"), list) else []

        item_name = str(item_name or "").strip()
        description = str(description or "").strip()
        normalized_category = str(normalized_category or "").strip()
        default_sweetness_text = str(default_sweetness_text or "").strip()
        default_temperature_text = str(default_temperature_text or "").strip()
        text = " ".join(
            value.strip()
            for value in [item_name, description, normalized_category, default_sweetness_text, default_temperature_text]
            if str(value or "").strip()
        )
        lowered = text.lower()

        def field_reasons(keywords: Tuple[str, ...], include_defaults: bool = False) -> List[str]:
            reasons: List[str] = []
            if self._contains_any(item_name, keywords):
                reasons.append("name_hit")
            if self._contains_any(description, keywords):
                reasons.append("description_hit")
            if self._contains_any(normalized_category, keywords):
                reasons.append("category_hit")
            if include_defaults and self._contains_any(default_sweetness_text, keywords):
                reasons.append("default_sweetness_hit")
            if include_defaults and self._contains_any(default_temperature_text, keywords):
                reasons.append("default_temperature_hit")
            return reasons

        tea_reasons = field_reasons(TEA_KEYWORDS)
        milk_reasons = field_reasons(MILK_KEYWORDS)
        fruit_reasons = field_reasons(FRUITY_KEYWORDS)
        coffee_reasons = field_reasons(COFFEE_KEYWORDS)
        lemon_reasons = field_reasons(LEMON_KEYWORDS)
        jasmine_reasons = field_reasons(JASMINE_KEYWORDS)
        oolong_reasons = field_reasons(OOLONG_KEYWORDS)
        yogurt_reasons = field_reasons(YOGURT_KEYWORDS)
        coconut_reasons = field_reasons(COCONUT_KEYWORDS)
        fresh_reasons = field_reasons(FRESH_KEYWORDS)
        smooth_reasons = field_reasons(SMOOTH_KEYWORDS)
        light_reasons = field_reasons(LIGHT_KEYWORDS)
        no_sugar_reasons = field_reasons(NO_SUGAR_KEYWORDS, include_defaults=True)

        is_coffee = normalized_category in PURE_COFFEE_CATEGORIES or bool(coffee_reasons)
        is_tea_forward = normalized_category in TEA_FORWARD_CATEGORIES or (
            normalized_category == "latte" and bool(tea_reasons) and not is_coffee
        )
        has_milk = normalized_category in {"milk_tea", "coffee_latte"} or bool(milk_reasons)
        has_fruit = normalized_category in {"fruit_tea", "smoothie", "yogurt"} or bool(fruit_reasons)
        has_yogurt = normalized_category == "yogurt" or bool(yogurt_reasons)
        default_is_explicit_sweet = self._contains_any(default_sweetness_text, SWEETENED_DEFAULT_KEYWORDS)
        no_sugar_friendly = bool(no_sugar_reasons)
        if not no_sugar_friendly and not default_is_explicit_sweet:
            if (normalized_category in {"tea", "coffee", "coffee_sparkling"} or "美式" in lowered) and not has_milk:
                no_sugar_friendly = True
                no_sugar_reasons = ["pure_unsweetened_style"]

        attributes = {
            "tea_base": is_tea_forward,
            "milk_base": has_milk,
            "fruit_component": has_fruit,
            "coffee_component": is_coffee,
            "lemon_component": bool(lemon_reasons),
            "jasmine_component": bool(jasmine_reasons),
            "oolong_component": bool(oolong_reasons),
            "yogurt_component": has_yogurt,
            "coconut_component": bool(coconut_reasons),
            "fresh_profile": bool(fresh_reasons) or (has_fruit and not has_milk and not is_coffee),
            "smooth_profile": bool(smooth_reasons) or (has_milk and not has_fruit and not is_coffee),
            "light_profile": bool(light_reasons) or (normalized_category in {"tea", "tea_sparkling"} and not has_milk and not has_fruit and not is_coffee),
            "sugar_friendliness": "friendly" if no_sugar_friendly else "neutral",
            "temperature_mode": temperature_type,
            "caffeine_level": caffeine_level_code,
        }

        override_keys = set(attribute_overrides.keys())
        for key, value in attribute_overrides.items():
            if key in attributes:
                attributes[key] = value

        def dedupe_reasons(reasons: Sequence[str]) -> List[str]:
            deduped: List[str] = []
            for reason in reasons:
                clean_reason = str(reason or "").strip()
                if clean_reason and clean_reason not in deduped:
                    deduped.append(clean_reason)
            return deduped

        def with_override(reason_list: Sequence[str], attribute_name: str) -> List[str]:
            reasons = dedupe_reasons(reason_list)
            if attribute_name in override_keys:
                reasons.append("manual_override")
            return dedupe_reasons(reasons)

        def reason_weight(reason_list: Sequence[str], base: float) -> float:
            reasons = set(reason_list)
            if "manual_override" in reasons:
                return base + 0.6
            if "name_hit" in reasons:
                return base + 0.5
            if "description_hit" in reasons:
                return base + 0.35
            if "category_hit" in reasons:
                return base + 0.2
            if "default_sweetness_hit" in reasons:
                return base + 0.2
            return base

        tag_reasons: Dict[str, List[str]] = {}
        structural_candidates: List[Tuple[float, str]] = []
        feel_candidates: List[Tuple[float, str]] = []
        ingredient_candidates: List[Tuple[float, str]] = []

        if attributes["tea_base"]:
            tag_reasons["茶感"] = with_override(tea_reasons or ["category_hit"], "tea_base")
            structural_candidates.append((reason_weight(tag_reasons["茶感"], 2.0), "茶感"))
        if attributes["milk_base"] and not attributes["coffee_component"]:
            tag_reasons["奶香"] = with_override(milk_reasons or ["category_hit"], "milk_base")
            structural_candidates.append((reason_weight(tag_reasons["奶香"], 1.95), "奶香"))
        if attributes["fruit_component"] and not attributes["coffee_component"]:
            tag_reasons["果香"] = with_override(fruit_reasons or ["category_hit"], "fruit_component")
            structural_candidates.append((reason_weight(tag_reasons["果香"], 1.9), "果香"))

        if attributes["fresh_profile"] and not (attributes["coffee_component"] and not attributes["fruit_component"]):
            tag_reasons["清新"] = with_override(fresh_reasons or ["derived_profile"], "fresh_profile")
            feel_candidates.append((reason_weight(tag_reasons["清新"], 1.6), "清新"))
        if attributes["smooth_profile"]:
            tag_reasons["顺口"] = with_override(smooth_reasons or ["derived_profile"], "smooth_profile")
            feel_candidates.append((reason_weight(tag_reasons["顺口"], 1.55), "顺口"))
        if attributes["light_profile"]:
            tag_reasons["轻盈"] = with_override(light_reasons or ["derived_profile"], "light_profile")
            feel_candidates.append((reason_weight(tag_reasons["轻盈"], 1.45), "轻盈"))
        if attributes["sugar_friendliness"] == "friendly":
            tag_reasons["无糖友好"] = with_override(no_sugar_reasons or ["derived_profile"], "sugar_friendliness")
            feel_candidates.append((reason_weight(tag_reasons["无糖友好"], 1.5), "无糖友好"))

        ingredient_signal_map = [
            ("柠檬", "lemon_component", lemon_reasons),
            ("茉莉", "jasmine_component", jasmine_reasons),
            ("乌龙", "oolong_component", oolong_reasons),
            ("酸奶", "yogurt_component", yogurt_reasons or (["category_hit"] if normalized_category == "yogurt" else [])),
            ("咖啡", "coffee_component", coffee_reasons or (["category_hit"] if is_coffee else [])),
            ("椰香", "coconut_component", coconut_reasons),
        ]
        for tag, attribute_name, reasons in ingredient_signal_map:
            if attributes.get(attribute_name):
                tag_reasons[tag] = with_override(reasons or ["derived_profile"], attribute_name)
                ingredient_candidates.append((reason_weight(tag_reasons[tag], 1.7), tag))

        structural_candidates.sort(key=lambda item: (-item[0], item[1]))
        feel_candidates.sort(key=lambda item: (-item[0], item[1]))
        ingredient_candidates.sort(key=lambda item: (-item[0], item[1]))

        display_tags: List[str] = []
        if structural_candidates:
            display_tags.append(structural_candidates[0][1])
        if ingredient_candidates and len(display_tags) < 2:
            display_tags.append(ingredient_candidates[0][1])
        if feel_candidates and len(display_tags) < 2:
            display_tags.append(feel_candidates[0][1])
        if not structural_candidates and ingredient_candidates and ingredient_candidates[0][1] not in display_tags and len(display_tags) < 2:
            display_tags.append(ingredient_candidates[0][1])

        if temperature_type == "smoothie":
            shape_tag = "冰沙"
            tag_reasons["冰沙"] = ["temperature_mode"]
        elif temperature_type == "hot":
            shape_tag = "热饮"
            tag_reasons["热饮"] = ["temperature_mode"]
        elif temperature_type == "cold":
            shape_tag = "冷饮"
            tag_reasons["冷饮"] = ["temperature_mode"]
        elif "热" in default_temperature_text and temperature_type in {"multi"}:
            shape_tag = "热饮"
            tag_reasons["热饮"] = ["temperature_mode"]
        else:
            shape_tag = "冷饮"
            tag_reasons["冷饮"] = ["temperature_mode"]
        display_tags.append(shape_tag)

        caffeine_tag_map = {
            "none": "无咖啡因",
            "low": "低咖啡因",
            "normal": "正常咖啡因",
            "strong": "强咖啡因",
        }
        caffeine_tag = caffeine_tag_map.get(caffeine_level_code, "低咖啡因")
        tag_reasons[caffeine_tag] = ["caffeine_rule"]
        if (
            caffeine_tag in {"无咖啡因", "强咖啡因"}
            or attributes["coffee_component"]
            or len(display_tags) < 2
        ) and len(display_tags) < SIMPLE_TAG_DISPLAY_LIMIT:
            display_tags.append(caffeine_tag)

        if display_tags_override:
            overridden_tags: List[str] = []
            for tag in display_tags_override:
                clean_tag = str(tag or "").strip()
                if clean_tag and clean_tag not in overridden_tags:
                    overridden_tags.append(clean_tag)
            display_tags = overridden_tags[:SIMPLE_TAG_DISPLAY_LIMIT]
            for tag in display_tags:
                tag_reasons[tag] = ["manual_override"]

        final_tags: List[str] = []
        for tag in display_tags:
            if tag and tag not in final_tags:
                final_tags.append(tag)
        final_tags = final_tags[:SIMPLE_TAG_DISPLAY_LIMIT]

        return {
            "display_tags": final_tags,
            "evidence": {
                "attributes": attributes,
                "tag_reasons": {tag: tag_reasons.get(tag, ["derived_profile"]) for tag in final_tags},
                "override_applied": bool(attribute_overrides or display_tags_override),
            },
        }

    def _derive_simple_mood_tag_payload(
        self,
        item_name: str,
        description: str,
        normalized_category: str,
        temperature_type: str,
        caffeine_level_code: str,
        display_tags: Sequence[str],
    ) -> Dict[str, Any]:
        text = " ".join(
            str(value or "").strip()
            for value in [item_name, description, normalized_category, " ".join(display_tags)]
            if str(value or "").strip()
        )
        scores = {
            "spark": 0.0,
            "ease": 0.0,
            "cooldown": 0.0,
            "recharge": 0.0,
        }
        reasons: Dict[str, List[str]] = {code: [] for code in scores}

        def add(code: str, amount: float, reason: str) -> None:
            scores[code] += amount
            reasons[code].append(reason)

        tags = set(str(tag or "").strip() for tag in display_tags if str(tag or "").strip())
        category = str(normalized_category or "").strip()
        temp = str(temperature_type or "").strip()
        caffeine = str(caffeine_level_code or "").strip()

        if category in {"coffee", "coffee_latte", "coffee_sparkling"} or "咖啡" in tags:
            add("spark", 2.2, "coffee_or_latte")
        if caffeine == "strong":
            add("spark", 2.4, "strong_caffeine")
        elif caffeine == "normal":
            add("spark", 1.0, "normal_caffeine")
        elif caffeine == "none":
            add("ease", 0.9, "no_caffeine")
            add("cooldown", 0.5, "no_caffeine")

        if tags & {"清新", "轻盈", "柠檬", "茉莉"}:
            add("cooldown", 1.8, "fresh_light_tags")
            add("ease", 0.7, "fresh_light_tags")
        if tags & {"茶感", "乌龙"}:
            add("spark", 0.9, "tea_forward_tags")
            add("ease", 0.5, "tea_forward_tags")
        if tags & {"奶香", "顺口", "椰香"}:
            add("recharge", 1.8, "smooth_milky_tags")
            add("ease", 0.8, "smooth_milky_tags")
        if tags & {"果香", "酸奶"}:
            add("ease", 1.2, "fruity_or_yogurt_tags")
            add("cooldown", 0.7, "fruity_or_yogurt_tags")
        if tags & {"冰沙", "冷饮"} or temp in {"cold", "smoothie"}:
            add("cooldown", 0.8, "cold_shape")
        if tags & {"热饮"} or temp == "hot":
            add("recharge", 0.8, "hot_shape")

        if self._contains_any(text, ("厚", "黑糖", "奥利奥", "冰淇淋", "芝士", "阿华田", "可可", "巧克力")):
            add("recharge", 1.2, "rich_name_signal")
        if self._contains_any(text, ("美式", "浓缩", "冷萃", "dirty", "espresso")):
            add("spark", 1.5, "direct_caffeine_name")
        if self._contains_any(text, ("柠檬", "青提", "西柚", "葡萄", "莓", "桃")):
            add("cooldown", 0.7, "bright_fruit_name")
            add("ease", 0.4, "bright_fruit_name")

        if tags & {"果香"}:
            if tags & {"清新", "轻盈"} or self._contains_any(text, ("柠檬", "青提", "葡萄", "荔枝", "芒果", "西柚", "橙", "橘", "莓", "桃")):
                add("spark", 0.8, "bright_fruit_balance")
                add("ease", 0.3, "bright_fruit_balance")
            else:
                add("spark", 0.4, "bright_fruit_balance")
        if not any(scores.values()):
            add("ease", 0.1, "default_balanced")

        priority = {"spark": 0, "ease": 1, "cooldown": 2, "recharge": 3}
        mood_tag_code = max(scores, key=lambda code: (scores[code], -priority[code]))
        return {
            "mood_tag_code": mood_tag_code,
            "evidence": {
                "scores": {code: round(score, 3) for code, score in scores.items()},
                "reasons": {code: reasons[code] for code in scores if reasons[code]},
                "display_tags": list(display_tags),
            },
        }

    def _derive_simple_verification_status(
        self,
        active_flag: bool,
        source_status: str,
        source_type: str,
        country_code: str,
        currency_code: str,
        image_url: str,
        source_url: str,
        image_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not active_flag:
            return SIMPLE_HIDDEN_STATUS
        if source_status != "active":
            return SIMPLE_HIDDEN_STATUS
        if country_code.upper() != "CN" or currency_code.upper() != "CNY":
            return SIMPLE_HIDDEN_STATUS
        if not image_url or not source_url:
            return SIMPLE_HIDDEN_STATUS
        quality_tier = str((image_meta or {}).get("quality_tier") or "").strip()
        if quality_tier == "brand_poster" and source_type != DELIVERY_PLATFORM_SOURCE_TYPE:
            return SIMPLE_HIDDEN_STATUS
        return SIMPLE_VISIBLE_STATUS

    def _contains_any(self, text: str, keywords: Tuple[str, ...]) -> bool:
        haystack = str(text or "").lower()
        return any(str(keyword).lower() in haystack for keyword in keywords)

    def _loads_json(self, value: Optional[str], fallback: Any) -> Any:
        if value in (None, ""):
            return fallback
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return fallback

    def _dump_json(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
