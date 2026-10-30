import joblib
import pandas as pd
from fetch import DATA_DIR
from games import GAMES
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline

# Provisional cleaning thresholds until the exploration decisions are made
MIN_WORDS = 5
MIN_LETTER_RATIO = 0.5

# Held-out test games, random seed, and saved model location
TEST_GAMES = [553850, 949230, 1030300]
RANDOM_SEED = 42
MODEL_PATH = DATA_DIR / "sentiment.joblib"

# Load every cached game into one table, one row per review
def load_dataset() -> pd.DataFrame:
    frames = []
    for appid, name in GAMES.items():
        path = DATA_DIR / f"{appid}.parquet"
        if path.exists():
            frames.append(pd.read_parquet(path).assign(appid=appid, game=name))
    reviews = pd.concat(frames, ignore_index=True)
    return reviews.drop_duplicates("recommendationid").reset_index(drop=True)

# Drop reviews too short or junky to learn from
def clean(reviews: pd.DataFrame) -> pd.DataFrame:
    words = reviews["review"].str.split().str.len()
    letter_ratio = reviews["review"].str.count(r"[A-Za-z]") / reviews["review"].str.len().clip(lower=1)
    return reviews[(words >= MIN_WORDS) & (letter_ratio >= MIN_LETTER_RATIO)].reset_index(drop=True)

# Split reviews into train and test sets by game
def split_by_game(reviews: pd.DataFrame, test_games: list[int] = TEST_GAMES) -> tuple[pd.DataFrame, pd.DataFrame]:
    is_test = reviews["appid"].isin(test_games)
    return reviews[~is_test].reset_index(drop=True), reviews[is_test].reset_index(drop=True)

# Build the TF-IDF and logistic regression pipeline
def build_model() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=5)),
        ("logreg", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=RANDOM_SEED)),
    ])

# Load the saved model
def load_model() -> Pipeline:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"No saved model at {MODEL_PATH}. Run: uv run python src/model.py")
    return joblib.load(MODEL_PATH)

# Evaluate on held-out games, then retrain on every game and save
def main() -> None:
    reviews = clean(load_dataset())
    train, test = split_by_game(reviews)
    print(f"Training on {len(train):,} reviews, testing on {len(test):,} from {', '.join(sorted(test['game'].unique()))}")
    model = build_model().fit(train["review"], train["voted_up"])
    print(classification_report(test["voted_up"], model.predict(test["review"]), target_names=["negative", "positive"], digits=3))

    final = build_model().fit(reviews["review"], reviews["voted_up"])
    joblib.dump(final, MODEL_PATH)
    print(f"Saved model trained on all {len(reviews):,} reviews from {reviews['game'].nunique()} games to {MODEL_PATH}")

# Entry point
if __name__ == "__main__":
    main()
