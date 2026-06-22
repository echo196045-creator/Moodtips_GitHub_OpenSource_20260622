from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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

CONTEXT_FIELDS = FEATURE_FIELDS + [
    "price_low_w",
    "price_mid_w",
    "price_high_w",
    "hot_available_w",
    "cold_available_w",
]

PRICE_BAND_ORDER = {"low": 0, "mid": 1, "high": 2}

FEATURE_LABELS = {
    "tea_intensity": "茶感清晰",
    "milk_intensity": "奶感更顺口",
    "fruit_intensity": "果香更明显",
    "sweetness_intensity": "甜感更满足",
    "refresh_intensity": "清爽轻负担",
    "comfort_intensity": "更有安抚感",
    "energy_intensity": "提神更直接",
    "indulgence_intensity": "奖励感更强",
    "heaviness_intensity": "口感更厚实",
    "caffeine_level": "咖啡因更明显",
}

GOAL_COPY = {
    "focus": "这次优先把清醒感和决策效率放在前面。",
    "relax": "这次更偏向顺口、安稳和放松。",
    "refresh": "这次优先给你干净、轻快、不腻的口感。",
    "reward": "这次更偏向一点满足感和被奖励到的感觉。",
}

MOOD_PREFIX = {
    "tired": "今天已经够累了，",
    "stressed": "先别让味道再给你添负担，",
    "empty": "这杯像是给自己留一点余地，",
    "need_care": "先让自己被轻轻接住，",
    "foggy": "现在更需要一点清醒的推力，",
    "none": "",
    "": "",
}

FOLLOWUP_QUESTIONS = {
    "taste_axis": {
        "question_type": "taste_axis",
        "title": "再问一句，口感会更准",
        "question": "你现在更想要奶感还是茶感？",
        "options": [
            {"value": "more_milk", "label": "奶感一点"},
            {"value": "more_tea", "label": "茶感一点"},
        ],
    },
    "caffeine_axis": {
        "question_type": "caffeine_axis",
        "title": "再确认一下提神强度",
        "question": "现在能接受比较明显的咖啡因吗？",
        "options": [
            {"value": "allow", "label": "可以"},
            {"value": "limit", "label": "适中就好"},
            {"value": "avoid", "label": "尽量不要"},
        ],
    },
    "temperature_axis": {
        "question_type": "temperature_axis",
        "title": "再确认一下温度",
        "question": "你现在更想喝热的还是冰的？",
        "options": [
            {"value": "hot", "label": "热的"},
            {"value": "cold", "label": "冰的"},
        ],
    },
    "sweetness_axis": {
        "question_type": "sweetness_axis",
        "title": "最后收一下口味方向",
        "question": "今天更想要清爽一点，还是满足一点？",
        "options": [
            {"value": "less_sweet", "label": "更清爽"},
            {"value": "indulgent", "label": "更满足"},
        ],
    },
    "scene_axis": {
        "question_type": "scene_axis",
        "title": "补一个场景会更稳",
        "question": "你现在更接近哪个场景？",
        "options": [
            {"value": "study", "label": "工作/学习"},
            {"value": "commute", "label": "通勤路上"},
            {"value": "after_work", "label": "下班后"},
            {"value": "alone", "label": "自己待着"},
        ],
    },
}


@dataclass
class RequestPayload:
    entry_mode: str
    goal: str
    mood: str
    scene: str
    budget_band: str
    temperature_pref: str
    caffeine_pref: str
    dairy_avoid: bool
    micro_adjusts: List[str]
    profile: Dict[str, Any]
    top_k: int


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def normalize_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def normalize_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if "|" in stripped:
            return [item for item in stripped.split("|") if item]
        return [stripped]
    return [str(value)]


