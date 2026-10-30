import argparse
import pandas as pd
import re
from fetch import load_reviews
from model import clean, load_model
from sklearn.pipeline import Pipeline

# Keywords that signal each theme
THEMES = {
    "performance": ["performance", "fps", "frame rate", "framerate", "frame drops", "stutter", "stuttering", "stutters",
                    "optimization", "optimized", "optimised", "unoptimized", "unoptimised", "runs well", "runs smooth",
                    "runs smoothly", "lag", "laggy", "loading times", "load times"],
    "bugs & crashes": ["bug", "bugs", "buggy", "glitch", "glitches", "glitchy", "crash", "crashes", "crashing", "crashed",
                       "freeze", "freezes", "freezing", "softlock", "broken", "unplayable"],
    "price & monetization": ["price", "priced", "pricing", "expensive", "overpriced", "cheap", "full price", "on sale",
                             "worth the money", "money", "microtransaction", "microtransactions", "mtx", "battle pass",
                             "pay to win", "p2w", "loot box", "loot boxes", "lootbox", "dlc", "dlcs", "greedy", "greed",
                             "cash grab", "refund", "refunded", "vc", "skins"],
    "servers & matchmaking": ["server", "servers", "matchmaking", "queue", "queues", "ping", "disconnect", "disconnects",
                              "disconnected", "connection", "netcode", "desync", "rubber banding", "rubberbanding"],
    "cheaters": ["cheater", "cheaters", "cheating", "cheat", "cheats", "hacker", "hackers", "hacking", "aimbot",
                 "wallhack", "anticheat", "anti-cheat", "anti cheat", "vac", "smurf", "smurfs", "smurfing"],
    "community": ["community", "toxic", "toxicity", "teammates", "randoms", "playerbase", "player base"],
    "co-op & multiplayer": ["co-op", "coop", "co op", "multiplayer", "with friends", "with my friends", "pvp", "pve",
                            "splitscreen", "split screen", "crossplay"],
    "story & characters": ["story", "storyline", "plot", "characters", "character", "writing", "written", "narrative",
                           "quest", "quests", "questline", "ending", "endings", "lore", "dialogue", "companions"],
    "gameplay & combat": ["gameplay", "combat", "mechanics", "gunplay", "movement", "weapons", "gameplay loop",
                          "boss fights", "bosses", "controls", "control scheme"],
    "graphics & art": ["graphics", "visuals", "visual", "visually", "art style", "artstyle", "art direction",
                       "beautiful", "gorgeous", "stunning", "textures", "animations", "pixel art"],
    "music & sound": ["music", "soundtrack", "ost", "sound design", "audio", "voice acting", "voice actors", "sound"],
    "content & grind": ["content", "endgame", "end game", "replayability", "replay value", "repetitive", "grind",
                        "grindy", "grinding", "variety", "too short", "hours of"],
    "difficulty": ["difficulty", "difficult", "challenging", "challenge", "punishing", "too hard", "too easy",
                   "soulslike", "souls-like"],
    "developers & updates": ["dev", "devs", "developer", "developers", "update", "updates", "patch", "patches",
                             "publisher", "roadmap", "support team", "customer support"],
    "accounts & launchers": ["account", "accounts", "psn", "launcher", "ea app", "epic games", "drm", "kernel",
                             "always online", "login", "log in"],
}

# Themes that only ever count as complaints
PROBLEM_THEMES = {"bugs & crashes", "cheaters"}

# Clause scores that flip a clause away from its review's thumbs up or down
FLIP_TO_COMPLAINT = 0.4
FLIP_TO_PRAISE = 0.8

# Regex per theme that matches any of its keywords as whole words
PATTERNS = {
    theme: re.compile(r"\b(?:" + "|".join(re.escape(k) for k in sorted(words, key=len, reverse=True)) + r")\b")
    for theme, words in THEMES.items()
}

# Punctuation and words where a review moves on to a new point
CLAUSE_BREAK = re.compile(r"[.!?;\n]+|\b(?:but|however|although|though|except|whereas)\b", re.IGNORECASE)

