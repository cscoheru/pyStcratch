"""
导出页 - 支持 QA CSV 和评论情感 JSON 导出
"""
import streamlit as st
import pandas as pd
import tempfile
from storage.database import DatabaseManager
from storage.models import Article
from sqlalchemy import and_


def show_page():
    st.title("📦 导出数据")

    db = DatabaseManager()

    # 导出格式选择
    col1, col2 = st.columns(2)

    with col1:
        export_type = st.selectbox(
            "选择导出格式",
            ["标准导出", "QA CSV", "评论情感 JSON"]
        )

    with col2:
        format_type = st.selectbox(
            "文件格式",
            ["txt", "json", "csv"]
        )

    st.divider()

    # 筛选条件
    with st.expander("筛选条件", expanded=False):
        source = st.selectbox("来源", ["全部", "zhihu", "toutiao", "wechat"])
        content_type = st.selectbox("内容类型", ["全部", "article", "review", "qa", "social", "news"])
        min_quality = st.slider("最低质量", 0.0, 1.0, 0.0)

    # 获取数据
    with db.get_session() as session:
        query = session.query(Article).filter(
            Article.is_valid == True,
            Article.is_spam == False,
            Article.quality_score >= min_quality
        )

        if source != "全部":
            query = query.filter(Article.source == source)
        if content_type != "全部":
            query = query.filter(Article.content_type == content_type)

        articles = query.limit(10000).all()

    if not articles:
        st.warning("没有符合条件的文章可以导出")
        return

    st.info(f"找到 {len(articles)} 篇文章可以导出")

    # 导出按钮
    if export_type == "标准导出":
        if format_type == "txt":
            if st.button("导出为 TXT", use_container_width=True):
                export_txt(articles)
        elif format_type == "json":
            if st.button("导出为 JSON", use_container_width=True):
                export_json(articles)
        elif format_type == "csv":
            if st.button("导出为 CSV", use_container_width=True):
                export_csv(articles)

    elif export_type == "QA CSV":
        # 只导出 QA 类型的文章
        qa_articles = [a for a in articles if a.content_type == "qa"]
        if qa_articles:
            if st.button(f"导出 QA 对为 CSV ({len(qa_articles)} 篇)", use_container_width=True):
                export_qa_csv(qa_articles)
        else:
            st.warning("没有 QA 类型的文章")

    elif export_type == "评论情感 JSON":
        # 只导出 review 类型的文章
        review_articles = [a for a in articles if a.content_type == "review"]
        if review_articles:
            if st.button(f"导出评论情感 JSON ({len(review_articles)} 篇)", use_container_width=True):
                export_sentiment_json(review_articles)
        else:
            st.warning("没有评论类型的文章")


def export_txt(articles):
    """导出为 TXT"""
    import os
    from datetime import datetime

    export_dir = os.path.join(os.getenv('DATA_DIR', './data'), 'exports')
    os.makedirs(export_dir, exist_ok=True)

    for article in articles:
        filename = f"{article.source}_{article.id}.txt"
        # 移除无效字符
        filename = "".join(c if c.isalnum() or c in ('-', '_', '.') else '_' for c in filename)
        filepath = os.path.join(export_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"标题: {article.title}\n")
            f.write(f"来源: {article.source}\n")
            f.write(f"作者: {article.author or 'N/A'}\n")
            f.write(f"类型: {article.content_type or 'article'}\n")
            f.write(f"情感: {article.sentiment or 'neutral'}\n")
            f.write(f"质量: {article.quality_score:.2f}\n")
            f.write("\n")
            f.write(article.content)
            f.write("\n")

    st.success(f"已导出 {len(articles)} 篇文章到 {export_dir}")


def export_json(articles):
    """导出为 JSON"""
    import json
    import os
    from datetime import datetime

    export_dir = os.path.join(os.getenv('DATA_DIR', './data'), 'exports')
    os.makedirs(export_dir, exist_ok=True)

    data = [article.to_dict() for article in articles]

    filename = f"articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(export_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    st.success(f"已导出 {len(articles)} 篇文章到 {filepath}")


def export_csv(articles):
    """导出为 CSV"""
    import pandas as pd
    import os
    from datetime import datetime

    export_dir = os.path.join(os.getenv('DATA_DIR', './data'), 'exports')
    os.makedirs(export_dir, exist_ok=True)

    data = []
    for article in articles:
        data.append({
            "ID": article.id,
            "来源": article.source,
            "标题": article.title,
            "作者": article.author or "",
            "类型": article.content_type or "",
            "情感": article.sentiment or "",
            "分类": article.category or "",
            "质量": article.quality_score,
            "创建时间": article.created_at.strftime("%Y-%m-%d %H:%M:%S") if article.created_at else ""
        })

    df = pd.DataFrame(data)

    filename = f"articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(export_dir, filename)

    df.to_csv(filepath, index=False, encoding='utf-8-sig')

    st.success(f"已导出 {len(articles)} 篇文章到 {filepath}")


def export_qa_csv(qa_articles):
    """导出 QA 对为 CSV"""
    import os
    from datetime import datetime

    export_dir = os.path.join(os.getenv('DATA_DIR', './data'), 'exports')
    os.makedirs(export_dir, exist_ok=True)

    data = []
    for article in qa_articles:
        data.append({
            "question": article.question or "",
            "answer": article.answer or "",
            "similarity": article.similarity or 0.0,
            "category": article.category or "",
            "source": article.source
        })

    df = pd.DataFrame(data)

    filename = f"qa_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(export_dir, filename)

    df.to_csv(filepath, index=False, encoding='utf-8-sig')

    st.success(f"已导出 {len(qa_articles)} 篇QA对到 {filepath}")


def export_sentiment_json(review_articles):
    """导出评论情感为 JSON"""
    import json
    import os
    from datetime import datetime

    export_dir = os.path.join(os.getenv('DATA_DIR', './data'), 'exports')
    os.makedirs(export_dir, exist_ok=True)

    data = []
    for article in review_articles:
        data.append({
            "content": article.content,
            "sentiment": article.sentiment or "neutral",
            "label": article.category or "",
            "source": article.source,
            "title": article.title
        })

    filename = f"sentiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(export_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    st.success(f"已导出 {len(review_articles)} 篇评论到 {filepath}")
