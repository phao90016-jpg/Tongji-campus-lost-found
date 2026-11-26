#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量渲染 models/ 下的 PlantUML 源文件到 docs/assets/。

约定（见 CONTRIBUTING.md §8）：
- 源文件：models/<类型>/<名字>.puml
- 渲染产物：docs/assets/<名字>.png
- 一图一 PR；改了 .puml 必须同步重渲染并提交 PNG，避免图文不一致

依赖：java（17+）与 PlantUML jar。jar 不入库，放 scripts/tools/plantuml.jar，
或设置环境变量 PLANTUML_JAR 指向已有 jar。

用法：
    python scripts/render_models.py            # 渲染全部
    python scripts/render_models.py --check    # 只校验语法，不写文件（CI 用）
    python scripts/render_models.py models/usecase/usecase-v01.puml
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
OUT = ROOT / "docs" / "assets"
DEFAULT_JAR = ROOT / "scripts" / "tools" / "plantuml.jar"


def find_jar() -> Path | None:
    env = os.environ.get("PLANTUML_JAR")
    if env and Path(env).exists():
        return Path(env)
    if DEFAULT_JAR.exists():
        return DEFAULT_JAR
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="指定 .puml 文件；缺省渲染 models/ 下全部")
    ap.add_argument("--check", action="store_true", help="只校验语法（-syntax），不写文件")
    a = ap.parse_args()

    if shutil.which("java") is None:
        print("✗ 未找到 java。请安装 JDK 17+，或改用在线渲染后把 PNG 放进 docs/assets/。")
        return 2

    jar = find_jar()
    if jar is None:
        print(f"✗ 未找到 plantuml.jar。请放到 {DEFAULT_JAR.relative_to(ROOT)}，")
        print("  或设置环境变量 PLANTUML_JAR 指向已有 jar（下载地址 https://plantuml.com/download）。")
        return 2

    files = [Path(f) for f in a.files] if a.files else sorted(MODELS.rglob("*.puml"))
    if not files:
        print("✗ models/ 下没有 .puml 文件")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, []
    for f in files:
        if a.check:
            cmd = ["java", "-jar", str(jar), "-syntax", "-charset", "UTF-8", str(f)]
        else:
            cmd = [
                "java", "-jar", str(jar), "-tpng", "-charset", "UTF-8",
                "-o", str(OUT), str(f),
            ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        bad = proc.returncode != 0 or "ERROR" in (proc.stdout or "") + (proc.stderr or "")
        if bad:
            failed.append(f.name)
            print(f"✗ {f.name}\n{proc.stdout}\n{proc.stderr}")
        else:
            ok += 1
            print(f"✓ {f.relative_to(ROOT)}")

    print(f"\n完成：{ok} 成功，{len(failed)} 失败")
    if failed:
        print("失败清单：" + ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
