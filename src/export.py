import argparse
import json
import pandas as pd
from fetch import HELPFUL_REVIEWS, HISTORY_REVIEWS, RECENT_DAYS, RECENT_REVIEWS, cache_is_fresh, cache_paths, cached_games
from games import GAMES
from model import RANDOM_SEED
from pathlib import Path
from summarize import (DROP_MIN_REVIEWS, DROP_SCORE_POINTS, FLAG_LOOKBACK_MONTHS, SURGE_EXTRA_NEGATIVES, SURGE_NEGATIVE_RATIO,
                       SURGE_SCORE_DROP, build_summary, display_name)
from themes import FLIP_TO_COMPLAINT, FLIP_TO_PRAISE, PROBLEM_THEMES, THEMES
from event_reasons import REASONS_FIELD, current_reasons
from written_summary import WRITTEN_FIELD, input_hash

# Where the exported summaries live, small enough to commit or host anywhere
EXPORT_DIR = Path(__file__).resolve().parent.parent / "site_data"
INDEX_NAME = "index.json"
SETTINGS_NAME = "site.json"

# Summary fields that are tables, saved with their column names so empty ones keep their shape
TABLE_FIELDS = ["trend", "events", "playtime", "praise", "complaints", "recent_complaints", "playtime_complaints", "shown_reviews"]

# Columns holding dates, restored to timestamps on load
DATE_COLUMNS = ["start", "created"]

# How many readable reviews to keep per game for the random review box
EXPORTED_REVIEWS = 50

# Turn a summary into plain JSON data, keeping a fixed random sample of readable reviews
def to_json_data(summary: dict) -> dict:
    data = {key: value for key, value in summary.items() if key not in TABLE_FIELDS and key != "recent"}
    for field in TABLE_FIELDS:
        table = summary[field]
        if table is not None and field == "shown_reviews":
            table = table.sample(min(EXPORTED_REVIEWS, len(table)), random_state=RANDOM_SEED).reset_index(drop=True)
        data[field] = None if table is None else json.loads(table.to_json(orient="split", index=False, date_format="iso"))
    return data

# Rebuild the summary dict the app expects from JSON data
def from_json_data(data: dict) -> dict:
    summary = {key: value for key, value in data.items() if key not in TABLE_FIELDS}
    for field in TABLE_FIELDS:
        saved = data[field]
        table = None if saved is None else pd.DataFrame(saved["data"], columns=saved["columns"])
        if table is not None:
            for column in DATE_COLUMNS:
                if column in table:
                    table[column] = pd.to_datetime(table[column], format="ISO8601", utc=True)
        summary[field] = table
    summary["recent"] = summary["trend"].iloc[-1]
    return summary

# One library entry shaped like the cached metadata the library cards read
def index_entry(meta: dict, sampled_reviews: int) -> dict:
    steam = meta["summary"]
    return {
        "appid": meta["appid"],
        "name": meta.get("name"),
        "header_image": meta.get("header_image"),
        "library_image": meta.get("library_image"),
        "developers": meta.get("developers") or [],
        "genres": meta.get("genres") or [],
        "sampled_reviews": sampled_reviews,
        "summary": {key: steam.get(key) for key in ("total_positive", "total_negative", "total_reviews", "review_score_desc")},
    }

# Carry over the old written summary when the facts it was written from have not changed
def keep_written_summary(data: dict, path: Path) -> dict:
    old = json.loads(path.read_text()).get(WRITTEN_FIELD) if path.exists() else None
    if old and old.get("input_hash") == input_hash(data):
        data[WRITTEN_FIELD] = old
    return data

# Carry over old event explanations whose event facts have not changed
def keep_event_reasons(data: dict, path: Path) -> dict:
    old = json.loads(path.read_text()).get(REASONS_FIELD) if path.exists() else None
    kept = current_reasons({**data, REASONS_FIELD: old})
    if kept:
        data[REASONS_FIELD] = sorted(kept.values(), key=lambda record: record["start"])
    return data

# Whether the saved file already matches the cached Steam data, so the export can be skipped
def is_current(appid: int) -> bool:
    path = EXPORT_DIR / f"{appid}.json"
    _, meta_path = cache_paths(appid)
    if not path.exists() or not cache_is_fresh(meta_path):
        return False
    return json.loads(path.read_text()).get("fetched_at") == json.loads(meta_path.read_text()).get("fetched_at", "")[:10]

# Write a file only when its text changed
def write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text() == text:
        return False
    path.write_text(text)
    return True

# Write one game's summary file and return its path
def export_summary(appid: int, refresh: bool = False) -> Path | None:
    summary = build_summary(appid, refresh)
    if summary is None:
        return None
    EXPORT_DIR.mkdir(exist_ok=True)
    path = EXPORT_DIR / f"{appid}.json"
    write_if_changed(path, json.dumps(keep_event_reasons(keep_written_summary(to_json_data(summary), path), path), separators=(",", ":")))
    return path

