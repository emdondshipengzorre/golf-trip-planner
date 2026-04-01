"""酒店数据 — Amadeus API (when available) + realistic fallback"""
from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from scrapers.base import cache_get, cache_set, make_cache_key, fetch_json, get_api_key

logger = logging.getLogger("scraper.hotel")
DATA_DIR = Path(__file__).parent.parent / "data"


def search_hotels(city: str, checkin: str, checkout: str,
                   lat: float = None, lng: float = None) -> list[dict]:
    key = make_cache_key("hotels_v3", city=city, checkin=checkin, checkout=checkout)
    cached = cache_get(key)
    if cached:
        return cached

    hotels = None

    if lat and lng:
        hotels = _search_amadeus_hotels(city, checkin, checkout, lat, lng)

    if not hotels:
        hotels = _generate_realistic_hotels(city, checkin, lat, lng)

    cache_set(key, hotels, ttl_seconds=86400)
    return hotels


# ─── Amadeus ───

def _search_amadeus_hotels(city, checkin, checkout, lat, lng):
    from scrapers.flight_scraper import _get_amadeus_token
    token = _get_amadeus_token()
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}

    hotel_list_data = fetch_json(
        "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-geocode",
        headers=headers,
        params={"latitude": lat, "longitude": lng, "radius": 30, "radiusUnit": "KM", "hotelSource": "ALL"},
    )

    if not hotel_list_data or "data" not in hotel_list_data:
        return None

    hotel_ids = [h["hotelId"] for h in hotel_list_data["data"][:15]]
    if not hotel_ids:
        return None

    offers_data = fetch_json(
        "https://test.api.amadeus.com/v3/shopping/hotel-offers",
        headers=headers,
        params={
            "hotelIds": ",".join(hotel_ids),
            "checkInDate": checkin, "checkOutDate": checkout,
            "adults": 1, "currency": "CNY",
        },
    )

    hotels = []
    hotel_geo = {h["hotelId"]: h for h in hotel_list_data["data"]}

    if offers_data and "data" in offers_data:
        for item in offers_data["data"]:
            try:
                hotel = item.get("hotel", {})
                name = hotel.get("name", "Unknown Hotel")
                hotel_id = hotel.get("hotelId", "")
                offer = item.get("offers", [{}])[0]
                price_info = offer.get("price", {})
                price = float(price_info.get("total", 0)) or float(price_info.get("base", 0))
                if not price:
                    continue

                geo = hotel_geo.get(hotel_id, {})
                hotel_lat = geo.get("geoCode", {}).get("latitude", 0)
                hotel_lng = geo.get("geoCode", {}).get("longitude", 0)
                dist_km, drive_min = _calc_distance(hotel_lat, hotel_lng, lat, lng) if hotel_lat else (None, None)
                rating = float(hotel.get("rating", 0) or 0) or 4.0

                hotel_type = "豪华" if price >= 800 else ("舒适" if price >= 350 else "经济")
                score = _calc_value_score(rating, int(price), dist_km)

                hotels.append({
                    "name": name, "city": city, "type": hotel_type,
                    "price_per_night": int(price), "rating": round(rating, 1),
                    "lat": hotel_lat, "lng": hotel_lng,
                    "distance_to_course_km": dist_km, "drive_minutes": drive_min,
                    "value_score": round(score, 1), "source": "Amadeus",
                })
            except (KeyError, IndexError, ValueError):
                continue

    return sorted(hotels, key=lambda x: -x["value_score"]) if hotels else None


# ─── Realistic Fallback ───

