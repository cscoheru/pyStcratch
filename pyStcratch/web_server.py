"""
Flask Web服务器 - 用于手动触发爬虫和查看状态
云端部署时提供HTTP API接口
"""
import os
import sys
from flask import Flask, jsonify, request
from loguru import logger

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scheduler.jobs import ManualJobs
from storage.database import DatabaseManager
from utils.dify_integration import DifyBatchSyncer

app = Flask(__name__)

# 配置日志
logger.remove()
logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"))

# 初始化数据库管理器
db_manager = DatabaseManager()


@app.route('/health')
def health():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "service": "crawler-web",
        "database": os.getenv("DATABASE_URL", "sqlite:///data/crawler.db")
    })


@app.route('/api/stats')
def get_stats():
    """获取数据库统计信息"""
    try:
        stats = db_manager.get_statistics()
        return jsonify({
            "success": True,
            "data": stats
        })
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/articles')
def get_articles():
    """
    获取文章列表 (支持筛选、搜索、分页)

    查询参数:
    - source: 来源筛选 (zhihu, toutiao, wechat, etc.)
    - category: 分类筛选 (psychology, management, etc.)
    - search: 搜索关键词 (标题/内容/作者)
    - min_quality: 最低质量分数 (0-1)
    - is_valid: 只显示有效文章 (true/false)
    - is_spam: 排除垃圾内容 (true/false)
    - sort_by: 排序字段 (publish_time, quality_score, created_at)
    - sort_order: 排序方向 (asc, desc)
    - page: 页码 (默认1)
    - page_size: 每页数量 (默认20)
    """
    try:
        from sqlalchemy import and_, or_, desc, asc
        from storage.models import Article

        # 获取查询参数
        source = request.args.get('source')
        category = request.args.get('category')
        subcategory = request.args.get('subcategory')
        search = request.args.get('search')
        min_quality = request.args.get('min_quality', type=float)
        is_valid = request.args.get('is_valid')
        is_spam = request.args.get('is_spam')
        sort_by = request.args.get('sort_by', 'publish_time')
        sort_order = request.args.get('sort_order', 'desc')
        page = request.args.get('page', 1, type=int)
        page_size = min(request.args.get('page_size', 20, type=int), 100)  # 最多100条

        with db_manager.get_session() as session:
            query = session.query(Article)

            # 应用筛选条件
            if is_valid is not None:
                is_valid_bool = is_valid.lower() == 'true'
                query = query.filter(Article.is_valid == is_valid_bool)
            if is_spam is not None:
                is_spam_bool = is_spam.lower() == 'true'
                query = query.filter(Article.is_spam == is_spam_bool)
            if source:
                query = query.filter(Article.source == source)
            if category:
                query = query.filter(Article.category == category)
            if subcategory:
                query = query.filter(Article.subcategory == subcategory)
            if min_quality is not None:
                query = query.filter(Article.quality_score >= min_quality)
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    or_(
                        Article.title.like(search_pattern),
                        Article.content.like(search_pattern),
                        Article.author.like(search_pattern)
                    )
                )

            # 获取总数
            total = query.count()

            # 应用排序
            order_col = getattr(Article, sort_by, Article.publish_time)
            if sort_order == 'desc':
                query = query.order_by(desc(order_col))
            else:
                query = query.order_by(asc(order_col))

            # 应用分页
            offset = (page - 1) * page_size
            articles = query.limit(page_size).offset(offset).all()

            # 转换为字典
            articles_data = [a.to_dict() for a in articles]

            return jsonify({
                "success": True,
                "data": {
                    "articles": articles_data,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
            })
    except Exception as e:
        logger.error(f"Failed to get articles: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/articles/<int:article_id>')
def get_article_detail(article_id):
    """获取单篇文章详情"""
    try:
        from storage.models import Article

        with db_manager.get_session() as session:
            article = session.query(Article).filter(Article.id == article_id).first()
            if article:
                return jsonify({
                    "success": True,
                    "data": article.to_dict()
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Article not found"
                }), 404
    except Exception as e:
        logger.error(f"Failed to get article detail: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/categories')
def get_categories():
    """获取所有分类列表"""
    try:
        from storage.models import Article
        from sqlalchemy import func

        with db_manager.get_session() as session:
            categories = session.query(Article.category).filter(
                Article.category.isnot(None)
            ).distinct().all()
            category_list = [c[0] for c in categories if c[0]]

            return jsonify({
                "success": True,
                "data": {
                    "categories": category_list
                }
            })
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/crawl', methods=['POST'])
def trigger_crawl():
    """
    手动触发爬虫

    请求体:
    {
        "source": "zhihu",  // 可选: all, zhihu, toutiao, wechat, bilibili, dedao, ximalaya
        "max_pages": 1       // 可选: 默认1
    }
    """
    try:
        data = request.json or {}
        source = data.get('source', 'zhihu')
        max_pages = data.get('max_pages', 1)

        logger.info(f"Manual crawl triggered: source={source}, max_pages={max_pages}")

        jobs = ManualJobs(db_manager=db_manager)
        result = jobs.crawl_source(source, max_pages=max_pages)

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        logger.error(f"Failed to trigger crawl: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/export', methods=['POST'])
def export_data():
    """
    导出数据

    请求体:
    {
        "format": "txt",      // txt, json, csv
        "category": null,     // 可选: psychology, management, finance
        "min_quality": 0.5    // 可选: 最低质量分数
    }
    """
    try:
        data = request.json or {}
        format_type = data.get('format', 'txt')
        category = data.get('category')
        min_quality = data.get('min_quality', 0.5)

        logger.info(f"Export triggered: format={format_type}, category={category}")

        # 导出目录
        export_dir = os.path.join(os.getenv('DATA_DIR', './data'), 'exports')
        os.makedirs(export_dir, exist_ok=True)

        # 执行导出
        if format_type == 'txt':
            path = db_manager.export_articles_to_txt(
                export_dir,
                category=category,
                min_quality=min_quality
            )
        elif format_type == 'json':
            import datetime
            filename = f"articles_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            path = os.path.join(export_dir, filename)
            path = db_manager.export_articles_to_json(
                path,
                category=category,
                min_quality=min_quality
            )
        elif format_type == 'csv':
            import datetime
            filename = f"articles_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            path = os.path.join(export_dir, filename)
            path = db_manager.export_articles_to_csv(
                path,
                category=category,
                min_quality=min_quality
            )
        else:
            return jsonify({
                "success": False,
                "error": f"Unsupported format: {format_type}"
            }), 400

        return jsonify({
            "success": True,
            "data": {
                "export_path": path,
                "format": format_type
            }
        })
    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/sync-dify', methods=['POST'])
def sync_to_dify():
    """
    同步数据到Dify知识库

    请求体:
    {
        "hours": 24,          // 最近N小时的文章
        "min_quality": 0.6    // 最低质量分数
    }
    """
    try:
        data = request.json or {}
        hours = data.get('hours', 24)
        min_quality = data.get('min_quality', 0.6)

        logger.info(f"Dify sync triggered: hours={hours}, min_quality={min_quality}")

        syncer = DifyBatchSyncer()
        result = syncer.sync_recent_articles(
            db_manager=db_manager,
            hours=hours,
            min_quality=min_quality
        )

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        logger.error(f"Failed to sync to Dify: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/run-full-sync', methods=['POST'])
def run_full_sync():
    """
    运行完整同步流程：爬取→分类→导出→Dify同步
    适合Railway Cron定时任务调用
    """
    try:
        logger.info("Starting full sync workflow...")

        results = {}

        # 1. 爬取数据（限制页面数以避免超时）
        logger.info("Step 1: Crawling data...")
        jobs = ManualJobs(db_manager=db_manager)

        # 依次爬取各平台
        sources = ['zhihu', 'toutiao', 'wechat']
        crawl_results = {}
        for source in sources:
            try:
                result = jobs.crawl_source(source, max_pages=1)
                crawl_results[source] = result
                logger.info(f"Crawled {source}: {result}")
            except Exception as e:
                logger.error(f"Failed to crawl {source}: {e}")
                crawl_results[source] = {"error": str(e)}

        results['crawl'] = crawl_results

        # 2. 分类未分类的文章
        logger.info("Step 2: Classifying articles...")
        try:
            from scheduler.jobs import CrawlerScheduler
            scheduler = CrawlerScheduler(db_manager=db_manager)
            # 运行分类任务
            import asyncio
            asyncio.run(scheduler._classify_articles_job())
            results['classify'] = {"success": True}
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            results['classify'] = {"error": str(e)}

        # 3. 导出到TXT
        logger.info("Step 3: Exporting to TXT...")
        try:
            export_dir = os.path.join(os.getenv('DATA_DIR', './data'), 'exports')
            os.makedirs(export_dir, exist_ok=True)
            export_path = db_manager.export_articles_to_txt(export_dir, min_quality=0.6)
            results['export'] = {"success": True, "path": export_path}
        except Exception as e:
            logger.error(f"Export failed: {e}")
            results['export'] = {"error": str(e)}

        # 4. 同步到Dify（如果配置了API密钥）
        if os.getenv('DIFY_API_KEY'):
            logger.info("Step 4: Syncing to Dify...")
            try:
                syncer = DifyBatchSyncer()
                sync_result = syncer.sync_recent_articles(
                    db_manager=db_manager,
                    hours=24,
                    min_quality=0.6
                )
                results['dify_sync'] = sync_result
            except Exception as e:
                logger.error(f"Dify sync failed: {e}")
                results['dify_sync'] = {"error": str(e)}
        else:
            logger.info("Dify API key not configured, skipping sync")
            results['dify_sync'] = {"skipped": True, "reason": "No API key"}

        # 5. 获取最终统计
        logger.info("Step 5: Getting final stats...")
        try:
            stats = db_manager.get_statistics()
            results['stats'] = stats
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            results['stats'] = {"error": str(e)}

        logger.info(f"Full sync completed: {results}")

        return jsonify({
            "success": True,
            "data": results
        })
    except Exception as e:
        logger.error(f"Full sync failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    # 开发环境直接运行
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
