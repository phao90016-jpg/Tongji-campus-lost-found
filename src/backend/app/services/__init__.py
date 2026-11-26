"""应用层：用例编排、事务边界、状态机、脱敏。

v0.1 起的模块（对应 docs/04-设计/详细设计.md 的 6 个构件）：
- state_machine.py  状态迁移表与校验（构件 1）
- claims.py         认领申请 / 初审 / 终审事务（构件 2、3）
- visibility.py     字段级可见性与脱敏（构件 4）
- audit.py          审计与状态日志（构件 4）
- notify.py         通知入队、投递、降级、补扫（构件 5）
- images.py         图片压缩、遮蔽、预签名（构件 6）
- items.py          发布 / 检索
- governance.py     举报 / 处置 / 信用分 / 申诉
- stats.py          统计口径（概要设计 §6）
"""
