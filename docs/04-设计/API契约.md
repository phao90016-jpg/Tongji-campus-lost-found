# API 契约

> 对应单元：4 设计建模｜检查点：第 6 次课（第 14 周）
> 负责人：架构 / 设计工程师｜状态：草稿，接口签字后方可编码
> 契约一旦签字定稿，变更须走 [变更流程](../02-需求规约/变更记录.md)。
> 机器可读版本：服务启动后 `GET /openapi.json`（FastAPI 自动生成），本文件是摘要与决策说明。

## 1. 通用约定

| 项 | 约定 |
|---|---|
| 基础路径 | `/api/v1` |
| 认证 | `Authorization: Bearer <token>`；token 为 `uid.exp.sig` 三段，服务端 HMAC 校验，有效期 8 小时 |
| 内容类型 | `application/json; charset=utf-8`（图片上传用 JSON + base64，见 §2.3） |
| 时间 | 请求与响应统一 UTC ISO8601（`2026-03-14T02:30:00Z`），前端转本地时区 |
| 分页 | 游标分页：`?cursor=<id>&limit=20`，响应含 `next_cursor`（为 `null` 表示到底）；**不用 OFFSET** |
| 错误格式 | `{"error": {"code": "CLAIM_CONFLICT", "message": "该物品已有认领在审核中", "details": {}}}` |
| 越权 | 统一 `403`，`code=FORBIDDEN`，**响应不体现资源是否存在** |
| 幂等 | 交接核销、通知投递、状态迁移为幂等操作；重复调用返回当前状态而非报错（交接码除外，见 §2.5） |
| 审计 | 标记 🔒 的接口写审计日志 |

### 1.1 错误码

| code | HTTP | 含义 |
|---|---|---|
| `UNAUTHORIZED` | 401 | 未登录或 token 过期 |
| `FORBIDDEN` | 403 | 无权限（不区分资源是否存在） |
| `NOT_FOUND` | 404 | 资源存在性可公开时使用 |
| `VALIDATION_ERROR` | 422 | 字段校验失败，`details.fields` 给出字段级原因 |
| `ITEM_STATE_INVALID` | 409 | 当前状态不允许该操作（状态机拒绝） |
| `CLAIM_CONFLICT` | 409 | 该物品已有进行中申请 / 申请已被处理 |
| `CLAIM_ALREADY_EXISTS` | 409 | 本人已对该物品提交过申请 |
| `HANDOVER_EXPIRED` | 410 | 交接码已过期 |
| `HANDOVER_CONSUMED` | 409 | 交接码已被核销 |
| `HANDOVER_LOCKED` | 423 | 连续输错 5 次，锁定 30 分钟 |
| `CREDIT_TOO_LOW` | 403 | 信用分不足，`details.min` 给出阈值 |
| `RATE_LIMITED` | 429 | 举报/订阅等超过次数限额 |
| `EXTERNAL_UNAVAILABLE` | 502 | 外部系统（存储/通知）不可用，可重试 |

## 2. 接口清单

### 2.1 系统与认证

| 方法 | 路径 | 说明 | 角色 | 需求 |
|---|---|---|---|---|
| GET | `/health` | 存活探针 | 匿名 | — |
| GET | `/api/v1/meta` | 分类、地点、状态中文映射、配置项（前端初始化用） | 匿名 | REQ-F-027 |
| POST | `/api/v1/auth/dev-login` | 演示登录（`auth_source=local`），生产禁用 | 匿名 | REQ-F-001 |
| GET | `/api/v1/auth/sso/login` | 跳转统一身份认证（未配置时返回 501） | 匿名 | REQ-F-001 |
| GET | `/api/v1/auth/sso/callback` | 授权回调，换 token 建会话 | 匿名 | REQ-F-001 |
| GET | `/api/v1/auth/me` | 当前用户 + 角色 + 能力 + 信用分 | 已登录 | REQ-F-001 |
| POST | `/api/v1/auth/logout` | 退出（token 加入吊销表） | 已登录 | REQ-F-001 |
| PATCH | `/api/v1/auth/me` | 改联系方式、可见性开关 | 已登录 | REQ-F-003 |
| DELETE | `/api/v1/auth/me` | 注销并删除个人数据 | 已登录 | REQ-F-003 🔒 |

