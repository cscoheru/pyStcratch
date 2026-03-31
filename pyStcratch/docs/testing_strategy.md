# 测试策略文档

## 概述

本文档定义爬虫数据管理系统的完整测试策略，包括单元测试、集成测试、性能测试和数据一致性验证。

---

## 测试层级

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          测试金字塔                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                    /\                                                        │
│                   /  \           端到端测试 (E2E)                             │
│                  /────\          约 10% 的测试                               │
│                 /      \                                                      │
│                /        \                                                    │
│               /  集成测试  \       API/数据库集成测试                          │
│              /            \      约 30% 的测试                               │
│             /              \                                                   │
│            /                \                                                 │
│           /    单元测试       \    组件/函数级测试                             │
│          /                    \  约 60% 的测试                               │
│         /                      \                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 一、单元测试

### 1.1 测试框架配置

```bash
# 安装测试依赖
pip install pytest pytest-cov pytest-asyncio pytest-mock
pip install responses  # HTTP 请求模拟
pip install freezegun  # 时间冻结
```

**pytest 配置**: `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
```

### 1.2 DatabaseManager 单元测试

**测试文件**: `tests/test_database_manager.py`

```python
import pytest
from datetime import datetime
from storage.database import DatabaseManager
from storage.models import Article

@pytest.fixture
def db_manager(tmp_path):
    """创建临时数据库管理器"""
    db_path = tmp_path / "test.db"
    return DatabaseManager(database_url=f"sqlite:///{db_path}")

@pytest.fixture
def sample_article():
    """示例文章数据"""
    return {
        "source": "zhihu",
        "article_id": "test_123",
        "title": "测试文章",
        "content": "这是测试内容",
        "author": "测试作者",
        "publish_time": datetime.now(),
        "url": "https://example.com/test",
        "category": "psychology",
        "quality_score": 0.8,
        "is_valid": True,
        "is_spam": False
    }

class TestDatabaseManager:
    """DatabaseManager 单元测试"""

    def test_add_article(self, db_manager, sample_article):
        """测试添加文章"""
        article_id = db_manager.add_article(**sample_article)
        assert article_id > 0

    def test_add_duplicate_article(self, db_manager, sample_article):
        """测试添加重复文章（应去重）"""
        db_manager.add_article(**sample_article)
        db_manager.add_article(**sample_article)
        count = db_manager.session.query(Article).filter_by(
            source="zhihu",
            article_id="test_123"
        ).count()
        assert count == 1

    def test_get_articles_by_category(self, db_manager, sample_article):
        """测试按分类获取文章"""
        db_manager.add_article(**sample_article)
        articles = db_manager.get_articles(category="psychology")
        assert len(articles) == 1
        assert articles[0].category == "psychology"

    def test_get_articles_with_filters(self, db_manager):
        """测试多条件筛选"""
        # 添加不同质量分数的文章
        for i in range(5):
            db_manager.add_article(
                source="zhihu",
                article_id=f"test_{i}",
                title=f"测试文章{i}",
                content="内容",
                quality_score=0.5 + i * 0.1
            )

        # 筛选高质量文章
        articles = db_manager.get_articles(min_quality=0.7)
        assert len(articles) == 3

    def test_update_article_quality(self, db_manager, sample_article):
        """测试更新文章质量分数"""
        article_id = db_manager.add_article(**sample_article)
        db_manager.update_article_quality(article_id, 0.95)

        article = db_manager.get_article_by_id(article_id)
        assert article.quality_score == 0.95

    def test_delete_article(self, db_manager, sample_article):
        """测试删除文章"""
        article_id = db_manager.add_article(**sample_article)
        db_manager.delete_article(article_id)

        article = db_manager.get_article_by_id(article_id)
        assert article is None
```

### 1.3 爬虫模块单元测试

**测试文件**: `tests/test_crawlers.py`

