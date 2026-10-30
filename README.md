# SteamTLDR

Explore why players like or dislike a Steam game, not just its score.

SteamTLDR is a personal learning project built to practice hands-on machine learning. Portions of the codebase are written with AI assistance from Claude Opus 5.5 with the intention of developing a learning exercise rather than a polished product.

<img width="3840" height="1865" alt="SteamTLDR - Home" src="https://github.com/user-attachments/assets/890e5aa3-9ada-4750-8478-5a30fe1bc55d" />

## Features

### Steam statistics

Metrics including all-time percent positive, Steam's rating, and the last 30 days compared with the all-time score.

### The Good & The Bad

Compare the most praised and most complained-about themes (performance, price, story, cheaters and more), each with an example quote from a real review.

<img width="3840" height="1865" alt="SteamTLDR - Overview" src="https://github.com/user-attachments/assets/2e66ed7c-6e3e-481d-915d-63cd88ed4920" />

### Recent sentiment

View what players have been unhappy about in the last 30 days, to spot new problems or recent fixes.

### Historical view

Monthly percent positive and review counts for a game's whole history.

<img width="3840" height="1865" alt="SteamTLDR - Graph" src="https://github.com/user-attachments/assets/0a634650-4eeb-4528-a675-71216964bfd4" />

### Playtime analysis

See how players with under 2 hours compare with those who have played 50+ hours.

### Outliers

Identify outliers every month across all games where negative reviews surged or the score dropped sharply, such as review bombs.

### Review randomizer

Read a random positive or negative review in full, fetched directly from Steam's review API.

### Growing game library dataset

<img width="3840" height="1865" alt="SteamTLDR - Games" src="https://github.com/user-attachments/assets/1db6f561-cb9f-43bd-ae50-782d1aa84f9f" />

## Methodology

1. **Collect reviews**: for each game, about 6,000 English reviews from Steam's public API, spread across the game's whole history. Scores and trends use Steam's exact totals, not the sample.
2. **Judge sentiment**: a TF-IDF + logistic regression model, trained on each review's thumbs up or down. Whole games are held out for testing, so the model is scored on games it has never seen.
3. **Find themes**: reviews are split into clauses ("great story *but* constant crashes") and matched against 15 keyword themes, like performance, price and story.
4. **Spot outliers**: a month is flagged when negative reviews surge or the score drops well below that game's usual level.
5. **Publish**: each game's summary is saved as a small JSON file that the web app reads.

## Results

### Sentiment model

On three games that it never saw during training, across 14,517 reviews:

| Metric | Score |
|---|---|
| Accuracy | 90.9% |
| Precision (negative reviews) | 0.88 |
| Recall (negative reviews) | 0.92 |
| F1 (negative reviews) | 0.90 |

### Transformer comparison

An off-the-shelf DistilBERT model *lost* to the simple baseline (the earlier 20-game version):

| Metric | Baseline (TF-IDF + logistic regression) | DistilBERT |
|---|---|---|
| Precision (negative reviews) | 0.88 | 0.76 |
| Recall (negative reviews) | 0.87 | 0.92 |
| F1 (negative reviews) | **0.88** | 0.83 |
| F1 on short reviews (5–25 words) | **0.79** | 0.69 |
| Speed (reviews per second) | **~10,600** | ~120 |

DistilBERT was trained on movie reviews, so gamer slang like "feet first into hell" and friendly suggestions like "could use a difficulty slider" read as negative to it. It catches slightly more negative reviews (higher recall), but flags too many positive ones by mistake (lower precision). Fine-tuning it on Steam reviews is a possible next step.

### Outliers

- 43 events (32 negative surges, 11 score drops) across 23 of the 60 games.
- this includes controversies such as Helldivers 2's PlayStation Network backlash in May 2024.

## Known Limitations

- **Keywords can't read context**: for example: Helldivers 2's enemy "bugs" count as bug complaints.
- **Sarcasm and negation** ("not bad at all") can fool a bag-of-words model.
- **English only**, and Steam's "English" is the language a reviewer selected, so some other-language text slips in.
- **Outliers** show that something happened, not why, or whether the reviews were fair.
- **Snapshots**: each game is fetched once and shows when it was last updated.
- **New games** have little monthly history, so trends and outliers say less about them.

## Project Structure

```
steam-tldr/
├── notebooks/        # marimo notebooks that teach each step, in order
│   ├── 01_explore.py           # data quality, review length, playtime, trends
│   ├── 02_text_to_numbers.py   # tokenizing, bag of words, TF-IDF
│   ├── 03_first_model.py       # train/test split, logistic regression
│   ├── 04_evaluating_models.py # confusion matrix, precision, recall, F1
│   ├── 05_themes.py            # keyword themes and clause scoring
│   └── 06_transformers.py      # baseline vs DistilBERT
├── src/
│   ├── fetch.py      # Steam API calls with caching and rate limiting
│   ├── games.py      # the 60 games
│   ├── model.py      # sentiment model training and evaluation
│   ├── themes.py     # theme matching and scoring
│   ├── summarize.py  # builds each game's summary and flags outliers
│   ├── export.py     # writes site_data/
│   ├── app.py        # Streamlit web app
│   └── ...           # transformer comparison and developer tools
└── site_data/        # exported summaries the app reads
```

### Getting Started

To run locally, SteamTLDR requires [uv](https://docs.astral.sh/uv/) and Python 3.14.

```bash
uv sync
uv run streamlit run src/app.py
```

The app runs straight from `site_data/`, with no fetching needed. To open the notebooks, run `uv run marimo edit notebooks/01_explore.py`. For the transformer comparison, install the extra packages with `uv sync --group transformer`.

## Data and Attribution

- Reviews and review statistics come from Steam's public [Web API](https://partner.steamgames.com/doc/webapi/IUserReviewsService), and game details from the Steam store
- SteamTLDR is not affiliated with or endorsed by Valve or Steam
- Game names, images and reviews belong to their respective owners
- Icons: [Lucide](https://lucide.dev) (ISC License) and [Material Symbols](https://fonts.google.com/icons) (Apache License 2.0)

## License

MIT. See [LICENSE](LICENSE).