`GET /auth/me` 响应示例：

```json
{
  "id": 2,
  "student_no": "2151234",
  "name": "李同学",
  "department": "计算机学院",
  "credit_score": 100,
  "roles": ["student", "finder"],
  "permissions": ["item:create", "item:create_found", "claim:create", "claim:review_first"],
  "contact_phone": "138****8000",
  "auth_source": "local"
}
```

### 2.2 拾取者认证

| 方法 | 路径 | 说明 | 角色 | 需求 |
|---|---|---|---|---|
| POST | `/api/v1/certifications` | 提交拾取者认证 | student | REQ-F-002 |
| GET | `/api/v1/certifications/mine` | 我的认证状态 | 已登录 | REQ-F-002 |
| GET | `/api/v1/admin/certifications` | 待审认证列表 | reviewer | REQ-F-002 |
| POST | `/api/v1/admin/certifications/{id}/review` | 认证审核 | reviewer | REQ-F-002 🔒 |

### 2.3 发布 items

| 方法 | 路径 | 说明 | 角色 | 需求 |
|---|---|---|---|---|
| POST | `/api/v1/items` | 发布失物或招领 | student / finder | REQ-F-004、REQ-F-005 |
| GET | `/api/v1/items` | 检索列表（见 §3 参数） | 已登录 | REQ-F-009、REQ-F-010 |
| GET | `/api/v1/items/{id}` | 详情（按角色裁剪字段） | 已登录 | REQ-F-010 |
| PATCH | `/api/v1/items/{id}` | 编辑（仅本人，`claiming` 后禁改特征） | 本人 | REQ-F-007 |
| POST | `/api/v1/items/{id}/close` | 下架 / 关闭 | 本人 | REQ-F-007 |
| POST | `/api/v1/items/{id}/images` | 上传图片（base64） | 本人 | REQ-F-006 |
| GET | `/api/v1/items/{id}/images/{image_id}/url` | 取预签名 URL（`variant=masked|original`） | 按角色 | REQ-F-006 🔒 |
| GET | `/api/v1/items/{id}/similar` | 相似物品 Top5 | 已登录 | REQ-F-011 |
| POST | `/api/v1/items/{id}/favorite` | 收藏 | 已登录 | REQ-F-025 |
| DELETE | `/api/v1/items/{id}/favorite` | 取消收藏 | 已登录 | REQ-F-025 |
| GET | `/api/v1/favorites` | 我的收藏 | 已登录 | REQ-F-025 |

**创建请求（招领）**

```json
{
  "kind": "found",
  "title": "图书馆三楼捡到校园卡一张",
  "description": "在靠窗自习桌捡到，卡面有猫咪贴纸。请回答核验问题后申请认领。",
  "category_id": 1,
  "location_id": 3,
  "happened_at": "2026-03-14T01:20:00Z",
  "color": "蓝色",
  "brand": "",
  "marks": "猫咪贴纸",
  "handover_location": "图书馆一楼服务台",
  "storage_note": "已交图书馆服务台代管",
  "verification_questions": [
    {"question": "卡套是什么颜色？", "answer": "透明蓝色"},
    {"question": "卡面右下角贴了什么？", "answer": "猫咪贴纸"}
  ]
}
```

**响应裁剪规则（按角色）**

| 字段 | 匿名/普通用户 | 本人 | 拾取者（该条发布人） | 审核员 |
|---|---|---|---|---|
| title / description / color / marks | ✓ | ✓ | ✓ | ✓ |
| owner 姓名 / 院系 | ✓ | ✓ | ✓ | ✓ |
| owner 手机号 | `138****8000` | 原文 | 原文 | 原文 |
| 图片 | 仅 masked URL | 两者 | 两者 | 两者 |
| 核验问题 | 只有问题文本 | 只有问题文本 | 问题 + 答案 | 问题 + 答案 |
| 认领申请列表 | ✗ | 仅自己的 | 该条全部 | 该条全部 |

**图片上传（base64）**

```json
{"filename": "card.jpg", "content_base64": "...", "content_type": "image/jpeg"}
```

> 选 JSON + base64 而不是 multipart：课程环境不需要额外依赖 `python-multipart`，
> 且测试里构造请求更简单。代价是体积膨胀 33%，由"单图 ≤2MB、单条 ≤5 张"约束兜住。

