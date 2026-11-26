# 后端（FastAPI）

## 目录

```
app/
├── main.py         # 应用入口（骨架期仅健康检查与元数据）
├── core/           # 配置、数据库连接、调度、日志
├── api/            # 路由层：参数校验、鉴权依赖、错误码映射
├── schemas/        # Pydantic 出入参模型
├── models/         # 领域模型：状态枚举、能力表、规则函数
├── services/       # 应用层：用例编排、事务边界、状态机、脱敏
└── integrations/   # 外部系统适配器（认证 / 存储 / 通知），见其 README
tests/              # pytest 单元与集成测试
```

## 分层约定（评审会查）

| 层 | 只做 | 不做 |
|---|---|---|
| `api` | 参数校验、鉴权依赖、错误码映射 | 业务规则、开事务、拼 SQL |
| `services` | 用例编排、事务边界、状态机、脱敏 | HTTP 参数校验 |
| `models` | 状态枚举、能力判定、领域规则函数 | 依赖 FastAPI、访问网络 |
| `integrations` | 外部系统调用 | 写库 |
| `core` | 连接、配置、调度 | 业务判断 |

**三条硬约束**（来自 [SRS](../../docs/02-需求规约/SRS-v1.0.md) §2.3）：

1. 状态迁移只能经 `services`，禁止直接 `UPDATE status`
2. 手机号/证件号一律在序列化层脱敏，业务代码不得各自拼接
3. 图片访问一律走预签名 URL，有效期 ≤10 分钟

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # 填写配置；.env 不提交
pytest -q
uvicorn app.main:app --reload      # http://localhost:8000/health
```

## 质量门禁

- `ruff check .` 无告警
- `pytest -q` 全绿
- 核心模块覆盖率 ≥80%（`services`：状态机、终审事务、领取确认、脱敏、通知投递）

## 骨架期包含什么

| 文件 | 内容 |
|---|---|
| `app/main.py` | 应用实例、`/health`、`/api/v1/meta`（骨架占位） |
| `app/core/config.py` | 从环境变量读配置，密钥不落代码 |
| `tests/test_health.py` | 冒烟测试，保证 CI 绿灯 |

> 其余目录只有 `__init__.py` 与分层说明，**没有业务代码**——自 v0.1 起按 Issue 逐个交付。