def load_sku_catalog(path: Path) -> List[Dict[str, Any]]:
    rows = read_csv_rows(path)
    skus: List[Dict[str, Any]] = []
    for row in rows:
        normalized = dict(row)
        normalized["base_price"] = normalize_float(row["base_price"])
        normalized["available_hot"] = int(row["available_hot"])
        normalized["available_cold"] = int(row["available_cold"])
        normalized["dairy_flag"] = int(row["dairy_flag"])
        for field in FEATURE_FIELDS:
            normalized[field] = normalize_float(row[field])
        normalized["default_scene_tags"] = normalize_list(row.get("default_scene_tags"))
        normalized["default_mood_tags"] = normalize_list(row.get("default_mood_tags"))
        skus.append(normalized)
    return skus


def load_weight_matrix(path: Path) -> Dict[str, Dict[str, Dict[str, float]]]:
    rows = read_csv_rows(path)
    weights: Dict[str, Dict[str, Dict[str, float]]] = {}
    for row in rows:
        context_type = row["context_type"]
        context_code = row["context_code"]
        numeric_row = {field: normalize_float(row.get("%s_w" % field)) for field in FEATURE_FIELDS}
        for field in ["price_low_w", "price_mid_w", "price_high_w", "hot_available_w", "cold_available_w"]:
            numeric_row[field] = normalize_float(row.get(field))
        weights.setdefault(context_type, {})[context_code] = numeric_row
    return weights


def load_request_payload(path: Path) -> RequestPayload:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return RequestPayload(
        entry_mode=str(raw.get("entry_mode", "quick")),
        goal=str(raw.get("goal", "refresh")),
        mood=str(raw.get("mood", "none")),
        scene=str(raw.get("scene", "")),
        budget_band=str(raw.get("budget_band", "high")),
        temperature_pref=str(raw.get("temperature_pref", "any")),
        caffeine_pref=str(raw.get("caffeine_pref", "allow")),
        dairy_avoid=normalize_bool(raw.get("dairy_avoid", False)),
        micro_adjusts=normalize_list(raw.get("micro_adjusts")),
        profile=raw.get("profile", {}) or {},
        top_k=int(raw.get("top_k", 3)),
    )


def build_context_weights(
    weight_matrix: Dict[str, Dict[str, Dict[str, float]]],
    payload: RequestPayload,
) -> Tuple[Dict[str, float], List[Dict[str, str]]]:
    combined = {field: 0.0 for field in CONTEXT_FIELDS}
    applied_rows: List[Dict[str, str]] = []

    contexts: List[Tuple[str, str]] = [("goal", payload.goal)]
    if payload.mood and payload.mood != "none":
        contexts.append(("mood", payload.mood))
    if payload.scene:
        contexts.append(("scene", payload.scene))
    for adjust_code in payload.micro_adjusts:
        contexts.append(("adjust", adjust_code))

    for context_type, context_code in contexts:
        row = weight_matrix.get(context_type, {}).get(context_code)
        if not row:
            continue
        applied_rows.append({"context_type": context_type, "context_code": context_code})
        for field in CONTEXT_FIELDS:
            combined[field] += row[field]

    return combined, applied_rows


def budget_allows(user_band: str, sku_band: str) -> bool:
    if user_band not in PRICE_BAND_ORDER or sku_band not in PRICE_BAND_ORDER:
        return True
    return PRICE_BAND_ORDER[sku_band] <= PRICE_BAND_ORDER[user_band]


def passes_hard_filters(sku: Dict[str, Any], payload: RequestPayload) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    if not budget_allows(payload.budget_band, sku["price_band"]):
        reasons.append("budget")
    if payload.temperature_pref == "hot" and not sku["available_hot"]:
        reasons.append("hot_unavailable")
    if payload.temperature_pref == "cold" and not sku["available_cold"]:
        reasons.append("cold_unavailable")
    if payload.caffeine_pref == "avoid" and sku["caffeine_level"] >= 4:
        reasons.append("high_caffeine")
    if payload.caffeine_pref == "limit" and sku["caffeine_level"] >= 5:
        reasons.append("very_high_caffeine")
    if payload.dairy_avoid and sku["dairy_flag"] == 1:
        reasons.append("contains_dairy")
    if sku.get("status") != "active":
        reasons.append("inactive")
    return len(reasons) == 0, reasons