HOTEL_DB = {
    "海口": [
        {"name": "观澜湖度假酒店", "type": "豪华", "base": 780, "rating": 4.7, "lat": 19.983, "lng": 110.355},
        {"name": "海口万豪酒店", "type": "豪华", "base": 620, "rating": 4.6, "lat": 20.020, "lng": 110.350},
        {"name": "观澜湖公寓式酒店", "type": "舒适", "base": 420, "rating": 4.4, "lat": 19.980, "lng": 110.352},
        {"name": "海口龙华亚朵", "type": "舒适", "base": 360, "rating": 4.5, "lat": 20.010, "lng": 110.340},
        {"name": "观澜湖附近民宿", "type": "经济", "base": 260, "rating": 4.3, "lat": 19.985, "lng": 110.360},
        {"name": "海口美兰区如家", "type": "经济", "base": 195, "rating": 4.0, "lat": 20.030, "lng": 110.348},
    ],
    "三亚": [
        {"name": "三亚海棠湾万豪", "type": "豪华", "base": 1150, "rating": 4.8, "lat": 18.312, "lng": 109.726},
        {"name": "三亚亚龙湾红树林", "type": "豪华", "base": 880, "rating": 4.7, "lat": 18.219, "lng": 109.638},
        {"name": "三亚吉阳全季", "type": "舒适", "base": 340, "rating": 4.4, "lat": 18.260, "lng": 109.502},
        {"name": "三亚湾海景民宿", "type": "经济", "base": 230, "rating": 4.2, "lat": 18.249, "lng": 109.431},
    ],
    "昆明": [
        {"name": "春城湖畔度假酒店", "type": "豪华", "base": 880, "rating": 4.8, "lat": 24.751, "lng": 103.021},
        {"name": "昆明洲际酒店", "type": "豪华", "base": 680, "rating": 4.7, "lat": 25.038, "lng": 102.718},
        {"name": "阳宗海温泉酒店", "type": "舒适", "base": 430, "rating": 4.5, "lat": 24.755, "lng": 103.025},
        {"name": "昆明市区全季", "type": "舒适", "base": 310, "rating": 4.4, "lat": 25.040, "lng": 102.720},
        {"name": "阳宗海镇民宿", "type": "经济", "base": 170, "rating": 4.2, "lat": 24.760, "lng": 103.030},
    ],
    "丽江": [
        {"name": "玉龙雪山度假酒店", "type": "豪华", "base": 980, "rating": 4.8, "lat": 27.050, "lng": 100.230},
        {"name": "丽江古城客栈", "type": "舒适", "base": 340, "rating": 4.6, "lat": 26.877, "lng": 100.234},
        {"name": "束河古镇民宿", "type": "经济", "base": 195, "rating": 4.3, "lat": 26.912, "lng": 100.195},
    ],
    "深圳": [
        {"name": "深圳观澜湖度假酒店", "type": "豪华", "base": 750, "rating": 4.6, "lat": 22.699, "lng": 114.066},
        {"name": "深圳福田亚朵", "type": "舒适", "base": 380, "rating": 4.5, "lat": 22.534, "lng": 114.054},
        {"name": "深圳南山如家", "type": "经济", "base": 220, "rating": 4.1, "lat": 22.523, "lng": 113.930},
    ],
}


def _generate_realistic_hotels(city: str, checkin: str,
                                 course_lat: float = None, course_lng: float = None) -> list[dict]:
    """基于真实酒店数据模型生成"""
    templates = HOTEL_DB.get(city, [
        {"name": f"{city}商务酒店", "type": "舒适", "base": 340, "rating": 4.3, "lat": 0, "lng": 0},
        {"name": f"{city}快捷酒店", "type": "经济", "base": 185, "rating": 4.0, "lat": 0, "lng": 0},
    ])

    # 用日期做种子保持一致
    rng = random.Random(hash(f"{city}{checkin}"))

    # 周末/假期价格上浮
    from scrapers.flight_scraper import HOLIDAYS_2026
    is_holiday = any(s <= checkin <= e for s, e in HOLIDAYS_2026)
    from datetime import datetime
    dt = datetime.strptime(checkin, "%Y-%m-%d")
    is_weekend = dt.weekday() >= 5
    price_factor = 1.5 if is_holiday else (1.2 if is_weekend else 1.0)

    hotels = []
    for t in templates:
        price = int(t["base"] * price_factor + rng.randint(-30, 60))
        price = max(price, 100)

        dist_km, drive_min = (None, None)
        if course_lat and course_lng and t["lat"] and t["lng"]:
            dist_km, drive_min = _calc_distance(t["lat"], t["lng"], course_lat, course_lng)

        score = _calc_value_score(t["rating"], price, dist_km)

        hotels.append({
            "name": t["name"], "city": city, "type": t["type"],
            "price_per_night": price, "rating": t["rating"],
            "lat": t["lat"], "lng": t["lng"],
            "distance_to_course_km": dist_km, "drive_minutes": drive_min,
            "value_score": round(score, 1), "source": "参考数据",
        })

    return sorted(hotels, key=lambda x: -x["value_score"])


# ─── 工具 ───

def _calc_distance(lat1, lng1, lat2, lng2):
    dlat = abs(lat1 - lat2) * 111
    dlng = abs(lng1 - lng2) * 111 * 0.85
    dist_km = round((dlat ** 2 + dlng ** 2) ** 0.5, 1)
    drive_min = max(5, int(dist_km * 2.5))
    return dist_km, drive_min


def _calc_value_score(rating, price, dist_km):
    if not rating or not price:
        return 0.0
    score = rating * (1000 / max(price, 1))
    if dist_km is not None and dist_km > 0:
        score *= (1 / max(dist_km, 0.1))
    return score
