"""
文章列表页 - 支持按 content_type 和 sentiment 筛选
"""
import streamlit as st
import pandas as pd
from storage.database import DatabaseManager
from storage.models import Article


def show_page():
    st.title("📄 文章列表")

    db = DatabaseManager()

    # 筛选器
    with st.sidebar:
        st.subheader("筛选条件")

        source = st.selectbox("来源", ["全部", "zhihu", "toutiao", "wechat", "bilibili", "chnsenticorp", "lcqmc"])
        content_type = st.selectbox("内容类型", ["全部", "article", "review", "qa", "social", "news"])
        sentiment = st.selectbox("情感标签", ["全部", "positive", "negative", "neutral"])
        min_quality = st.slider("最低质量", 0.0, 1.0, 0.5)

    # 获取数据
    with db.get_session() as session:
        query = session.query(Article)

        # 应用筛选
        if source != "全部":
            query = query.filter(Article.source == source)
        if content_type != "全部":
            query = query.filter(Article.content_type == content_type)
        if sentiment != "全部":
            query = query.filter(Article.sentiment == sentiment)

        query = query.filter(Article.quality_score >= min_quality)
        query = query.filter(Article.is_valid == True, Article.is_spam == False)

        articles = query.limit(100).all()

    if not articles:
        st.info("没有找到符合条件的文章")
        return

    # 显示表格
    data = []
    for a in articles:
        data.append({
            "ID": a.id,
            "标题": a.title[:50] + "..." if len(a.title) > 50 else a.title,
            "来源": a.source,
            "类型": a.content_type or "article",
            "情感": a.sentiment or "neutral",
            "分类": a.category or "未分类",
            "质量": f"{a.quality_score:.2f}"
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

    # 详情展示
    st.divider()
    st.subheader("文章详情")

    article_options = {f"{a.id}: {a.title[:40]}...": a for a in articles}
    selected = st.selectbox("选择文章查看详情", options=list(article_options.keys()))

    if selected:
        article = article_options[selected]
        show_article_detail(article)


def show_article_detail(article):
    """根据 content_type 显示不同格式"""
    st.subheader(article.title)

    # 元信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.caption(f"📍 来源: {article.source}")
    with col2:
        st.caption(f"📝 类型: {article.content_type or 'article'}")
    with col3:
        st.caption(f"😊 情感: {article.sentiment or 'neutral'}")
    with col4:
        st.caption(f"⭐ 质量: {article.quality_score:.2f}")

    st.divider()

    # 根据类型显示不同格式
    content_type = article.content_type or "article"

    if content_type == "qa":
        col1, col2 = st.columns(2)
        with col1:
            st.write("**问题:**")
            if article.question:
                st.write(article.question)
            else:
                st.write("(未设置)")
        with col2:
            st.write("**答案:**")
            if article.answer:
                st.write(article.answer)
            else:
                st.write("(未设置)")
        if article.similarity:
            st.info(f"相似度: {article.similarity:.2f}")

    elif content_type == "review":
        sentiment_emoji = {"positive": "😊", "negative": "😞", "neutral": "😐"}
        emoji = sentiment_emoji.get(article.sentiment or "neutral", "😐")
        st.markdown(f"**情感:** {emoji} {article.sentiment or 'neutral'}")
        st.write(article.content)

    else:
        # article, news, social - 标准格式
        st.write(article.content)
