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
| 幂等 | 同一领取人的重复交接确认返回原结果；通知投递按事件去重，审核决策等状态迁移按 §2.5 校验版本 |
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
| `CLAIM_ALREADY_EXISTS` | 409 | 本人仍有进行中申请，或已用完该物品的提交资格 |
| `PUBLICATION_ENDED` | 409 | 公示到期，停止受理新申请或重申 |
| `PICKUP_ARRANGEMENT_REQUIRED` | 409 | 领取安排尚未填写或已失效，提示保管方更新 |
| `EVIDENCE_CHANGED` | 409 | 招领的核验信息已更新；刷新信息并保留表单草稿 |
| `EVIDENCE_LOCKED` | 409 | 存在进行中申请，核验字段或直接关闭已锁定 |
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
| GET | `/api/v1/me/profile` | 个人资料页，返回本人手机号 | 本人 | REQ-F-003 |
| PATCH | `/api/v1/auth/me` | 编辑本人资料与手机号 | 本人 | REQ-F-003 |
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
| GET | `/api/v1/items` | 检索列表（见 §2.4；公开检索剔除到期招领） | 已登录 | REQ-F-009、REQ-F-010 |
| GET | `/api/v1/items/{id}` | 详情（含核验版本；到期旧链接仅显示结束摘要，关闭后的举报入口单独裁剪） | 已登录 | REQ-F-010 |
| PATCH | `/api/v1/items/{id}` | 编辑（仅本人，存在进行中申请时锁定核验字段） | 本人 | REQ-F-007 |
| POST | `/api/v1/items/{id}/close` | 下架 / 关闭（存在进行中申请时 409） | 本人 | REQ-F-007 |
| POST | `/api/v1/items/{id}/images` | 上传图片（base64；核验锁定时禁止替换或新增） | 本人 | REQ-F-006 |
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
| 私人手机号 | 脱敏或省略 | 物品详情脱敏；个人资料页可读本人号码 | 脱敏或省略 | 仅通过已授权的单案读取并审计 |
| 图片 | 仅 masked URL | 两者 | 两者 | 两者 |
| 核验问题 | 只有问题文本 | 只有问题文本 | 问题 + 答案 | 问题 + 答案 |
| 认领申请列表 | ✗ | 仅自己的 | 该条全部 | 该条全部 |

旧链接到达收件截止后，公共详情只返回结束摘要及 `can_apply=false`，已有申请通过按归属授权的申请详情继续办理。列表、相似推荐和普通详情使用同一截止判断。

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
| POST | `/api/v1/items/{id}/claims` | 提交或限一次重申，携带 `evidence_revision`；重申提供 `previous_claim_id` 和说明 | 学生 | REQ-F-013、REQ-F-014 |
| GET | `/api/v1/claims` | `role=applicant` 我提交的 / `role=owner` 我收到的 | 已登录 | REQ-F-015 |
| GET | `/api/v1/claims/{id}` | 申请详情、补交截止、等待环节、领取安排与交接进度 | 按归属 / 有权限的审核员 | REQ-F-014～018 |
| POST | `/api/v1/claims/{id}/withdraw` | 撤回待初审、待补充或待终审申请 | 申请人 | REQ-F-014 |
| POST | `/api/v1/claims/{id}/first-review` | 建议通过／驳回或请求补交 | 招领发布人 | REQ-F-015 |
| POST | `/api/v1/claims/{id}/final-review` | 通过／驳回或请求补交 | 有权限的审核员 | REQ-F-016 |
| POST | `/api/v1/claims/{id}/supplement` | 提交一次补充材料 | 申请人 | REQ-F-015、REQ-F-016、REQ-F-018 |
| POST | `/api/v1/claims/{id}/handover` | 确认已领取；无请求体，重复提交返回同一结果 | 获准领取人 | REQ-F-017 |
| PATCH | `/api/v1/claims/{id}/pickup-arrangement` | 更新本案领取点、日期、可领时段与公用服务点；校验版本 | 记录中的保管方 | REQ-F-017、REQ-F-018 |
| POST | `/api/v1/claims/{id}/follow-up` | 催办或登记获授权案件的跟进结果 | 分派到该案的志愿者／值班老师 | REQ-F-024 |
| POST | `/api/v1/admin/claims/{id}/contact-read` | 按单案读取一位参与方手机号，须填目标人及业务原因并写审计 | 有该案授权且具备 `pii:read` 的老师 | REQ-F-003、REQ-N-003 |
| POST | `/api/v1/claims/{id}/take-over` | 登记未取得初审原因、指派终审老师，将待初审转待终审 | 值班老师 | REQ-F-016、REQ-F-024 |
| POST | `/api/v1/claims/{id}/close-unfulfilled` | 逾期核实未交付后结束认领，必填说明 | 有权限的审核员 | REQ-F-017 |
| POST | `/api/v1/claims/{id}/close-for-correction` | 根据发布人所报核验错误结束在审申请，必填说明；待领取另走未交付核实 | 有权限的审核员 | REQ-F-007 |

