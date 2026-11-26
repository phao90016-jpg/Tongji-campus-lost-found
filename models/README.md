# 模型源文件

所有图的源文件放这里，**一图一 PR**。文档中引用渲染后的图，不贴截图。

## 目录

| 目录 | 内容 | 格式 |
|---|---|---|
| `usecase/` | 用例图（参与者边界图 + 分增量主链路） | PlantUML `.puml` |
| `class/` | 领域类图 | PlantUML `.puml` |
| `state/` | 状态图 | PlantUML `.puml`（文档内另用 Mermaid 便于 GitHub 直接渲染） |
| `sequence/` | 顺序图、活动图 | PlantUML `.puml` |

## 文件清单

| 文件 | 内容 | 对应文档 |
|---|---|---|
| `usecase/usecase-actors.puml` | 参与者与系统边界 | [用例图](../docs/03-需求分析模型/用例图.md) §3.1 |
| `usecase/usecase-v01.puml` | v0.1 主链路（发布→检索→认领→审核→交接） | 同上 §3.2 |
| `usecase/usecase-v02.puml` | v0.2 主链路（举报/通知/统计/权限） | 同上 §3.3 |
| `usecase/usecase-v03.puml` | v0.3 主链路（匹配与开放能力） | 同上 §3.4 |
| `class/domain.puml` | 领域类图（29 个分析类） | [类图与CRC](../docs/03-需求分析模型/类图与CRC.md) §2 |
| `state/item-state.puml` | 发布状态图 | [状态图与顺序图](../docs/03-需求分析模型/状态图与顺序图.md) §1.1 |
| `state/claim-state.puml` | 认领申请状态图 | 同上 §1.2 |
| `sequence/sd01-submit-claim.puml` | 提交认领申请（含并发冲突） | 同上 §2 |
| `sequence/sd02-final-review.puml` | 终审通过（事务 + 交接码） | 同上 §2.1 |
| `sequence/sd03-handover.puml` | 交接码核销 | 同上 §2 |
| `sequence/sd04-notify-fallback.puml` | 通知投递与降级 | 同上 §2.2 |
| `sequence/act-uc06-publish-found.puml` | 活动图：发布招领 | [SRS](../docs/02-需求规约/SRS-v1.0.md) §4.1 |
| `sequence/act-uc15-submit-claim.puml` | 活动图：提交认领 | 同上 §4.2 |
| `sequence/act-uc18-final-review.puml` | 活动图：终审 | 同上 §4.3 |
| `sequence/act-uc19-handover.puml` | 活动图：交接核销 | 同上 §4.4 |

## 渲染

```bash
# 单张
java -jar scripts/tools/plantuml.jar -tpng -charset UTF-8 models/usecase/usecase-v01.puml
# 全部（输出到 docs/assets/）
python scripts/render_models.py
```

> `scripts/tools/plantuml.jar` 不入库（22MB），首次使用按 [scripts/README.md](../scripts/README.md) 下载；
> 已渲染的 PNG 入库到 `docs/assets/`，保证评审时无需 Java 也能看图。

## 命名约定

```
<类型>-<编号>-<简述>.puml
例：usecase-v01.puml
    act-uc18-final-review.puml
    sd02-final-review.puml
```

## 为什么用源文件

- 可版本化、可 diff、可评审
- 改一个状态不用重画整张图
- 与"文档即代码"一致：图也是代码
- 渲染命令可复跑，评审时能当场验证"图是真的"

## 自查

- [x] 语法能渲染（CI 校验 `scripts/render_models.py --check`）
- [x] 与 SRS 编号一致（UC-、AC-、REQ-）
- [x] 与追溯矩阵对应
- [x] 图与文档文字描述一致（改图同步改文，反之亦然）
