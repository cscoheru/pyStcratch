# API 参考文档

## 概述

本文档定义爬虫数据管理系统的 RESTful API 接口规范。

---

## 基础信息

| 项目 | 说明 |
|------|------|
| **Base URL** | `http://localhost:8000` |
| **内容类型** | `application/json` |
| **字符编码** | UTF-8 |

---

## 通用响应格式

### 成功响应

```json
{
    "success": true,
    "data": { /* 数据内容 */ }
}
```

### 错误响应

```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "错误描述"
    }
}
```

### 分页响应

```json
{
    "success": true,
    "data": {
        "items": [...],
        "total": 100,
        "page": 1,
        "page_size": 20,
        "total_pages": 5
    }
}
```

---

## API 端点

### 1. 健康检查

检查服务运行状态。

```
GET /health
```

**响应示例**:
```json
{
    "status": "healthy",
    "service": "crawler-web",
    "database": "sqlite:///data/crawler.db"
}
```

---

### 2. 统计信息

获取数据库统计信息。

```
GET /api/stats
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "total_articles": 1523,
        "valid_articles": 1200,
        "spam_articles": 323,
        "average_quality_score": 0.75,
        "by_source": {
            "zhihu": 523,
            "toutiao": 412,
            "wechat": 334,
            "bilibili": 254
        },
        "by_category": {
            "psychology": 456,
            "management": 389,
            "finance": 234,
            "other": 444
        },
        "by_content_type": {
            "article": 800,
            "review": 300,
            "qa": 200,
            "social": 223
        }
    }
}
```

---

### 3. 详细统计 (NEW)

获取按内容类型、情感、数据集分组的详细统计。

```
GET /api/stats/detailed
```

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| group_by | string | 否 | 分组类型: content_type/sentiment/dataset_source |

**响应示例**:
```json
{
    "success": true,
    "data": {
        "by_content_type": {
            "article": 800,
            "review": 300,
            "qa": 200,
            "social": 223
        },
        "by_sentiment": {
            "positive": 450,
            "neutral": 800,
            "negative": 273
        },
        "by_dataset_source": {
            "wangrui6/Zhihu-KOL": 500,
            "clue/thucnews": 300,
            "shibing624/weibo-sentiment-100k": 200,
            "crawler": 523
        },
        "recent_crawls": [
            {
                "source": "zhihu",
                "start_time": "2026-02-26T10:00:00",
                "success_count": 50,
                "status": "completed"
            }
        ]
    }
}
```

---

### 4. 获取文章列表

获取文章列表，支持筛选、搜索和分页。

```
GET /api/articles
```

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| source | string | 否 | 数据源筛选: zhihu/toutiao/wechat/bilibili/ximalaya/huggingface |
| content_type | string | 否 | 内容类型: article/review/qa/social |
| category | string | 否 | 分类筛选: psychology/management/finance/other |
| sentiment | string | 否 | 情感筛选: positive/neutral/negative |
| dataset_source | string | 否 | 数据集来源筛选 |
| search | string | 否 | 搜索关键词 (标题/内容/作者) |
| min_quality | float | 否 | 最低质量分数 (0-1) |
| is_valid | boolean | 否 | 是否只显示有效文章 |
| is_spam | boolean | 否 | 是否排除垃圾内容 |
| sort_by | string | 否 | 排序字段: publish_time/quality_score/created_at |
| sort_order | string | 否 | 排序方向: asc/desc |
| page | integer | 否 | 页码 (默认1) |
| page_size | integer | 否 | 每页数量 (默认20, 最大100) |

**响应示例**:
```json
{
    "success": true,
    "data": {
        "articles": [
            {
                "id": 1,
                "source": "zhihu",
                "article_id": "hf_12345",
                "title": "心理学最经典的理论有哪些？",
                "content": "心理学经典理论包括...",
                "author": "张三",
                "publish_time": "2025-01-15T10:30:00",
                "url": "https://www.zhihu.com/question/12345",
                "category": "psychology",
                "subcategory": "clinical",
                "sub_subcategory": "depression",
                "category_path": ["心理咨询", "临床心理", "抑郁症"],
                "confidence": 0.95,
                "quality_score": 0.88,
                "content_type": "qa",
                "dataset_source": "wangrui6/Zhihu-KOL",
                "sentiment": "neutral",
                "sentiment_label": 0,
                "question": "心理学最经典的理论有哪些？",
                "answer": "心理学经典理论包括...",
                "language": "zh",
                "is_valid": true,
                "is_spam": false,
                "created_at": "2026-02-26T00:00:00",
                "updated_at": "2026-02-26T00:00:00"
            }
        ],
        "total": 1523,
        "page": 1,
        "page_size": 20,
        "total_pages": 77
    }
}
```

---

### 5. 获取文章详情

获取单篇文章的完整信息。

