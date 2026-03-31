# 迁移策略文档

## 概述

本文档描述数据库从 v1.0 迁移到 v1.1 的完整策略，包括新增字段支持、数据迁移、兼容性保证和回滚方案。

---

## 迁移目标

### v1.0 → v1.1 变更

| 变更类型 | 说明 |
|---------|------|
| 新增字段 | content_type, dataset_source, sentiment, sentiment_label, question, answer, choices, similarity, language |
| 新增索引 | idx_content_type, idx_sentiment, idx_dataset_source, idx_question |
| 新增约束 | chk_content_type, chk_sentiment |

---

## 迁移策略

### 阶段 1: 准备阶段

1. **数据备份**
   ```bash
   cp data/crawler.db data/crawler.db.backup_$(date +%Y%m%d)
   ```

2. **检查当前状态**
   ```sql
   SELECT COUNT(*) FROM articles;
   SELECT source, COUNT(*) FROM articles GROUP BY source;
   ```

### 阶段 2: 执行迁移

使用 Alembic 风格的迁移脚本：

```python
# storage/migration_add_huggingface_fields.py

def upgrade():
    """升级数据库到 v1.1"""

    # 1. 添加新字段
    op.add_column('articles', sa.Column('content_type', sa.String(50), nullable=True))
    op.add_column('articles', sa.Column('dataset_source', sa.String(200), nullable=True))
    op.add_column('articles', sa.Column('sentiment', sa.String(20), nullable=True))
    op.add_column('articles', sa.Column('sentiment_label', sa.Integer, nullable=True))
    op.add_column('articles', sa.Column('question', sa.Text, nullable=True))
    op.add_column('articles', sa.Column('answer', sa.Text, nullable=True))
    op.add_column('articles', sa.Column('choices', sa.Text, nullable=True))
    op.add_column('articles', sa.Column('similarity', sa.String(20), nullable=True))
    op.add_column('articles', sa.Column('language', sa.String(10), nullable=True))

    # 2. 设置默认值
    op.execute("UPDATE articles SET content_type = 'article' WHERE content_type IS NULL")
    op.execute("UPDATE articles SET language = 'zh' WHERE language IS NULL")
    op.execute("UPDATE articles SET similarity = 'medium' WHERE similarity IS NULL")

    # 3. 根据 source 推断 content_type
    op.execute("UPDATE articles SET content_type = 'social' WHERE source = 'weibo'")

    # 4. 创建索引
    op.create_index('idx_content_type', 'articles', ['content_type'])
    op.create_index('idx_sentiment', 'articles', ['sentiment'])
    op.create_index('idx_dataset_source', 'articles', ['dataset_source'])
    op.create_index('idx_question', 'articles', ['question'])

    # 5. 创建约束
    op.execute("""
        ALTER TABLE articles
        ADD CONSTRAINT chk_content_type
        CHECK (content_type IN ('article', 'review', 'qa', 'social') OR content_type IS NULL)
    """)

    op.execute("""
        ALTER TABLE articles
        ADD CONSTRAINT chk_sentiment
        CHECK (sentiment IN ('positive', 'neutral', 'negative') OR sentiment IS NULL)
    """)

def downgrade():
    """回滚到 v1.0"""

    # 1. 删除约束
    op.execute("ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_content_type")
    op.execute("ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_sentiment")

    # 2. 删除索引
    op.drop_index('idx_content_type', 'articles')
    op.drop_index('idx_sentiment', 'articles')
    op.drop_index('idx_dataset_source', 'articles')
    op.drop_index('idx_question', 'articles')

    # 3. 删除字段
    op.drop_column('articles', 'content_type')
    op.drop_column('articles', 'dataset_source')
    op.drop_column('articles', 'sentiment')
    op.drop_column('articles', 'sentiment_label')
    op.drop_column('articles', 'question')
    op.drop_column('articles', 'answer')
    op.drop_column('articles', 'choices')
    op.drop_column('articles', 'similarity')
    op.drop_column('articles', 'language')
```

