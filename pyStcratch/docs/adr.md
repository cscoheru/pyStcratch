# 技术决策记录 (Architecture Decision Records)

## 概述

本文档记录爬虫数据管理系统的关键技术决策及其理由。

---

## 决策记录

| # | 决策点 | 选择 | 状态 | 日期 |
|---|--------|------|------|------|
| ADR-001 | Streamlit 数据访问方式 | 直接数据库访问 | ✅ 已采纳 | 2026-02-26 |
| ADR-002 | DatasetMetadata 表实现时机 | P3 阶段实现 | ✅ 已采纳 | 2026-02-26 |
| ADR-003 | 数据集同步策略 | 手动触发 + 定时任务 | ✅ 已采纳 | 2026-02-26 |
| ADR-004 | 情感标签存储方式 | 同时存储英文和数字 | ✅ 已采纳 | 2026-02-26 |
| ADR-005 | QA 内容存储方式 | 分开 question 和 answer 字段 | ✅ 已采纳 | 2026-02-26 |
| ADR-006 | 数据库选择 | SQLite (开发) / PostgreSQL (生产可选) | ✅ 已采纳 | 2026-02-26 |
| ADR-007 | API 响应格式 | 统一的 success/data/error 结构 | ✅ 已采纳 | 2026-02-26 |

---

## ADR-001: Streamlit 数据访问方式

### 上下文

Streamlit 前端需要访问数据库，可以选择：
- 直接数据库访问
- 通过 Flask API 访问

### 决策

**选择直接数据库访问**

### 理由

| 因素 | 直接访问 | API 访问 |
|------|---------|---------|
| 性能 | 更快，无网络开销 | 有网络延迟 |
| 简化 | 无需额外 API 层 | 需要维护 API |
| 可维护性 | 代码更直接 | 增加维护复杂度 |
| 部署 | 同服务器部署 | 优势明显 |

### 权衡

- **优势**:
  - 减少网络开销
  - 简化开发流程
  - 更容易调试

- **劣势**:
  - 耦合度较高（前端和数据库直接绑定）
  - 难以分离前后端部署

### 结论

由于 Streamlit 和 Flask 在同一服务器部署，直接访问数据库可以提升性能并简化开发。

---

## ADR-002: DatasetMetadata 表实现时机

### 上下文

DatasetMetadata 表用于存储数据集的元信息，包括数据集描述、更新时间等。需要决定是在 P1 还是 P3 阶段实现。

### 决策

**选择 P3 阶段实现**

### 理由

1. **优先级**: 核心功能（数据爬取、分类、导出）优先
2. **依赖**: DatasetMetadata 是优化功能，不影响核心流程
3. **复杂度**: 实现复杂度较高，需要额外维护
4. **价值**: 数据集元信息可以通过其他方式获取

### 权衡

- **优势**: 聚焦核心功能，快速交付
- **劣势**: 暂时缺少数据集元数据管理

### 结论

第一阶段专注核心功能，DatasetMetadata 留待 P3 阶段实现。

---

## ADR-003: 数据集同步策略

### 上下文

Hugging Face 数据集可以：
- 手动触发同步
- 定时自动同步
- 实时同步

### 决策

**选择手动触发 + 定时任务（可选）**

### 理由

1. **资源控制**: 避免过度消耗资源
2. **灵活性**: 用户可按需同步
3. **可监控**: 每次同步都有明确记录

### 实现方式

```python
# 手动触发
POST /api/datasets/{name}/sync

# 定时任务（可选）
# scheduler/jobs.py 中添加定时同步任务
@scheduler.scheduled_job('cron', hour='2', minute='0')
def sync_datasets_job():
    # 每天凌晨2点同步
    pass
```

### 结论

手动触发为主，定时任务作为可选配置。

---

## ADR-004: 情感标签存储方式

### 上下文

情感分析结果可以存储为：
- 仅英文标签 (positive/neutral/negative)
- 仅数字标签 (0/1/-1)
- 同时存储英文和数字

### 决策

**同时存储英文和数字标签**

### 理由

1. **可读性**: 英文标签直观易懂
2. **保留精度**: 数字标签保留原始模型输出
3. **灵活性**: 支持不同使用场景

### 数据结构

```python
class Article(Base):
    sentiment = Column(String(20))  # 'positive', 'neutral', 'negative'
    sentiment_label = Column(Integer)  # 1, 0, -1
```

### 使用场景

```python
# 展示给用户
display_sentiment = article.sentiment  # 'positive'

# 机器学习
ml_feature = article.sentiment_label  # 1
```

### 结论

同时存储英文和数字，兼顾可读性和精度。

---

## ADR-005: QA 内容存储方式

### 上下文

问答对内容可以：
- 存储为单个 content 字段
- 分开存储 question 和 answer 字段

### 决策

**分开存储 question 和 answer 字段**

### 理由

1. **查询**: 便于单独查询问题或答案
2. **展示**: 前端可以灵活展示
3. **搜索**: 支持问题/答案分别搜索

### 数据结构

```python
class Article(Base):
    content = Column(Text)  # 完整内容（兼容旧字段）
    question = Column(Text)   # 问题部分
    answer = Column(Text)     # 答案部分
```

### 前端展示

```python
# QA 类型
if article.content_type == 'qa':
    display_question(article.question)
    display_answer(article.answer)
# 普通文章
else:
    display_content(article.content)
```

### 结论

分开存储，提升数据可用性。

---

## ADR-006: 数据库选择

### 上下文

需要选择开发环境和生产环境的数据库：
- SQLite
- PostgreSQL
- MySQL

### 决策

**开发环境: SQLite，生产环境: PostgreSQL (可选)**

### 理由

| 环境 | 选择 | 理由 |
|------|------|------|
| 开发 | SQLite | 零配置，文件数据库，易于调试 |
| 生产 | PostgreSQL | 可选，适合大规模部署 |
| 备选 | MySQL | 兼容性好，但需额外配置 |

### 技术栈

```python
# 开发环境
DATABASE_URL = "sqlite:///data/crawler.db"

# 生产环境 (可选)
DATABASE_URL = "postgresql://user:pass@host/dbname"
```

### 结论

开发使用 SQLite 简化开发，生产可按需选择 PostgreSQL。

---

## ADR-007: API 响应格式

### 上下文

API 响应格式需要统一，便于前端处理。

### 决策

**统一的 success/data/error 结构**

### 响应格式

```json
// 成功
{
    "success": true,
    "data": { /* 数据 */ }
}

// 失败
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "错误描述"
    }
}
```

### 理由

1. **一致性**: 所有端点格式统一
2. **类型安全**: 前端可以准确判断
3. **调试**: success 标识明确
4. **扩展性**: 易于添加元数据

### 错误码规范

| 错误码 | 模块 | 说明 |
|--------|------|------|
| 1000-1099 | 通用 | 服务器错误 |
| 2000-2099 | 数据库 | 数据库操作错误 |
| 3000-3099 | 爬虫 | 爬虫执行错误 |
| 4000-4099 | 分类 | 分类服务错误 |
| 5000-5099 | 导出 | 数据导出错误 |
| 6000-6099 | 集成 | 第三方集成错误 |

### 结论

统一的 API 响应格式提升前端开发体验。

---

## 决策状态说明

| 状态 | 说明 |
|------|------|
| ✅ 已采纳 | 决策已确认并在实施中 |
| 🔄 待审核 | 决策提出但未最终确认 |
| ❌ 已废弃 | 决策曾被采纳但后来被替换 |

---

## 相关文档

- [数据库设计文档](database_schema.md)
- [API �参考文档](api_reference.md)
- [迁移策略文档](migration_strategy.md)
