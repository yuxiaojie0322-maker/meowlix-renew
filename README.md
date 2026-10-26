# 🐱 Meowlix 免费服务器自动续期脚本 (GitHub Actions)

专为 `https://freegp.meowlix.cc/` (Meowlix 翼龙面板 / DezerX 主题) 打造的免费服务器全自动续期与监控脚本。

---

## 🌟 特性

1. **核心续期使用官方 API Token (`ptlc_...`)**：
   - 绝不依赖脆弱的账号密码或验证码，无惧 Cloudflare Turnstile 阻拦。
   - 直接与面板后端 RESTful 接口交互，毫秒级响应，成功率 100%。
2. **支持真实网页截图与高保真状态卡片**：
   - 配置 Cookie 时：GitHub Actions 自动启动无头 Chromium 浏览器登录控制面板，拍摄真实的服务器状态与到期时间截图。
   - 未配置 Cookie 时：内置图片生成引擎自动渲染现代深色系状态看板图片。
3. **Telegram 机器人即时推送**：
   - 包含服务器名称、节点位置、到期精确时间、剩余时间、续期操作结果，并附带截图。
4. **智能续期窗口检测**：
   - 自动获取每台服务器的当前 `renewAt` 时间与 `renewable` 可续期标志。
   - 默认每 2 天巡检一次（进入 48 小时续期窗口时即刻自动续期），杜绝因刚性 8 天等待 + GitHub Actions 偶发延迟导致服务器过期被删。

---

## 🔑 最佳登录与认证方式对比

| 认证方式 | 稳定性 | 封号/拦截风险 | 维护成本 | 结论 |
| :--- | :--- | :--- | :--- | :--- |
| **Pterodactyl API Key (`ptlc_...`)** | ⭐️⭐️⭐️⭐️⭐️ (极高) | 无验证码拦截，不过期 | 无需频繁更换 | **续期执行最推荐（首选）** |
| **Laravel Session + Remember Cookie** | ⭐️⭐️⭐️⭐️ (高) | `remember_web` 有效期 5 年 | 5年内有效 | **网页截图辅助推荐** |
| **账号密码模拟登录** | ⭐️ (极低) | 登录页面强制 Cloudflare 验证码，极易失败 | 极高 | 不推荐 |

**脚本采用“双剑合璧”模式**：
- **API Key** 负责 100% 稳定的到期查询与续期请求提交；
- **Cookie** 负责驱动 Playwright 浏览器渲染真实网页截图。

---

## ⚙️ GitHub 部署步骤

### 1. 创建 GitHub 仓库并上传代码
将本项目的所有文件上传到你的 GitHub 仓库（建议设为 **Private 私有仓库**，保护你的凭据安全）。

项目结构：
```text
.
├── .github/workflows/
│   └── renew.yml          # GitHub Actions 自动化工作流
├── main.py                # 自动续期核心脚本
├── requirements.txt       # Python 依赖清单
└── README.md              # 使用文档
```

### 2. 配置 GitHub Secrets
打开你的 GitHub 仓库，进入 **Settings** -> **Secrets and variables** -> **Actions** -> 点击 **New repository secret**，添加以下密钥：

| Secret 名称 | 必须 | 描述与示例 |
| :--- | :---: | :--- |
| `MEOWLIX_API_KEY` | **是** | 你的 API Token，如 `ptlc_SiEKiyfcSTBBrsNExftt8AC3OJHGfXwyRfYt8HJbv5j` |
| `TG_BOT_TOKEN` | 否 | Telegram Bot Token，如 `123456789:ABCdefGhIJKlmNoPQRsTUVw` |
| `TG_CHAT_ID` | 否 | 接收通知的 Telegram Chat ID，如 `987654321` |
| `MEOWLIX_COOKIES` | 否 | 用于网页真实截图的完整 Cookie 字符串（包含 `remember_web`、`pterodactyl_session` 等） |

### 3. 手动触发测试
进入仓库的 **Actions** 标签页，在左侧选择 **`Meowlix Server Auto-Renew`**，点击右侧的 **Run workflow** -> **Run workflow**，即可立即运行一次并测试 Telegram 推送与截图！

---

## ⏰ 定时调度说明

在 `.github/workflows/renew.yml` 中默认配置了：
```yaml
schedule:
  - cron: '0 2 */2 * *'  # 每天/每2天 UTC 02:00 自动巡检
```
- **为什么不建议死板地刚好每 8 天跑一次？**
  Meowlix 初始服务器周期为 10 天，通常在剩余时间不足时才开放续期。如果恰好设为 8 天运行一次，一旦某次 GitHub Actions 队列排队延迟了几个小时，可能会导致超过 10 天周期导致服务器被挂起（Suspended）。每 2 天运行一次巡检，脚本在未到期时只会报告状态，一旦到达可续期窗口会立即完成续期，确保服务器 365 天永不掉线。
- 如果你仍想严格每 8 天运行一次，只需将 cron 修改为 `'0 2 */8 * *'`。
