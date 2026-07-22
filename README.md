# 推文日报 — @whyyoutouzhele

每日自动抓取 X 用户推文，AI 总结分类，交互式 Web 展示。

## 功能

- 🐦 每天 18:00 自动抓取前 24 小时的推文
- 📊 自动分类：国际/地缘、言论/审查、社会/民生、制度/法治
- 📱 响应式设计，手机/桌面均可访问
- 🏷️ 点击推文卡片展开全文
- 🔍 按分类筛选、按日期切换历史
- ☁️ GitHub Pages 免费托管，无需服务器

## 部署

1. Fork 此仓库
2. Settings → Secrets → Actions → 添加 `TWITTER_AUTH_TOKEN` 和 `TWITTER_CT0`
3. Settings → Pages → Source → GitHub Actions
4. 手动触发一次 workflow 或等待每日 18:00 自动运行

## 获取 Cookie

Chrome 打开 x.com → F12 → Application → Cookies → x.com → 复制 `auth_token` 和 `ct0`
