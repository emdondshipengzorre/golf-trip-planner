"""一键行程生成器 — 智能日程安排 + 多方案对比"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from core.flight_analyzer import compare_flights
from core.hotel_recommender import recommend_hotels
from core.coupon_aggregator import aggregate_coupons

DATA_DIR = Path(__file__).parent.parent / "data"

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load_courses():
    with open(DATA_DIR / "golf_courses.json", "r", encoding="utf-8") as f:
        return json.load(f)["courses"]


def generate_trip(
    origin: str,
    destination_city: str,
    start_date: str,
    end_date: str,
    budget: int = 8000,
    hotel_preference: str = None,
    course_names: list[str] = None,
) -> dict:
    """生成完整行程方案"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    nights = (end - start).days

    # 查找目的地球场
    all_courses = load_courses()
    city_courses = [c for c in all_courses if c["city"] == destination_city]
    if course_names:
        selected_courses = [c for c in city_courses if c["name"] in course_names]
        if not selected_courses:
            selected_courses = city_courses[:3]
    else:
        selected_courses = city_courses[:3]

    # 球场中心坐标
    course_lat = selected_courses[0]["lat"] if selected_courses else None
    course_lng = selected_courses[0]["lng"] if selected_courses else None

    # 查询机票
    outbound = compare_flights(origin, destination_city, start_date)
    inbound = compare_flights(destination_city, origin, end_date)

    # 查询酒店
    hotel_data = recommend_hotels(
        destination_city, start_date, end_date,
        course_lat, course_lng, hotel_type=hotel_preference,
    )

    # 查询优惠
    coupon_data = aggregate_coupons(destination_city)

    # 推荐选择
    rec_outbound = outbound["cheapest"]
    rec_inbound = inbound["cheapest"]
    rec_hotel = hotel_data["best_value"]

    # 计算预算
    breakdown = _calc_budget(rec_outbound, rec_inbound, rec_hotel, selected_courses, nights)

    # 生成逐日计划
    daily_plan = _build_daily_plan(
        start, end, selected_courses, rec_hotel,
        rec_outbound, rec_inbound, destination_city,
    )

    # 三档方案
    tiers = _build_tiers(
        outbound, inbound, hotel_data, selected_courses, nights,
    )

    # 匹配相关优惠
    relevant_coupons = _match_coupons(coupon_data["all_coupons"], selected_courses, rec_hotel)

    return {
        "summary": {
            "origin": origin,
            "destination": destination_city,
            "dates": f"{start_date} → {end_date}",
            "nights": nights,
            "courses_count": len(selected_courses),
            "total_budget": breakdown["合计"],
        },
        "outbound_flight": rec_outbound,
        "return_flight": rec_inbound,
        "hotel": rec_hotel,
        "courses": selected_courses,
        "coupons": relevant_coupons[:5],
        "daily_plan": daily_plan,
        "budget_breakdown": breakdown,
        "tiers": tiers,
    }


def _calc_budget(outbound, inbound, hotel, courses, nights) -> dict:
    """计算预算明细"""
    flight_cost = 0
    if outbound:
        flight_cost += outbound["price"]
    if inbound:
        flight_cost += inbound["price"]

    hotel_cost = hotel["price_per_night"] * nights if hotel else 0

    green_fee = 0
    for c in courses:
        green_fee += sum(c["green_fee_range"]) / 2

    # 餐饮交通估算：根据城市消费水平
    daily_misc = 300
    misc_cost = daily_misc * (nights + 1)

    total = flight_cost + hotel_cost + green_fee + misc_cost

    return {
        "机票": round(flight_cost),
        "酒店": round(hotel_cost),
        "果岭费": round(green_fee),
        "餐饮交通": round(misc_cost),
        "合计": round(total),
    }


