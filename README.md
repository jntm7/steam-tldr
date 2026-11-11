# SteamTLDR

<div align="center">
   
   [![SteamTLDR](https://github.com/user-attachments/assets/2e1210e3-fa4b-4794-a216-d1b1e3ea8f9f)](https://steamtldr.jntam.ca)
   ![License](https://img.shields.io/github/license/jntm7/steam-tldr)
   ![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
   ![Astro](https://img.shields.io/badge/Astro-site-BC52EE?logo=astro&logoColor=white)
   ![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikitlearn&logoColor=white)
   ![pandas](https://img.shields.io/badge/pandas-data-150458?logo=pandas&logoColor=white)
   
   [steamtldr.jntam.ca](https://steamtldr.jntam.ca)
   
</div>

SteamTLDR is a personal project built to get hands-on practice with machine learning and sentiment analysis.

> Portions of the project contain AI-assisted code. It is a learning exercise rather than a complete product.

![SteamTLDR Home](https://github.com/user-attachments/assets/b3d54cfa-d795-4e78-b534-97bd4389d565)

## Features

![SteamTLDR Helldivers 2](https://github.com/user-attachments/assets/c0454358-374b-4214-bd21-ed1473c52f64)

### Steam statistics

Metrics including all-time percent positive, Steam's rating, and the last 30 days compared with the all-time score.

### Praise & Complaints

Compare the most praised and most complained-about themes, each with an example quote from a real review.

> Common praises: gameplay & combat, content, story & characters, graphics & art, co-op & multiplayer

> Common complaints: bugs & crashes, price & monetization, developer updates, servers, cheaters

### Recent sentiment

View what players have been unhappy about in the last 30 days, to spot new problems or recent fixes.

### Historical view

Monthly percent positive and review counts for a game's whole history.

![SteamTLDR Historical](https://github.com/user-attachments/assets/317b0ba8-05e4-44f3-a127-c7c6741f7395)

### Playtime analysis

See how players with under 2 hours compare with those who have played 50+ hours.

### Outliers

Identify outliers every month across all games where negative reviews surged or the score dropped sharply, such as review bombs.

### Review randomizer

Read a random positive or negative review in full, fetched directly from Steam's review API.

### Curated game library

SteamTLDR's dataset currently includes 200 games and training on 820,000+ reviews.

![SteamTLDR Library](https://github.com/user-attachments/assets/6084533c-67cd-4df3-ac7e-99fd8a26298d)

## Methodology
1. **Collect reviews**: for each game, up to 6,000 English reviews from Steam's public API, built from three groups:
   - **Most helpful**: the 1,000 most helpful reviews of all time.
   - **Recent**: up to 1,000 from the last 30 days, in four windows of 250.
   - **Monthly**: up to 4,000 spread evenly across every earlier month, at most 500 per month.
   - Reviews that appear in more than one group are counted once, so a typical game ends up with about 4,700.
   - New games have far fewer, since they have little monthly history.
   - Scores, review counts and trends use Steam's exact totals, not the sample.
2. **Judge sentiment**: a TF-IDF + logistic regression model, trained on each review's thumbs up or down. It works in two steps:
   - **TF-IDF** turns each review into numbers by counting its words and two-word phrases, giving more weight to distinctive ones ("crashes", "refund") than to common ones ("the", "game").
   - **Logistic regression** learns one weight per word or phrase, so that adding up a review's weights gives a positive score for thumbs-up reviews and a negative one for thumbs-down. The sum becomes a probability between 0 and 1.
   - It reads word counts, not sentence structure, so it is fast (trained on 820k+ reviews in minutes) and easy to inspect, and it beat an off-the-shelf DistilBERT here. Whole games are held out for testing, so the model is scored on games it has never seen.
3. **Find themes**: reviews are split into clauses ("great story *but* constant crashes") and matched against 16 keyword themes, like performance, price and story.
4. **Spot outliers**: a month is flagged when negative reviews surge or the score drops well below that game's usual level.
5. **Publish**: each game's summary is saved as a small JSON file that the web app reads.

## Results

### Sentiment model

On three games that it never saw during training, across 14,517 reviews:

| Metric | Score |
|---|---|
| Accuracy | 92.0% |
| Precision (negative reviews) | 0.893 |
| Recall (negative reviews) | 0.929 |
| F1 (negative reviews) | 0.911 |

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

- 87 events (71 negative surges, 16 score drops) across 54 of the 200 games.
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
├── notebooks/                  # marimo notebooks that teach each step, in order
│   ├── 01_explore.py           # data quality, review length, playtime, trends
│   ├── 02_text_to_numbers.py   # tokenizing, bag of words, TF-IDF
│   ├── 03_first_model.py       # train/test split, logistic regression
│   ├── 04_evaluating_models.py # confusion matrix, precision, recall, F1
│   ├── 05_themes.py            # keyword themes and clause scoring
│   └── 06_transformers.py      # baseline vs DistilBERT
├── src/
│   ├── fetch.py      # Steam API calls with caching and rate limiting
│   ├── games.py      # the 200 games
│   ├── model.py      # sentiment model training and evaluation
│   ├── themes.py     # theme matching and scoring
│   ├── summarize.py  # builds each game's summary and flags outliers
│   ├── export.py     # writes site_data/
│   └── ...           # transformer comparison and developer tools
├── site_data/        # exported summaries the site reads
└── web/              # Astro static site built from site_data/ (GitHub Pages)
```

### Getting Started

The website needs [Node.js](https://nodejs.org/) and runs straight from `site_data/`, with no fetching needed:

```bash
npm install --prefix web
npm run dev --prefix web
```

The Python pipeline (fetching, the model, themes and exports) needs [uv](https://docs.astral.sh/uv/) and Python 3.14:

```bash
uv sync
uv run python src/export.py
```

## Notebooks

The `notebooks/` directory contains six marimo notebooks generated by Claude that walk through how the project was built, step by step. They are written to explain ideas in plain language to developers who are new to machine learning, and include live demo examples to try them on real Steam reviews.

Open one with:

```bash
uv run marimo edit notebooks/01_explore.py
```

The notebooks read the raw review data, which isn't included in the repo. There are two options:

- fetch it with `uv run python src/fetch.py <appid>` (this fetches individual games with their Steam app ID).
- fetch it with `uv run python src/games.py` (this calls Steam's API for all 200 games and takes a long time)

Then train the model with `uv run python src/model.py`. Notebook 06 also needs `uv sync --group transformer`.

## Data and Attribution

- Reviews and review statistics come from Steam's public [Web API](https://partner.steamgames.com/doc/webapi/IUserReviewsService), and game details from the Steam store
- SteamTLDR is not affiliated with or endorsed by Valve or Steam
- Game names, images and reviews belong to their respective owners
- Icons: [Lucide](https://lucide.dev) (ISC License) and [Material Symbols](https://fonts.google.com/icons) (Apache License 2.0)

## License

MIT. See [LICENSE](LICENSE).




