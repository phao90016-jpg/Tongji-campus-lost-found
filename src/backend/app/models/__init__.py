"""领域模型：状态枚举、能力表、领域规则函数。不依赖 FastAPI，不访问网络。

v0.1 起的模块：
- enums.py         ItemStatus / ClaimStatus / ReportStatus / CertStatus
- capabilities.py  能力码与角色→能力映射（见概要设计 §4.1）
- rules.py         信用分阈值、状态迁移表、可认领判定
"""
