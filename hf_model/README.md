---
library_name: sklearn
license: mit
language:
  - en
tags:
  - sentiment-analysis
  - text-classification
  - tf-idf
  - logistic-regression
  - steam
  - video-games
---

# SteamTLDR sentiment model

A small, fast sentiment classifier for English Steam game reviews. It predicts whether a review is a thumbs up (positive) or thumbs down (negative). It is the model behind [SteamTLDR](https://steamtldr.streamlit.app), which summarizes what players praise and complain about for each game.

Code and training pipeline: https://github.com/jntm7/steam-tldr

## Model details

- **Type:** scikit-learn `Pipeline` of `TfidfVectorizer` (word 1-grams and 2-grams, `min_df=5`) and `LogisticRegression` (`class_weight="balanced"`, `max_iter=1000`, `random_state=42`).
- **Input:** one review as a string. **Output:** the probability that the review is positive.
- **Size:** about 25 MB.
- **Trained with:** scikit-learn 1.9.1, joblib 1.6.0, Python 3.14. Load it with the same major versions, since pickled scikit-learn models can break across versions.

## Training data

English reviews from Steam's public review API for 100 games across many genres (shooters, RPGs, strategy, racing, gacha, free-to-play and indie titles). Each game contributes up to about 6,000 reviews, drawn from its most helpful, most recent and month-by-month history, so the model sees both old and new reviews.

- **Labels:** each review's own thumbs up or down (`voted_up`), so no manual labelling.
- **Cleaning:** reviews with fewer than 5 words, or where under half the characters are letters, were dropped.
- **Final model:** trained on all 426,308 cleaned reviews from the 100 games.
- **No reviewer identities:** the training pipeline does not use reviewer IDs or names. The model file stores a vocabulary and weights, not review text.

## Evaluation

Whole games were held out for testing, so the model is scored on games it has never seen. For this test, a version was trained on 411,791 reviews from 97 games and tested on 14,517 reviews from three held-out games: Helldivers 2, Cities: Skylines II and Hollow Knight: Silksong (a shooter, a city builder and a platformer).

| Class | Precision | Recall | F1 |
|---|---|---|---|
| Negative | 0.889 | 0.915 | 0.902 |
| Positive | 0.932 | 0.911 | 0.921 |

Overall accuracy is 91.3% (threshold 0.5). The headline number is F1 on negative reviews, because most games skew positive and accuracy alone would hide a model that ignores complaints.

For comparison, an off-the-shelf DistilBERT sentiment model scored an F1 of 0.83 on negative reviews in an earlier test on 20 games (precision 0.76, recall 0.92). The simple model beat it, mostly because DistilBERT was trained on movie reviews and misreads gamer slang. Fine-tuning it on Steam reviews was not tried.

## Usage

```python
import joblib
from huggingface_hub import hf_hub_download

path = hf_hub_download("jntam/steamtldr", "sentiment.joblib")
model = joblib.load(path)

reviews = [
    "Great game, the combat feels amazing and the story kept me hooked.",
    "Constant crashes and the servers are down every night. Do not buy.",
]
print(model.predict_proba(reviews)[:, 1])  # probability each review is positive
```

Only load pickle files from sources you trust. This file was produced by the training script in the repository above.

## Intended use and limits

- **Intended use:** scoring the sentiment of English Steam-style game reviews or short clauses taken from them, and learning how a simple text classifier works.
- **Sarcasm and negation:** the model reads word counts and two-word phrases, not sentence structure, so "not bad at all" or a sarcastic "love waiting 20 minutes for a match" can fool it.
- **Short text:** it leans positive on very short text, and short reviews (5–25 words) score lower than long ones.
- **Noisy labels:** the labels are thumbs up or down, which do not always match what the text says (misclicks, jokes, "recommended but...").
- **English only:** Steam's "English" is the language a reviewer selected, so some other-language text appears in the training data.
- **Domain:** trained on Steam reviews. Expect weaker results on other kinds of text.
