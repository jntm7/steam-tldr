# SteamTLDR

<!-- markdownlint-disable-next-line MD033 -->
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

### TL;DR summary

A short written summary at the top of each game page. Haiku 5.5 writes it from the game's own numbers, and plain code checks every number and quote against those numbers before it is published.

### Praise & Complaints

Compare the most praised and most complained-about themes, each with an example quote from a real review.

> Praises: gameplay & combat, content, story & characters, graphics & art, co-op & multiplayer
>
> Complaints: bugs & crashes, price & monetization, developer updates, servers, cheaters

### Recent sentiment

View what players have been unhappy about in the last 30 days, to spot new problems or recent fixes.

### Historical view

Monthly percent positive and review counts for a game's whole history.

![SteamTLDR Historical](https://github.com/user-attachments/assets/317b0ba8-05e4-44f3-a127-c7c6741f7395)

### Playtime analysis

See how players with under 2 hours compare with those who have played 50+ hours.

### Outliers

Identify outliers every month across all games where negative reviews surged or the score dropped sharply, such as review bombs. Each event gets a short explanation of what its negative reviews pointed to, with reason tags (account/DRM, monetization, bugs/performance and more) you can filter by, and links to the Steam news it cited.

### Review randomizer

Read a random positive or negative review in full, fetched directly from Steam's review API.

### Curated game library

SteamTLDR's dataset currently includes 200 games and training on 820,000+ reviews.

![SteamTLDR Library](https://github.com/user-attachments/assets/6084533c-67cd-4df3-ac7e-99fd8a26298d)

## Methodology

| Step | What happens |
| --- | --- |
| **1. Collect** | Up to 6,000 English reviews per game from Steam's public API: the 1,000 most helpful, 1,000 from the last 30 days, and up to 4,000 spread across earlier months. After duplicates are removed, a typical game has about 4,700. |
| **2. Score tone** | A TF-IDF + logistic regression model scores each clause from 0 (negative) to 1 (positive). TF-IDF counts words, giving rare ones more weight; logistic regression learns which words lean positive or negative from each review's thumbs up or down. |
| **3. Find themes** | Reviews are split into clauses ("great story *but* constant crashes") and matched to 16 keyword themes, like performance, price and story. |
| **4. Flag outliers** | A month is flagged when negative reviews surge or the score drops well below the game's usual level. |
| **5. Summarize** | Claude Haiku writes a short TL;DR from the game's numbers and explains each flagged event from its reviews and Steam news. Code checks every number, quote and tag before it is kept. |
| **6. Publish** | Each game is saved as a small JSON file that the website reads. |

Scores, review counts and trends always use Steam's exact totals. The sample is only used for themes and tone.

## Results

### Sentiment model

On three games that it never saw during training, across 14,517 reviews:

| Metric | Score |
| --- | --- |
| Accuracy | 92.0% |
| Precision (negative reviews) | 0.893 |
| Recall (negative reviews) | 0.929 |
| F1 (negative reviews) | 0.911 |

### Transformer comparison

An off-the-shelf DistilBERT model *lost* to the simple baseline (the earlier 20-game version):

| Metric | Baseline (TF-IDF + logistic regression) | DistilBERT |
| --- | --- | --- |
| Precision (negative reviews) | 0.88 | 0.76 |
| Recall (negative reviews) | 0.87 | 0.92 |
| F1 (negative reviews) | **0.88** | 0.83 |
| F1 on short reviews (5–25 words) | **0.79** | 0.69 |
| Speed (reviews per second) | **~10,600** | ~120 |

DistilBERT learned from movie reviews, so certain "gamer slang" reads as negative to it. It catches more negative reviews but also mislabels more positive ones. Fine-tuning it on Steam reviews could fix this.

### Game Summaries

Claude Haiku 5.5 writes each summary from the game's own numbers, and code checks it before it is published:

- Every number and quote must match the facts it cites.
- The checks verify numbers and quotes, not meaning, so a sentence can still stretch a point.

### Outliers & Event Explanations

Claude Haiku 5.5 explains each event in one or two sentences from that time's negative reviews and Steam news, and code checks every quote, number and tag.

| Finding | Result |
| --- | --- |
| Events | 87 across 54 games, all explained |
| Cite Steam news | 54 |
| Tagged unclear | 7 |
| Top tags | game changes (30), bugs/performance (29), monetization (29) |

## Known Limitations

- **Keywords can't read context**: for example: Helldivers 2's enemy "bugs" count as bug complaints.
- **Sarcasm and negation** ("not bad at all") can fool a bag-of-words model.
- **English only**, and Steam's "English" is the language a reviewer selected, so some other-language text slips in.
- **Event explanations** report what angry reviews pointed to, not whether the anger was fair; a tag only proves a cited line mentions its topic, not that it is the best fit.
- **Snapshots**: each game is fetched once and shows when it was last updated.
- **Written summaries** are checked for numbers and quotes, not meaning, so a sentence can still overstate a trend.
- **New games** have little monthly history, so trends and outliers say less about them.

## Project Structure

```bash
steam-tldr/
├── notebooks/                      # marimo notebooks that teach each step, in order
│   ├── 01_explore.py               # data quality, review length, playtime, trends
│   ├── 02_text_to_numbers.py       # tokenizing, bag of words, TF-IDF
│   ├── 03_first_model.py           # train/test split, logistic regression
│   ├── 04_evaluating_models.py     # confusion matrix, precision, recall, F1
│   ├── 05_themes.py                # keyword themes and clause scoring
│   └── 06_transformers.py          # baseline vs DistilBERT
├── src/
│   ├── fetch.py                    # Steam API calls with caching and rate limiting
│   ├── games.py                    # SteamTLDR's game library
│   ├── model.py                    # sentiment model training and evaluation
│   ├── themes.py                   # theme matching and scoring
│   ├── summarize.py                # builds each game's summary and flags outliers
│   ├── export.py                   # writes site_data/
│   ├── llm.py                      # one complete() CLI call to Claude Haiku
│   ├── written_summary.py          # TL;DR from the export's numbers, fact-checked
│   ├── news.py                     # Steam news around a date, cached in data/
│   ├── event_reasons.py            # why each flagged event happened
│   ├── check_site_data.py          # offline checks of site_data/ that CI runs
│   └── ...                         # transformer comparison and developer tools
├── site_data/                      # exported summaries the site reads
└── web/                            # Astro static site built from site_data/ (GitHub Pages)
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

The written summaries and event explanations come from separate scripts, ran using Claude Code CLI after an export. They skip games and events whose facts have not changed:

```bash
uv run python src/written_summary.py
uv run python src/event_reasons.py
```

## Notebooks

Six marimo notebooks in `notebooks/` walk through how the project was built in plain language, with live demos on real Steam reviews.

They need the raw reviews, which aren't in the repo:

```bash
uv run python src/fetch.py <appid>           # fetch one game (use Steam App ID)
uv run python src/games.py                   # fetch all games (not recommended)
uv run python src/model.py                   # train the model
uv run marimo edit notebooks/01_explore.py   # open a notebook
```

Notebook 06 also needs `uv sync --group transformer`.

## Data and Attribution

- Reviews and review statistics come from the public [Steam Web API](https://partner.steamgames.com/doc/webapi/IUserReviewsService), and game details from the Steam store.
- SteamTLDR is not affiliated with or endorsed by Valve. ©2026 Valve Corporation. Steam and the Steam logo are trademarks and/or registered trademarks of Valve Corporation in the U.S. and/or other countries.
- Game names, images and reviews belong to their respective owners.
- [Lucide](https://lucide.dev) (ISC License)
- [Material Symbols](https://fonts.google.com/icons) (Apache License 2.0)

## License

MIT. See [LICENSE](LICENSE).
