#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""立项阶段技术可行性探测（可复跑，只依赖标准库 + 可选 Pillow）。

回答四个"设计假设到底成不成立"的问题：

  P1  SQLite 是否支持 FTS5，中文能否被检索到，性能是否够（REQ-N-001）
  P2  部分唯一索引能否在并发下保证"同一招领只有一条进行中申请"（REQ-N-002 / ADR-0002）
  P3  图片遮蔽（高斯模糊 + 压缩）的耗时与体积是否可接受（REQ-F-006 / REQ-N-006）
  P4  PlantUML 渲染链路是否可用（文档里的图能不能自己生成）

诚实原则：本脚本只测**本机可验证**的东西。学校统一身份认证、微信服务号、对象存储
需要授权与部署环境，本脚本**不测**，报告中写"未实测"。

用法：
    python probe/probe_feasibility.py            # 人读表格
    python probe/probe_feasibility.py --json     # 机器可读，写入 probe/probe_result.json
"""
import argparse
import hashlib
import json
import os
import random
import shutil
import sqlite3
import statistics
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULT = ROOT / "probe" / "probe_result.json"

WORDS = ["校园卡", "耳机", "水杯", "钥匙", "雨伞", "充电宝", "身份证", "书包", "眼镜", "手表"]
PLACES = ["图书馆", "三教", "食堂", "体育馆", "宿舍楼", "实验楼"]
COLORS = ["黑色", "蓝色", "白色", "透明", "灰色"]


# --------------------------------------------------------------------------- P1
def cjk_tokenize(text: str) -> str:
    """把中文按字拆开、ASCII 词整体保留，供 FTS5 unicode61 做短语匹配。"""
    out, buf = [], []
    for ch in text:
        if ch.isascii() and ch.isalnum():
            buf.append(ch)
            continue
        if buf:
            out.append("".join(buf))
            buf = []
        if "\u4e00" <= ch <= "\u9fff":
            out.append(ch)
        elif ch.strip():
            out.append(ch)
    if buf:
        out.append("".join(buf))
    return " ".join(out)


def probe_fts(rows: int = 10000) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="probe-fts-"))
    db = tmp / "fts.db"
    info = {"rows": rows}
    try:
        conn = sqlite3.connect(db)
        info["sqlite_version"] = sqlite3.sqlite_version
        try:
            conn.execute("CREATE VIRTUAL TABLE t_probe USING fts5(x, tokenize='unicode61')")
            info["fts5"] = True
        except sqlite3.OperationalError as exc:
            info["fts5"] = False
            info["fts5_error"] = str(exc)
            return info

        conn.executescript(
            """
            CREATE TABLE item (id INTEGER PRIMARY KEY, title TEXT, description TEXT, marks TEXT,
                               category_id INTEGER, location_id INTEGER, status TEXT, happened_at TEXT);
            CREATE VIRTUAL TABLE item_fts USING fts5(
                search_text, content='', tokenize='unicode61'
            );
            CREATE INDEX idx_item_list ON item(status, happened_at DESC);
            CREATE INDEX idx_item_cat ON item(category_id, status);
            """
        )

        rnd = random.Random(20261126)
        payload = []
        for i in range(rows):
            title = f"{rnd.choice(PLACES)}{rnd.choice(['捡到', '丢失'])}{rnd.choice(WORDS)}一件"
            desc = f"{rnd.choice(COLORS)}色，{rnd.choice(['有贴纸', '无标记', '有划痕', '全新'])}，编号{i:05d}"
            marks = rnd.choice(["贴纸", "刻字", "挂件", "无"])
            payload.append((
                title, desc, marks,
                rnd.randint(1, 6), rnd.randint(1, 20), "published",
                f"2026-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}T10:00:00Z",
                cjk_tokenize(f"{title} {desc} {marks}"),
            ))
        conn.executemany(
            "INSERT INTO item(title, description, marks, category_id, location_id, status, happened_at) "
            "VALUES (?,?,?,?,?,?,?)",
            [p[:7] for p in payload],
        )
        conn.executemany(
            "INSERT INTO item_fts(rowid, search_text) VALUES (?, ?)",
            [(i + 1, p[7]) for i, p in enumerate(payload)],
        )
        conn.commit()
        info["indexed"] = conn.execute("SELECT count(*) FROM item_fts").fetchone()[0]

        # 中文短语检索：拆字后做短语匹配，等价子串匹配
        def fts_query(q: str) -> int:
            phrase = '"' + cjk_tokenize(q) + '"'
            return conn.execute(
                "SELECT count(*) FROM item_fts WHERE item_fts MATCH ?", (phrase,)
            ).fetchone()[0]

        def like_query(q: str) -> int:
            return conn.execute(
                "SELECT count(*) FROM item WHERE title LIKE ? OR description LIKE ? OR marks LIKE ?",
                (f"%{q}%", f"%{q}%", f"%{q}%"),
            ).fetchone()[0]

        for q in ["校园卡", "图书馆", "耳机"]:
            info[f"hit_{q}_fts"] = fts_query(q)
            info[f"hit_{q}_like"] = like_query(q)

        # 计时：各 20 次取 P95
        def timed(fn, q, n=20):
            ts = []
            for _ in range(n):
                t0 = time.perf_counter()
                fn(q)
                ts.append((time.perf_counter() - t0) * 1000)
            return round(statistics.quantiles(ts, n=20)[-1], 2) if n >= 20 else round(max(ts), 2)

        info["fts_p95_ms"] = timed(fts_query, "校园卡")
        info["like_p95_ms"] = timed(like_query, "校园卡")
        info["list_query_p95_ms"] = timed(
            lambda _q: conn.execute(
                "SELECT id FROM item WHERE status='published' ORDER BY happened_at DESC LIMIT 20"
            ).fetchall(), None
        )
        conn.close()
        return info
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- P2
def probe_concurrency(threads: int = 10) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="probe-cc-"))
    db = tmp / "cc.db"
    info = {"threads": threads}
    try:
        conn = sqlite3.connect(db, isolation_level=None, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.executescript(
            """
            CREATE TABLE claim_application (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                applicant_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1
            );
            CREATE UNIQUE INDEX uq_claim_active ON claim_application(item_id)
              WHERE status IN ('pending_first','pending_final','need_more','approved');
            """
        )
        conn.execute(
            "INSERT INTO claim_application(item_id, applicant_id, status) VALUES (1, 999, 'rejected')"
        )

        barrier = threading.Barrier(threads)
        results = {"ok": 0, "conflict": 0, "other": 0}

        def worker(i: int) -> None:
            c = sqlite3.connect(db, isolation_level=None, timeout=10)
            c.execute("PRAGMA busy_timeout=5000")
            try:
                barrier.wait()
                c.execute("BEGIN IMMEDIATE")
                c.execute(
                    "INSERT INTO claim_application(item_id, applicant_id, status) VALUES (1, ?, 'pending_first')",
                    (i,),
                )
                c.execute("COMMIT")
                results["ok"] += 1
            except sqlite3.IntegrityError:
                results["conflict"] += 1
            except Exception:
                results["other"] += 1
            finally:
                c.close()

        ts = [threading.Thread(target=worker, args=(i,)) for i in range(threads)]
        t0 = time.perf_counter()
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        info["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        info.update(results)
        info["active_rows"] = conn.execute(
            "SELECT count(*) FROM claim_application WHERE status IN "
            "('pending_first','pending_final','need_more','approved')"
        ).fetchone()[0]
        info["partial_index_supported"] = True
        conn.close()
        return info
    except sqlite3.OperationalError as exc:
        info["partial_index_supported"] = False
        info["error"] = str(exc)
        return info
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- P3
def probe_image() -> dict:
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        return {"skipped": "未安装 Pillow（pip install pillow）"}
    tmp = Path(tempfile.mkdtemp(prefix="probe-img-"))
    try:
        # 造一张 3024x4032 的"证件照"（手机直出尺寸）
        img = Image.new("RGB", (3024, 4032), (238, 240, 243))
        src = tmp / "src.jpg"
        img.save(src, "JPEG", quality=92)
        t0 = time.perf_counter()
        with Image.open(src) as im:
            im = im.convert("RGB")
            im.thumbnail((1600, 1600))
            orig = tmp / "orig.jpg"
            im.save(orig, "JPEG", quality=85)
            masked = tmp / "masked.jpg"
            im.filter(ImageFilter.GaussianBlur(radius=8)).resize(
                (im.width // 2, im.height // 2)
            ).save(masked, "JPEG", quality=80)
        elapsed = (time.perf_counter() - t0) * 1000
        return {
            "source_kb": round(src.stat().st_size / 1024, 1),
            "original_kb": round(orig.stat().st_size / 1024, 1),
            "masked_kb": round(masked.stat().st_size / 1024, 1),
            "elapsed_ms": round(elapsed, 1),
            "note": "整图模糊（v0.1 策略），v0.3 改为 OCR 定位后局部模糊",
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- P4
def probe_plantuml() -> dict:
    jar = ROOT / "scripts" / "tools" / "plantuml.jar"
    return {
        "java": shutil.which("java") or "",
        "jar_exists": jar.exists(),
        "note": "jar 不入库；渲染产物已提交到 docs/assets/，评审无需 java",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    t0 = time.perf_counter()
    result = {
        "probed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "P1_fts5": probe_fts(),
        "P2_concurrency": probe_concurrency(),
        "P3_image_mask": probe_image(),
        "P4_plantuml": probe_plantuml(),
        "not_probed": [
            "学校统一身份认证（需应用登记与回调备案）",
            "微信服务号模板消息（需 openid、模板审核与额度）",
            "对象存储预签名 URL（需部署 MinIO 或云 OSS）",
            "1 万条真实业务数据的端到端检索（需 v0.1 后端）",
        ],
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }

    if a.json:
        RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入 {RESULT.relative_to(ROOT)}")
        return 0

    p1, p2, p3 = result["P1_fts5"], result["P2_concurrency"], result["P3_image_mask"]
    print(f"探测时间 {result['probed_at']}｜Python {result['python']}｜SQLite {p1.get('sqlite_version')}")
    print(f"\nP1 中文全文检索（{p1.get('rows')} 条）")
    print(f"  FTS5 可用            {p1.get('fts5')}")
    print(f"  索引条数             {p1.get('indexed')}")
    print(f"  命中 校园卡          FTS5 {p1.get('hit_校园卡_fts')} / LIKE {p1.get('hit_校园卡_like')}")
    print(f"  P95  FTS5 {p1.get('fts_p95_ms')} ms｜LIKE {p1.get('like_p95_ms')} ms｜列表 {p1.get('list_query_p95_ms')} ms")
    print("\nP2 并发互斥（部分唯一索引）")
    print(f"  部分索引支持          {p2.get('partial_index_supported')}")
    print(f"  {p2.get('threads')} 线程结果        成功 {p2.get('ok')}｜冲突 {p2.get('conflict')}｜其他 {p2.get('other')}")
    print(f"  进行中记录数          {p2.get('active_rows')}（应为 1）｜耗时 {p2.get('elapsed_ms')} ms")
    print("\nP3 图片遮蔽")
    if p3.get("skipped"):
        print(f"  跳过：{p3['skipped']}")
    else:
        print(f"  源图 {p3['source_kb']} KB → 原图 {p3['original_kb']} KB + 遮蔽图 {p3['masked_kb']} KB，耗时 {p3['elapsed_ms']} ms")
    print("\nP4 图渲染")
    print(f"  java {result['P4_plantuml']['java'] or '未找到'}｜jar {result['P4_plantuml']['jar_exists']}")
    print("\n未实测（需授权或部署环境）：")
    for item in result["not_probed"]:
        print(f"  - {item}")
    print(f"\n总耗时 {result['elapsed_s']}s。加 --json 写入 probe/probe_result.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
