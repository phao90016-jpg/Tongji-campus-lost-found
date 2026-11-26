#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 Markdown 相对链接与图片引用是否可解析（CI 用，不依赖第三方库）。

规则：
- 只检查本地相对链接（跳过 http(s)、mailto、锚点、纯 #）
- 支持 `<path with space>` 与 URL 编码（%20）
- 跳过代码块内的链接
- 退出码非 0 表示有断链

用法：
    python scripts/check_links.py
    python scripts/check_links.py --quiet
"""
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "var", "dist"}
LINK = re.compile(r"!?\[[^\]]*\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
FENCE = re.compile(r"^```")


def md_files() -> list[Path]:
    out = []
    for p in ROOT.rglob("*.md"):
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        out.append(p)
    return sorted(out)


def strip_code(text: str) -> str:
    """把 ``` 代码块内容替换为空行，避免误报。"""
    lines, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            lines.append("")
            continue
        lines.append("" if in_fence else line)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    broken, checked = [], 0
    for md in md_files():
        text = strip_code(md.read_text(encoding="utf-8", errors="replace"))
        for m in LINK.finditer(text):
            raw = m.group(1).strip()
            if raw.startswith("<") and raw.endswith(">"):
                raw = raw[1:-1]
            if raw.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = raw.split("#", 1)[0]
            if not target:
                continue
            checked += 1
            path = (md.parent / unquote(target)).resolve()
            if not path.exists():
                broken.append((md.relative_to(ROOT).as_posix(), raw))

    if not a.quiet:
        for f, link in broken:
            print(f"✗ {f} → {link}")
        print(f"\n检查 {len(md_files())} 个 Markdown，{checked} 条相对链接，断链 {len(broken)} 条")
    return 0 if not broken else 1


if __name__ == "__main__":
    sys.exit(main())