```python
import pytest
from unittest.mock import Mock, patch
from crawler.huggingface_zhihu import HuggingFaceZhihuCrawler

@pytest.fixture
def hf_crawler():
    """创建 Hugging Face 爬虫实例"""
    return HuggingFaceZhihuCrawler()

class TestHuggingFaceZhihuCrawler:
    """HuggingFaceZhihuCrawler 单元测试"""

    @patch('crawler.huggingface_zhihu.load_dataset')
    def test_search_by_keyword(self, mock_load, hf_crawler):
        """测试关键词搜索"""
        # 模拟数据集返回
        mock_data = {
            "train": [
                {"question": "什么是心理学？", "answer": "心理学是..."},
                {"question": "心理咨询有用吗？", "answer": "心理咨询..."}
            ]
        }
        mock_load.return_value = mock_data

        results = hf_crawler.search("心理学", max_results=2)
        assert len(results) == 2
        assert "心理学" in results[0]["question"]

    @patch('crawler.huggingface_zhihu.load_dataset')
    def test_crawl_by_keywords(self, mock_load, hf_crawler):
        """测试多关键词爬取"""
        mock_load.return_value = {"train": [{"question": "测试", "answer": "答案"}]}

        results = hf_crawler.crawl_by_keywords(["心理学", "管理学"], max_samples=5)
        assert len(results) > 0

    def test_get_random_samples(self, hf_crawler):
        """测试随机采样"""
        with patch.object(hf_crawler, 'dataset') as mock_dataset:
            mock_dataset.shuffle.return_value = mock_dataset
            mock_dataset.take.return_value = [
                {"question": "Q1", "answer": "A1"},
                {"question": "Q2", "answer": "A2"}
            ]

            samples = hf_crawler.get_random_samples(n=2)
            assert len(samples) == 2

class TestTextCleaner:
    """TextCleaner 单元测试"""

    def test_clean_html_tags(self):
        """测试 HTML 标签清理"""
        from utils.text_cleaner import TextCleaner

        dirty = "<p>这是一段<p>包含<b>HTML</b>标签的内容</p>"
        clean = TextCleaner.clean(dirty)
        assert "<p>" not in clean
        assert "HTML" in clean

    def test_remove_extra_whitespace(self):
        """测试多余空格清理"""
        from utils.text_cleaner import TextCleaner

        dirty = "这  是  一段   有   多余  空格  的  内容"
        clean = TextCleaner.clean(dirty)
        assert "  " not in clean

    def test_extract_main_content(self):
        """测试主要内容提取"""
        from utils.text_cleaner import TextCleaner

        html = """
        <html>
            <head><title>测试</title></head>
            <body>
                <nav>导航菜单</nav>
                <main>主要内容</main>
                <footer>页脚</footer>
            </body>
        </html>
        """
        content = TextCleaner.extract_main_content(html)
        assert "主要内容" in content
        assert "导航菜单" not in content
```

### 1.4 分类器单元测试

**测试文件**: `tests/test_classifier.py`

```python
import pytest
from classifier.multi_level_classifier import MultiLevelClassifier

@pytest.fixture
def classifier():
    """创建分类器实例"""
    return MultiLevelClassifier()

class TestMultiLevelClassifier:
    """MultiLevelClassifier 单元测试"""

    def test_classify_psychology_article(self, classifier):
        """测试心理学文章分类"""
        text = "心理学研究发现，认知行为疗法对治疗抑郁症效果显著。"
        result = classifier.classify(text)

        assert result["primary_category"] == "psychology"
        assert result["confidence"] > 0.5

    def test_classify_with_confidence_threshold(self, classifier):
        """测试置信度阈值"""
        short_text = "短内容"
        result = classifier.classify(short_text)

        # 短内容应返回默认分类
        assert result["primary_category"] == "other"
        assert result["confidence"] < 0.5

    def test_batch_classify(self, classifier):
        """测试批量分类"""
        texts = [
            "心理学研究表明...",
            "企业管理实践...",
            "金融市场分析..."
        ]

        results = classifier.batch_classify(texts)
        assert len(results) == 3
        assert results[0]["primary_category"] == "psychology"
```

---

## 二、集成测试

### 2.1 API 集成测试

**测试文件**: `tests/test_api_integration.py`

```python
import pytest
import json
from web_server import app

@pytest.fixture
def client(tmp_path):
    """创建测试客户端"""
    # 使用临时数据库
    app.config['TESTING'] = True
    app.config['DATABASE_URL'] = f"sqlite:///{tmp_path}/test.db"

    with app.test_client() as client:
        yield client

class TestAPIEndpoints:
    """API 端点集成测试"""

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"

    def test_get_articles_empty(self, client):
        """测试获取空文章列表"""
        response = client.get('/api/articles')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] == True
        assert len(data["data"]["articles"]) == 0

    def test_get_articles_with_filters(self, client):
        """测试带筛选的文章查询"""
        # 先添加测试数据
        # ... (通过 API 或直接操作数据库)

        response = client.get('/api/articles?category=psychology&page=1&page_size=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "articles" in data["data"]

    def test_trigger_crawl(self, client):
        """测试触发爬虫"""
        response = client.post('/api/crawl', json={
            "source": "zhihu",
            "max_pages": 1
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] == True
        assert "source" in data["data"]

    def test_export_data(self, client):
        """测试数据导出"""
        response = client.post('/api/export', json={
            "format": "txt",
            "min_quality": 0.5
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "file_path" in data["data"]

    def test_sync_dify(self, client):
        """测试 Dify 同步"""
        response = client.post('/api/sync-dify', json={
            "hours": 24,
            "min_quality": 0.6
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "synced" in data["data"]
```

