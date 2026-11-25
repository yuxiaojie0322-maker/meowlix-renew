# Meowlix 自动续期

通过 GitHub Actions 定时调度私有仓库 `my-private-scripts/meowlix` 中的核心续期脚本，支持多账号自动续期与 Telegram 通知。

## 必要 Secrets 配置

请在当前仓库的 **Settings -> Secrets and variables -> Actions -> Secrets** 中配置以下密钥：

- `CORE_SCRIPT_TOKEN`（或 `REPO_TOKEN` / `GH_PAT_PRIVATE_REPO`）：用于检出私有仓库 `my-private-scripts` 的 GitHub PAT。
- 账号配置（任选其一）：
  - `MEOWLIX_ACCOUNT_<名称>`：单行格式 `api_key` 或 `账号名#api_key#cookies#server_id`（支持配置多个不同后缀的 Secret 实现多账号）。
  - `MEOWLIX_ACCOUNTS`：多行格式，每行一个 `账号名#api_key#cookies#server_id`。
  - `MEOWLIX_API_KEY`：单账号回退密钥（可选搭配 `MEOWLIX_COOKIES`、`SERVER_ID`）。
- 通知配置（可选）：
  - `TG_BOT_TOKEN`：Telegram Bot Token。
  - `TG_CHAT_ID`：接收报告的 Telegram Chat ID。

## 可选 Variables 配置

- `MEOWLIX_URL`：面板地址，默认 `https://freegp.meowlix.cc`。
