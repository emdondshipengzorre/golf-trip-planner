"""优惠信息聚合"""
from __future__ import annotations

from scrapers.coupon_scraper import search_coupons


def aggregate_coupons(city: str, course_name: str = None) -> dict:
    """聚合优惠信息并分类

    Returns:
        {
            "all_coupons": [...],
            "by_type": {"球场套餐": [...], "酒店套餐": [...], ...},
            "by_source": {"美团": [...], "携程": [...], ...},
            "total_potential_savings": 999,
            "best_deal": {...},
        }
    """
    coupons = search_coupons(city, course_name)

    by_type = {}
    by_source = {}
    for c in coupons:
        by_type.setdefault(c["type"], []).append(c)
        by_source.setdefault(c["source"], []).append(c)

    total_savings = sum(c["savings"] for c in coupons)
    best_deal = coupons[0] if coupons else None

    return {
        "all_coupons": coupons,
        "by_type": by_type,
        "by_source": by_source,
        "total_potential_savings": total_savings,
        "best_deal": best_deal,
    }
