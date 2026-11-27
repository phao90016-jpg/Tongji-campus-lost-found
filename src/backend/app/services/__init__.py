"""应用层：用例编排、事务边界、状态机、脱敏。

v0.1 起的模块（按 docs/03-设计.md 拆分）：
- state_machine.py  状态迁移表与校验（构件 1）
- claims.py         认领申请 / 初审 / 终审 / 领取确认
- visibility.py     字段级可见性与脱敏
- audit.py          审计与状态日志
- notify.py         通知入队、投递和补扫
- images.py         图片压缩、遮蔽和签名地址
- items.py          发布 / 检索
- governance.py     举报 / 处置 / 信用分 / 申诉
- stats.py          统计口径
"""
