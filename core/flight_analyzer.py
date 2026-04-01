"""机票比价分析 + 最佳日期推荐"""
from __future__ import annotations

from scrapers.flight_scraper import search_flights, search_flights_range


def analyze_price_trend(origin: str, destination: str, start_date: str, days: int = 30) -> dict:
    """分析价格走势，找出最佳出行日期

    Returns:
        {
            "dates": [...],
            "min_prices": [...],
            "best_date": "YYYY-MM-DD",
            "best_price": 999,
            "avg_price": 999,
            "price_range": (min, max),
            "flights": {date: [flights]},
            "weekday_avg": 999,
            "weekend_avg": 999,
        }
    """
    from datetime import datetime

    data = search_flights_range(origin, destination, start_date, days)

    dates = data["dates"]
    min_prices = data["min_prices"]

    if not min_prices or all(p == 0 for p in min_prices):
        return {
            "dates": dates,
            "min_prices": min_prices,
            "best_date": None,
            "best_price": 0,
            "avg_price": 0,
            "price_range": (0, 0),
            "flights": data["flights"],
            "weekday_avg": 0,
            "weekend_avg": 0,
        }

    valid_prices = [p for p in min_prices if p > 0]
    best_idx = min_prices.index(min(valid_prices))

    weekday_prices = []
    weekend_prices = []
    for d, p in zip(dates, min_prices):
        if p == 0:
            continue
        dt = datetime.strptime(d, "%Y-%m-%d")
        if dt.weekday() < 5:
            weekday_prices.append(p)
        else:
            weekend_prices.append(p)

    return {
        "dates": dates,
        "min_prices": min_prices,
        "best_date": dates[best_idx],
        "best_price": min_prices[best_idx],
        "avg_price": round(sum(valid_prices) / len(valid_prices)),
        "price_range": (min(valid_prices), max(valid_prices)),
        "flights": data["flights"],
        "weekday_avg": round(sum(weekday_prices) / len(weekday_prices)) if weekday_prices else 0,
        "weekend_avg": round(sum(weekend_prices) / len(weekend_prices)) if weekend_prices else 0,
    }


def compare_flights(origin: str, destination: str, date: str) -> dict:
    """对比指定日期的航班

    Returns:
        {
            "flights": [...],
            "cheapest": {...},
            "earliest": {...},
            "by_airline": {airline: [flights]},
        }
    """
    flights = search_flights(origin, destination, date)
    if not flights:
        return {"flights": [], "cheapest": None, "earliest": None, "by_airline": {}}

    cheapest = min(flights, key=lambda f: f["price"])
    earliest = min(flights, key=lambda f: f["dep_time"])

    by_airline = {}
    for f in flights:
        by_airline.setdefault(f["airline"], []).append(f)

    return {
        "flights": flights,
        "cheapest": cheapest,
        "earliest": earliest,
        "by_airline": by_airline,
    }