def calc_profile_score(sku: Dict[str, Any], payload: RequestPayload) -> float:
    profile = payload.profile or {}
    score = 0.0

    if "sweet_pref" in profile:
        diff = abs(normalize_float(profile["sweet_pref"]) - sku["sweetness_intensity"])
        if diff <= 1:
            score += 0.4
        elif diff >= 3:
            score -= 0.4

    if "caffeine_pref_level" in profile:
        diff = abs(normalize_float(profile["caffeine_pref_level"]) - sku["caffeine_level"])
        if diff <= 1:
            score += 0.4
        elif diff >= 3:
            score -= 0.6

    usual_temp = str(profile.get("usual_temp", ""))
    if usual_temp == "hot" and sku["available_hot"]:
        score += 0.2
    if usual_temp == "cold" and sku["available_cold"]:
        score += 0.2

    liked_categories = normalize_list(profile.get("liked_categories"))
    disliked_categories = normalize_list(profile.get("disliked_categories"))
    if sku["category"] in liked_categories:
        score += 0.5
    if sku["category"] in disliked_categories:
        score -= 0.5

    return score


def calc_price_band_score(sku: Dict[str, Any], context: Dict[str, float]) -> float:
    band = sku["price_band"]
    if band == "low":
        return context["price_low_w"]
    if band == "mid":
        return context["price_mid_w"]
    if band == "high":
        return context["price_high_w"]
    return 0.0


def calc_temperature_score(sku: Dict[str, Any], payload: RequestPayload, context: Dict[str, float]) -> float:
    if payload.temperature_pref == "hot":
        return context["hot_available_w"] * sku["available_hot"]
    if payload.temperature_pref == "cold":
        return context["cold_available_w"] * sku["available_cold"]
    return 0.0


def calc_hard_match_count(sku: Dict[str, Any], payload: RequestPayload) -> int:
    count = 1
    if payload.budget_band:
        count += int(budget_allows(payload.budget_band, sku["price_band"]))
    if payload.temperature_pref == "hot":
        count += int(sku["available_hot"] == 1)
    elif payload.temperature_pref == "cold":
        count += int(sku["available_cold"] == 1)
    if payload.caffeine_pref == "avoid":
        count += int(sku["caffeine_level"] < 4)
    elif payload.caffeine_pref == "limit":
        count += int(sku["caffeine_level"] < 5)
    if payload.dairy_avoid:
        count += int(sku["dairy_flag"] == 0)
    return count


def build_feature_contributions(sku: Dict[str, Any], context: Dict[str, float]) -> Dict[str, float]:
    contributions: Dict[str, float] = {}
    for field in FEATURE_FIELDS:
        contributions[field] = sku[field] * context[field]
    return contributions


def build_explanation_tags(
    sku: Dict[str, Any],
    payload: RequestPayload,
    contributions: Dict[str, float],
    final_score: float,
) -> List[str]:
    tags: List[str] = []

    if payload.budget_band in {"low", "mid"} and sku["price_band"] == "low":
        tags.append("预算友好")
    elif payload.budget_band == "mid" and sku["price_band"] == "mid":
        tags.append("价格稳妥")

    if payload.temperature_pref == "hot" and sku["available_hot"]:
        tags.append("热饮可选")
    elif payload.temperature_pref == "cold" and sku["available_cold"]:
        tags.append("冷饮更合适")

    sorted_features = sorted(contributions.items(), key=lambda item: item[1], reverse=True)
    for field, score in sorted_features:
        if score <= 0:
            continue
        label = FEATURE_LABELS.get(field)
        if label and label not in tags:
            tags.append(label)
        if len(tags) >= 3:
            break

    if not tags:
        if final_score >= 0:
            tags.append("整体匹配度较高")
        else:
            tags.append("作为备选更稳妥")

    return tags[:3]