### 2.2 数据库迁移集成测试

**测试文件**: `tests/test_migration.py`

```python
import pytest
import tempfile
from pathlib import Path
from storage.migration_add_huggingface_fields import upgrade, downgrade, validate_post_migration

class TestDatabaseMigration:
    """数据库迁移集成测试"""

    @pytest.fixture
    def test_db(self):
        """创建测试数据库"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            test_db_path = f.name
        yield test_db_path
        Path(test_db_path).unlink(missing_ok=True)

    def test_migration_upgrade(self, test_db):
        """测试升级迁移"""
        # 创建 v1.0 数据库结构
        # ... (执行旧版 schema)

        # 执行升级
        upgrade()

        # 验证新字段存在
        # ... (检查 content_type, sentiment 等字段)

    def test_migration_downgrade(self, test_db):
        """测试降级迁移"""
        # 先升级
        upgrade()

        # 再降级
        downgrade()

        # 验证新字段已删除
        # ... (检查 content_type 等字段不存在)

    def test_migration_data_preservation(self, test_db):
        """测试迁移后数据完整性"""
        # 插入测试数据
        # ... (添加旧版数据)

        # 执行迁移
        upgrade()

        # 验证数据未丢失
        # ... (检查原始数据完整)

        # 验证默认值设置正确
        # ... (检查 content_type='article', language='zh')
```

### 2.3 完整工作流集成测试

**测试文件**: `tests/test_workflow.py`

```python
import pytest
from crawler.huggingface_zhihu import HuggingFaceZhihuCrawler
from classifier.multi_level_classifier import MultiLevelClassifier
from storage.database import DatabaseManager

class TestFullWorkflow:
    """完整工作流集成测试"""

    def test_crawl_classify_store_workflow(self, tmp_path):
        """测试爬取-分类-存储完整流程"""
        # 1. 初始化组件
        crawler = HuggingFaceZhihuCrawler()
        classifier = MultiLevelClassifier()
        db = DatabaseManager(database_url=f"sqlite:///{tmp_path}/test.db")

        # 2. 爬取数据
        articles = crawler.search("心理学", max_results=5)
        assert len(articles) > 0

        # 3. 分类处理
        for article in articles:
            result = classifier.classify(article["answer"])
            article["category"] = result["primary_category"]
            article["confidence"] = result["confidence"]

        # 4. 存储到数据库
        for article in articles:
            article_id = db.add_article(
                source="huggingface",
                article_id=article["id"],
                title=article["question"],
                content=article["answer"],
                category=article.get("category"),
                confidence=article.get("confidence"),
                content_type="qa",
                dataset_source="wangrui6/Zhihu-KOL"
            )
            assert article_id > 0

        # 5. 验证存储
        stored_articles = db.get_articles(category="psychology")
        assert len(stored_articles) > 0
```

---

## 三、性能测试

### 3.1 数据库查询性能测试

**测试文件**: `tests/test_performance.py`

```python
import pytest
import time
from storage.database import DatabaseManager

class TestDatabasePerformance:
    """数据库性能测试"""

    @pytest.mark.slow
    def test_bulk_insert_performance(self, db_manager):
        """测试批量插入性能"""
        n = 1000
        start_time = time.time()

        for i in range(n):
            db_manager.add_article(
                source=f"source_{i % 5}",
                article_id=f"article_{i}",
                title=f"标题{i}",
                content="内容" * 100,
                category="psychology"
            )

        elapsed = time.time() - start_time
        rate = n / elapsed

        assert rate > 100  # 至少 100 条/秒
        print(f"插入速率: {rate:.2f} 条/秒")

    @pytest.mark.slow
    def test_query_with_filters_performance(self, db_manager):
        """测试带筛选查询性能"""
        # 准备 10,000 条数据
        # ...

        start_time = time.time()
        articles = db_manager.get_articles(
            category="psychology",
            min_quality=0.7,
            page_size=100
        )
        elapsed = time.time() - start_time

        assert elapsed < 1.0  # 查询应在 1 秒内完成
        print(f"查询耗时: {elapsed*1000:.2f}ms")

    @pytest.mark.slow
    def test_full_text_search_performance(self, db_manager):
        """测试全文搜索性能"""
        # 准备数据
        # ...

        start_time = time.time()
        articles = db_manager.search_articles("心理学", limit=50)
        elapsed = time.time() - start_time

        assert elapsed < 2.0
```

