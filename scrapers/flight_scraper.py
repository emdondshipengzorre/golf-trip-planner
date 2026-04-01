"""机票数据 — Amadeus API (when available) + smart fallback"""
from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

from scrapers.base import cache_get, cache_set, make_cache_key, fetch_json, get_api_key

logger = logging.getLogger("scraper.flight")
DATA_DIR = Path(__file__).parent.parent / "data"

_city_iata = None


def _get_iata(city: str) -> str:
    global _city_iata
    if _city_iata is None:
        with open(DATA_DIR / "cities.json", "r", encoding="utf-8") as f:
            cities = json.load(f)["cities"]
        _city_iata = {c["name"]: c["airports"][0]["iata"] for c in cities}
    return _city_iata.get(city, "")


# ─── Amadeus OAuth ───

_amadeus_token = None
_token_expires = 0


def _get_amadeus_token() -> str | None:
    global _amadeus_token, _token_expires
    import time

    if _amadeus_token and time.time() < _token_expires:
        return _amadeus_token

    client_id = get_api_key("AMADEUS_API_KEY")
    client_secret = get_api_key("AMADEUS_API_SECRET")
    if not client_id or not client_secret:
        return None

    try:
        import requests
        resp = requests.post(
            "https://test.api.amadeus.com/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            _amadeus_token = data["access_token"]
            _token_expires = time.time() + data.get("expires_in", 1799) - 60
            return _amadeus_token
    except Exception as e:
        logger.error(f"Amadeus auth error: {e}")
    return None


# ─── 公开接口 ───

def search_flights(origin: str, destination: str, date: str) -> list[dict]:
    key = make_cache_key("flights_v3", origin=origin, dest=destination, date=date)
    cached = cache_get(key)
    if cached:
        return cached

    # 尝试 Amadeus
    flights = _search_amadeus(origin, destination, date)

    # Fallback
    if not flights:
        flights = _generate_realistic_flights(origin, destination, date)

    cache_set(key, flights, ttl_seconds=14400)
    return flights


def search_flights_range(origin: str, destination: str, start_date: str, days: int = 30) -> dict:
    key = make_cache_key("flight_range_v3", origin=origin, dest=destination, start=start_date, days=days)
    cached = cache_get(key)
    if cached:
        return cached

    start = datetime.strptime(start_date, "%Y-%m-%d")
    dates = []
    min_prices = []
    all_flights = {}

    for i in range(days):
        d = start + timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        flights = search_flights(origin, destination, date_str)
        dates.append(date_str)
        prices = [f["price"] for f in flights]
        min_prices.append(min(prices) if prices else 0)
        all_flights[date_str] = flights

    result = {"dates": dates, "min_prices": min_prices, "flights": all_flights}
    cache_set(key, result, ttl_seconds=14400)
    return result


# ─── Amadeus Flight Offers ───

def _search_amadeus(origin: str, destination: str, date: str) -> list[dict] | None:
    token = _get_amadeus_token()
    if not token:
        return None

    origin_iata = _get_iata(origin)
    dest_iata = _get_iata(destination)
    if not origin_iata or not dest_iata:
        return None

    data = fetch_json(
        "https://test.api.amadeus.com/v2/shopping/flight-offers",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "originLocationCode": origin_iata,
            "destinationLocationCode": dest_iata,
            "departureDate": date,
            "adults": 1,
            "currencyCode": "CNY",
            "max": 10,
        },
    )

    if not data or "data" not in data:
        return None

    flights = []
    for offer in data["data"]:
        try:
            itinerary = offer["itineraries"][0]
            segments = itinerary["segments"]
            first_seg = segments[0]
            last_seg = segments[-1]

            dep_time = first_seg["departure"]["at"][11:16]
            arr_time = last_seg["arrival"]["at"][11:16]
            duration_raw = itinerary.get("duration", "")
            duration_str = duration_raw.replace("PT", "").lower() if duration_raw else ""
            price = float(offer["price"]["total"])
            airline_code = first_seg["carrierCode"]
            flight_no = f"{airline_code}{first_seg['number']}"
            dep_hour = int(dep_time[:2])

            flights.append({
                "airline": AIRLINE_NAMES.get(airline_code, airline_code),
                "airline_code": airline_code,
                "flight_no": flight_no,
                "origin": origin,
                "destination": destination,
                "date": date,
                "dep_time": dep_time,
                "arr_time": arr_time,
                "duration": duration_str,
                "price": int(price),
                "is_red_eye": dep_hour >= 22 or dep_hour < 6,
                "direct": len(segments) == 1,
                "source": "Amadeus",
            })
        except (KeyError, IndexError, ValueError):
            continue

    return sorted(flights, key=lambda x: x["price"]) if flights else None


# ─── Realistic Fallback ───

# 基于真实航线数据的价格和时刻表模型
ROUTE_DATA = {
    ("北京", "海口"): {"base": (980, 1650), "duration": (3.5, 4.2), "flights_per_day": 8},
    ("北京", "三亚"): {"base": (1100, 1800), "duration": (4.0, 4.8), "flights_per_day": 6},
    ("北京", "昆明"): {"base": (850, 1500), "duration": (3.5, 4.2), "flights_per_day": 7},
    ("北京", "丽江"): {"base": (950, 1750), "duration": (4.0, 4.8), "flights_per_day": 3},
    ("北京", "深圳"): {"base": (750, 1350), "duration": (3.0, 3.5), "flights_per_day": 12},
    ("北京", "烟台"): {"base": (380, 750), "duration": (1.3, 1.8), "flights_per_day": 5},
    ("北京", "天津"): {"base": (250, 500), "duration": (0.8, 1.2), "flights_per_day": 3},
    ("北京", "秦皇岛"): {"base": (300, 600), "duration": (1.0, 1.5), "flights_per_day": 2},
}
# 反向航线同价
for (a, b), v in list(ROUTE_DATA.items()):
    ROUTE_DATA[(b, a)] = v

