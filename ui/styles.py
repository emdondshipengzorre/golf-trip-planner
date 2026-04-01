"""自定义 CSS 样式"""

import streamlit as st

CUSTOM_CSS = """
<style>
/* ─── 全局 ─── */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');

.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* ─── 侧边栏 ─── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B5E20 0%, #2E7D32 40%, #388E3C 100%);
}

[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}

[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stDateInput label {
    color: #E8F5E9 !important;
    font-weight: 500;
}

[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stMultiSelect > div > div,
[data-testid="stSidebar"] .stDateInput > div > div > input {
    background-color: rgba(255,255,255,0.15) !important;
    border-color: rgba(255,255,255,0.3) !important;
    color: #FFFFFF !important;
}

[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.2);
}

/* ─── Metric 卡片 ─── */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

[data-testid="stMetric"] label {
    color: #666 !important;
    font-size: 0.85rem !important;
}

[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-weight: 700 !important;
    color: #1B5E20 !important;
}

/* ─── Tab ─── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #F5F5F5;
    border-radius: 10px;
    padding: 4px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 500;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #2E7D32 !important;
    color: white !important;
}

/* ─── Expander ─── */
.streamlit-expanderHeader {
    background: #F9FBF9;
    border-radius: 8px;
    font-weight: 500;
}

/* ─── DataFrame ─── */
.stDataFrame {
    border-radius: 8px;
    overflow: hidden;
}

/* ─── 按钮 ─── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2E7D32, #43A047) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.2rem !important;
    transition: transform 0.1s ease;
}

.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(46,125,50,0.3);
}

.stDownloadButton > button {
    background: linear-gradient(135deg, #1565C0, #1E88E5) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
}

/* ─── Success/Error/Info ─── */
.stSuccess {
    border-radius: 8px;
}

.stAlert {
    border-radius: 8px;
}

/* ─── Footer ─── */
.footer {
    text-align: center;
    padding: 1.5rem 0;
    color: #999;
    font-size: 0.8rem;
    border-top: 1px solid #E0E0E0;
    margin-top: 2rem;
}
</style>
"""


def inject_styles():
    """注入自定义样式"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header():
    """渲染页面顶部"""
    st.markdown("""
    <div style="text-align:center; padding: 0.5rem 0 1rem 0">
        <h1 style="color:#2E7D32; margin-bottom:0.2rem">⛳ 高尔夫旅行规划器</h1>
        <p style="color:#666; font-size:0.95rem; margin:0">
            智能比价 · 一键行程 · 轻松出发
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    """渲染页面底部"""
    st.markdown("""
    <div class="footer">
        ⛳ 高尔夫旅行规划器 &nbsp;|&nbsp; 数据仅供参考，实际价格以购买时为准<br>
        Built with Streamlit &nbsp;·&nbsp; Data from 携程/美团/球场官网
    </div>
    """, unsafe_allow_html=True)
