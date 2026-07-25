import json, os, sys, traceback, time
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
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    if event == "schedule" and (now.hour != 18):
        print("Not collection window, skipping")
        sys.exit(0)

    auth_token = os.environ.get("TWITTER_AUTH_TOKEN", "").strip()
    ct0 = os.environ.get("TWITTER_CT0", "").strip()
    print(f"AT len={len(auth_token)} CT0 len={len(ct0)}", flush=True)
    if not auth_token or not ct0:
        print("FATAL: Secrets missing", flush=True)
        sys.exit(1)

    from twitter_cli.client import TwitterClient
    client = TwitterClient(auth_token, ct0)
    print("Client OK", flush=True)

    print(f"Resolving user ID for @{TARGET}...", flush=True)
    user_id = client.resolve_user_id(TARGET)
    print(f"User ID: {user_id}", flush=True)

    # Phase 1: get tweets using reliable fetch_user_tweets  
    print("Phase 1: fetch_user_tweets...", flush=True)
    try:
        raw_tweets = client.fetch_user_tweets(user_id, 40)
        print(f"Got {len(raw_tweets)} tweets", flush=True)
    except Exception as e:
        print(f"fetch_user_tweets FAILED: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

    # Phase 2: get raw GraphQL for images
    print("Phase 2: raw GraphQL for images...", flush=True)
    tweet_images = {}
    try:
        from twitter_cli.client import FEATURES
        for rtype in ["", "Media"]:
            raw = client._graphql_get("UserTweets", {
                "userId": user_id, "count": 50,
                "includePromotedContent": False,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True, "withV2Timeline": True
            }, FEATURES)
            insts = raw.get("data",{}).get("user",{}).get("result",{}).get("timeline_v2",{}).get("timeline",{}).get("instructions",[])
            img_count = 0
            for inst in insts:
                if inst.get("type") != "TimelineAddEntries": continue
                for entry in inst.get("entries", []):
                    tr = entry.get("content",{}).get("itemContent",{}).get("tweet_results",{}).get("result",{})
                    if not tr: continue
                    leg = tr.get("legacy", {})
                    tid = leg.get("id_str", "") or str(tr.get("rest_id", ""))
                    entities = leg.get("extended_entities", {}) or tr.get("extended_entities", {})
                    images = [m.get("media_url_https","") for m in entities.get("media",[]) if m.get("media_url_https")]
                    if images:
                        tweet_images[tid] = images
                        img_count += 1
            print(f"Found {img_count} tweets with images in raw data", flush=True)
            if img_count > 0: break
    except Exception as e:
        print(f"Raw GraphQL image extraction failed: {e}", flush=True)
        traceback.print_exc()

    # Build tweet list
    tweets = []
    for t in raw_tweets:
        ts = getattr(t, "created_at", "")
        text = getattr(t, "full_text", "") or getattr(t, "text", "")
        if not ts or not text or ts < cutoff:
            continue
        score = getattr(t, "score", 0) or 0
        if isinstance(score, (int, float)): score = float(score)
        else: score = 0
        tid = getattr(t, "id", "")
        images = tweet_images.get(str(tid), [])
        tweets.append({"text": text, "time": ts, "score": score, "id": str(tid), "images": images})

    print(f"Parsed {len(tweets)} tweets", flush=True)

    seen = set(); unique = []
    for t in tweets:
        key = t["text"][:40]
        if key not in seen: seen.add(key); unique.append(t)
    unique.sort(key=lambda t: t["score"], reverse=True)
    print(f"Unique: {len(unique)}", flush=True)

    # Comments  
    for t in unique[:10]:
        try:
            tid = t.get("id", "")
            if tid:
                detail = client.fetch_tweet_detail(str(tid), 6)
                comments = []
                for d in detail[1:]:
                    text = getattr(d, "full_text", "") or getattr(d, "text", "")
                    if text and not getattr(d, "is_retweet", False):
                        comments.append(text)
                        if len(comments) >= 3: break
                t["comments"] = comments
            time.sleep(0.3)
        except Exception as e:
            t["comments"] = []

    items = []
    cat_map = {}
    for t in unique:
        cat = categorize(t["text"])
        title = t["text"][:40].strip()
        if len(t["text"]) > 40: title = title[:39] + "\u2026"
        items.append({"title": title, "text": t["text"], "time": t["time"], "category": cat,
                       "score": int(t.get("score", 0)), "comments": t.get("comments", []),
                       "images": t.get("images", [])})
        cat_map[cat] = cat_map.get(cat, 0) + 1

    # Report image status
    img_tweets = [t for t in items if t["images"]]
    print(f"Items with images: {len(img_tweets)}")
    if img_tweets:
        print(f"Sample image tweet: {img_tweets[0]['text'][:80]} -> {img_tweets[0]['images']}")

    cats = sorted([{"name": k, "count": v} for k, v in cat_map.items()], key=lambda x: x["count"], reverse=True)
    sl = ["**今日要点**"]
    for ce in cats:
        cts = [t for t in items if t["category"] == ce["name"]]
        sl.append(f"\n**{ce['name']}**：{'、'.join(t['title'][:15] for t in cts[:3])}")

    digest = {
        "meta": {"user": TARGET, "date": now.strftime("%Y-%m-%d"),
                 "dateRange": f"{yesterday.strftime('%-m/%-d')} 18:00 \u2014 {now.strftime('%-m/%-d')} 18:00",
                 "generatedAt": now.strftime("%Y-%m-%d %H:%M")},
        "summary": "\n".join(sl), "categories": cats, "tweets": items,
    }

    dk = now.strftime("%Y-%m-%d")
    dj = json.dumps(digest, ensure_ascii=False, indent=2)
    (DATA_DIR / f"{dk}.json").write_text(dj, encoding="utf-8")
    (STATIC_DATA / f"{dk}.json").write_text(dj, encoding="utf-8")

    all_days = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        try: all_days[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except: pass
    (STATIC_DATA / "index.json").write_text(json.dumps(all_days, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE: {len(items)} tweets for {dk}", flush=True)

if __name__ == "__main__":
    collect()
