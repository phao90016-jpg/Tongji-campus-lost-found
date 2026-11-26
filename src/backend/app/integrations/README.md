# 外部系统适配器

对应 **ADR-0001**（分层架构 + 集成适配器）。这里的每个模块都定义一个**协议**（接口）与两套实现：
本地实现用于课程环境（可测试、可演示），生产实现用于真实对接。

## 为什么这么设计

立项阶段的可行性判定（见 [选题文稿](../../../../docs/00-立项/选题文稿.md) §15.1）结论是：
学校统一身份认证、对象存储、微信服务号**在课程环境里都无法真正实测**——认证需要应用登记与回调备案，
微信需要 `openid` 与模板审核，存储需要部署 MinIO。如果把这些调用直接写进业务代码，会出现两个问题：

1. 演示环境跑不通，业务代码无法测试，CI 只能红灯或跳过；
2. 换到真实环境要改多处，评审时说不清"哪部分是模拟的"。

因此把"契约"与"实现"分开：业务层只依赖协议，答辩时能明确回答"哪部分是模拟的"。

## 三个协议

| 协议 | 本地实现（默认） | 生产实现 | 配置项 |
|---|---|---|---|
| `AuthProvider` | `LocalAuthProvider`：按学工号直接建会话，`auth_source=local` | `SsoAuthProvider`：OAuth2 授权码换 token，解析学工号 | `AUTH_PROVIDER` |
| `ObjectStore` | `LocalDiskStore`：写 `var/objects/`，用 HMAC 签名做"预签名 URL" | `S3ObjectStore`：MinIO / 云 OSS 预签名 | `STORAGE_PROVIDER` |
| `Notifier` | `ConsoleNotifier`：打印到日志并写 `delivery_log` | `WechatNotifier` / `SmtpNotifier` | `NOTIFY_PROVIDER` |

## 硬约束

1. **适配器不写业务表。** 通知适配器只负责"发出去 + 返回结果"，投递记录由 `services/notify.py` 写，
   这样"降级链"与"幂等补扫"才能被单独测试（REQ-N-004）。
2. **本地实现必须与生产实现语义一致。** 本地通知也要返回成功/失败、也要有耗时，
   否则故障注入测试（关通道看降级）在本地跑不出真实行为。
3. **凭据只存引用。** `notify_channel.credential_ref` 存的是密钥管理里的键名，不存明文凭据。
4. **认证失败不泄露细节。** 统一返回 401，不在响应里区分"账号不存在"与"令牌无效"。

## 计划实现顺序

| 适配器 | 增量 | 说明 |
|---|---|---|
| `LocalAuthProvider` | v0.1 | 演示兜底；显式标记 `auth_source=local`，生产禁用 |
| `LocalDiskStore` | v0.1 | 图片遮蔽后的本地存储 + 签名 URL |
| `ConsoleNotifier` | v0.1 | 只落投递记录，便于演示"降级" |
| `SsoAuthProvider` | v0.1 末 | 拿到应用登记后接入 |
| `S3ObjectStore` | v0.2 | 部署环境用 |
| `WechatNotifier` / `SmtpNotifier` | v0.2 | 通知主通道与兜底 |
