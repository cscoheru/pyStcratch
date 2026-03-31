# 数据库设计文档

## 概述

本文档定义爬虫数据管理系统的数据库架构设计，包括表结构、字段定义、索引策略和迁移方案。

---

## 数据库技术栈

| 环境 | 数据库 | 用途 |
|------|--------|------|
| 开发 | SQLite | 本地开发和测试 |
| 生产 | PostgreSQL (可选) | 云端部署 |

---

## 表结构设计

### 1. articles 表 (核心文章表)

存储所有爬取的文章内容，支持多来源、多分类。

#### 字段定义

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| **id** | Integer | PRIMARY KEY AUTO_INCREMENT | - | 主键 |
| **source** | String(50) | NOT NULL | - | 数据源 (zhihu, toutiao, wechat, bilibili, ximalaya, huggingface) |
| **article_id** | String(100) | NOT NULL | - | 源平台文章唯一ID |
| **title** | String(500) | NOT NULL | - | 文章标题 |
| **content** | Text | NOT NULL | - | 文章内容 |
| **author** | String(200) | NULLABLE | - | 作者 |
| **publish_time** | DateTime | NULLABLE | - | 发布时间 |
| **url** | Text | NULLABLE | - | 文章URL |
| **category** | String(50) | NULLABLE | - | 一级分类 (psychology, management, finance, other) |
| **subcategory** | String(50) | NULLABLE | - | 二级分类 |
| **sub_subcategory** | String(50) | NULLABLE | - | 三级分类 |
| **category_path** | Text | NULLABLE | - | 完整分类路径 (JSON数组) |
| **confidence** | Float | - | 0.0 | 分类置信度 |
| **quality_score** | Float | - | 0.0 | 内容质量分数 (0-1) |
| **is_valid** | Boolean | - | True | 是否有效内容 |
| **is_spam** | Boolean | - | False | 是否为垃圾内容 |

#### 新增字段 (Hugging Face 数据集支持)

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| **content_type** | String(50) | NULLABLE | "article" | 内容类型: article/review/qa/social |
| **dataset_source** | String(200) | NULLABLE | - | 数据集来源 (如: wangrui6/Zhihu-KOL) |
| **sentiment** | String(20) | NULLABLE | - | 情感标签: positive/neutral/negative |
| **sentiment_label** | Integer | NULLABLE | - | 情感原始标签值 |
| **question** | Text | NULLABLE | - | QA内容的问题部分 |
| **answer** | Text | NULLABLE | - | QA内容的答案部分 |
| **choices** | Text | NULLABLE | - | 选择题选项 (JSON格式) |
| **similarity** | String(20) | NULLABLE | - | 相似度状态: high/medium/low |
| **language** | String(10) | NULLABLE | "zh" | 内容语言 |

#### 索引设计

```sql
-- 基础索引
CREATE INDEX idx_source_article_id ON articles(source, article_id);  -- 唯一索引
CREATE INDEX idx_category ON articles(category);
CREATE INDEX idx_publish_time ON articles(publish_time);
CREATE INDEX idx_quality_score ON articles(quality_score);

-- 新增索引
CREATE INDEX idx_content_type ON articles(content_type);
CREATE INDEX idx_sentiment ON articles(sentiment);
CREATE INDEX idx_dataset_source ON articles(dataset_source);
CREATE INDEX idx_question ON articles(question) WHERE content_type='qa';

-- 复合索引
CREATE INDEX idx_source_category ON articles(source, category) WHERE category IS NOT NULL;
CREATE INDEX idx_source_valid ON articles(source, is_valid) WHERE is_valid = TRUE;
CREATE INDEX idx_dataset_type ON articles(dataset_source, content_type) WHERE dataset_source IS NOT NULL;
```

---

### 2. crawl_logs 表 (爬虫日志表)

记录爬虫执行日志，用于监控和调试。

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| **id** | Integer | PRIMARY KEY AUTO_INCREMENT | - | 主键 |
| **source** | String(50) | NOT NULL | - | 数据源 |
| **start_time** | DateTime | NOT NULL | - | 开始时间 |
| **end_time** | DateTime | NULLABLE | - | 结束时间 |
| **success_count** | Integer | - | 0 | 成功数量 |
| **failed_count** | Integer | - | 0 | 失败数量 |
| **error_msg** | Text | NULLABLE | - | 错误信息 |
| **created_at** | DateTime | - | NOW() | 创建时间 |

