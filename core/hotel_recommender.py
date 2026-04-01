"""酒店筛选推荐 + 球场距离计算"""
from __future__ import annotations

from scrapers.hotel_scraper import search_hotels


def recommend_hotels(
    city: str,
    checkin: str,
    checkout: str,
    course_lat: float = None,
    course_lng: float = None,
    budget_max: int = None,
    hotel_type: str = None,
) -> dict:
    """筛选并推荐酒店

    Args:
        budget_max: 每晚最高预算
        hotel_type: "经济" / "舒适" / "豪华" 或 None（全部）

    Returns:
        {
            "all_hotels": [...],
            "filtered": [...],
            "best_value": {...},
            "nearest": {...},
            "cheapest": {...},
            "stats": {"avg_price": ..., "price_range": ...},
        }
    """
    hotels = search_hotels(city, checkin, checkout, course_lat, course_lng)

    filtered = hotels[:]
    if budget_max:
        filtered = [h for h in filtered if h["price_per_night"] <= budget_max]
    if hotel_type:
        filtered = [h for h in filtered if h["type"] == hotel_type]

    if not filtered:
        return {
            "all_hotels": hotels,
            "filtered": [],
            "best_value": None,
            "nearest": None,
            "cheapest": None,
            "stats": {"avg_price": 0, "price_range": (0, 0)},
        }

    prices = [h["price_per_night"] for h in filtered]
    best_value = max(filtered, key=lambda h: h["value_score"])
    cheapest = min(filtered, key=lambda h: h["price_per_night"])

    nearest = None
    has_distance = [h for h in filtered if h.get("distance_to_course_km") is not None]
    if has_distance:
        nearest = min(has_distance, key=lambda h: h["distance_to_course_km"])

    return {
        "all_hotels": hotels,
        "filtered": filtered,
        "best_value": best_value,
        "nearest": nearest,
        "cheapest": cheapest,
        "stats": {
            "avg_price": round(sum(prices) / len(prices)),
            "price_range": (min(prices), max(prices)),
        },
    }