# Write the library index from every game already exported
def export_index() -> Path:
    exported = {int(path.stem) for path in EXPORT_DIR.glob("*.json") if path.stem.isdigit()}
    entries = [index_entry(meta, json.loads((EXPORT_DIR / f"{meta['appid']}.json").read_text())["sampled_reviews"])
               for meta in cached_games() if meta["appid"] in exported]
    path = EXPORT_DIR / INDEX_NAME
    write_if_changed(path, json.dumps(entries, separators=(",", ":")))
    return path

# The sampling, theme and flag settings the website's FAQ quotes
def current_settings() -> dict:
    return {
        "helpful_reviews": HELPFUL_REVIEWS, "recent_reviews": RECENT_REVIEWS, "recent_days": RECENT_DAYS, "history_reviews": HISTORY_REVIEWS,
        "themes": THEMES, "problem_themes": sorted(PROBLEM_THEMES), "flip_to_complaint": FLIP_TO_COMPLAINT, "flip_to_praise": FLIP_TO_PRAISE,
        "flag_lookback_months": FLAG_LOOKBACK_MONTHS, "surge_negative_ratio": SURGE_NEGATIVE_RATIO, "surge_extra_negatives": SURGE_EXTRA_NEGATIVES,
        "surge_score_drop": SURGE_SCORE_DROP, "drop_min_reviews": DROP_MIN_REVIEWS, "drop_score_points": DROP_SCORE_POINTS,
    }

# Whether the saved settings differ from the current ones, which means every game needs rebuilding
def settings_changed() -> bool:
    path = EXPORT_DIR / SETTINGS_NAME
    return not path.exists() or json.loads(path.read_text()) != json.loads(json.dumps(current_settings()))

# Write the settings file
def export_settings() -> Path:
    path = EXPORT_DIR / SETTINGS_NAME
    write_if_changed(path, json.dumps(current_settings(), separators=(",", ":")))
    return path

# Read one exported summary, or None when it was never exported
def load_summary(appid: int) -> dict | None:
    path = EXPORT_DIR / f"{appid}.json"
    return from_json_data(json.loads(path.read_text())) if path.exists() else None

# Read the library index
def load_index() -> list[dict]:
    return json.loads((EXPORT_DIR / INDEX_NAME).read_text())

# Every flagged event across the exported games, one row per run of consecutive flagged months
def flagged_events() -> pd.DataFrame:
    columns = ["appid", "game", "header_image", "kind", "label", "start", "end", "months", "reviews", "extra_negatives",
               "pct_positive", "usual_pct", "drop_points"]
    rows = []
    for meta in load_index():
        flagged = load_summary(meta["appid"])["events"].assign(drop_points=lambda f: f["usual_pct"] - f["pct_positive"])
        for _, run in flagged.groupby("episode"):
            first, last = run.iloc[0], run.iloc[-1]
            rows.append({
                "appid": meta["appid"], "game": display_name(meta, meta["appid"]), "header_image": meta.get("header_image"),
                "kind": "Negative surge" if (run["kind"] == "Negative surge").any() else "Score drop",
                "label": first["label"], "start": first["start"], "end": last["start"], "months": len(run),
                "reviews": run["reviews"].sum(), "extra_negatives": run["extra_negatives"].sum(),
                "pct_positive": run["pct_positive"].min(), "usual_pct": first["usual_pct"], "drop_points": run["drop_points"].max(),
            })
    return pd.DataFrame(rows, columns=columns)

# Export the listed games, or the given ones
def main() -> None:
    parser = argparse.ArgumentParser(description="Export game summaries as small JSON files for the website.")
    parser.add_argument("appids", type=int, nargs="*", help="app IDs to export (default: every game in games.py)")
    parser.add_argument("--refresh", action="store_true", help="re-fetch from Steam even when the cache is under 30 days old")
    parser.add_argument("--force", action="store_true", help="rebuild every game from its cache, e.g. after retraining the model")
    args = parser.parse_args()

    force = args.force or args.refresh or settings_changed()
    appids = args.appids or list(GAMES)
    for i, appid in enumerate(appids, start=1):
        print(f"[{i}/{len(appids)}] {GAMES.get(appid, appid)}", end=" ")
        if not force and is_current(appid):
            print("unchanged")
            continue
        path = export_summary(appid, args.refresh)
        print("skipped (no reviews)" if path is None else f"{path.stat().st_size / 1024:.0f} KB")
    print(f"Index: {export_index()}")
    print(f"Settings: {export_settings()}")

# Entry point
if __name__ == "__main__":
    main()