### 2.4 检索参数（`GET /items`）

| 参数 | 类型 | 说明 |
|---|---|---|
| `kind` | enum | `lost` / `found`，不传为全部 |
| `category_id` | int | 分类 |
| `location_id` | int | 地点（含下级楼栋时由服务端展开） |
| `status` | enum | 默认只返回 `published`；传 `all` 需 `admin` 能力 |
| `q` | string | 关键词，按字拆词后短语匹配 |
| `from` / `to` | ISO8601 | `happened_at` 区间 |
| `mine` | bool | 只看自己发布的（含草稿与已关闭） |
| `unclaimed` | bool | 只看还没被认领的（`published` 且无进行中申请） |
| `cursor` / `limit` | int | 游标分页，`limit` 默认 20、上限 50 |

响应：

```json
{
  "items": [{"id": 12, "kind": "found", "title": "...", "status": "published",
             "category": {"id": 1, "name": "证件卡类"},
             "location": {"id": 3, "campus": "四平路", "building": "图书馆", "floor": "3F"},
             "happened_at": "2026-03-14T01:20:00Z",
             "masked_image_url": "/api/v1/items/12/images/5/url?variant=masked&token=...",
             "owner": {"name": "王同学", "department": "计算机学院"},
             "has_active_claim": false}],
  "next_cursor": 12,
  "search_mode": "fts5"
}
```

### 2.5 认领 claims

| 方法 | 路径 | 说明 | 角色 | 需求 |
|---|---|---|---|---|
| POST | `/api/v1/items/{id}/claims` | 提交认领申请 | student | REQ-F-013 |
| GET | `/api/v1/claims` | `role=applicant` 我提交的 / `role=owner` 我收到的 | 已登录 | REQ-F-015 |
| GET | `/api/v1/claims/{id}` | 申请详情（含审核记录、交接码状态） | 相关方 / reviewer | REQ-F-015、REQ-F-016 |
| POST | `/api/v1/claims/{id}/withdraw` | 撤回 | 申请人 | REQ-F-014 |
| POST | `/api/v1/claims/{id}/first-review` | 初审 | 发布人（finder） | REQ-F-015 |
| POST | `/api/v1/claims/{id}/final-review` | 终审 | reviewer | REQ-F-016 🔒 |
| POST | `/api/v1/claims/{id}/handover` | 核销交接码 | 相关方 | REQ-F-017 |
| POST | `/api/v1/claims/{id}/handover/resend` | 重发交接码（≤2 次） | 相关方 | REQ-F-017 |

**提交申请**

```json
{
  "reason": "3 月 14 日上午在图书馆三楼自习时丢失",
  "answers": [{"question_id": 7, "answer": "透明蓝色"}],
  "materials": "购买记录截图：https://example.com/order.png",
  "expected_handover_at": "2026-03-15T10:00:00Z"
}
```

**初审 / 终审请求**

```json
{"decision": "suggest_approve", "reason_code": "answer_match", "comment": "核验问题答对，建议通过"}
{"decision": "approve", "reason_code": "verified", "comment": "材料充分，通过"}
```

`decision` 取值：初审 `suggest_approve | suggest_reject | request_more`；终审 `approve | reject | request_more`。
`reason_code` 取值见 `GET /api/v1/meta` 的 `reject_reasons`。

**终审通过响应（含交接码明文，仅此一次）**

```json
{
  "claim": {"id": 31, "status": "approved"},
  "handover": {"code": "K7F2Q9", "expires_at": "2026-03-17T08:00:00Z", "resend_count": 0},
  "rejected_others": [32, 33]
}
```

> 交接码明文只在创建时返回一次，之后只存哈希；重发会生成新码并作废旧码。

### 2.6 举报、处置与申诉

| 方法 | 路径 | 说明 | 角色 | 需求 |
|---|---|---|---|---|
| POST | `/api/v1/reports` | 提交举报 | 已登录 | REQ-F-020 |
| GET | `/api/v1/reports/mine` | 我提交的举报 | 已登录 | REQ-F-020 |
| GET | `/api/v1/admin/reports` | 举报队列 | reviewer | REQ-F-021 |
| POST | `/api/v1/admin/reports/{id}/dispose` | 处置 | reviewer | REQ-F-021 🔒 |
| POST | `/api/v1/appeals` | 提交申诉 | 被处置人 | REQ-F-022 |
| GET | `/api/v1/admin/appeals` | 申诉队列 | reviewer | REQ-F-022 |
| POST | `/api/v1/admin/appeals/{id}/review` | 复核（非原处置人） | reviewer | REQ-F-022 🔒 |

