"""应用入口（骨架）。

当前只提供健康检查与元数据占位，用于验证 CI 与部署链路；
业务接口自 v0.1 起按 Issue 逐个增量加入（见 docs/04-设计/API契约.md）。

分层约定：
- 接口层 app/api        只做参数校验、鉴权、错误码映射
- 应用层 app/services   用例编排、事务边界、状态机、脱敏
- 领域层 app/models     状态枚举、能力判定、领域规则
- 集成层 app/integrations 认证 / 存储 / 通知适配器
"""

from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="校园失物招领与认领审核系统 API",
    version="0.0.0",
    description=(
        "骨架阶段：仅健康检查与元数据占位。"
        "业务接口自 v0.1 起增量交付，契约见 docs/04-设计/API契约.md。"
    ),
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """存活探针，供 CI 冒烟与部署健康检查使用。"""
    return {"status": "ok"}


@app.get("/api/v1/meta", tags=["system"])
def meta() -> dict[str, object]:
    """前端初始化用的元数据占位。

    v0.1 起由 services 从 category / location / system_config 表读取并返回，
    同时给出状态枚举的中文映射（见 docs/04-设计/数据库设计.md §3）。
    """
    return {
        "app": "campus-lost-found",
        "version": app.version,
        "env": settings.app_env,
        "status": "skeleton",
        "note": "分类、地点、状态中文映射、驳回原因码将在 v0.1 由数据库提供",
    }
