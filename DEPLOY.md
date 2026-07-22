# 推文日报 — GitHub Pages 部署

## 需要你操作

### 1. 获取 Cookie（1 分钟）

打开 Chrome，确保已登录 x.com，然后：

**方法：Chrome DevTools**
1. 按 `F12` 打开开发者工具
2. 点击顶部 `Application`（应用程序）标签
3. 左侧找到 `Cookies` → 点击 `https://x.com`
4. 在右侧列表中找到 `auth_token`，双击它的 Value，Ctrl+C 复制
5. 同样复制 `ct0` 的 Value

### 2. 创建 GitHub 仓库并推送代码

```bash
cd C:\Users\ming\Documents\Codex\2026-07-22\x\tweet-digest
git init
git add .
git commit -m "Initial: tweet digest with GitHub Pages"
```
然后在 GitHub 上创建新仓库（名字随意，比如 `tweet-digest`），跟着 GitHub 的提示 push。

### 3. 添加 Secrets

在仓库 Settings → Secrets and variables → Actions → New repository secret：
- 名称 `TWITTER_AUTH_TOKEN`，值粘贴刚才复制的 auth_token
- 名称 `TWITTER_CT0`，值粘贴 ct0

### 4. 启用 GitHub Pages

Settings → Pages → Source 选 "GitHub Actions"

完成！之后每天 18:00 自动抓取，你的 GitHub Pages URL 就是手机上的访问地址。
