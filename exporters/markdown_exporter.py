"""导出行程为 Markdown 文件"""

from pathlib import Path


def export_trip_markdown(trip: dict, output_path: str = None) -> str:
    """将行程方案导出为 Markdown"""
    s = trip["summary"]
    lines = [
        f"# ⛳ 高尔夫旅行方案",
        f"## {s['origin']} → {s['destination']}",
        f"",
        f"| 项目 | 详情 |",
        f"|------|------|",
        f"| 日期 | {s['dates']} |",
        f"| 天数 | {s['nights']}晚 |",
        f"| 球场 | {s['courses_count']}个 |",
        f"| 预估费用 | ¥{s['total_budget']} |",
        f"",
    ]

    # 航班
    lines.append("## ✈️ 航班")
    if trip.get("outbound_flight"):
        f = trip["outbound_flight"]
        lines.append(f"- **去程:** {f.get('airline', '')} {f.get('flight_no', '')} "
                      f"{f['dep_time']}→{f['arr_time']} **¥{f['price']}**")
    if trip.get("return_flight"):
        f = trip["return_flight"]
        lines.append(f"- **返程:** {f.get('airline', '')} {f.get('flight_no', '')} "
                      f"{f['dep_time']}→{f['arr_time']} **¥{f['price']}**")
    lines.append("")

    # 酒店
    if trip.get("hotel"):
        h = trip["hotel"]
        lines.append("## 🏨 酒店")
        lines.append(f"- **{h['name']}** ({h['type']})")
        lines.append(f"  - 价格: ¥{h['price_per_night']}/晚 | 评分: ⭐{h['rating']}")
        if h.get("distance_to_course_km"):
            lines.append(f"  - 距球场 {h['distance_to_course_km']}km，车程约{h.get('drive_minutes', '?')}分钟")
        lines.append("")

    # 球场
    if trip.get("courses"):
        lines.append("## ⛳ 球场")
        for c in trip["courses"]:
            fee = f"¥{c['green_fee_range'][0]}~¥{c['green_fee_range'][1]}"
            lines.append(f"- **{c['name']}** — {fee}")
            if c.get("designer"):
                lines.append(f"  - 设计师: {c['designer']}")
            if c.get("tags"):
                lines.append(f"  - 特色: {', '.join(c['tags'])}")
        lines.append("")

    # 逐日行程
    lines.append("## 📅 逐日行程")
    lines.append("")
    for day in trip["daily_plan"]:
        lines.append(f"### {day['day_label']} ({day['date']})")
        for a in day["activities"]:
            lines.append(f"- {a}")
        if day.get("tips"):
            lines.append("")
            for tip in day["tips"]:
                lines.append(f"> 💡 {tip}")
        lines.append("")

    # 预算
    lines.append("## 💰 预算明细")
    lines.append("")
    lines.append("| 项目 | 金额 | 占比 |")
    lines.append("|------|------|------|")
    total = trip["budget_breakdown"].get("合计", 1)
    for item, cost in trip["budget_breakdown"].items():
        if item == "合计":
            lines.append(f"| **{item}** | **¥{cost}** | **100%** |")
        else:
            pct = round(cost / total * 100)
            lines.append(f"| {item} | ¥{cost} | {pct}% |")
    lines.append("")

    # 方案对比
    if trip.get("tiers"):
        lines.append("## 🔄 方案对比")
        lines.append("")
        lines.append("| 档次 | 机票 | 酒店 | 果岭费 | 餐饮交通 | **合计** |")
        lines.append("|------|------|------|--------|----------|----------|")
        for name, t in trip["tiers"].items():
            hotel_name = t["hotel"]["name"] if t.get("hotel") else "—"
            lines.append(
                f"| {name} | ¥{t['flight_cost']} | ¥{t['hotel_cost']} | "
                f"¥{t['green_fee']} | ¥{t['misc']} | **¥{t['total']}** |"
            )
        lines.append("")

    # 优惠
    if trip.get("coupons"):
        lines.append("## 🏷️ 可用优惠")
        lines.append("")
        for c in trip["coupons"]:
            lines.append(f"- **{c['title']}** — 省 ¥{c['savings']} (来源: {c['source']})")
            if c.get("description"):
                lines.append(f"  - {c['description']}")
        lines.append("")

    lines.append("---")
    lines.append("*由高尔夫旅行规划器生成*")

    md = "\n".join(lines)

    if output_path:
        Path(output_path).write_text(md, encoding="utf-8")

    return md
