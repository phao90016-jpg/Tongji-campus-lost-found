# 脚本

用于文档生成、图渲染、链接检查与（后续）造数压测。**不属于业务代码**。

| 脚本 | 用途 | 依赖 | 对应交付物 |
|---|---|---|---|
| `md2docx.py` | Markdown → docx，保证 md 与 docx 单一内容源 | python-docx | 选题文稿等需提交 Word 的文档 |
| `render_models.py` | 批量渲染 `models/**/*.puml` 到 `docs/assets/` | java + plantuml.jar | 用例图 / 类图 / 状态图 / 顺序图 |
| `check_links.py` | 检查 Markdown 相对链接与图片引用 | 无（标准库） | CI 的 docs 任务 |

## 首次使用

```bash
pip install python-docx            # md2docx 需要

# 图渲染需要 java 与 plantuml.jar（约 22MB，不入库）
mkdir -p scripts/tools
# 下载 https://github.com/plantuml/plantuml/releases/latest 的 plantuml.jar 放到 scripts/tools/
# 或设置 PLANTUML_JAR 指向已有 jar
python scripts/render_models.py
```

## 约定

- 脚本必须可重复执行，不污染真实数据
- 生成的 docx / PNG 一并提交（评审时无需装工具也能看）
- 结论写进对应文档：图 → `docs/03-需求分析模型/`，测试数据 → `docs/05-测试/测试报告.md`

## 待补（v0.1 起）

| 脚本（计划） | 用途 | 对应需求 |
|---|---|---|
| `seed_items.py` | 造 1 万条发布数据，测检索性能 | REQ-N-001 |
| `concurrent_claim.py` | 多线程并发提交同一招领，验证互斥 | REQ-N-002 |
| `bench_search.py` | 连续 20 次计时取 P95 | REQ-N-001 |
| `export_fixtures.py` | 导出演示用固定数据集（答辩可复现） | — |
