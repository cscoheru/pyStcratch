"""
数据统计页 - 显示内容类型和情感分布图
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from storage.database import DatabaseManager
from storage.models import Article
from sqlalchemy import func


def show_page():
    st.title("📊 数据统计")

    db = DatabaseManager()

    # 获取统计数据
    with db.get_session() as session:
        # 基础统计
        total_articles = session.query(Article).count()
        valid_articles = session.query(Article).filter(
            Article.is_valid == True,
            Article.is_spam == False
        ).count()

        # 平均质量分
        avg_quality = session.query(func.avg(Article.quality_score)).filter(
            Article.is_valid == True
        ).scalar() or 0

        # 按内容类型统计
        content_type_counts = dict(session.query(
            Article.content_type,
            func.count(Article.id)
        ).filter(Article.is_valid == True).group_by(Article.content_type).all())

        # 按情感统计
        sentiment_counts = dict(session.query(
            Article.sentiment,
            func.count(Article.id)
        ).filter(Article.is_valid == True).group_by(Article.sentiment).all())

        # 按数据集来源统计
        dataset_counts = dict(session.query(
            Article.dataset_source,
            func.count(Article.id)
        ).filter(Article.dataset_source.isnot(None)).group_by(Article.dataset_source).all())

        # 按分类统计
        category_counts = dict(session.query(
            Article.category,
            func.count(Article.id)
        ).filter(
            Article.is_valid == True,
            Article.category.isnot(None)
        ).group_by(Article.category).all())

        # 按来源统计
        source_counts = dict(session.query(
            Article.source,
            func.count(Article.id)
        ).filter(Article.is_valid == True).group_by(Article.source).all())

    # 统计卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总文章数", f"{total_articles:,}")
    with col2:
        st.metric("有效文章", f"{valid_articles:,}")
    with col3:
        st.metric("平均质量", f"{avg_quality:.2f}")
    with col4:
        st.metric("数据集数量", f"{len(dataset_counts)}")

    st.divider()

    # 内容类型分布
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("内容类型分布")
        if content_type_counts:
            fig_content_type = px.pie(
                values=list(content_type_counts.values()),
                names=list(content_type_counts.keys()),
                title="按内容类型"
            )
            st.plotly_chart(fig_content_type, use_container_width=True)
        else:
            st.info("暂无内容类型数据")

    with col2:
        st.subheader("情感分布")
        if sentiment_counts:
            colors = {"positive": "#00CC96", "negative": "#EF553B", "neutral": "#636EFA"}
            fig_sentiment = go.Figure(data=[go.Pie(
                labels=list(sentiment_counts.keys()),
                values=list(sentiment_counts.values()),
                marker=dict(colors=[colors.get(k, "#636EFA") for k in sentiment_counts.keys()]),
                textinfo='label+percent'
            )])
            fig_sentiment.update_layout(title="按情感标签", height=400)
            st.plotly_chart(fig_sentiment, use_container_width=True)
        else:
            st.info("暂无情感数据")

    st.divider()

    # 数据集来源分布
    if dataset_counts:
        st.subheader("数据集来源分布")
        fig_dataset = px.bar(
            x=list(dataset_counts.keys()),
            y=list(dataset_counts.values()),
            title="按数据集来源"
        )
        st.plotly_chart(fig_dataset, use_container_width=True)

    # 分类分布
    if category_counts:
        st.subheader("分类分布")
        fig_category = px.bar(
            x=list(category_counts.keys()),
            y=list(category_counts.values()),
            title="按分类"
        )
        st.plotly_chart(fig_category, use_container_width=True)

    # 来源分布
    if source_counts:
        st.subheader("来源分布")
        fig_source = px.bar(
            x=list(source_counts.keys()),
            y=list(source_counts.values()),
            title="按来源"
        )
        st.plotly_chart(fig_source, use_container_width=True)
