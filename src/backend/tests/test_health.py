"""骨架冒烟测试：保证 CI 从第一次提交起可运行。

业务测试自 v0.1 起按 Issue 交付，编号与 docs/05-测试/测试用例库.md 对齐
（例如 TC-UC15-01 提交认领申请、TC-NFR01-01 并发认领互斥）。
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_meta_is_skeleton() -> None:
    """骨架期 /api/v1/meta 只返回占位信息，v0.1 起改为读数据库。"""
    resp = client.get("/api/v1/meta")
    assert resp.status_code == 200
    body = resp.json()
    assert body["app"] == "campus-lost-found"
    assert body["status"] == "skeleton"
