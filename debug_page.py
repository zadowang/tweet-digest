import requests, re, json
s = requests.Session()
auth = "814b81e12ce5904d5e4d35b760df13c29c43e8dfe1673be4c21485656a9f022763c83e112c1d5d99a6ae15e9d90552815ea791226d4a332ab94f94942c397c7670e2c73a28cd9e4163c49881a197dfa0"
ct0 = "437f56c28a57f4c0024144657085272d8f0b7cbe"
r = s.get("https://x.com/whyyoutouzhele",
    cookies={"auth_token": auth, "ct0": ct0},
    headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
html = r.text
print(f"Status: {r.status_code}, URL: {r.url[:80]}, Length: {len(html)}")

# Check if we got redirected to login
if "login" in r.url.lower() or "Please enable JavaScript" in html:
    print("GOT LOGIN PAGE - cookies may be expired")
    exit()

# Search for user ID
for pat in ["rest_id", "id_str", '"id":"', "userId"]:
    pos = html.find(pat)
    if pos > -1:
        snippet = html[pos:pos+100]
        print(f"  '{pat}' at {pos}: {snippet[:80]}")

# Try JSON data block
m = re.search(r"__INITIAL_STATE__\s*=\s*(\{.+?\});", html)
if m:
    try:
        data = json.loads(m.group(1))
        print(f"INITIAL_STATE keys: {list(data.keys())[:10]}")
    except Exception as e:
        print(f"INITIAL_STATE parse: {e}")
