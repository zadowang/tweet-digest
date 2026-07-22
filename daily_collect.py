"""Daily collector — uses requests directly (bypasses twitter-cli verification issues)"""
import json, os, sys, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

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

BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

def fetch_tweets(auth_token, ct0):
    """Fetch tweets using X GraphQL API"""
    s = requests.Session()
    cookie_str = f"auth_token={auth_token}; ct0={ct0}"
    headers = {
        "Authorization": f"Bearer {BEARER}",
        "Cookie": cookie_str,
        "X-Csrf-Token": ct0,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
    }

    # Step 1: get user ID from screen name
    r = s.get(f"https://x.com/{TARGET}", headers=headers, timeout=15)
    match = re.search(r'"rest_id":"(\d+)"', r.text)
    if not match:
        print(f"Could not find user ID. Response length: {len(r.text)}")
        print(f"First 500 chars: {r.text[:500]}")
        sys.exit(1)
    user_id = match.group(1)
    print(f"User ID: {user_id}")

    # Step 2: fetch tweets via GraphQL
    variables = json.dumps({
        "userId": user_id,
        "count": 50,
        "includePromotedContent": False,
        "withQuickPromoteEligibilityTweetFields": False,
        "withVoice": False,
        "withV2Timeline": True,
    })
    features = json.dumps({
        "profile_label_improvements_pcf_label_in_post_enabled": False,
        "rweb_tipjar_consumption_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "premium_content_api_read_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
        "responsive_web_grok_analyze_post_followups_enabled": True,
        "responsive_web_jetfuel_frame": False,
        "responsive_web_grok_share_attachment_enabled": True,
        "articles_preview_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "responsive_web_grok_show_grok_translated_post": False,
        "responsive_web_grok_analyze_image_upload_enabled": True,
        "responsive_web_grok_conversation_starters_enabled": True,
        "creator_subscriptions_quote_tweet_preview_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "rweb_video_timestamps_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_enhance_cards_enabled": False,
    })

    params = {"variables": variables, "features": features}
    url = f"https://x.com/i/api/graphql/V7H0Ap3rV0G8h_wq_E6y6A/UserTweets"
    r = s.get(url, params=params, headers=headers, timeout=20)

    data = r.json()
    entries = []
    try:
        instructions = data["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]
        for inst in instructions:
            if inst.get("type") != "TimelineAddEntries":
                continue
            for entry in inst.get("entries", []):
                content = entry.get("content", {})
                if content.get("entryType") != "TimelineTimelineItem":
                    continue
                tweet = content.get("itemContent", {}).get("tweet_results", {}).get("result", {})
                if not tweet:
                    continue
                legacy = tweet.get("legacy", {})
                text = legacy.get("full_text", "")
                created = legacy.get("created_at", "")
                if text and created:
                    entries.append({"text": text, "time": created})
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Response keys: {list(data.keys())}")
        sys.exit(1)

    print(f"Fetched {len(entries)} tweets total")
    return entries

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

    entries = fetch_tweets(auth_token, ct0)

    # Filter and deduplicate
    tweets = []
    seen = set()
    for e in entries:
        if e["time"] >= cutoff:
            key = e["text"][:40]
            if key not in seen:
                seen.add(key)
                tweets.append(e)

    tweets.sort(key=lambda t: t["time"], reverse=True)
    print(f"{len(tweets)} tweets in time range")

    items = []
    cat_map = {}
    for t in tweets:
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
    print(f"Saved {len(items)} tweets for {date_key}")

if __name__ == "__main__":
    collect()