### 3.2 API 性能测试

**使用工具**: Apache Bench (ab) 或 locust

```bash
# 安装 locust
pip install locust

# 创建性能测试: tests/performance/locustfile.py
```

```python
from locust import HttpUser, task, between

class CrawlerAPIUser(HttpUser):
    """API 性能测试用户"""
    wait_time = between(1, 3)

    @task(3)
    def get_articles(self):
        """测试文章列表查询"""
        self.client.get("/api/articles?page_size=20")

    @task(2)
    def get_stats(self):
        """测试统计信息查询"""
        self.client.get("/api/stats")

    @task(1)
    def get_article_detail(self):
        """测试文章详情查询"""
        self.client.get("/api/articles/1")

    @task
    def health_check(self):
        """测试健康检查"""
        self.client.get("/health")
```

**运行性能测试**:

```bash
# 使用 locust
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# 使用 ab (Apache Bench)
ab -n 1000 -c 10 http://localhost:8000/api/articles
```

### 3.3 性能基准

| 操作 | 目标性能 | 测试方法 |
|------|---------|---------|
| 文章列表查询 | < 200ms (P95) | API 性能测试 |
| 文章详情查询 | < 100ms (P95) | API 性能测试 |
| 统计信息查询 | < 500ms (P95) | API 性能测试 |
| 批量插入 | > 100 条/秒 | 数据库性能测试 |
| 全文搜索 | < 2 秒 | 数据库性能测试 |

---

## 四、数据一致性验证

### 4.1 数据完整性检查

**测试文件**: `tests/test_data_consistency.py`

```python
import pytest
from storage.database import DatabaseManager

class TestDataConsistency:
    """数据一致性测试"""

    def test_unique_constraint(self, db_manager):
        """测试唯一约束"""
        db_manager.add_article(
            source="zhihu",
            article_id="duplicate_test",
            title="标题",
            content="内容"
        )

        # 重复添加应被拒绝
        with pytest.raises(Exception):
            db_manager.add_article(
                source="zhihu",
                article_id="duplicate_test",
                title="标题2",
                content="内容2"
            )

    def test_not_null_constraints(self, db_manager):
        """测试非空约束"""
        with pytest.raises(Exception):
            db_manager.add_article(
                source=None,  # 必填字段
                article_id="test",
                title="标题",
                content="内容"
            )

    def test_foreign_key_constraints(self, db_manager):
        """测试外键约束（如果有）"""
        # ... 外键约束测试
        pass

    def test_data_type_validation(self, db_manager):
        """测试数据类型验证"""
        # quality_score 应在 0-1 之间
        with pytest.raises(ValueError):
            db_manager.add_article(
                source="zhihu",
                article_id="test",
                title="标题",
                content="内容",
                quality_score=1.5  # 超出范围
            )
```

### 4.2 迁移数据验证脚本

**验证脚本**: `scripts/validate_migration.py`

```python
"""验证数据库迁移后的数据一致性"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.database import DatabaseManager
from loguru import logger

def validate_migration():
    """验证迁移后的数据"""
    db = DatabaseManager()

    # 1. 验证所有文章都有 content_type
    null_content_type = db.session.execute(
        "SELECT COUNT(*) FROM articles WHERE content_type IS NULL"
    ).scalar()
    if null_content_type > 0:
        logger.error(f"发现 {null_content_type} 条文章缺少 content_type")
        return False
    logger.info("✓ 所有文章都有 content_type")

    # 2. 验证所有文章都有 language
    null_language = db.session.execute(
        "SELECT COUNT(*) FROM articles WHERE language IS NULL"
    ).scalar()
    if null_language > 0:
        logger.error(f"发现 {null_language} 条文章缺少 language")
        return False
    logger.info("✓ 所有文章都有 language")

    # 3. 验证 content_type 值有效
    invalid_types = db.session.execute(
        "SELECT COUNT(*) FROM articles WHERE content_type NOT IN ('article', 'review', 'qa', 'social')"
    ).scalar()
    if invalid_types > 0:
        logger.error(f"发现 {invalid_types} 条无效的 content_type")
        return False
    logger.info("✓ 所有 content_type 值有效")

    # 4. 验证 sentiment 值有效（如果不为空）
    invalid_sentiment = db.session.execute(
        "SELECT COUNT(*) FROM articles WHERE sentiment IS NOT NULL AND sentiment NOT IN ('positive', 'neutral', 'negative')"
    ).scalar()
    if invalid_sentiment > 0:
        logger.error(f"发现 {invalid_sentiment} 条无效的 sentiment")
        return False
    logger.info("✓ 所有 sentiment 值有效")

    # 5. 统计各类型文章数量
    stats = db.session.execute("""
        SELECT content_type, COUNT(*) as count
        FROM articles
        GROUP BY content_type
    """).fetchall()
    logger.info("Content type 分布:")
    for row in stats:
        logger.info(f"  {row[0]}: {row[1]}")

    logger.info("✅ 迁移验证通过")
    return True

if __name__ == "__main__":
    success = validate_migration()
    sys.exit(0 if success else 1)
```

