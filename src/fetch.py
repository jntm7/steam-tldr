import argparse
import json
import pandas as pd
import requests
import time
from datetime import datetime, timezone
from pathlib import Path

# API and fetch settings
API_URL = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
LIBRARY_IMAGE_URL = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{}/library_600x900.jpg"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_DAYS = 30
SLEEP_SECONDS = 1.0
MAX_RETRIES = 4

# Sample sizes for each part of a game's reviews
HELPFUL_REVIEWS = 1000
RECENT_DAYS = 30
RECENT_WINDOWS = 4
RECENT_REVIEWS = 1000
HISTORY_REVIEWS = 4000
MAX_PER_MONTH = 500

# Playtime groups as (min hours, max hours), where 0 max means no limit
PLAYTIME_BUCKETS = {"<2h": (0, 2), "2-10h": (2, 10), "10-50h": (10, 50), "50h+": (50, 0)}

# Shared query filters
BASE_PARAMS = {"purchase_type": 1, "filter": 0, "day_range": 0}

# Request one page of reviews
def get_page(params: dict) -> dict:
    for attempt in range(MAX_RETRIES):
        response = requests.get(API_URL, params=params, timeout=30)
        if response.status_code == 429 or response.status_code >= 500:
            wait = 5 * 2**attempt
            print(f"  Steam returned {response.status_code}, retrying in {wait}s...")
            time.sleep(wait)
            continue
        response.raise_for_status()
        time.sleep(SLEEP_SECONDS)
        return response.json()["response"]
    raise RuntimeError(f"Gave up after {MAX_RETRIES} attempts (last status {response.status_code})")

# Page through reviews up to the cap
def fetch_reviews(appid: int, max_reviews: int, **filters) -> tuple[list[dict], dict]:
    params = {"appid": appid, "cursor": "*", **BASE_PARAMS, **filters}
    reviews: list[dict] = []
    summary: dict = {}
    seen_cursors = set()

    while len(reviews) < max_reviews:
        params["num_per_page"] = min(100, max_reviews - len(reviews))
        data = get_page(params)
        if not summary:
            summary = data.get("query_summary", {})

        page = data.get("reviews", [])
        if not page:
            break
        reviews.extend(page)

        cursor = data.get("cursor")
        if not cursor or cursor in seen_cursors:
            break
        seen_cursors.add(cursor)
        params["cursor"] = cursor

    return reviews[:max_reviews], summary

