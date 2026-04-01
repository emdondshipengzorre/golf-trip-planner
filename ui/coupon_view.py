"""优惠信息视图 — 展示 + 手动录入"""

import streamlit as st

from core.coupon_aggregator import aggregate_coupons
from scrapers.coupon_scraper import save_coupon


def render_coupon_tab(city: str, course_name: str = None):
    """渲染优惠信息 Tab"""

    st.header("🏷️ 优惠信息")

    # 功能切换
    view_mode = st.radio("", ["查看优惠", "手动录入"], horizontal=True, label_visibility="collapsed")

    if view_mode == "手动录入":
        _render_manual_entry(city)
        return

    with st.spinner("正在搜索优惠..."):
        data = aggregate_coupons(city, course_name)

    coupons = data["all_coupons"]

    if not coupons:
        st.info(f"暂未找到{city}的优惠信息")
        return

    # 概览
    col1, col2, col3 = st.columns(3)
    col1.metric("可用优惠", f"{len(coupons)} 条")
    col2.metric("最大单笔可省", f"¥{data['best_deal']['savings']}" if data["best_deal"] else "—")
    col3.metric("累计可省", f"¥{data['total_potential_savings']}")

    # 按类型筛选
    all_types = list(data["by_type"].keys())
    selected_types = st.multiselect(
        "按类型筛选", all_types, default=all_types,
    )
    if selected_types:
        coupons = [c for c in coupons if c["type"] in selected_types]

    st.markdown("---")

    # 优惠卡片
    for coupon in coupons:
        discount_pct = round((1 - coupon["discount_price"] / coupon["original_price"]) * 100) if coupon["original_price"] else 0

        with st.container():
            col_tag, col_content, col_price = st.columns([1, 3, 2])

            with col_tag:
                type_colors = {
                    "球场套餐": "🟢", "联票": "🔵", "酒店套餐": "🟠",
                    "早鸟折扣": "🟡", "其他优惠": "⚪",
                }
                emoji = type_colors.get(coupon["type"], "⚪")
                st.markdown(f"### {emoji}")
                st.caption(coupon["type"])

            with col_content:
                st.markdown(f"**{coupon['title']}**")
                source_badge = f"📌 {coupon['source']}"
                valid_text = f"有效期至 {coupon['valid_until']}" if coupon.get("valid_until") else ""
                st.caption(f"{source_badge} | {valid_text}")
                if coupon.get("description"):
                    st.markdown(coupon["description"])

            with col_price:
                st.markdown(f"~~¥{coupon['original_price']}~~")
                st.markdown(f"### ¥{coupon['discount_price']}")
                st.success(f"省 ¥{coupon['savings']} ({discount_pct}% off)")

        st.markdown("---")

    # 按类型统计
    if data["by_type"]:
        st.subheader("📊 按类型分布")
        for type_name, items in data["by_type"].items():
            total_savings = sum(c["savings"] for c in items)
            st.markdown(f"- **{type_name}**: {len(items)} 条，共省 ¥{total_savings}")

    # 按来源统计
    if data["by_source"]:
        st.subheader("📡 数据来源")
        for source, items in data["by_source"].items():
            st.markdown(f"- **{source}**: {len(items)} 条")


def _render_manual_entry(city: str):
    """手动录入优惠信息表单"""

    st.subheader("✏️ 手动录入优惠")
    st.caption("适用于球场官网/微信公众号/朋友分享的优惠，爬虫抓不到的信息")

    with st.form("manual_coupon_form"):
        title = st.text_input("优惠标题 *", placeholder="如：观澜湖3场套餐")

        col1, col2 = st.columns(2)
        with col1:
            source = st.text_input("信息来源", value="球场官网", placeholder="如：球场官网、朋友推荐")
            coupon_type = st.selectbox("优惠类型", ["球场套餐", "酒店套餐", "联票", "早鸟折扣", "其他优惠"])
        with col2:
            course = st.text_input("关联球场（可选）", placeholder="如：观澜湖·黑石场")
            valid_until = st.text_input("有效期至", placeholder="2026-12-31")

        col3, col4 = st.columns(2)
        with col3:
            original_price = st.number_input("原价 (¥)", min_value=0, value=1000, step=50)
        with col4:
            discount_price = st.number_input("优惠价 (¥)", min_value=0, value=800, step=50)

        description = st.text_area("详细描述", placeholder="包含哪些内容、使用条件等")

        submitted = st.form_submit_button("💾 保存优惠", type="primary", use_container_width=True)

        if submitted:
            if not title:
                st.error("请填写优惠标题")
                return

            coupon = {
                "city": city,
                "title": title,
                "source": source,
                "type": coupon_type,
                "original_price": original_price,
                "discount_price": discount_price,
                "savings": original_price - discount_price,
                "description": description,
                "valid_until": valid_until,
            }
            if course:
                coupon["course"] = course

            save_coupon(coupon)
            st.success(f"已保存优惠「{title}」，省 ¥{original_price - discount_price}")
            st.info("切换回「查看优惠」即可看到新录入的优惠")
