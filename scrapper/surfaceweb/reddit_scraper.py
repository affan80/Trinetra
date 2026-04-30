import requests
import time
import json
import random
from datetime import datetime

# 🔥 Seen posts (dedup)
seen = set()

# 🔥 Keywords
KEYWORDS = [
    "hack", "cyber", "attack", "breach",
    "war", "military", "exploit", "leak"
]

# 🔥 Subreddits
SUBREDDITS = ["worldnews", "technology"]

# 🔥 Proper browser headers (IMPORTANT)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0 Safari/537.36"
}


# 🔹 Keyword filter
def is_relevant(text):
    text = text.lower()
    return any(k in text for k in KEYWORDS)


# 🔹 Safe request handler
def safe_request(url, retries=3):
    for attempt in range(retries):
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)

            if res.status_code == 200:
                return res.json()

            elif res.status_code == 429:
                wait = (attempt + 1) * 5
                print(f"⏳ Rate limited. Waiting {wait}s...")
                time.sleep(wait)

            else:
                print(f"⚠️ Error {res.status_code} → {url}")
                return None

        except Exception as e:
            print("❌ Request error:", e)

    return None


# 🔹 Fetch from subreddits (with pagination)
def fetch_subreddits():
    results = []

    for sub in SUBREDDITS:
        print(f"📡 Fetching r/{sub}")

        after = None

        for _ in range(1):  # pages per subreddit
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=25"

            if after:
                url += f"&after={after}"

            data = safe_request(url)

            if not data:
                break

            after = data["data"]["after"]

            for post in data["data"]["children"]:
                p = post["data"]
                post_id = p["id"]

                if post_id not in seen and is_relevant(p["title"]):
                    seen.add(post_id)

                    results.append({
                        "id": post_id,
                        "text": p["title"],
                        "subreddit": sub,
                        "source": "reddit",
                        "timestamp": p["created_utc"],
                        "url": p["url"],
                        "score": p["score"],
                        "collected_at": datetime.utcnow().isoformat()
                    })

            time.sleep(random.uniform(1, 2))  # 🔥 avoid blocking

    return results


# 🔹 Fetch via search (whole Reddit)
def fetch_search():
    results = []

    for keyword in KEYWORDS:
        print(f"🔎 Searching: {keyword}")

        url = f"https://www.reddit.com/search.json?q={keyword}&sort=new&limit=10"

        data = safe_request(url)

        if not data:
            continue

        for post in data["data"]["children"]:
            p = post["data"]
            post_id = p["id"]

            if post_id not in seen:
                seen.add(post_id)

                results.append({
                    "id": post_id,
                    "text": p["title"],
                    "subreddit": p["subreddit"],
                    "source": "reddit",
                    "timestamp": p["created_utc"],
                    "url": p["url"],
                    "score": p["score"],
                    "collected_at": datetime.utcnow().isoformat()
                })

        time.sleep(random.uniform(2, 4))  # 🔥 avoid blocking

    return results


# 🔹 Save data
def save(data):
    if not data:
        print("⚠️ No new relevant posts")
        return

    with open("reddit_osint.jsonl", "a") as f:
        for item in data:
            print("\n", json.dumps(item, indent=2))
            f.write(json.dumps(item) + "\n")


# 🔁 MAIN LOOP
while True:
    print("\n🚀 Collecting OSINT Reddit Data...\n")

    data = fetch_subreddits()   # ONLY this, remove search for now

    print(f"\nCollected: {len(data)} posts\n")

    if data:
        save(data)
    else:
        print("⚠️ No data fetched (likely rate-limited)")

    print("⏳ Sleeping...\n")
    time.sleep(120)