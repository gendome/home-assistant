# Gendome HACS 网页 OAuth 接入说明

本文档约定以下正式用户路径：

> HACS 安装 Gendome → 添加集成 → 跳转 Gendome 网页登录并同意授权 →
> 返回 Home Assistant → 自动加载设备

该路径使用 Gendome 内置的公共 OAuth 客户端以及 Authorization Code + PKCE，
不依赖 Nabu Casa Cloud Account Linking，也不要求用户创建或填写 Application
Credentials。

## 用户连接流程

1. 用户通过 HACS 安装 Gendome，重启 Home Assistant。
2. 用户打开“设置 → 设备与服务 → 添加集成 → Gendome”。
3. 集成使用固定公共客户端 `gendome_home_assistant` 创建随机 PKCE verifier，
   并跳转到 Gendome `/oauth/authorize`。
4. Gendome 网页完成账号登录并展示授权说明。用户选择“允许”或“拒绝”。
5. 同意后，Gendome 携带一次性 code 和原始 state 返回 Home Assistant；拒绝时
   返回 `error=access_denied` 和原始 state。
6. Home Assistant 使用 code、公共 client ID、redirect URI 和 PKCE verifier
   换取 access token 与 refresh token。
7. 集成调用 `/profile` 校验账号。校验成功后创建配置项，首次拉取设备状态，
   随后自动加载设备与实体。

正常流程不得显示 OAuth 实现选择页或 Client ID/Secret 输入框。授权页面只需明确
说明：

> Home Assistant 可以查看和控制当前 Gendome 账号下绑定的所有受支持设备。

当前版本不向普通用户展示细粒度 Scope 选择。

## OAuth 客户端要求

| 配置项 | 值 |
| --- | --- |
| Client ID | `gendome_home_assistant` |
| 客户端类型 | Public |
| Client Secret | 无 |
| 授权地址 | `https://oauth.gendome.cloud/oauth/authorize` |
| Token 地址 | `https://oauth.gendome.cloud/oauth/token` |
| Token 认证方式 | `none` |
| PKCE | 必须为 `S256` |
| 主回调地址 | `https://my.home-assistant.io/redirect/oauth` |

集成把 Home Assistant 的 `my` 组件声明为依赖，因此正式流程始终使用上表中的固定
HTTPS 回调。My Home Assistant 只负责把回调送回最初发起配置的实例，不保存
Gendome Client Secret；本方案的公共客户端本身也没有 Secret。

Home Assistant 请求以下 Scope：

```text
device:read statistics:read device:control:switch device:control:setting scheduled_charging:read scheduled_charging:write
```

授权服务必须：

- 对公共客户端禁用 client secret 和 HTTP Basic 客户端认证；
- 授权请求只接受 `code_challenge_method=S256`，并保存对应 challenge；
- 换码时校验 `code_verifier`，校验失败立即拒绝；
- 精确校验 client ID、redirect URI、state、response type 和 Scope；
- 授权 code 短时有效、单次使用，并绑定 client、redirect、用户和 PKCE challenge；
- 网页登录完成后必须由用户明确同意，不得自动批准；
- Token 响应提供 `access_token`、`refresh_token`、`expires_in` 和 `token_type`；
- Refresh Token 流程接受公共 client ID，不要求客户端密钥；
- 拒绝、登录失败和服务错误都按照 OAuth 规范返回错误，不生成 Token。

公共 client ID 出现在 HACS 源码中是正常设计。任何 secret 一旦放入自定义集成，
所有安装者都能读取，因此不得给该客户端配置或分发 secret。

## Home Assistant 端实现

集成固定使用生产服务和公共 PKCE 客户端，不读取环境变量，也不提供 Client Secret
或 Application Credentials 回退模式。每次配置流使用独立的 PKCE verifier，避免
并发授权相互覆盖。

## 网页要求

- 页面必须支持桌面端和移动端浏览器，不依赖已安装 Gendome App；
- 未登录时显示 Gendome 登录，已登录时直接进入授权确认；
- 明确展示授权主体、权限范围、允许和拒绝操作；
- 登录态、授权事务和回调参数由服务端绑定，前端不能修改 redirect 或 Scope；
- 登录、同意、拒绝具有 CSRF 防护；
- 成功返回后显示“可以关闭此页面并返回 Home Assistant”；
- 页面不得记录或上报 authorization code、Token、密码或完整回调 URL。

## 联调验收

- 全新 Home Assistant 中未配置任何 Gendome Application Credential；
- 即使用户未启用 `default_config`，依赖加载的 `my` 组件仍生成固定 HTTPS 回调；
- 添加集成后直接打开 Gendome 网页，无实现选择页、无凭据输入页；
- 覆盖未登录、已登录、密码错误、允许、拒绝、取消和授权超时；
- 验证 code 只能兑换一次，错误 verifier、redirect、client 或 state 均失败；
- 成功回调后 `/profile` 校验通过，配置项自动创建，设备和实体自动出现；
- 验证无设备、单设备、多设备、离线设备和账号重复添加；
- 验证 access token 到期自动刷新，refresh token 撤销后进入重新认证；
- 验证 Home Assistant 重启后无需重新登录即可恢复设备；
- 验证删除配置项后撤销 Token；
- 验证集成只调用公开的生产 API 和 OAuth 服务。
