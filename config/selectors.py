"""页面元素选择器集中配置。

BOSS 直聘页面结构可能变化，所有选择器集中在此处，便于改版后热更新。
当前为占位初值，需结合实际页面 DOM 校准。
"""

from __future__ import annotations

# 检索页
SEARCH_URL = "https://www.zhipin.com/web/geek/job"

SELECTORS = {
    # 岗位列表卡片
    "job_card": ".job-card-wrapper",
    "job_title": ".job-name",
    "job_salary": ".salary",
    "job_company": ".company-name",
    "job_city": ".job-area",
    # 岗位详情
    "jd_text": ".job-sec-text",
    # 沟通按钮 / 输入框 / 发送
    "chat_button": ".btn-startchat",
    "chat_input": ".chat-input",
    "chat_send": ".chat-send",
    # 搜索输入框 / 筛选
    "search_input": ".search-input",
    "search_button": ".search-btn",
}