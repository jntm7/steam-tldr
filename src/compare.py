import pandas as pd
import time
from fetch import DATA_DIR
from model import build_model, clean, load_dataset, split_by_game
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from transformer import TransformerSentiment

# Where comparison scores are saved for the notebook
RESULTS_PATH = DATA_DIR / "model_comparison.parquet"
TRICKY_PATH = DATA_DIR / "tricky_cases.parquet"

# Word range that makes a review short enough to stand in for a single clause
SHORT_MIN_WORDS = 5
SHORT_MAX_WORDS = 25

# Hand-written sentences with obvious answers, grouped by what makes them hard
TRICKY_CASES = [
    ("negation", "Not bad at all, I actually had a lot of fun", True),
    ("negation", "I wouldn't say this game is good", False),
    ("negation", "Never had a single crash, runs perfectly", True),
    ("negation", "Not worth the money", False),
    ("negation", "I can't stop playing this", True),
    ("negation", "There is nothing fun about this game", False),
    ("negation", "Not a single bug in 100 hours", True),
    ("negation", "I don't hate it, but I can't recommend it either", False),
    ("sarcasm", "Great, another update that breaks everything", False),
    ("sarcasm", "Wow, only crashed five times tonight. Amazing optimization", False),
    ("sarcasm", "Love paying full price for a beta", False),
    ("sarcasm", "10/10 would get scammed again", False),
    ("clause", "The story is amazing", True),
    ("clause", "The servers are a disaster", False),
    ("clause", "Runs smoothly on my old laptop", True),
    ("clause", "The matchmaking takes forever", False),
    ("slang", "GOTY, no contest", True),
    ("slang", "Absolute cash grab", False),
    ("slang", "Peak gaming", True),
    ("slang", "Refunded after an hour", False),
    ("slang", "It's so mid", False),
    ("slang", "This game slaps", True),
]

# Precision, recall and F1 for negative reviews, plus accuracy
def scores(is_positive: pd.Series, prob_positive: pd.Series) -> dict:
    predicted = prob_positive >= 0.5
    return {
        "precision": precision_score(is_positive, predicted, pos_label=False),
        "recall": recall_score(is_positive, predicted, pos_label=False),
        "F1": f1_score(is_positive, predicted, pos_label=False),
        "accuracy": accuracy_score(is_positive, predicted),
    }

# Score held-out reviews and tricky cases with both models and save the results
def main() -> None:
    train, test = split_by_game(clean(load_dataset()))
    print(f"Test set: {len(test):,} reviews from {', '.join(sorted(test['game'].unique()))}")

    start = time.perf_counter()
    baseline = build_model().fit(train["review"], train["voted_up"])
    print(f"Baseline trained on {len(train):,} reviews in {time.perf_counter() - start:.0f}s")
    transformer = TransformerSentiment()

    timings = {}
    results = test[["recommendationid", "game", "voted_up", "review"]].copy()
    for name, model in (("baseline", baseline), ("transformer", transformer)):
        start = time.perf_counter()
        results[f"{name}_prob"] = model.predict_proba(results["review"])[:, 1]
        timings[name] = len(results) / (time.perf_counter() - start)
        print(f"{name}: {timings[name]:,.0f} reviews/second")
    results["words"] = results["review"].str.split().str.len()
    results.to_parquet(RESULTS_PATH, index=False)

    tricky = pd.DataFrame(TRICKY_CASES, columns=["kind", "text", "expected"])
    for name, model in (("baseline", baseline), ("transformer", transformer)):
        tricky[f"{name}_prob"] = model.predict_proba(tricky["text"])[:, 1]
    tricky.to_parquet(TRICKY_PATH, index=False)

    short = results[results["words"].between(SHORT_MIN_WORDS, SHORT_MAX_WORDS)]
    rows = []
    for subset, data in (("all test reviews", results), (f"short reviews ({SHORT_MIN_WORDS}-{SHORT_MAX_WORDS} words)", short)):
        for name in ("baseline", "transformer"):
            rows.append({"test set": subset, "model": name, "reviews": len(data), **scores(data["voted_up"], data[f"{name}_prob"])})
    print("\nNegative-review scores (threshold 0.5)")
    print(pd.DataFrame(rows).round(3).to_string(index=False))

    print("\nTricky cases correct")
    correct = tricky.assign(**{name: (tricky[f"{name}_prob"] >= 0.5) == tricky["expected"] for name in ("baseline", "transformer")})
    print(correct.groupby("kind")[["baseline", "transformer"]].sum().astype(int).assign(cases=correct.groupby("kind").size()).to_string())
    print(f"\nSaved scores to {RESULTS_PATH} and {TRICKY_PATH}")

# Entry point
if __name__ == "__main__":
    main()