### 4.3 分类器一致性验证

**测试文件**: `tests/test_classifier_consistency.py`

```python
import pytest
from classifier.multi_level_classifier import MultiLevelClassifier

class TestClassifierConsistency:
    """分类器一致性测试"""

    def test_same_text_same_result(self):
        """测试相同文本产生相同分类结果"""
        classifier = MultiLevelClassifier()
        text = "心理学研究显示，认知行为疗法有效。"

        result1 = classifier.classify(text)
        result2 = classifier.classify(text)

        assert result1["primary_category"] == result2["primary_category"]
        assert result1["confidence"] == result2["confidence"]

    def test_similar_text_similar_result(self):
        """测试相似文本产生相似分类结果"""
        classifier = MultiLevelClassifier()
        text1 = "心理学研究发现认知行为疗法对抑郁症有效"
        text2 = "心理学研究表明认知行为疗法可治疗抑郁症状"

        result1 = classifier.classify(text1)
        result2 = classifier.classify(text2)

        assert result1["primary_category"] == result2["primary_category"]
```

---

## 五、测试覆盖率目标

| 模块 | 目标覆盖率 | 当前状态 |
|------|-----------|---------|
| storage/database.py | > 80% | - |
| crawler/*.py | > 70% | - |
| classifier/*.py | > 75% | - |
| utils/*.py | > 70% | - |
| web_server.py | > 60% | - |
| 整体 | > 70% | - |

### 运行覆盖率测试

```bash
# 运行所有测试并生成覆盖率报告
pytest --cov=. --cov-report=html --cov-report=term

# 查看报告
open htmlcov/index.html
```

---

## 六、持续集成配置

### GitHub Actions 工作流

**文件**: `.github/workflows/test.yml`

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run unit tests
      run: pytest tests/ -m unit --cov=. --cov-report=xml

    - name: Run integration tests
      run: pytest tests/ -m integration

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

## 七、测试数据管理

### 7.1 测试数据集

**目录结构**:
```
tests/
├── fixtures/          # 测试数据
│   ├── sample_articles.json
│   ├── sample_crawl_results.json
│   └── expected_classifications.json
├── data/              # 大型测试数据
│   └── test_dataset.db
```

### 7.2 Mock 数据使用

```python
# 使用 pytest fixtures 创建 mock 数据
@pytest.fixture
def mock_huggingface_dataset():
    """Mock Hugging Face 数据集返回"""
    return {
        "train": [
            {
                "id": "1",
                "question": "什么是心理学？",
                "answer": "心理学是研究人类心理活动的科学。",
                "topic": "psychology"
            },
            # ... 更多样本
        ]
    }
```

---

## 八、测试执行指南

### 8.1 本地测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 运行特定文件
pytest tests/test_database_manager.py

# 运行特定测试函数
pytest tests/test_database_manager.py::TestDatabaseManager::test_add_article

# 查看详细输出
pytest -v

# 停在第一个失败
pytest -x

# 进入调试模式
pytest --pdb
```

### 8.2 CI/CD 测试

```bash
# GitHub Actions 自动运行
# 推送代码到 GitHub 触发测试

# 查看测试结果
# GitHub Actions → Tests → View runs
```

---

## 九、测试检查清单

### 发布前测试

- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 代码覆盖率 > 70%
- [ ] 性能测试达到基准
- [ ] 数据迁移验证通过
- [ ] 手动冒烟测试完成

### 数据迁移测试

- [ ] 迁移前备份完成
- [ ] 升级迁移成功
- [ ] 数据完整性验证通过
- [ ] 降级回滚测试通过
- [ ] 迁移脚本文档更新

---

## 十、相关文档

- [数据库设计文档](database_schema.md)
- [迁移策略文档](migration_strategy.md)
- [API 参考文档](api_reference.md)
- [技术决策记录](adr.md)
