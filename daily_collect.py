"""Daily collector for GitHub Actions — uses twitter-cli client directly"""
import json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
TARGET = "whyyoutouzhele"
DATA_DIR = Path("data")
STATIC_DATA = Path("static") / "data"
DATA_DIR.mkdir(exist_ok=True)
STATIC_DATA.mkdir(parents=True, exist_ok=True)

def categorize(text):
    rules = [
        ("国际/地缘", ["乌克兰","俄罗斯","美国","欧洲","北约","泽连斯基","特朗普","普京","以色列","伊朗","朝鲜","韩国","日本","泰国","越南","缅甸","台湾","香港"]),
        ("言论/审查", ["删","封","禁","限流","审查","敏感","删除","屏蔽","拉黑","下架","水军","五毛","网信","国安","言论","自由"]),
        ("社会/民生", ["死","伤","事故","火灾","洪水","地震","爆炸","食品","药品","医疗","教育","住房","污染","动物","环境"]),
        ("制度/法治", ["腐败","法治","权利","公民","纳税人","维权","上访","拆迁","护照","签证","执法","法院","宪法"]),
    ]
    for cat, words in rules:
        if any(w in text for w in words):
            return cat
    return "其他"

def collect():
    now = datetime.now(CST)
    yesterday = now - timedelta(days=1)
    cutoff = yesterday.replace(hour=18, minute=0, second=0).isoformat()
    print(f"Collecting @{TARGET} tweets since {cutoff}")

    auth_token = os.environ.get("TWITTER_AUTH_TOKEN", "").strip()
    ct0 = os.environ.get("TWITTER_CT0", "").strip()
    if not auth_token or not ct0:
        print("ERROR: Secrets not set")
        sys.exit(1)

    from twitter_cli.client import TwitterClient
    client = TwitterClient(auth_token, ct0)

    try:
        raw_tweets = client.fetch_user_tweets(TARGET, 50)
    except AttributeError:
        raw_tweets = client.fetch_tweets_by_screen_name(TARGET, 50)
    except Exception as e:
        print(f"Fetch error: {e}")
        sys.exit(1)

    print(f"Raw tweets fetched: {len(raw_tweets)}")

    tweets = []
    for t in raw_tweets:
        ts = getattr(t, "created_at", "") or (t.get("created_at", "") if isinstance(t, dict) else "")
        text = ""
        if hasattr(t, "full_text"):
            text = t.full_text
        elif hasattr(t, "text"):
            text = t.text
        elif isinstance(t, dict):
            text = t.get("full_text", "") or t.get("text", "")
        if ts and ts >= cutoff and text:
            tweets.append({"text": text, "time": ts})

    seen = set()
    unique = []
    for t in tweets:
        key = t["text"][:40]
        if key not in seen:
            seen.add(key)
            unique.append(t)
    unique.sort(key=lambda t: t["time"], reverse=True)
    print(f"Tweets in time range: {len(unique)}")

    items = []
    cat_map = {}
    for t in unique:
        cat = categorize(t["text"])
        title = t["text"][:40].strip()
        if len(t["text"]) > 40:
            title = title[:39] + "\u2026"
        items.append({"title": title, "text": t["text"], "time": t["time"], "category": cat})
        cat_map[cat] = cat_map.get(cat, 0) + 1

    categories_list = sorted([{"name": k, "count": v} for k, v in cat_map.items()],
                             key=lambda x: x["count"], reverse=True)
    summary_lines = ["**今日要点**"]
    for ce in categories_list:
        cat_tweets = [t for t in items if t["category"] == ce["name"]]
        titles = "\u3001".join(t["title"][:15] for t in cat_tweets[:3])
        summary_lines.append(f"\n**{ce['name']}**：{titles}")

    digest = {
        "meta": {
            "user": TARGET,
            "date": now.strftime("%Y-%m-%d"),
            "dateRange": f"{yesterday.strftime('%-m/%-d')} 18:00 \u2014 {now.strftime('%-m/%-d')} 18:00",
            "generatedAt": now.strftime("%Y-%m-%d %H:%M"),
        },
        "summary": "\n".join(summary_lines),
        "categories": categories_list,
        "tweets": items,
    }

    date_key = now.strftime("%Y-%m-%d")
    digest_json = json.dumps(digest, ensure_ascii=False, indent=2)
    (DATA_DIR / f"{date_key}.json").write_text(digest_json, encoding="utf-8")
    (STATIC_DATA / f"{date_key}.json").write_text(digest_json, encoding="utf-8")

    all_days = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        try:
            all_days[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except:
            pass
    (STATIC_DATA / "index.json").write_text(json.dumps(all_days, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(unique)} tweets for {date_key}")

if __name__ == "__main__":
    collect()
