"""优惠信息 — 手动录入 + JSON 数据库（无可靠的免费优惠 API）"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from scrapers.base import cache_get, cache_set, make_cache_key

logger = logging.getLogger("scraper.coupon")

DATA_DIR = Path(__file__).parent.parent / "data"
COUPONS_FILE = DATA_DIR / "manual_coupons.json"


def search_coupons(city: str, course_name: str = None) -> list[dict]:
    """搜索优惠信息"""
    key = make_cache_key("coupons_v3", city=city, course=course_name or "")
    cached = cache_get(key)
    if cached:
        return cached

    coupons = _load_coupons(city, course_name)
    result = sorted(coupons, key=lambda x: -x.get("savings", 0))
    cache_set(key, result, ttl_seconds=43200)
    return result


def _load_coupons(city: str, course_name: str = None) -> list[dict]:
    """从 JSON 文件加载优惠"""
    if not COUPONS_FILE.exists():
        return []

    try:
        with open(COUPONS_FILE, "r", encoding="utf-8") as f:
            all_coupons = json.load(f)

        filtered = [c for c in all_coupons if c.get("city") == city]
        if course_name:
            filtered = [c for c in filtered
                        if not c.get("course") or c["course"] == course_name]

        logger.info(f"Loaded {len(filtered)} coupons for {city}")
        return filtered

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to load coupons: {e}")
        return []


def save_coupon(coupon: dict):
    """保存一条优惠信息"""
    coupons = []
    if COUPONS_FILE.exists():
        with open(COUPONS_FILE, "r", encoding="utf-8") as f:
            coupons = json.load(f)

    coupon["source"] = coupon.get("source", "手动录入")
    if "savings" not in coupon:
        coupon["savings"] = coupon.get("original_price", 0) - coupon.get("discount_price", 0)

    coupons.append(coupon)

    COUPONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(COUPONS_FILE, "w", encoding="utf-8") as f:
        json.dump(coupons, f, ensure_ascii=False, indent=2)

    # 清除缓存
    from scrapers.base import cache_clear
    cache_clear()

    logger.info(f"Saved coupon: {coupon['title']}")


def delete_coupon(title: str, city: str):
    """删除一条优惠"""
    if not COUPONS_FILE.exists():
        return

    with open(COUPONS_FILE, "r", encoding="utf-8") as f:
        coupons = json.load(f)

    coupons = [c for c in coupons if not (c["title"] == title and c.get("city") == city)]

    with open(COUPONS_FILE, "w", encoding="utf-8") as f:
        json.dump(coupons, f, ensure_ascii=False, indent=2)