### 阶段 3: 数据验证

迁移后验证脚本：

```python
def validate_migration():
    """验证迁移结果"""

    # 验证所有文章都有 content_type
    result = db.execute("SELECT COUNT(*) FROM articles WHERE content_type IS NULL")
    assert result.scalar() == 0, "存在无 content_type 的文章"

    # 验证所有文章都有 language
    result = db.execute("SELECT COUNT(*) FROM articles WHERE language IS NULL")
    assert result.scalar() == 0, "存在无 language 的文章"

    # 验证 content_type 推断正确
    result = db.execute("""
        SELECT content_type, source FROM articles
        WHERE source = 'weibo' AND content_type != 'social'
    """)
    assert result.rowcount == 0, "微博文章 content_type 推断错误"

    print("✅ 数据验证通过")
```

---

## 向后兼容性保证

### API 兼容性

| API 版本 | 变更 |
|---------|------|
| 现有端点 | 无变化，保持兼容 |
| 新参数 | 所有新增查询参数为可选 |
| 响应格式 | 新增字段向后兼容 |

### 数据库访问兼容

```python
# DatabaseManager 向后兼容

class DatabaseManager:
    def get_articles(self, content_type=None, **kwargs):
        """获取文章列表，兼容旧调用方式"""
        query = session.query(Article)

        # 新参数：支持 content_type 筛选
        if content_type:
            query = query.filter(Article.content_type == content_type)

        # 旧参数：保持兼容
        if kwargs.get('source'):
            query = query.filter(Article.source == kwargs['source'])
        # ...
```

### 前端兼容性

```python
# Streamlit 前端向后兼容

def get_articles(filters=None):
    """获取文章，兼容旧版筛选器"""
    if filters is None:
        filters = {}

    # 新筛选器
    if 'content_type' in filters:
        # 使用新参数
        pass

    # 旧筛选器保持兼容
    if 'source' in filters:
        # 使用旧参数
        pass
```

---

## 回滚方案

### 自动回滚条件

迁移失败时自动回滚：

```python
def run_migration():
    """执行迁移，失败时自动回滚"""
    try:
        upgrade()
        validate_migration()
        print("✅ 迁移成功")
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        print("正在回滚...")
        try:
            downgrade()
            print("✅ 回滚成功")
        except Exception as rollback_error:
            print(f"❌ 回滚失败: {rollback_error}")
            print("⚠️  请从备份恢复数据库")
            raise
```

### 手动回滚步骤

1. **停止应用**
   ```bash
   # 停止 Flask 服务
   # 停止 Streamlit 服务
   ```

2. **恢复备份**
   ```bash
   cp data/crawler.db.backup_YYYYMMDD data/crawler.db
   ```

3. **重启应用**
   ```bash
   python3 web_server.py &
   streamlit run web_ui/app.py
   ```

---

## 风险评估

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| 数据库迁移失败 | 高 | 低 | 提前备份，提供回滚脚本 |
| 旧数据兼容性问题 | 中 | 低 | 设置合理默认值，推断 content_type |
| 索引创建时间过长 | 低 | 低 | 在低峰期执行，使用 CONCURRENTLY |
| 应用启动失败 | 中 | 低 | 新字段允许 NULL，逐步迁移 |

---

## 部署检查清单

### 迁移前

- [ ] 创建数据库备份
- [ ] 在测试环境验证迁移脚本
- [ ] 通知相关开发人员
- [ ] 准备回滚方案

### 迁移中

- [ ] 执行迁移脚本
- [ ] 监控执行日志
- [ ] 验证数据完整性

### 迁移后

- [ ] 验证应用功能正常
- [ ] 检查 API 响应
- [ ] 验证前端显示
- [ ] 监控性能指标

---

## 相关文档

- [数据库设计文档](database_schema.md)
- [API 参考文档](api_reference.md)
- [技术决策记录](adr.md)