# Split a review into short clauses
def split_clauses(text: str) -> list[str]:
    return [c.strip() for c in CLAUSE_BREAK.split(text) if len(c.split()) >= 2]

# Find which themes a piece of text mentions
def find_themes(text: str) -> list[str]:
    lowered = text.lower()
    return [theme for theme, pattern in PATTERNS.items() if pattern.search(lowered)]

# List every clause that mentions a theme, one row per clause and theme
def theme_mentions(reviews: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for review in reviews.itertuples():
        for clause in split_clauses(review.review):
            for theme in find_themes(clause):
                rows.append({"recommendationid": review.recommendationid, "voted_up": review.voted_up,
                             "theme": theme, "clause": clause})
    return pd.DataFrame(rows, columns=["recommendationid", "voted_up", "theme", "clause"])

# Weight reviews so the sample's positive share matches Steam's real one
def review_weights(reviews: pd.DataFrame, positive_share: float) -> pd.Series:
    sample_share = reviews["voted_up"].mean()
    weights = reviews["voted_up"].map({True: positive_share / sample_share, False: (1 - positive_share) / (1 - sample_share)})
    return pd.Series(weights.to_numpy(), index=reviews["recommendationid"])

# Decide whether each mention is praise, starting from its review's label
def score_mentions(mentions: pd.DataFrame, model: Pipeline) -> pd.DataFrame:
    prob = model.predict_proba(mentions["clause"])[:, 1] if len(mentions) else []
    flip_to_complaint = mentions["voted_up"] & (prob < FLIP_TO_COMPLAINT)
    flip_to_praise = ~mentions["voted_up"] & (prob > FLIP_TO_PRAISE)
    positive = (mentions["voted_up"] & ~flip_to_complaint) | flip_to_praise
    return mentions.assign(prob_positive=prob, positive=positive & ~mentions["theme"].isin(PROBLEM_THEMES))

# Score each mention and summarize praise and complaints per theme
def summarize_themes(reviews: pd.DataFrame, model: Pipeline, positive_share: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    mentions = score_mentions(theme_mentions(reviews), model)
    weights = review_weights(reviews, positive_share)

    per_review = mentions.groupby(["theme", "recommendationid"])["positive"].agg(
        praised="any", complained=lambda s: (~s).any()
    ).reset_index()
    per_review["weight"] = per_review["recommendationid"].map(weights)
    total_weight = weights.sum()

    summary = per_review.groupby("theme").apply(lambda g: pd.Series({
        "reviews": len(g),
        "praise_pct": 100 * (g["weight"] * g["praised"]).sum() / total_weight,
        "complaint_pct": 100 * (g["weight"] * g["complained"]).sum() / total_weight,
    }), include_groups=False)
    return summary, mentions

# Print the top praised and complained-about themes for one game
def main() -> None:
    parser = argparse.ArgumentParser(description="Show the main praised and criticized themes for a Steam game.")
    parser.add_argument("appid", type=int, help="Steam app ID")
    args = parser.parse_args()

    df, meta = load_reviews(args.appid)
    summary = meta["summary"]
    if df.empty or not summary.get("total_reviews"):
        print("No reviews found. Check the app ID.")
        return

    reviews = clean(df.drop_duplicates("recommendationid").reset_index(drop=True))
    positive_share = summary["total_positive"] / summary["total_reviews"]
    themes, _ = summarize_themes(reviews, load_model(), positive_share)

    print(f"\nSteam score: {summary['review_score_desc']} ({100 * positive_share:.1f}% positive)")
    for label, column in (("Most praised", "praise_pct"), ("Top complaints", "complaint_pct")):
        print(f"\n{label}:")
        for theme, row in themes.sort_values(column, ascending=False).head(5).iterrows():
            print(f"  {theme:<24} {row[column]:5.1f}% of reviews  ({int(row['reviews'])} reviews mention it)")

# Entry point
if __name__ == "__main__":
    main()