```sql
CREATE INDEX idx_source_start_time ON crawl_logs(source, start_time);
```

---

### 3. keywords 表 (关键词配置表)

存储分类关键词配置。

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| **id** | Integer | PRIMARY KEY AUTO_INCREMENT | - | 主键 |
| **category** | String(50) | NOT NULL | - | 分类 |
| **keyword** | String(100) | NOT NULL | - | 关键词 |
| **weight** | Float | - | 1.0 | 权重 |

```sql
CREATE INDEX idx_category_keyword ON keywords(category, keyword);
```

---

## 字段类型说明

### content_type 枚举值

| 值 | 说明 | 适用场景 |
|----|------|----------|
| `article` | 普通文章 | 默认类型，新闻、博客文章 |
| `review` | 评论/评价 | 用户评论、产品评价 |
| `qa` | 问答内容 | 问答对、FAQ |
| `social` | 社交内容 | 微博、社交媒体帖子 |

### sentiment 枚举值

| 值 | sentiment_label | 说明 |
|----|-----------------|------|
| `positive` | 1 | 积极/正面 |
| `neutral` | 0 | 中性 |
| `negative` | -1 | 消极/负面 |

### source 枚举值

| 值 | 说明 | content_type 推断 |
|----|------|-------------------|
| `zhihu` | 知乎 | article/qa |
| `toutiao` | 今日头条 | article |
| `wechat` | 微信公众号 | article |
| `weibo` | 微博 | social |
| `bilibili` | B站 | article/review |
| `ximalaya` | 喜马拉雅 | article |
| `huggingface` | Hugging Face | - |

---

## 默认值策略

### 新增字段默认值

| 字段 | 新数据默认值 | 旧数据迁移值 | 说明 |
|------|-------------|---------------|------|
| `content_type` | "article" | 根据 source 推断 | 保持向后兼容 |
| `language` | "zh" | "zh" | 默认中文 |
| `dataset_source` | NULL | NULL | 仅数据集有值 |
| `sentiment` | NULL | NULL | 需情感分析 |
| `question` | NULL | NULL | 仅 QA 类型 |
| `answer` | NULL | NULL | 仅 QA 类型 |
| `choices` | NULL | NULL | 仅选择题类型 |
| `similarity` | NULL | "medium" | 默认中等相似度 |

### 旧数据 content_type 推断规则

```python
def infer_content_type(source: str, content: dict) -> str:
    """根据 source 和内容推断 content_type"""
    if source == "weibo":
        return "social"
    elif source == "zhihu" and "question" in content:
        return "qa"
    else:
        return "article"
```

---

## 数据完整性约束

### 必填字段

- `source`
- `article_id`
- `title`
- `content`

### 唯一约束

- `(source, article_id)` 组合唯一

### 检查约束

```sql
-- content_type 必须是有效值
ALTER TABLE articles ADD CONSTRAINT chk_content_type
    CHECK (content_type IN ('article', 'review', 'qa', 'social'));

-- sentiment 必须是有效值（如果不为 NULL）
ALTER TABLE articles ADD CONSTRAINT chk_sentiment
    CHECK (sentiment IN ('positive', 'neutral', 'negative') OR sentiment IS NULL);
```

---

## 性能优化建议

### 1. 索引优化

- 为高频查询字段添加索引
- 使用复合索引加速多条件查询
- 定期分析慢查询并优化

### 2. 分区策略 (PostgreSQL)

```sql
-- 按创建时间分区（月度）
CREATE TABLE articles_partitioned (
    -- 字段定义同上
) PARTITION BY RANGE (created_at);

-- 创建分区
CREATE TABLE articles_2026_01 PARTITION OF articles_partitioned
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### 3. 查询优化

```python
# 避免 SELECT *
# 只查询需要的字段

# 使用 LIMIT 分页
# 避免一次查询大量数据

# 批量操作使用事务
# 提高写入性能
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2025-02-26 | 初始设计，支持基础爬虫功能 |
| v1.1 | 2026-02-26 | 添加 Hugging Face 数据集支持字段 |

---

## 相关文档

- [迁移策略文档](migration_strategy.md)
- [API 参考文档](api_reference.md)
- [技术决策记录](adr.md)