def build_emotional_copy(payload: RequestPayload, tags: List[str]) -> str:
    prefix = MOOD_PREFIX.get(payload.mood, "")
    goal_copy = GOAL_COPY.get(payload.goal, "这次会尽量给你一个更顺手的选择。")
    tag_copy = ""
    if tags:
        tag_copy = " 这次更偏向%s。" % "、".join(tags[:2])
    return "%s%s%s" % (prefix, goal_copy, tag_copy)


def build_order_hint(sku: Dict[str, Any]) -> str:
    temp_hint = "冷热都可" if sku["available_hot"] and sku["available_cold"] else "更适合热饮" if sku["available_hot"] else "更适合冷饮"
    return "建议先搜索“%s”，%s，价格约 %.0f 元。" % (sku["sku_name"], temp_hint, sku["base_price"])


def choose_followup_question(payload: RequestPayload, ranked_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    top_results = ranked_results[:3]
    if not top_results:
        return FOLLOWUP_QUESTIONS["scene_axis"]

    if payload.entry_mode == "mood" and not payload.scene:
        return FOLLOWUP_QUESTIONS["scene_axis"]

    caffeine_levels = [item["sku"]["caffeine_level"] for item in top_results]
    if payload.caffeine_pref == "allow" and max(caffeine_levels) - min(caffeine_levels) >= 3:
        return FOLLOWUP_QUESTIONS["caffeine_axis"]

    if payload.temperature_pref == "any":
        hot_only = any(item["sku"]["available_hot"] and not item["sku"]["available_cold"] for item in top_results)
        cold_only = any(item["sku"]["available_cold"] and not item["sku"]["available_hot"] for item in top_results)
        if hot_only and cold_only:
            return FOLLOWUP_QUESTIONS["temperature_axis"]

    milk_values = [item["sku"]["milk_intensity"] for item in top_results]
    tea_values = [item["sku"]["tea_intensity"] for item in top_results]
    if max(milk_values) - min(milk_values) >= 2 and max(tea_values) - min(tea_values) >= 2:
        return FOLLOWUP_QUESTIONS["taste_axis"]

    if payload.goal == "reward":
        sweetness_values = [item["sku"]["sweetness_intensity"] for item in top_results]
        if max(sweetness_values) - min(sweetness_values) >= 2:
            return FOLLOWUP_QUESTIONS["sweetness_axis"]

    return FOLLOWUP_QUESTIONS["taste_axis"]


def evaluate_request(
    sku_catalog: List[Dict[str, Any]],
    weight_matrix: Dict[str, Dict[str, Dict[str, float]]],
    payload: RequestPayload,
    debug: bool = False,
) -> Dict[str, Any]:
    context, applied_rows = build_context_weights(weight_matrix, payload)
    ranked: List[Dict[str, Any]] = []
    filtered_out: List[Dict[str, Any]] = []

    for sku in sku_catalog:
        passed, reasons = passes_hard_filters(sku, payload)
        if not passed:
            filtered_out.append({"sku_id": sku["sku_id"], "sku_name": sku["sku_name"], "reasons": reasons})
            continue

        contributions = build_feature_contributions(sku, context)
        feature_score = sum(contributions.values())
        price_score = calc_price_band_score(sku, context)
        temperature_score = calc_temperature_score(sku, payload, context)
        profile_score = calc_profile_score(sku, payload)
        final_score = feature_score + price_score + temperature_score + profile_score
        hard_match_count = calc_hard_match_count(sku, payload)

        ranked.append(
            {
                "sku": sku,
                "final_score": round(final_score, 3),
                "feature_score": round(feature_score, 3),
                "price_score": round(price_score, 3),
                "temperature_score": round(temperature_score, 3),
                "profile_score": round(profile_score, 3),
                "hard_match_count": hard_match_count,
                "contributions": contributions,
            }
        )

    ranked.sort(key=lambda item: item["final_score"], reverse=True)

    if not ranked:
        return {
            "session_input": payload.__dict__,
            "meta": {
                "candidate_count": 0,
                "filtered_out_count": len(filtered_out),
                "followup_required": False,
                "confidence_score": 0.0,
                "applied_contexts": applied_rows,
            },
            "followup_question": None,
            "recommendations": [],
            "filtered_out": filtered_out if debug else [],
        }

    top1 = ranked[0]
    top2 = ranked[1] if len(ranked) > 1 else ranked[0]
    score_gap = top1["final_score"] - top2["final_score"]
    confidence_score = min(
        0.95,
        0.45 + 0.12 * score_gap + 0.05 * top1["hard_match_count"],
    )
    followup_required = score_gap < 0.8 or confidence_score < 0.60
    followup_question = choose_followup_question(payload, ranked) if followup_required else None

    top_k = max(1, payload.top_k)
    recommendation_cards: List[Dict[str, Any]] = []
    for index, item in enumerate(ranked[:top_k], start=1):
        sku = item["sku"]
        tags = build_explanation_tags(sku, payload, item["contributions"], item["final_score"])
        card = {
            "rank": index,
            "sku_id": sku["sku_id"],
            "sku_name": sku["sku_name"],
            "category": sku["category"],
            "base_price": sku["base_price"],
            "price_band": sku["price_band"],
            "score": item["final_score"],
            "explanation_tags": tags,
            "emotional_copy": build_emotional_copy(payload, tags),
            "order_hint": build_order_hint(sku),
        }
        if debug:
            card["debug"] = {
                "feature_score": item["feature_score"],
                "price_score": item["price_score"],
                "temperature_score": item["temperature_score"],
                "profile_score": item["profile_score"],
                "top_feature_contributions": sorted(
                    ((field, round(score, 3)) for field, score in item["contributions"].items()),
                    key=lambda pair: pair[1],
                    reverse=True,
                )[:5],
            }
        recommendation_cards.append(card)

    return {
        "session_input": payload.__dict__,
        "meta": {
            "candidate_count": len(ranked),
            "filtered_out_count": len(filtered_out),
            "score_gap_top1_top2": round(score_gap, 3),
            "followup_required": followup_required,
            "confidence_score": round(confidence_score, 3),
            "applied_contexts": applied_rows,
        },
        "followup_question": followup_question,
        "recommendations": recommendation_cards,
        "filtered_out": filtered_out if debug else [],
    }


def default_request_path(script_dir: Path) -> Path:
    return script_dir / "moodsips_demo_requests_20260404.json"


def load_preset_request(preset_name: str, request_path: Path) -> RequestPayload:
    raw = json.loads(request_path.read_text(encoding="utf-8"))
    if preset_name not in raw:
        raise KeyError("Preset '%s' was not found in %s" % (preset_name, request_path))
    preset_file = request_path.parent / (preset_name + ".tmp.request.json")
    preset_file.write_text(json.dumps(raw[preset_name], ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        return load_request_payload(preset_file)
    finally:
        preset_file.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MoodSips v1 recommendation engine demo")
    parser.add_argument("--request", type=str, help="Path to a single request JSON payload")
    parser.add_argument("--preset", type=str, help="Preset name from moodsips_demo_requests_20260404.json")
    parser.add_argument("--top-k", type=int, default=3, help="Number of results to return")
    parser.add_argument("--debug", action="store_true", help="Include debug scoring breakdowns")
    parser.add_argument("--out", type=str, help="Optional output JSON file path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[1]
    prototype_dir = project_root / "07_prototype"

    sku_catalog = load_sku_catalog(prototype_dir / "moodsips_v1_seed_sku_catalog_20260404.csv")
    weight_matrix = load_weight_matrix(prototype_dir / "moodsips_v1_weight_matrix_20260404.csv")

    if args.request:
        payload = load_request_payload(Path(args.request))
    else:
        preset_name = args.preset or "focus_foggy_commute"
        payload = load_preset_request(preset_name, default_request_path(script_dir))

    payload.top_k = args.top_k
    result = evaluate_request(sku_catalog, weight_matrix, payload, debug=args.debug)

    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(serialized, encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
