"""路由层：参数校验、鉴权依赖、错误码映射。不写业务逻辑。

v0.1 起的路由模块（按 docs/04-设计/API契约.md）：
- auth.py        登录 / 会话 / 资料
- items.py       发布 / 检索 / 图片
- claims.py      申请 / 初审 / 终审 / 交接
- reports.py     举报 / 处置 / 申诉
- notify.py      站内消息 / 渠道
- stats.py       个人统计 / 看板
- admin.py       用户角色 / 基础数据 / 审计
"""
