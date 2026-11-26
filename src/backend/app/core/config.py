"""配置骨架：从环境变量读取，密钥不落代码。

对应《要求》5.1 原则五：护密与合规——密钥、真实学工号与手机号严禁进入提示词与仓库。
字段名小写，环境变量名大写（大小写不敏感），见 .env.example。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。所有外部集成都可切换实现，便于在无授权的课程环境里演示。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 运行环境
    app_env: str = "dev"
    database_url: str = "sqlite:///./var/app.db"

    # 会话
    secret_key: str = "dev-only-change-me"
    token_ttl_hours: int = 8

    # 认证适配器：local（演示兜底） / sso（学校统一身份认证）
    auth_provider: str = "local"
    sso_client_id: str = ""
    sso_client_secret: str = ""
    sso_redirect_uri: str = "http://localhost:8000/api/v1/auth/sso/callback"

    # 对象存储：local（本地磁盘） / s3（MinIO 或云 OSS）
    storage_provider: str = "local"
    storage_dir: str = "./var/objects"
    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # 通知：console / wechat / smtp
    notify_provider: str = "console"
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # 业务参数（也可在后台 system_config 中改）
    item_expire_days: int = 60
    handover_ttl_hours: int = 72
    claim_sla_hours: int = 24
    claim_overdue_hours: int = 48
    retention_days: int = 180


@lru_cache
def get_settings() -> Settings:
    """进程内单例，避免重复解析 .env。"""
    return Settings()
