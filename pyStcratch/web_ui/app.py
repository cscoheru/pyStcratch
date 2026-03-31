"""
Streamlit 前端主应用
运行: streamlit run web_ui/app.py --server.port 8501
"""
import streamlit as st
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import DatabaseManager

st.set_page_config(
    page_title="爬虫数据管理系统",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🕷️"
)

# 侧边栏导航
page = st.sidebar.selectbox(
    "选择功能",
    ["文章列表", "数据统计", "数据清洗", "导出", "数据集管理"],
)

# 路由到各页面
if page == "文章列表":
    from web_ui.pages.article_list import show_page
    show_page()
elif page == "数据统计":
    from web_ui.pages.statistics import show_page
    show_page()
elif page == "数据清洗":
    from web_ui.pages.cleaning import show_page
    show_page()
elif page == "导出":
    from web_ui.pages.export import show_page
    show_page()
elif page == "数据集管理":
    from web_ui.pages.dataset_manager import show_page
    show_page()
