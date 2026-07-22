"""抓取 X 用户推文并保存摘要"""
import json, re, sys, os
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CST = timezone(timedelta(hours=8))

TARGET_USER = "whyyoutouzhele"

def categorize_tweet(text):
    """简单分类推文主题"""
    text_lower = text.lower()
    keywords = {
        "国际/地缘": ["乌克兰", "俄罗斯", "美国", "欧洲", "北约", "泽连斯基", "特朗普", "普京", "以色列",
                     "伊朗", "朝鲜", "韩国", "日本", "泰国", "越南", "缅甸", "台湾", "香港"],
        "言论/审查": ["删", "封", "禁", "限流", "审查", "敏感", "删除", "屏蔽", "拉黑", "下架",
                     "水军", "五毛", "网信办", "国安", "言论", "自由"],
        "社会/民生": ["死", "伤", "事故", "火灾", "洪水", "地震", "爆炸", "食品", "药品", "医疗",
                     "教育", "住房", "污染", "动物", "环境"],
        "制度/法治": ["腐败", "法治", "权利", "公民", "纳税人", "维权", "上访", "拆迁",
                     "护照", "签证", "执法", "法院", "宪法"],
    }
    for cat, words in keywords.items():
        for w in words:
            if w in text:
                return cat
    return "其他"

def make_title(text, max_len=40):
    """从推文生成短标题"""
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= max_len:
        return clean
    return clean[:max_len-1] + "…"

def save_digest(tweets, summary="", categories=None):
    """保存抓取结果到 JSON 文件"""
    now = datetime.now(CST)
    yesterday = now - timedelta(days=1)

    date_key = now.strftime("%Y-%m-%d")
    date_range = f"{yesterday.strftime('%-m/%-d')} 18:00 — {now.strftime('%-m/%-d')} 18:00"

    tweet_items = []
    cat_map = {}
    for t in tweets:
        cat = t.get("category") or categorize_tweet(t.get("text", ""))
        item = {
            "title": make_title(t.get("text", "")),
            "text": t["text"],
            "time": t["time"],
            "category": cat,
        }
        tweet_items.append(item)
        cat_map[cat] = cat_map.get(cat, 0) + 1

    category_list = sorted(
        [{"name": k, "count": v} for k, v in cat_map.items()],
        key=lambda x: x["count"], reverse=True
    )

    digest = {
        "meta": {
            "user": TARGET_USER,
            "date": date_key,
            "dateRange": date_range,
            "generatedAt": now.strftime("%Y-%m-%d %H:%M"),
        },
        "summary": summary,
        "categories": category_list,
        "tweets": tweet_items,
    }

    fp = DATA_DIR / f"{date_key}.json"
    fp.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(tweet_items)} tweets to {fp}")
    return digest

if __name__ == "__main__":
    print("scraper module imported")