# Flatten raw reviews into a table
def to_dataframe(reviews: list[dict]) -> pd.DataFrame:
    rows = []
    for r in reviews:
        author = r.get("author", {})
        hardware = r.get("hardware", {})
        rows.append({
            "recommendationid": r["recommendationid"],
            "review": r.get("review", ""),
            "voted_up": r["voted_up"],
            "votes_up": r.get("votes_up", 0),
            "votes_funny": r.get("votes_funny", 0),
            "weighted_vote_score": float(r.get("weighted_vote_score", 0)),
            "created": r["timestamp_created"],
            "updated": r.get("timestamp_updated"),
            "playtime_at_review_h": author.get("playtime_at_review", 0) / 60,
            "playtime_forever_h": author.get("playtime_forever", 0) / 60,
            "author_num_reviews": author.get("num_reviews", 0),
            "steam_purchase": r.get("steam_purchase"),
            "received_for_free": r.get("received_for_free"),
            "early_access": r.get("written_during_early_access"),
            "steam_deck": r.get("primarily_steam_deck"),
            "refunded": r.get("refunded"),
            "os": hardware.get("os"),
            "gpu": hardware.get("adapter_description"),
            "ram_mb": hardware.get("system_ram"),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["created"] = pd.to_datetime(df["created"], unit="s", utc=True)
    df["updated"] = pd.to_datetime(df["updated"], unit="s", utc=True)
    df["ram_mb"] = pd.to_numeric(df["ram_mb"], errors="coerce")
    return df.drop_duplicates("recommendationid")

# Split the last RECENT_DAYS into equal windows
def recent_windows(now: pd.Timestamp) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    step = pd.Timedelta(days=RECENT_DAYS / RECENT_WINDOWS)
    start = now - pd.Timedelta(days=RECENT_DAYS)
    edges = [start + step * i for i in range(RECENT_WINDOWS + 1)]
    return list(zip(edges, edges[1:]))

# Split the time between two dates into calendar months
def month_windows(first: pd.Timestamp, last: pd.Timestamp) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    month_start = first.normalize().replace(day=1)
    edges = [t for t in pd.date_range(month_start, last, freq="MS") if t < last] + [last]
    return list(zip(edges, edges[1:]))

# Fetch reviews and Steam's exact totals for each date window
def fetch_windows(appid: int, sample: str, windows: list, per_window: int) -> tuple[list[pd.DataFrame], list[dict]]:
    frames, periods = [], []
    for i, (start, end) in enumerate(windows, start=1):
        reviews, summary = fetch_reviews(appid, per_window, date_range_start=int(start.timestamp()),
                                         date_range_end=int(end.timestamp()))
        periods.append({
            "sample": sample,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "positive": summary.get("total_positive", 0),
            "negative": summary.get("total_negative", 0),
        })
        if reviews:
            frames.append(to_dataframe(reviews).assign(sample=sample, period=start))
        if i % 12 == 0 or i == len(windows):
            print(f"  {sample}: {i}/{len(windows)} windows")
    return frames, periods

# Look up a game's name, header image, developers, publishers, release date and genres on the Steam store
def fetch_app_details(appid: int) -> dict:
    params = {"appids": appid, "filters": "basic,developers,publishers,release_date,genres"}
    response = requests.get(APP_DETAILS_URL, params=params, timeout=30)
    time.sleep(SLEEP_SECONDS)
    details = response.json().get(str(appid), {}) if response.ok else {}
    data = details.get("data", {}) if details.get("success") else {}
    return {
        "name": data.get("name"),
        "header_image": data.get("header_image"),
        "developers": data.get("developers", []),
        "publishers": data.get("publishers", []),
        "release_date": data.get("release_date", {}).get("date") or None,
        "genres": [genre["description"] for genre in data.get("genres", [])],
    }

# Portrait library cover, if Steam has one at the usual link
def fetch_library_image(appid: int) -> str | None:
    url = LIBRARY_IMAGE_URL.format(appid)
    return url if requests.head(url, timeout=30).ok else None

# Fetch Steam's exact review totals for each playtime group
def fetch_playtime(appid: int) -> dict:
    totals = {}
    for group, (low, high) in PLAYTIME_BUCKETS.items():
        _, summary = fetch_reviews(appid, 1, playtime_min_hours=low, playtime_max_hours=high)
        totals[group] = {"positive": summary.get("total_positive", 0), "negative": summary.get("total_negative", 0)}
    return totals

# Fetch helpful, recent, and monthly samples for one game
def fetch_game(appid: int) -> tuple[pd.DataFrame, dict]:
    now = pd.Timestamp.now(tz="UTC")
    helpful, summary = fetch_reviews(appid, HELPFUL_REVIEWS)
    if not helpful:
        return pd.DataFrame(), {"summary": summary, "periods": []}
    helpful_df = to_dataframe(helpful).assign(sample="helpful", period=pd.NaT)
    print(f"  helpful: {len(helpful_df)} reviews")

    recent_frames, recent_periods = fetch_windows(appid, "recent", recent_windows(now),
                                                  RECENT_REVIEWS // RECENT_WINDOWS)

    months = month_windows(helpful_df["created"].min(), now - pd.Timedelta(days=RECENT_DAYS))
    per_month = min(MAX_PER_MONTH, max(1, HISTORY_REVIEWS // max(1, len(months))))
    monthly_frames, monthly_periods = fetch_windows(appid, "monthly", months, per_month)

    df = pd.concat([helpful_df, *recent_frames, *monthly_frames], ignore_index=True)
    return df, {
        **fetch_app_details(appid),
        "library_image": fetch_library_image(appid),
        "summary": summary,
        "periods": recent_periods + monthly_periods,
        "playtime": fetch_playtime(appid),
    }

# Build cache file paths
def cache_paths(appid: int) -> tuple[Path, Path]:
    stem = DATA_DIR / str(appid)
    return stem.with_suffix(".parquet"), stem.with_suffix(".json")

# Check if the cache is still fresh
def cache_is_fresh(meta_path: Path) -> bool:
    if not meta_path.exists():
        return False
    meta = json.loads(meta_path.read_text())
    fetched_at = datetime.fromisoformat(meta["fetched_at"])
    return (datetime.now(timezone.utc) - fetched_at).days < CACHE_DAYS

# Load reviews from cache or Steam
def load_reviews(appid: int, refresh: bool = False) -> tuple[pd.DataFrame, dict]:
    data_path, meta_path = cache_paths(appid)

    if not refresh and data_path.exists() and cache_is_fresh(meta_path):
        meta = json.loads(meta_path.read_text())
        print(f"  using cache from {meta['fetched_at'][:10]}")
        missing = {}
        if any(key not in meta for key in ("name", "header_image", "developers", "publishers", "release_date", "genres")):
            missing.update(fetch_app_details(appid))
        if "library_image" not in meta:
            missing["library_image"] = fetch_library_image(appid)
        if "playtime" not in meta:
            missing["playtime"] = fetch_playtime(appid)
        if missing:
            meta = {**meta, **missing}
            meta_path.write_text(json.dumps(meta, indent=2))
        return pd.read_parquet(data_path), meta

    df, meta = fetch_game(appid)
    if df.empty:
        return df, meta

    DATA_DIR.mkdir(exist_ok=True)
    df.to_parquet(data_path, index=False)
    meta = {"appid": appid, "fetched_at": datetime.now(timezone.utc).isoformat(), **meta}
    meta_path.write_text(json.dumps(meta, indent=2))
    return df, meta

# Stored details of every cached game
def cached_games() -> list[dict]:
    return [{**json.loads(path.read_text()), "appid": int(path.stem)}
            for path in DATA_DIR.glob("*.json") if path.stem.isdigit()]

# Fetch one game and print a summary
def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and cache Steam reviews for a game.")
    parser.add_argument("appid", type=int, help="Steam app ID (from store.steampowered.com/app/<appid>/)")
    parser.add_argument("--refresh", action="store_true", help="ignore the cache and re-fetch")
    args = parser.parse_args()

    print(f"Fetching reviews for app {args.appid}")
    df, meta = load_reviews(args.appid, args.refresh)
    summary = meta["summary"]
    total = summary.get("total_reviews", 0)
    if df.empty or not total:
        print("\nNo reviews found. Check the app ID.")
        return

    pct = 100 * summary["total_positive"] / total
    print(f"\nSteam score: {summary['review_score_desc']} ({pct:.1f}% positive of {total:,} English reviews)")

    recent = [p for p in meta["periods"] if p["sample"] == "recent"]
    recent_pos = sum(p["positive"] for p in recent)
    recent_total = recent_pos + sum(p["negative"] for p in recent)
    if recent_total:
        print(f"Last {RECENT_DAYS} days: {100 * recent_pos / recent_total:.1f}% positive of {recent_total:,} reviews")

    months = sum(p["sample"] == "monthly" for p in meta["periods"])
    print(f"Sampled {len(df):,} reviews: " + ", ".join(f"{n:,} {s}" for s, n in df["sample"].value_counts().items())
          + f" across {months} months")

# Entry point
if __name__ == "__main__":
    main()
