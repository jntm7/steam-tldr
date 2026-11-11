import argparse
import matplotlib.pyplot as plt
import pandas as pd
import re
from fetch import DATA_DIR, PLAYTIME_BUCKETS, RECENT_DAYS, load_reviews
from matplotlib.ticker import FuncFormatter
from model import clean, load_model
from themes import summarize_themes

# Negative-surge rule: a month's negative reviews and score compared with the months before it
FLAG_LOOKBACK_MONTHS = 6
SURGE_NEGATIVE_RATIO = 2.0
SURGE_EXTRA_NEGATIVES = 300
SURGE_SCORE_DROP = 10

# Score-drop rule: a steep fall in score without a surge of negative reviews
DROP_SCORE_POINTS = 20
DROP_MIN_REVIEWS = 500

# How much of each section the report shows
TOP_THEMES = 5
RECENT_THEMES = 5
EXAMPLES_SHOWN = 3
MIN_GROUP_REVIEWS = 100
GROUP_THEMES = 3
MIN_THEME_PCT = 5.0
MIN_RECENT_REVIEWS = 100
TREND_MONTHS = 12
SAME_SCORE_POINTS = 3

# Length limits in words for reviews shown whole
SHOWN_REVIEW_MIN_WORDS = 15
SHOWN_REVIEW_MAX_WORDS = 250

# Slurs and self-harm taunts kept out of quotes and shown reviews, so they never reach the site
BLOCKED_WORDS = re.compile(r"\b(?:n[i1]gg(?:er|a)s?|f[a4]gg?(?:ot)?s?|retard(?:s|ed)?|trann(?:y|ies)|kys|kill yourself)\b", re.IGNORECASE)

# Strip trademark symbols from Steam's game name
def display_name(meta: dict, appid: int) -> str:
    name = meta.get("name") or f"App {appid}"
    return name.replace("™", "").replace("®", "").strip()

# Percent positive, or None when there are no reviews
def pct_positive(positive: int, negative: int) -> float | None:
    total = positive + negative
    return 100 * positive / total if total else None

# Turn Steam's monthly totals into a table that ends with the last 30 days
def monthly_trend(meta: dict) -> pd.DataFrame:
    periods = pd.DataFrame(meta["periods"])
    periods["start"] = pd.to_datetime(periods["start"], format="ISO8601")
    months = periods[periods["sample"] == "monthly"].assign(label=lambda p: p["start"].dt.strftime("%Y-%m"))
    recent = periods[periods["sample"] == "recent"]
    last_days = pd.DataFrame([{
        "start": recent["start"].min(),
        "label": f"last {RECENT_DAYS}d",
        "positive": recent["positive"].sum(),
        "negative": recent["negative"].sum(),
    }])
    trend = pd.concat([months[["start", "label", "positive", "negative"]], last_days], ignore_index=True)
    trend["reviews"] = trend["positive"] + trend["negative"]
    trend["pct_positive"] = 100 * trend["positive"] / trend["reviews"].where(trend["reviews"] > 0)
    return trend

# Flag months with a surge of negative reviews and a drop in score, or a steep drop in score alone, grouping runs of months into episodes
def find_flagged_events(trend: pd.DataFrame) -> pd.DataFrame:
    def usual(column: str) -> pd.Series:
        return trend[column].rolling(FLAG_LOOKBACK_MONTHS, min_periods=3).median().shift(1)

    usual_reviews, usual_pct, usual_negative = usual("reviews"), usual("pct_positive"), usual("negative")
    extra_negatives = trend["negative"] - usual_negative
    drop = usual_pct - trend["pct_positive"]
    surge = ((extra_negatives >= SURGE_EXTRA_NEGATIVES) & (trend["negative"] >= SURGE_NEGATIVE_RATIO * usual_negative)
            & (drop >= SURGE_SCORE_DROP))
    steep = ~surge & (trend["reviews"] >= DROP_MIN_REVIEWS) & (drop >= DROP_SCORE_POINTS)
    flagged = surge | steep
    kind = pd.Series("Score drop", index=trend.index).where(~surge, "Negative surge")
    months = trend[flagged].assign(usual_reviews=usual_reviews[flagged], usual_pct=usual_pct[flagged],
                                   usual_negative=usual_negative[flagged], extra_negatives=extra_negatives[flagged], kind=kind[flagged])
    return months.assign(episode=(months.index.to_series().diff() != 1).cumsum())

