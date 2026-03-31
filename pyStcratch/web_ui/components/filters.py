"""筛选器组件"""
import streamlit as st


def content_type_filter(default="全部"):
    """内容类型筛选器"""
    options = ["全部", "article", "review", "qa", "social", "news"]
    try:
        index = options.index(default) if default in options else 0
    except ValueError:
        index = 0
    return st.selectbox("内容类型", options, index=index)


def sentiment_filter(default="全部"):
    """情感标签筛选器"""
    options = ["全部", "positive", "negative", "neutral"]
    try:
        index = options.index(default) if default in options else 0
    except ValueError:
        index = 0
    return st.selectbox("情感标签", options, index=index)
