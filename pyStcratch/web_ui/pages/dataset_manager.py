"""
数据集管理页 - 数据集同步管理
"""
import streamlit as st
import pandas as pd
from storage.database import DatabaseManager


def show_page():
    st.title("🗄️ 数据集管理")

    # 数据集列表
    datasets = [
        {
            "name": "THUCNews",
            "source": "toutiao",
            "type": "news",
            "dataset": "lansinuote/ChnSentiCorp",
            "description": "今日头条新闻数据集"
        },
        {
            "name": "ChnSentiCorp",
            "source": "chnsenticorp",
            "type": "review",
            "dataset": "lansinuote/ChnSentiCorp",
            "description": "中文情感分析数据集"
        },
        {
            "name": "LCQMC",
            "source": "lcqmc",
            "type": "qa",
            "dataset": "clue/lcqmc",
            "description": "大规模中文问答数据集"
        },
    ]

    # 显示数据集表格
    for ds in datasets:
        with st.expander(f"📦 {ds['name']} ({ds['type']})"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**数据集:** `{ds['dataset']}`")
                st.caption(f"类型: {ds['type']}")
            with col2:
                st.write(f"**来源:** {ds['source']}")
                st.caption(ds['description'])
            with col3:
                if st.button(f"同步 {ds['name']}", key=f"sync_{ds['name']}"):
                    sync_dataset(ds['source'], ds['name'])

    st.divider()

    # 同步日志
    if "sync_logs" in st.session_state:
        st.subheader("同步日志")
        st.code(st.session_state.sync_logs, language="text")


def sync_dataset(source: str, name: str):
    """手动触发数据集同步"""
    try:
        from scheduler.jobs import ManualJobs

        st.info(f"正在同步 {name} (source: {source})...")

        jobs = ManualJobs()
        result = jobs.crawl_source(source, max_pages=5)

        if isinstance(result, dict) and result.get('success'):
            # 显示结果
            if 'success' in result and 'failed' in result:
                st.success(f"同步完成: {result['success']} 篇成功, {result['failed']} 篇失败")
            else:
                st.success(f"同步完成!")
        else:
            st.warning(f"同步结果: {result}")

        # 记录日志
        if "sync_logs" not in st.session_state:
            st.session_state.sync_logs = []
        st.session_state.sync_logs.append(f"[{name}] 同步完成: {result}")

    except Exception as e:
        st.error(f"同步失败: {e}")
        import traceback
        st.exception(e)