AIRLINE_NAMES = {
    "CA": "中国国航", "HU": "海南航空", "CZ": "南方航空",
    "MU": "东方航空", "9C": "春秋航空", "ZH": "深圳航空",
    "FM": "上海航空", "SC": "山东航空", "3U": "四川航空",
}

# 航线常飞航司
ROUTE_AIRLINES = {
    ("北京", "海口"): ["CA", "HU", "CZ", "MU", "9C"],
    ("北京", "三亚"): ["CA", "HU", "CZ", "MU"],
    ("北京", "昆明"): ["CA", "CZ", "MU", "3U"],
    ("北京", "丽江"): ["CA", "MU", "3U"],
    ("北京", "深圳"): ["CA", "CZ", "ZH", "HU", "9C"],
    ("北京", "烟台"): ["CA", "SC", "MU"],
    ("北京", "天津"): ["CA", "9C"],
    ("北京", "秦皇岛"): ["CA", "9C"],
}
for (a, b), v in list(ROUTE_AIRLINES.items()):
    ROUTE_AIRLINES[(b, a)] = v

# 2026 中国法定假期
HOLIDAYS_2026 = [
    ("2026-01-01", "2026-01-03"),
    ("2026-01-26", "2026-02-01"),
    ("2026-04-04", "2026-04-06"),
    ("2026-05-01", "2026-05-05"),
    ("2026-06-19", "2026-06-21"),
    ("2026-09-25", "2026-10-07"),
]

# 标准出发时刻
DEPARTURE_SLOTS = [
    ("06:30", 0.80), ("07:15", 0.85), ("08:00", 0.90), ("09:30", 0.95),
    ("10:45", 1.00), ("12:00", 0.95), ("13:30", 0.95), ("14:50", 1.00),
    ("16:15", 1.05), ("17:30", 1.05), ("19:00", 1.00), ("20:30", 0.90),
    ("22:00", 0.70), ("23:15", 0.65),
]


def _generate_realistic_flights(origin: str, destination: str, date: str) -> list[dict]:
    """基于真实航线模型生成航班数据"""
    route = ROUTE_DATA.get((origin, destination))
    if not route:
        route = {"base": (800, 1400), "duration": (3.0, 4.0), "flights_per_day": 4}

    airlines = ROUTE_AIRLINES.get((origin, destination), ["CA", "CZ", "MU"])

    dt = datetime.strptime(date, "%Y-%m-%d")
    # 用日期作为随机种子 → 同一天同一航线结果一致
    seed = hash(f"{origin}{destination}{date}")
    rng = random.Random(seed)

    # 价格因子
    is_holiday = any(s <= date <= e for s, e in HOLIDAYS_2026)
    is_weekend = dt.weekday() >= 5
    # 提前天数影响价格
    days_ahead = (dt - datetime.now()).days
    advance_factor = 1.0
    if days_ahead < 3:
        advance_factor = 1.4
    elif days_ahead < 7:
        advance_factor = 1.2
    elif days_ahead < 14:
        advance_factor = 1.1
    elif days_ahead > 30:
        advance_factor = 0.9

    holiday_factor = 1.5 if is_holiday else (1.2 if is_weekend else 1.0)
    base_low, base_high = route["base"]

    # 选择本日航班时刻
    num_flights = route["flights_per_day"] + rng.randint(-1, 1)
    num_flights = max(2, min(num_flights, len(DEPARTURE_SLOTS)))
    slots = rng.sample(DEPARTURE_SLOTS, num_flights)
    slots.sort(key=lambda x: x[0])

    flights = []
    for dep_str, time_factor in slots:
        airline_code = rng.choice(airlines)
        flight_num = rng.randint(1000, 9999)

        # 价格计算
        base = rng.randint(base_low, base_high)
        price = int(base * holiday_factor * advance_factor * time_factor)
        price = max(price, 280)

        # 飞行时间
        dur_low, dur_high = route["duration"]
        duration_h = rng.uniform(dur_low, dur_high)
        dep_hour = int(dep_str[:2])
        dep_min = int(dep_str[3:5])
        arr_total_min = dep_hour * 60 + dep_min + int(duration_h * 60)
        arr_hour = (arr_total_min // 60) % 24
        arr_min = arr_total_min % 60

        flights.append({
            "airline": AIRLINE_NAMES.get(airline_code, airline_code),
            "airline_code": airline_code,
            "flight_no": f"{airline_code}{flight_num}",
            "origin": origin,
            "destination": destination,
            "date": date,
            "dep_time": dep_str,
            "arr_time": f"{arr_hour:02d}:{arr_min:02d}",
            "duration": f"{int(duration_h)}h{int((duration_h % 1) * 60)}m",
            "price": price,
            "is_red_eye": dep_hour >= 22 or dep_hour < 6,
            "direct": True,
            "source": "参考数据",
        })

    return sorted(flights, key=lambda x: x["price"])
