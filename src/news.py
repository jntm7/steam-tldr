import argparse
import html
import json
import re
import requests
import time
from datetime import datetime, timezone
from fetch import DATA_DIR, MAX_RETRIES, SLEEP_SECONDS

# Steam's news feed for a game: official announcements plus press articles, no API key needed
NEWS_URL = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
PAGE_SIZE = 100
SNIPPET_CHARS = 300

# Where one game's news is cached
def news_path(appid: int):
    return DATA_DIR / f"{appid}_news.json"

# Request one page of news items published before a Unix time
def get_news_page(appid: int, before: int) -> list[dict]:
    params = {"appid": appid, "count": PAGE_SIZE, "maxlength": SNIPPET_CHARS, "enddate": before}
    for attempt in range(MAX_RETRIES):
        response = requests.get(NEWS_URL, params=params, timeout=30)
        if response.status_code == 429 or response.status_code >= 500:
            wait = 5 * 2**attempt
            print(f"  Steam news returned {response.status_code}, retrying in {wait}s...")
            time.sleep(wait)
            continue
        response.raise_for_status()
        time.sleep(SLEEP_SECONDS)
        return response.json().get("appnews", {}).get("newsitems", [])
    raise RuntimeError(f"Gave up after {MAX_RETRIES} attempts (last status {response.status_code})")

# Plain text from a news snippet, without HTML tags, BBCode or extra spaces
def plain_text(text: str) -> str:
    text = re.sub(r"<[^>]+>|\[/?[a-z0-9*]+(?:=[^\]]*)?\]", " ", text or "", flags=re.IGNORECASE)
    return " ".join(html.unescape(text).split())

# The fields kept for each news item
def keep_fields(item: dict) -> dict:
    official = item.get("feedname") == "steam_community_announcements"
    return {"gid": item["gid"], "date": item["date"], "title": plain_text(item.get("title", "")), "url": item.get("url"),
            "source": "Official announcement" if official else (item.get("feedlabel") or "News"), "official": official,
            "snippet": plain_text(item.get("contents", ""))}

# Fetch every news item between two Unix times, paging back from the end
def fetch_news_window(appid: int, start: int, end: int) -> list[dict]:
    items, before = [], end
    while True:
        page = get_news_page(appid, before)
        items += [keep_fields(item) for item in page if start <= item["date"] <= end]
        oldest = min((item["date"] for item in page), default=start)
        if len(page) < PAGE_SIZE or oldest <= start:
            return items
        before = oldest - 1

# News between two Unix times, fetching only windows the cache has not covered yet
def load_news(appid: int, start: int, end: int) -> list[dict]:
    path = news_path(appid)
    cache = json.loads(path.read_text()) if path.exists() else {"windows": [], "items": {}}
    now = int(datetime.now(timezone.utc).timestamp())
    covered = any(first <= start and end <= min(last, fetched) for first, last, fetched in cache["windows"])
    if not covered:
        print(f"  fetching news for {appid}, {datetime.fromtimestamp(start, timezone.utc):%Y-%m-%d} to "
              f"{datetime.fromtimestamp(end, timezone.utc):%Y-%m-%d}")
        for item in fetch_news_window(appid, start, end):
            cache["items"][item["gid"]] = item
        cache["windows"].append([start, end, now])
        DATA_DIR.mkdir(exist_ok=True)
        path.write_text(json.dumps(cache, indent=2))
    return sorted((item for item in cache["items"].values() if start <= item["date"] <= end), key=lambda item: item["date"])

# A day like "2024-05-01" as a Unix time at midnight UTC
def day_to_unix(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())

# Print the news around a date, for development
def main() -> None:
    parser = argparse.ArgumentParser(description="Print a game's Steam news between two dates (cached in data/).")
    parser.add_argument("appid", type=int)
    parser.add_argument("start", help="first day, like 2024-04-01")
    parser.add_argument("end", help="last day, like 2024-06-30")
    args = parser.parse_args()
    for item in load_news(args.appid, day_to_unix(args.start), day_to_unix(args.end)):
        print(f"{datetime.fromtimestamp(item['date'], timezone.utc):%Y-%m-%d}  {item['source']}: {item['title']}")

# Entry point
if __name__ == "__main__":
    main()
