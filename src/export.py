import argparse
import json
import pandas as pd
from fetch import cached_games
from games import GAMES
from model import RANDOM_SEED
from pathlib import Path
from summarize import build_summary, display_name

# Where the exported summaries live, small enough to commit or host anywhere
EXPORT_DIR = Path(__file__).resolve().parent.parent / "site_data"
INDEX_NAME = "index.json"

# Summary fields that are tables, saved with their column names so empty ones keep their shape
TABLE_FIELDS = ["trend", "events", "playtime", "praise", "complaints", "recent_complaints", "shown_reviews"]

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
        "sampled_reviews": sampled_reviews,
        "summary": {key: steam.get(key) for key in ("total_positive", "total_negative", "total_reviews", "review_score_desc")},
    }

# Write one game's summary file and return its path
def export_summary(appid: int, refresh: bool = False) -> Path | None:
    summary = build_summary(appid, refresh)
    if summary is None:
        return None
    EXPORT_DIR.mkdir(exist_ok=True)
    path = EXPORT_DIR / f"{appid}.json"
    path.write_text(json.dumps(to_json_data(summary), separators=(",", ":")))
    return path

# Write the library index from every game already exported
def export_index() -> Path:
    exported = {int(path.stem) for path in EXPORT_DIR.glob("*.json") if path.stem.isdigit()}
    entries = [index_entry(meta, json.loads((EXPORT_DIR / f"{meta['appid']}.json").read_text())["sampled_reviews"])
               for meta in cached_games() if meta["appid"] in exported]
    path = EXPORT_DIR / INDEX_NAME
    path.write_text(json.dumps(entries, separators=(",", ":")))
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
    args = parser.parse_args()

    appids = args.appids or list(GAMES)
    for i, appid in enumerate(appids, start=1):
        print(f"[{i}/{len(appids)}] {GAMES.get(appid, appid)}", end=" ")
        path = export_summary(appid)
        print("skipped (no reviews)" if path is None else f"{path.stat().st_size / 1024:.0f} KB")
    print(f"Index: {export_index()}")

# Entry point
if __name__ == "__main__":
    main()