# Steam's exact percent positive for each playtime group
def playtime_split(meta: dict) -> pd.DataFrame:
    rows = [{"group": group, "reviews": t["positive"] + t["negative"], "pct_positive": pct_positive(t["positive"], t["negative"])}
            for group, t in meta.get("playtime", {}).items()]
    return pd.DataFrame(rows, columns=["group", "reviews", "pct_positive"])

# Pick up to `count` short, clear example clauses for a theme, preferring ones whose review agrees
def example_clauses(mentions: pd.DataFrame, theme: str, praise: bool, used: set, count: int = 1) -> list[str]:
    rows = mentions[(mentions["theme"] == theme) & (mentions["positive"] == praise) & ~mentions["clause"].isin(used)
                    & ~mentions["clause"].str.contains(BLOCKED_WORDS)]
    words = rows["clause"].str.split().str.len()
    rows = rows[(words >= 6) & (words <= 25)]
    rows = rows.assign(agrees=rows["voted_up"] == praise)
    clauses = rows.sort_values(["agrees", "prob_positive"], ascending=[False, not praise])["clause"].drop_duplicates().head(count).tolist()
    used.update(clauses)
    return clauses

# Pick one example clause for a theme, or None
def example_clause(mentions: pd.DataFrame, theme: str, praise: bool, used: set) -> str | None:
    clauses = example_clauses(mentions, theme, praise, used)
    return clauses[0] if clauses else None

# The most common praised or complained-about themes, with an example each
def top_themes(themes: pd.DataFrame, mentions: pd.DataFrame, praise: bool, count: int = TOP_THEMES) -> pd.DataFrame:
    column = "praise_pct" if praise else "complaint_pct"
    top = themes[themes[column] >= MIN_THEME_PCT].sort_values(column, ascending=False).head(count)
    used: set = set()
    return pd.DataFrame({
        "theme": top.index,
        "pct": top[column].to_numpy(),
        "example": [example_clause(mentions, theme, praise, used) for theme in top.index],
    })

# Complaint themes in the last 30 days next to their all-time share, with a few quotes each, or None if there are too few reviews.
# Shows the biggest recent themes plus the biggest all-time ones, so themes that faded still appear
def recent_complaints(df: pd.DataFrame, recent: pd.Series, model, all_time: pd.DataFrame) -> pd.DataFrame | None:
    reviews = clean(df[df["sample"] == "recent"].drop_duplicates("recommendationid").reset_index(drop=True))
    if len(reviews) < MIN_RECENT_REVIEWS or not recent["reviews"]:
        return None
    themes, mentions = summarize_themes(reviews, model, recent["positive"] / recent["reviews"])
    recent_pct = themes["complaint_pct"].reindex(all_time.index).fillna(0)
    big_recent = themes[themes["complaint_pct"] >= MIN_THEME_PCT]["complaint_pct"].nlargest(RECENT_THEMES).index
    big_all_time = all_time[all_time["complaint_pct"] >= MIN_THEME_PCT]["complaint_pct"].nlargest(RECENT_THEMES).index
    shown = pd.DataFrame({"recent": themes["complaint_pct"], "all_time": all_time["complaint_pct"]}).fillna(0).loc[big_recent.union(big_all_time)]
    shown = shown.assign(top=shown.max(axis=1)).sort_values("top", ascending=False).head(RECENT_THEMES + 1)
    used: set = set()
    return pd.DataFrame({
        "theme": shown.index,
        "pct": shown["recent"].to_numpy(),
        "all_time_pct": shown["all_time"].to_numpy(),
        "examples": [example_clauses(mentions, theme, False, used, EXAMPLES_SHOWN) for theme in shown.index],
    })

