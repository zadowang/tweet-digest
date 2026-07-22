"""Playwright-based tweet collector using user Chrome profile"""
import json, os, sys, time, re
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
CST = timezone(timedelta(hours=8))
TARGET = "whyyoutouzhele"

# Chrome user profile
CHROME_PROFILE = os.environ.get(
    "CHROME_USER_DATA",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
)

def categorize(text):
    rules = [
        ("国际/地缘", ["乌克兰","俄罗斯","美国","欧洲","北约","泽连斯基","特朗普",
                       "普京","以色列","伊朗","朝鲜","韩国","日本","泰国","越南",
                       "缅甸","台湾","香港"]),
        ("言论/审查", ["删","封","禁","限流","审查","敏感","删除","屏蔽","拉黑",
                       "下架","水军","五毛","网信办","国安","言论","自由"]),
        ("社会/民生", ["死","伤","事故","火灾","洪水","地震","爆炸","食品","药品",
                       "医疗","教育","住房","污染","动物","环境"]),
        ("制度/法治", ["腐败","法治","权利","公民","纳税人","维权","上访","拆迁",
                       "护照","签证","执法","法院","宪法"]),
    ]
    for cat, words in rules:
        if any(w in text for w in words):
            return cat
    return "其他"

def collect():
    from playwright.sync_api import sync_playwright

    now = datetime.now(CST)
    yesterday = now - timedelta(days=1)
    cutoff = yesterday.replace(hour=18, minute=0, second=0)

    print(f"Collecting tweets since {cutoff.isoformat()}")
    tweets = []

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            CHROME_PROFILE,
            headless=False,
            channel="chrome",
            args=["--profile-directory=Default", "--no-first-run"],
        )
        page = ctx.new_page()
        page.goto(f"https://x.com/{TARGET}", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Scroll and collect
        for _ in range(10):
            page.evaluate("window.scrollBy(0, 1200)")
            page.wait_for_timeout(800)

        articles = page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('article[data-testid="tweet"]').forEach(a => {
                const text = a.querySelector('[data-testid="tweetText"]');
                const time = a.querySelector('time');
                if (text && time) {
                    result.push({
                        text: text.textContent.trim(),
                        time: time.getAttribute("datetime")
                    });
                }
            });
            return result;
        }""")

        ctx.close()

        for t in articles:
            if t.get("time") and t["time"] >= cutoff.isoformat():
                tweets.append(t)

    # Deduplicate
    seen = set()
    unique = []
    for t in tweets:
        key = t["text"][:40]
        if key not in seen:
            seen.add(key)
            unique.append(t)

    unique.sort(key=lambda t: t.get("time", ""), reverse=True)
    print(f"Collected {len(unique)} tweets")

    # Build digest
    items = []
    cat_map = {}
    for t in unique:
        cat = categorize(t["text"])
        title = t["text"][:40].strip()
        if len(t["text"]) > 40:
            title = title[:39] + "…"
        items.append({"title": title, "text": t["text"], "time": t["time"], "category": cat})
        cat_map[cat] = cat_map.get(cat, 0) + 1

    # Generate summary
    categories_list = sorted([{"name": k, "count": v} for k, v in cat_map.items()],
                             key=lambda x: x["count"], reverse=True)
    summary_lines = ["**今日要点**"]
    for cat_entry in categories_list:
        cat_name = cat_entry["name"]
        cat_tweets = [t for t in items if t["category"] == cat_name]
        titles = "、".join(t["title"][:15] for t in cat_tweets[:3])
        summary_lines.append(f"\n**{cat_name}**：{titles}")

    summary = "\n".join(summary_lines)

    digest = {
        "meta": {
            "user": TARGET,
            "date": now.strftime("%Y-%m-%d"),
            "dateRange": f"{yesterday.strftime('%-m/%-d')} 18:00 — {now.strftime('%-m/%-d')} 18:00",
            "generatedAt": now.strftime("%Y-%m-%d %H:%M"),
        },
        "summary": summary,
        "categories": categories_list,
        "tweets": items,
    }

    DATA_DIR.mkdir(exist_ok=True)
    fp = DATA_DIR / f"{now.strftime('%Y-%m-%d')}.json"
    fp.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved to {fp}")
    return digest

if __name__ == "__main__":
    collect()