编辑与提交在同一物品事务内校验。服务端受理时间达到首次公示后 60 个自然日，新的申请或重申返回 `409 PUBLICATION_ENDED`，不受定时任务是否已更新状态影响。核验版本不匹配返回 `409 EVIDENCE_CHANGED`。已受理的申请继续使用已保存的证据。

**跟进和接手**

跟进只记催办及附件以外的业务摘要，和申请主状态分开存放。志愿者只读本人分派案件的脱敏摘要，不能改变申请结论。接手请求含 `version`、`reason` 与指定老师；仅仍待初审且达到 48 小时跟进门槛时可入终审。和原初审提交竞争状态、版本，失败一方返回 409 并刷新。

**领取安排**

保管方用 `PATCH` 保存本案安排，字段为 `location`、`pickup_from`、`pickup_until`、`service_point_id`、`version`。日期由起止时间表达，公用联系值来自已核实的服务点配置，备注不接受私人联系方式。老师批准前校验安排仍有效，缺失或过期返回 `409 PICKUP_ARRANGEMENT_REQUIRED`。通过后双方读取同一份最新 `pickup_arrangement`，含 `updated_at`；改期按新版本通知。

**提交申请**

```json
{
  "reason": "上午在图书馆自习时丢失",
  "answers": [{"question_id": 7, "answer": "透明蓝色"}],
  "materials": "已提交的购买凭证引用",
  "expected_handover_at": "2026-11-27T10:00:00+08:00",
  "evidence_revision": 3
}
```

**审核和补交**

初审 `decision` 为 `suggest_approve | suggest_reject | request_more`，终审为 `approve | reject | request_more`。提交时带当前 `version` 及 `comment`。两种初审建议都转 `pending_final`。要求补交时 `comment` 须说明缺项，响应和详情返回 `supplement_deadline_at`。补交请求携带 `materials`，截止前成功时回到原审核环节。补交超时、状态已变更或未获补交机会返回 409。

**终审通过与交接确认**

- 终审通过返回申请状态 `approved`、发布状态 `claiming` 及 `handover_reminder_at`（通过后第 72 小时）。详情根据归属返回 `pickup_arrangement`、`can_confirm_handover` 与 `handover_overdue`。
- 领取确认首次成功和同一领取人后续重试均返回 200，含申请号、物品号、`completed`、`handed_over`、`confirmed_by` 和原 `confirmed_at`。先校验身份归属，无权确认返回 403，申请已失效等状态返回 409。
- 申请人从详情可见当前状态、补交截止、剩余重申资格及交接安排。无关用户不会看到申请人身份或材料。

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

v0.2 允许对已交接或已关闭的招领索引提交 `impersonation`。以交接确认时间起算 30 天，使用原招领链接或编号定位，旧链接只返回必要的招领摘要和是否可举报；举报记录关联同一发布且保留原交接状态。窗口结束时提示经招领处确认的线下渠道。

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
| GET | `/api/v1/admin/workbench/queue` | v0.1 可查待终审及需跟进；v0.2 添加完整队列和累计耗时标色 | 值班老师；志愿者限本人分派待办摘要 | REQ-F-024 |

跟进记录包含当前待办原因、等待环节、责任人、进入待办的时间和最新跟进结果。私密核验材料、手机号和申请人历史不出现在志愿者响应。

统计按 [SRS §5.1](../02-需求规约/SRS-v1.0.md) 的同批口径，返回各指标成熟状态、分母和剔除数。未成熟或暂无样本时比率为 `null`，通过 `review_sla_state` 区分。

看板响应示例（已成熟的提交批次）：

```json
{
  "period": "month",
  "published": 486, "claims": 298, "completed": 182,
  "claim_success_rate": 0.611,
  "median_user_wait_hours": 17.4,
  "median_review_hours": 11.4,
  "review_sla_state": {"within_24h": "ready", "overdue_48h": "ready"},
  "review_sla_population": {"within_24h": 290, "overdue_48h": 292},
  "review_sla_excluded": {"within_24h": 8, "overdue_48h": 6},
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
