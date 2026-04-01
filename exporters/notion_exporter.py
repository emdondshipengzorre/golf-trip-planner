"""导出行程到 Notion（预留接口）"""


def export_trip_to_notion(trip: dict, notion_token: str = None, page_id: str = None) -> str:
    """将行程方案导出到 Notion

    TODO: Phase 5 实现真实 Notion API 集成

    Args:
        trip: generate_trip() 返回的行程数据
        notion_token: Notion Integration Token
        page_id: 目标 Notion 页面 ID

    Returns:
        Notion 页面 URL
    """
    # 当前返回提示信息，Phase 5 替换为真实实现
    return "Notion 导出功能即将上线，请先使用 Markdown 导出"