处置 `action`：`warning | unpublish | ban7 | ban_forever | dismiss`。
处置响应含信用分变动：`{"action": "warning", "credit": {"before": 100, "after": 90}}`。

### 2.7 通知

| 方法 | 路径 | 说明 | 角色 | 需求 |
|---|---|---|---|---|
| GET | `/api/v1/notifications` | 站内消息列表（`?unread=true`） | 已登录 | REQ-F-023 |
| POST | `/api/v1/notifications/{id}/read` | 标记已读 | 本人 | REQ-F-023 |
| GET | `/api/v1/notifications/channels` | 我的通道 | 已登录 | REQ-F-023 |
| POST | `/api/v1/notifications/channels` | 绑定通道（凭据只存引用） | 已登录 | REQ-F-023 |
| POST | `/api/v1/notifications/channels/test` | 发测试消息 | 已登录 | REQ-F-023 |
| POST | `/api/v1/admin/notifications/tick` | 手动触发投递扫描（演示用） | admin | REQ-N-004 |

### 2.8 统计

| 方法 | 路径 | 说明 | 角色 | 需求 |
|---|---|---|---|---|
| GET | `/api/v1/stats/me` | 我的发布数、申请数、通过率、信用分 | 已登录 | REQ-F-025 |
| GET | `/api/v1/admin/stats/overview` | 管理看板（`?period=week|month|all`） | reviewer / admin | REQ-F-025 |
| GET | `/api/v1/admin/stats/export` | 导出 CSV | admin | REQ-F-025 🔒 |
| GET | `/api/v1/admin/workbench/queue` | 审核工作台队列（含超时标记） | reviewer | REQ-F-024 |

看板响应示例：

```json
{
  "period": "month",
  "published": 486, "claims": 298, "completed": 182,
  "claim_success_rate": 0.611,
  "median_handle_hours": 11.4,
  "within_24h_rate": 0.93,
  "overdue_48h_rate": 0.04,
  "category_distribution": [{"name": "证件卡类", "count": 204}],
  "location_top": [{"name": "图书馆", "count": 97}],
  "report_dispose_rate": 0.88
}
```

### 2.9 后台

| 方法 | 路径 | 说明 | 角色 | 需求 |
|---|---|---|---|---|
| GET | `/api/v1/admin/users` | 用户列表（`?q=`） | admin | REQ-F-026 |
| PATCH | `/api/v1/admin/users/{id}/roles` | 授予 / 收回角色 | admin | REQ-F-026 🔒 |
| POST | `/api/v1/admin/users/{id}/credit` | 手工调整信用分（须填理由） | reviewer | REQ-F-021 🔒 |
| GET | `/api/v1/admin/categories` | 分类列表 | reviewer / admin | REQ-F-027 |
| POST | `/api/v1/admin/categories` | 新增分类 | admin | REQ-F-027 🔒 |
| PATCH | `/api/v1/admin/categories/{id}` | 改名 / 停用 | admin | REQ-F-027 🔒 |
| GET | `/api/v1/admin/locations` | 地点列表 | reviewer / admin | REQ-F-027 |
| POST | `/api/v1/admin/locations` | 新增地点 | admin | REQ-F-027 🔒 |
| GET | `/api/v1/admin/configs` | 配置项 | admin | REQ-F-027 |
| PUT | `/api/v1/admin/configs/{key}` | 修改配置 | admin | REQ-F-027 🔒 |
| GET | `/api/v1/admin/audit-logs` | 审计查询（`?action=&actor_id=`） | admin | REQ-F-026 |

## 3. 契约签字

| 项 | 内容 |
|---|---|
| 定稿版本 | v1.0 |
| 签字人 | 待填 |
| 日期 | 待填 |
| 变更记录 | 见 [变更记录](../02-需求规约/变更记录.md) |
| 与实现的一致性 | `pytest tests/test_api_contract.py` 逐条比对路径与状态码；新增接口先改本文档再写代码 |
