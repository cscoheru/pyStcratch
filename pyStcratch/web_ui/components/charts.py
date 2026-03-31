"""
图表组件
"""
import plotly.express as px
import plotly.graph_objects as go


def sentiment_pie_chart(sentiment_data):
    """情感分布饼图"""
    colors = {"positive": "#00CC96", "negative": "#EF553B", "neutral": "#636EFA"}

    fig = go.Figure(data=[go.Pie(
        labels=list(sentiment_data.keys()),
        values=list(sentiment_data.values()),
        marker=dict(colors=[colors.get(k, "#636EFA") for k in sentiment_data.keys()]),
        textinfo='label+percent'
    )])

    fig.update_layout(
        title="情感分布",
        height=400
    )
    return fig


def content_type_bar_chart(content_type_data):
    """内容类型分布柱状图"""
    fig = px.bar(
        x=list(content_type_data.keys()),
        y=list(content_type_data.values()),
        labels={"x": "内容类型", "y": "文章数量"},
        title="内容类型分布"
    )
    return fig