# Top complaint themes for each playtime group (hours at review), weighted to Steam's exact score for that group
def playtime_complaints(reviews: pd.DataFrame, meta: dict, model) -> pd.DataFrame:
    rows = []
    for group, (low, high) in PLAYTIME_BUCKETS.items():
        hours = reviews["playtime_at_review_h"]
        sample = reviews[(hours >= low) & ((hours < high) if high else True)].reset_index(drop=True)
        totals = meta.get("playtime", {}).get(group)
        if len(sample) < MIN_GROUP_REVIEWS or not totals or not sample["voted_up"].nunique() == 2:
            continue
        themes, _ = summarize_themes(sample, model, totals["positive"] / (totals["positive"] + totals["negative"]))
        top = themes[themes["complaint_pct"] >= MIN_THEME_PCT]["complaint_pct"].nlargest(GROUP_THEMES)
        rows += [{"group": group, "theme": theme, "pct": pct} for theme, pct in top.items()]
    return pd.DataFrame(rows, columns=["group", "theme", "pct"])

# Reviews short enough to show whole and free of blocked words, with Steam's formatting tags removed
def readable_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    text = (reviews["review"]
            .str.replace(r"\[/?[a-z0-9*]+(?:=[^\]]*)?\]", " ", regex=True, flags=re.IGNORECASE)
            .str.replace(r"[ \t]+", " ", regex=True)
            .str.replace(r" *\n *", "\n", regex=True)
            .str.replace(r"\n{3,}", "\n\n", regex=True)
            .str.strip())
    words = text.str.split().str.len()
    keep = (words >= SHOWN_REVIEW_MIN_WORDS) & (words <= SHOWN_REVIEW_MAX_WORDS) & ~text.str.contains(BLOCKED_WORDS)
    columns = ["review", "voted_up", "playtime_at_review_h", "created"]
    return reviews.assign(review=text)[keep][columns].reset_index(drop=True)

# Build every part of a game's summary
def build_summary(appid: int, refresh: bool = False) -> dict | None:
    df, meta = load_reviews(appid, refresh)
    steam = meta["summary"]
    if df.empty or not steam.get("total_reviews"):
        return None

    model = load_model()
    reviews = clean(df.drop_duplicates("recommendationid").reset_index(drop=True))
    positive_share = steam["total_positive"] / steam["total_reviews"]
    themes, mentions = summarize_themes(reviews, model, positive_share)
    trend = monthly_trend(meta)
    return {
        "appid": appid,
        "name": display_name(meta, appid),
        "header_image": meta.get("header_image"),
        "developers": meta.get("developers") or [],
        "publishers": meta.get("publishers") or [],
        "release_date": meta.get("release_date"),
        "genres": meta.get("genres") or [],
        "fetched_at": meta.get("fetched_at", "")[:10],
        "score_desc": steam["review_score_desc"],
        "pct_positive": 100 * positive_share,
        "total_reviews": steam["total_reviews"],
        "recent": trend.iloc[-1],
        "trend": trend,
        "events": find_flagged_events(trend),
        "playtime": playtime_split(meta),
        "praise": top_themes(themes, mentions, praise=True),
        "complaints": top_themes(themes, mentions, praise=False),
        "recent_complaints": recent_complaints(df, trend.iloc[-1], model, themes),
        "playtime_complaints": playtime_complaints(reviews, meta, model),
        "sampled_reviews": len(reviews),
        "shown_reviews": readable_reviews(reviews),
    }

# Describe how the last 30 days compare with the overall score
def recent_direction(summary: dict) -> str:
    change = summary["recent"]["pct_positive"] - summary["pct_positive"]
    if abs(change) < SAME_SCORE_POINTS:
        return "about the same as overall"
    return f"{abs(change):.0f} points {'better' if change > 0 else 'worse'} than overall"

# Draw a text bar for a percentage
def text_bar(pct: float, width: int = 20) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)

# Shorten long text for one-line display
def shorten(text: str, limit: int = 90) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

