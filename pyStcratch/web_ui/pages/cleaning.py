"""
数据清洗页 - 数据质量检查和清洗
"""
import streamlit as st
from storage.database import DatabaseManager
from storage.models import Article
from sqlalchemy import or_


def show_page():
    st.title("🧹 数据清洗")

    db = DatabaseManager()

    # 低质量文章
    st.subheader("低质量文章 (质量 < 0.5)")
    with db.get_session() as session:
        low_quality = session.query(Article).filter(
            Article.quality_score < 0.5,
            Article.is_valid == True
        ).limit(50).all()

    if low_quality:
        st.info(f"找到 {len(low_quality)} 篇低质量文章")

        # 显示前10篇
        for article in low_quality[:10]:
            with st.expander(f"{article.title[:50]}... (质量: {article.quality_score:.2f})"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_score = st.slider(
                        f"调整质量分数",
                        0.0, 1.0,
                        float(article.quality_score),
                        0.05,
                        key=f"quality_{article.id}"
                    )
                with col2:
                    if st.button("更新", key=f"update_{article.id}"):
                        article.quality_score = new_score
                        session.commit()
                        st.success("已更新!")
                        st.rerun()
                with col3:
                    if st.button("删除", key=f"del_{article.id}", type="secondary"):
                        session.delete(article)
                        session.commit()
                        st.success("已删除!")
                        st.rerun()
        st.divider()
    else:
        st.success("没有低质量文章！")

    # 未分类文章
    st.subheader("未分类文章")
    with db.get_session() as session:
        unclassified = session.query(Article).filter(
            or_(
                Article.category == None,
                Article.category == ""
            )
        ).limit(50).all()

    if unclassified:
        st.info(f"找到 {len(unclassified)} 篇未分类文章")

        for article in unclassified[:10]:
            with st.expander(f"{article.title[:50]}..."):
                col1, col2 = st.columns(2)
                with col1:
                    category = st.selectbox(
                        "分类",
                        ["psychology", "management", "finance", "other"],
                        key=f"cat_{article.id}"
                    )
                with col2:
                    if st.button("保存", key=f"save_{article.id}"):
                        article.category = category
                        session.commit()
                        st.success("已分类!")
                        st.rerun()
        st.divider()
    else:
        st.success("所有文章都已分类！")

    # 垃圾文章
    st.subheader("垃圾文章")
    with db.get_session() as session:
        spam_articles = session.query(Article).filter(
            Article.is_spam == True
        ).limit(50).all()

    if spam_articles:
        st.warning(f"找到 {len(spam_articles)} 篇垃圾文章")

        for article in spam_articles[:10]:
            with st.expander(f"{article.title[:50]}..."):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(article.content[:200] + "..." if len(article.content) > 200 else article.content)
                with col2:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("标记为有效", key=f"valid_{article.id}"):
                            article.is_spam = False
                            session.commit()
                            st.success("已更新!")
                            st.rerun()
                    with col2:
                        if st.button("永久删除", key=f"delete_{article.id}", type="secondary"):
                            session.delete(article)
                            session.commit()
                            st.success("已删除!")
                            st.rerun()
    else:
        st.success("没有垃圾文章！")
