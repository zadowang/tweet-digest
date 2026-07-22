"""Daily collector — fixed cookie swap + resolve_user_id"""
import json, os, sys, traceback
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
    print(f"Collecting @{TARGET}, cutoff={cutoff}", flush=True)

    auth_token = os.environ.get("TWITTER_AUTH_TOKEN", "").strip()
    ct0 = os.environ.get("TWITTER_CT0", "").strip()
    print(f"AT len={len(auth_token)} CT0 len={len(ct0)}", flush=True)

    # Auto-swap: auth_token should be longer than ct0
    if len(auth_token) < len(ct0):
        print("AUTO-SWAP: cookies were reversed", flush=True)
        auth_token, ct0 = ct0, auth_token

    if not auth_token or not ct0:
        print("FATAL: Secrets missing", flush=True)
        sys.exit(1)

    from twitter_cli.client import TwitterClient
    client = TwitterClient(auth_token, ct0)
    print("Client OK", flush=True)

    # fetch_user_tweets wants a numeric user_id
    print(f"Resolving user ID for @{TARGET}...", flush=True)
    try:
        user_id = client.resolve_user_id(TARGET)
        print(f"User ID: {user_id}", flush=True)
    except Exception as e:
        print(f"resolve_user_id FAILED: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

    print("Fetching tweets...", flush=True)
    try:
        raw_tweets = client.fetch_user_tweets(user_id, 30)
    except Exception as e:
        print(f"fetch FAILED: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

    print(f"Got {len(raw_tweets)} raw tweets", flush=True)

    tweets = []
    for t in raw_tweets:
        ts = getattr(t, "created_at", "")
        text = getattr(t, "full_text", "") or getattr(t, "text", "")
        if ts and text:
            tweets.append({"text": text, "time": ts})

    print(f"Parsed {len(tweets)} tweets", flush=True)
    in_range = [t for t in tweets if t["time"] >= cutoff]
    print(f"In range: {len(in_range)}", flush=True)

    seen = set()
    unique = []
    for t in in_range:
        key = t["text"][:40]
        if key not in seen:
            seen.add(key)
            unique.append(t)
    unique.sort(key=lambda t: t["time"], reverse=True)

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
            "user": TARGET, "date": now.strftime("%Y-%m-%d"),
            "dateRange": f"{yesterday.strftime('%-m/%-d')} 18:00 \u2014 {now.strftime('%-m/%-d')} 18:00",
            "generatedAt": now.strftime("%Y-%m-%d %H:%M"),
        },
        "summary": "\n".join(summary_lines), "categories": categories_list, "tweets": items,
    }

    date_key = now.strftime("%Y-%m-%d")
    dj = json.dumps(digest, ensure_ascii=False, indent=2)
    (DATA_DIR / f"{date_key}.json").write_text(dj, encoding="utf-8")
    (STATIC_DATA / f"{date_key}.json").write_text(dj, encoding="utf-8")

    all_days = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        try:
            all_days[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except: pass
    (STATIC_DATA / "index.json").write_text(json.dumps(all_days, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE: {len(items)} tweets for {date_key}", flush=True)

if __name__ == "__main__":
    collect()