```
GET /api/articles/{id}
```

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| id | integer | 文章ID |

**响应示例**:
```json
{
    "success": true,
    "data": {
        "id": 1,
        "title": "...",
        "content": "...",
        // ... (同文章列表字段)
    }
}
```

---

### 6. 触发爬虫

手动触发指定平台的爬虫任务。

```
POST /api/crawl
```

**请求体**:
```json
{
    "source": "zhihu",
    "max_pages": 2
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| source | string | 是 | 数据源: zhihu/toutiao/wechat/bilibili/ximalaya/all |
| max_pages | integer | 否 | 最大页数 (默认1) |

**响应示例**:
```json
{
    "success": true,
    "data": {
        "source": "zhihu",
        "status": "running",
        "articles_found": 50,
        "articles_saved": 45,
        "duplicates": 5,
        "failed": 0
    }
}
```

---

### 7. 数据集管理 (NEW)

#### 7.1 获取数据集列表

```
GET /api/datasets
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "datasets": [
            {
                "name": "wangrui6/Zhihu-KOL",
                "type": "huggingface",
                "articles_count": 500,
                "description": "知乎问答数据集"
            },
            {
                "name": "clue/thucnews",
                "type": "huggingface",
                "articles_count": 300,
                "description": "THUCNews 新闻数据集"
            }
        ]
    }
}
```

#### 7.2 同步数据集

手动触发数据集同步。

```
POST /api/datasets/{name}/sync
```

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| name | string | 数据集名称 (URL编码) |

**请求体**:
```json
{
    "max_samples": 1000
}
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "dataset": "wangrui6/Zhihu-KOL",
        "synced": 500,
        "skipped": 0,
        "failed": 0
    }
}
```

---

### 8. 导出数据

导出文章数据。

```
POST /api/export
```

**请求体**:
```json
{
    "format": "txt",
    "category": null,
    "min_quality": 0.5
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| format | string | 是 | 导出格式: txt/json/csv |
| category | string | 否 | 分类筛选 |
| min_quality | float | 否 | 最低质量分数 |

**响应示例**:
```json
{
    "success": true,
    "data": {
        "format": "txt",
        "file_path": "/data/exports/articles_20260226.txt",
        "articles_count": 150
    }
}
```

---

### 9. 同步到 Dify

同步文章到 Dify 知识库。

```
POST /api/sync-dify
```

**请求体**:
```json
{
    "hours": 24,
    "min_quality": 0.6
}
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "synced": 100,
        "failed": 5,
        "batch_id": "batch_123456"
    }
}
```

---

### 10. 全量同步 (NEW)

运行完整的同步流程：爬取 → 分类 → 导出 → Dify同步。

```
POST /api/run-full-sync
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "crawl": {
            "zhihu": {"articles_found": 50, "saved": 45},
            "toutiao": {"articles_found": 30, "saved": 28}
        },
        "classify": {"success": true},
        "export": {"path": "/data/exports/export.txt"},
        "dify_sync": {"synced": 50},
        "stats": {
            "total_articles": 1523,
            "valid_articles": 1200
        }
    }
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 1000 | 内部服务器错误 |
| 1001 | 无效请求参数 |
| 1002 | 未找到资源 |
| 2000 | 数据库操作失败 |
| 2001 | 数据验证失败 |
| 3000 | 爬虫执行失败 |
| 3001 | 数据源不可用 |
| 4000 | 分类服务失败 |
| 5000 | 导出失败 |
| 6000 | Dify 同步失败 |

---

## 数据模型

### Article 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | integer | 主键 |
| source | string | 数据源 |
| article_id | string | 源平台ID |
| title | string | 标题 |
| content | string | 内容 |
| author | string | 作者 |
| publish_time | string | 发布时间 (ISO 8601) |
| url | string | URL |
| category | string | 一级分类 |
| subcategory | string | 二级分类 |
| sub_subcategory | string | 三级分类 |
| category_path | array | 分类路径 |
| confidence | number | 分类置信度 |
| quality_score | number | 质量分数 |
| content_type | string | 内容类型 (NEW) |
| dataset_source | string | 数据集来源 (NEW) |
| sentiment | string | 情感标签 (NEW) |
| sentiment_label | integer | 情感标签值 (NEW) |
| question | string | 问题 (NEW) |
| answer | string | 答案 (NEW) |
| choices | string | 选项 (NEW) |
| similarity | string | 相似度 (NEW) |
| language | string | 语言 (NEW) |
| is_valid | boolean | 是否有效 |
| is_spam | boolean | 是否垃圾 |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2025-02-26 | 初始 API 设计 |
| v1.1 | 2026-02-26 | 添加 Hugging Face 数据集支持 |

---

## 相关文档

- [数据库设计文档](database_schema.md)
- [迁移策略文档](migration_strategy.md)
- [技术决策记录](adr.md)