# Print the summary as a readable report
def print_summary(summary: dict) -> None:
    title = f"{summary['name']} (app {summary['appid']})"
    print(f"\n{title}\n{'=' * len(title)}")
    print(f"Steam score:   {summary['score_desc']}, {summary['pct_positive']:.1f}% positive of {summary['total_reviews']:,} English reviews")
    recent = summary["recent"]
    if recent["reviews"]:
        print(f"Last {RECENT_DAYS} days:  {recent['pct_positive']:.1f}% positive of {int(recent['reviews']):,} reviews ({recent_direction(summary)})")

    sections = [("Most praised", summary["praise"]), ("Top complaints", summary["complaints"])]
    if summary["recent_complaints"] is not None:
        sections.append((f"Top complaints in the last {RECENT_DAYS} days", summary["recent_complaints"]))
    for heading, rows in sections:
        print(f"\n{heading}")
        if rows.empty:
            print("  (nothing stands out)")
        for row in rows.itertuples():
            quotes = [row.example] if hasattr(row, "example") and row.example else list(getattr(row, "examples", []))
            example = f'  "{shorten(quotes[0])}"' if quotes else ""
            print(f"  {row.theme:<24} {row.pct:4.0f}% of reviews{example}")

    print("\nBy playtime at review")
    for row in summary["playtime"].itertuples():
        if row.pct_positive is not None and row.reviews:
            print(f"  {row.group:<7} {text_bar(row.pct_positive)} {row.pct_positive:4.0f}% positive  ({row.reviews:,} reviews)")

    print(f"\nLast {TREND_MONTHS} months")
    for row in summary["trend"].tail(TREND_MONTHS + 1).itertuples():
        if row.reviews:
            print(f"  {row.label:<9} {text_bar(row.pct_positive)} {row.pct_positive:4.0f}%  {row.reviews:>9,} reviews")

    flagged = summary["events"]
    print("\nFlagged events")
    if flagged.empty:
        print("  none found")
    for row in flagged.itertuples():
        print(f"  {row.label}: {row.kind.lower()}, {row.reviews:,} reviews ({row.extra_negatives:+,.0f} negatives vs usual), "
              f"{row.pct_positive:.0f}% positive vs usual {row.usual_pct:.0f}%")

    print(f"\nThemes are estimated from {summary['sampled_reviews']:,} sampled reviews; scores, playtime and trends are Steam's exact totals.")

# Save a monthly sentiment chart with flagged months marked
def plot_trend(summary: dict) -> str:
    trend = summary["trend"].dropna(subset=["pct_positive"])
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True, height_ratios=[2, 1])
    top.plot(trend["start"], trend["pct_positive"], marker=".")
    top.axhline(summary["pct_positive"], linestyle="--", linewidth=0.8, color="gray", label="overall")
    top.scatter(summary["events"]["start"], summary["events"]["pct_positive"], color="tab:red", zorder=3, label="flagged event")
    top.set(ylabel="% positive", ylim=(0, 100), title=f"{summary['name']}: sentiment by month")
    top.legend(loc="lower left")
    bottom.bar(trend["start"], trend["reviews"], width=25)
    bottom.set(ylabel="reviews")
    bottom.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
    fig.tight_layout()
    path = DATA_DIR / f"{summary['appid']}_trend.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return str(path)

# Fetch, analyze, and print a summary for one game
def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize how players feel about a Steam game.")
    parser.add_argument("appid", type=int, help="Steam app ID (from store.steampowered.com/app/<appid>/)")
    parser.add_argument("--refresh", action="store_true", help="ignore the cache and re-fetch")
    parser.add_argument("--chart", action="store_true", help="also save a sentiment-over-time chart")
    args = parser.parse_args()

    summary = build_summary(args.appid, args.refresh)
    if summary is None:
        print("No reviews found. Check the app ID.")
        return
    print_summary(summary)
    if args.chart:
        print(f"\nChart saved to {plot_trend(summary)}")

# Entry point
if __name__ == "__main__":
    main()