def _build_daily_plan(start, end, courses, hotel, outbound, inbound, city):
    """生成智能逐日行程"""
    days = (end - start).days + 1
    plan = []

    # 分配球场到中间天数（避免第一天和最后一天）
    play_days = list(range(1, days - 1)) if days > 2 else []
    course_schedule = {}
    for i, day_idx in enumerate(play_days):
        if courses:
            course_schedule[day_idx] = courses[i % len(courses)]

    for i in range(days):
        date = start + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        day_label = f"Day {i + 1} ({WEEKDAY_NAMES[date.weekday()]})"

        activities = []
        tips = []

        if i == 0:
            # 抵达日
            if outbound:
                activities.append(f"✈️ {outbound['dep_time']} {outbound.get('airline', '')} {outbound.get('flight_no', '')} 出发")
                activities.append(f"✈️ {outbound['arr_time']} 抵达{city}")
            else:
                activities.append(f"✈️ 出发飞往{city}")

            if hotel:
                activities.append(f"🏨 入住 {hotel['name']}（{hotel['type']}）")
                if hotel.get("drive_minutes"):
                    tips.append(f"机场到酒店约 {hotel['drive_minutes']} 分钟")

            activities.append("🌆 周边探索 / 休整调整")
            tips.append("建议早到的话可以去练习场热身")

        elif i == days - 1:
            # 返程日
            activities.append("🧳 退房、整理行李")
            if inbound:
                activities.append(f"✈️ {inbound['dep_time']} {inbound.get('airline', '')} {inbound.get('flight_no', '')} 返程")
            else:
                activities.append("✈️ 返程")
            tips.append("建议提前2小时到机场")

        else:
            # 打球日
            course = course_schedule.get(i)
            if course:
                fee_range = course["green_fee_range"]
                avg_fee = sum(fee_range) / 2
                activities.append(f"🌅 7:00 早餐")
                activities.append(f"⛳ 8:00 {course['name']}")
                activities.append(f"   💰 果岭费 ¥{fee_range[0]}~¥{fee_range[1]}")

                if course.get("difficulty", 3) >= 4:
                    tips.append(f"难度较高，建议量力而行")
                if course.get("scenery", 3) >= 4:
                    tips.append(f"风景绝佳，记得拍照/录视频（小红书素材）")
                if course.get("tags"):
                    tips.append(f"特色: {', '.join(course['tags'])}")

            activities.append("🍽️ 12:30 午餐")
            activities.append("🍽️ 18:00 晚餐 — 当地特色美食")

            if i % 2 == 0:
                activities.append("🧖 20:00 温泉/SPA 放松")
            else:
                activities.append("🌃 20:00 自由活动")

        plan.append({
            "date": date_str,
            "day_label": day_label,
            "activities": activities,
            "tips": tips,
        })

    return plan


def _match_coupons(coupons, courses, hotel):
    """匹配与选中球场/酒店相关的优惠"""
    course_names = [c["name"] for c in courses]
    hotel_name = hotel["name"] if hotel else ""

    scored = []
    for c in coupons:
        relevance = 0
        title = c["title"]
        desc = c.get("description", "")
        text = title + desc

        for name in course_names:
            # 匹配球场关键词
            short_name = name.split("·")[0] if "·" in name else name
            if short_name in text:
                relevance += 3

        if hotel_name and hotel_name.split("·")[0] in text:
            relevance += 2

        # 节省金额权重
        relevance += c["savings"] / 500

        scored.append((relevance, c))

    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored]


def _build_tiers(outbound, inbound, hotel_data, courses, nights):
    """生成经济/舒适/豪华三档方案"""
    tiers = {}

    for tier_name, hotel_type, flight_pick in [
        ("经济", "经济", "cheapest"),
        ("舒适", "舒适", "median"),
        ("豪华", "豪华", "premium"),
    ]:
        # 选航班
        out_flights = outbound["flights"]
        in_flights = inbound["flights"]
        out_flight = _pick_flight(out_flights, flight_pick)
        in_flight = _pick_flight(in_flights, flight_pick)

        # 选酒店
        tier_hotels = [h for h in hotel_data["all_hotels"] if h["type"] == hotel_type]
        if not tier_hotels:
            tier_hotels = hotel_data["all_hotels"]
        tier_hotel = tier_hotels[0] if tier_hotels else None

        flight_cost = (out_flight["price"] if out_flight else 0) + (in_flight["price"] if in_flight else 0)
        hotel_cost = tier_hotel["price_per_night"] * nights if tier_hotel else 0
        green_fee = sum(sum(c["green_fee_range"]) / 2 for c in courses)
        misc_rate = {"经济": 200, "舒适": 300, "豪华": 500}.get(tier_name, 300)
        misc = misc_rate * (nights + 1)

        tiers[tier_name] = {
            "flight": out_flight,
            "hotel": tier_hotel,
            "flight_cost": round(flight_cost),
            "hotel_cost": round(hotel_cost),
            "green_fee": round(green_fee),
            "misc": round(misc),
            "total": round(flight_cost + hotel_cost + green_fee + misc),
        }

    return tiers


def _pick_flight(flights, strategy):
    """根据策略选择航班"""
    if not flights:
        return None
    sorted_flights = sorted(flights, key=lambda f: f["price"])
    if strategy == "cheapest":
        return sorted_flights[0]
    elif strategy == "median":
        return sorted_flights[len(sorted_flights) // 2]
    elif strategy == "premium":
        # 最贵的非红眼航班
        non_redeye = [f for f in sorted_flights if not f.get("is_red_eye")]
        return non_redeye[-1] if non_redeye else sorted_flights[-1]
    return sorted_flights[0]
