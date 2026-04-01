"""天气数据 — OpenWeatherMap API (free tier: 1000 calls/day)"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from scrapers.base import cache_get, cache_set, make_cache_key, fetch_json, get_api_key

logger = logging.getLogger("scraper.weather")
DATA_DIR = Path(__file__).parent.parent / "data"


def _get_city_coords(city: str) -> tuple[float, float] | None:
    with open(DATA_DIR / "cities.json", "r", encoding="utf-8") as f:
        cities = json.load(f)["cities"]
    for c in cities:
        if c["name"] == city:
            return c["lat"], c["lng"]
    return None


def get_weather_forecast(city: str) -> list[dict]:
    """获取 5 天天气预报（每 3 小时一条，免费 API）

    Returns:
        [{"date": "2026-05-01", "temp": 28, "temp_min": 24, "temp_max": 31,
          "weather": "晴", "icon": "01d", "humidity": 65, "wind_speed": 3.5,
          "golf_score": 85}, ...]
    """
    key = make_cache_key("weather_v1", city=city)
    cached = cache_get(key)
    if cached:
        return cached

    api_key = get_api_key("OPENWEATHER_API_KEY")
    if not api_key:
        logger.warning("OpenWeatherMap API key not configured")
        return []

    coords = _get_city_coords(city)
    if not coords:
        return []

    lat, lng = coords
    data = fetch_json(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={
            "lat": lat,
            "lon": lng,
            "appid": api_key,
            "units": "metric",
            "lang": "zh_cn",
        },
    )

    if not data or "list" not in data:
        return []

    # 按天聚合（API 返回每 3 小时一条）
    daily = {}
    for item in data["list"]:
        date = item["dt_txt"][:10]
        if date not in daily:
            daily[date] = {
                "date": date,
                "temps": [],
                "weather": item["weather"][0]["description"],
                "icon": item["weather"][0]["icon"],
                "humidity": [],
                "wind_speed": [],
            }
        main = item["main"]
        daily[date]["temps"].append(main["temp"])
        daily[date]["humidity"].append(main["humidity"])
        daily[date]["wind_speed"].append(item["wind"]["speed"])

    result = []
    for date, d in daily.items():
        temp_avg = round(sum(d["temps"]) / len(d["temps"]), 1)
        temp_min = round(min(d["temps"]), 1)
        temp_max = round(max(d["temps"]), 1)
        humidity = round(sum(d["humidity"]) / len(d["humidity"]))
        wind = round(sum(d["wind_speed"]) / len(d["wind_speed"]), 1)

        # 高尔夫适宜度评分（满分100）
        golf_score = _calc_golf_score(temp_avg, humidity, wind, d["weather"])

        result.append({
            "date": date,
            "temp": temp_avg,
            "temp_min": temp_min,
            "temp_max": temp_max,
            "weather": d["weather"],
            "icon": d["icon"],
            "humidity": humidity,
            "wind_speed": wind,
            "golf_score": golf_score,
        })

    cache_set(key, result, ttl_seconds=10800)  # 3 小时缓存
    return result


def _calc_golf_score(temp: float, humidity: int, wind: float, weather: str) -> int:
    """计算高尔夫适宜度（0-100）"""
    score = 100

    # 温度：20-28 度最佳
    if temp < 10 or temp > 38:
        score -= 40
    elif temp < 15 or temp > 35:
        score -= 25
    elif temp < 20 or temp > 30:
        score -= 10

    # 湿度：40-70 最佳
    if humidity > 85:
        score -= 20
    elif humidity > 75:
        score -= 10

    # 风速：< 5 m/s 最佳
    if wind > 10:
        score -= 30
    elif wind > 7:
        score -= 15
    elif wind > 5:
        score -= 5

    # 天气
    bad_weather = ["雨", "雷", "暴", "雪", "雾"]
    if any(w in weather for w in bad_weather):
        score -= 30

    return max(0, min(100, score))
