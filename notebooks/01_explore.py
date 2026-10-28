import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 01 · Explore the review data

    Before training anything, we look at the raw reviews to learn what we're working with. Each section answers one question, and the answers decide how we clean the data in the next step.

    1. How much data do we have per game, and how many negative reviews?
    2. How far off are our samples from Steam's real score?
    3. How long are reviews, and how many are too short to be useful?
    4. How much junk is there (ASCII art, emoji spam, non-English)?
    5. Does playtime change how people feel?
    6. What does sentiment over time look like?

    marimo is reactive: move a slider or pick a game and every cell that depends on it updates on its own.
    """)
    return


@app.cell
def _():
    import json
    import marimo as mo
    import matplotlib.pyplot as plt
    import pandas as pd
    import sys

    ROOT = mo.notebook_dir().parent
    DATA_DIR = ROOT / "data"
    sys.path.insert(0, str(ROOT / "src"))
    from games import GAMES
    return DATA_DIR, GAMES, json, mo, pd, plt


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Setup

    Load every cached game into one table. `df` keeps every row, including reviews that appear in more than one sample. `reviews` keeps each review once, so counts aren't inflated.
    """)
    return


@app.cell
def _(DATA_DIR, GAMES, json, mo, pd):
    _frames, metas, _missing = [], {}, []
    for _appid, _name in GAMES.items():
        _path = DATA_DIR / f"{_appid}.parquet"
        if not _path.exists():
            _missing.append(_name)
            continue
        _frames.append(pd.read_parquet(_path).assign(appid=_appid, game=_name))
        metas[_appid] = json.loads((DATA_DIR / f"{_appid}.json").read_text())

    df = pd.concat(_frames, ignore_index=True)
    reviews = df.drop_duplicates("recommendationid").reset_index(drop=True)

    mo.md(
        f"**{len(df):,}** rows, **{len(reviews):,}** unique reviews from **{len(metas)}** games"
        + (f"  \nNot fetched yet: {', '.join(_missing)}" if _missing else "")
    )
    return metas, reviews


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Data per game, and the sample-vs-Steam gap

    **What to look for:**

    - `negatives`: the model learns what "negative" looks like from these. A game with very few gives the model little to learn from, and that's a **class imbalance** problem.
    - `sample_pct` vs `steam_pct`: our samples come from Steam's *helpful* sort, which favors upvoted reviews. The gap shows how biased the samples are. This is why every percentage we show users comes from Steam's totals, never from our samples.
    """)
    return


@app.cell
def _(GAMES, metas, pd, reviews):
    _overview = reviews.groupby("game").agg(
        reviews=("voted_up", "size"),
        negatives=("voted_up", lambda s: (~s).sum()),
        sample_pct=("voted_up", lambda s: 100 * s.mean()),
    )
    _overview["steam_pct"] = pd.Series({
        GAMES[appid]: 100 * m["summary"]["total_positive"] / m["summary"]["total_reviews"]
        for appid, m in metas.items()
    })
    _overview["gap"] = _overview["sample_pct"] - _overview["steam_pct"]
    _overview.round(1).sort_values("steam_pct")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Review length

    Many Steam reviews are one word ("good", "10/10") or a meme. Those carry almost no information about *why* someone liked or disliked a game, so they don't help with themes and add noise to training.

    **What to look for:** the percentiles and histogram, then move the slider to see what reviews below each length look like. We'll use it to pick a minimum length.
    """)
    return


@app.cell
def _(reviews):
    words = reviews["review"].str.split().str.len()
    words.describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.99]).round(0).to_frame("words")
    return (words,)


@app.cell
def _(plt, words):
    _fig, _ax = plt.subplots(figsize=(9, 3))
    words.clip(upper=300).plot.hist(bins=60, ax=_ax)
    _ax.set(xlabel="words (capped at 300)", ylabel="reviews", title="Review length")
    _fig
    return


@app.cell
def _(mo):
    min_words = mo.ui.slider(1, 20, value=5, label="Minimum words", show_value=True)
    min_words
    return (min_words,)


@app.cell
def _(min_words, mo, reviews, words):
    _short = reviews[words < min_words.value]
    mo.vstack([
        mo.md(f"**{len(_short):,}** reviews (**{len(_short) / len(reviews):.1%}**) have fewer than {min_words.value} words"),
        _short[["game", "voted_up", "review"]].sample(min(15, len(_short)), random_state=42),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Junk reviews

    Some reviews are ASCII art, emoji spam, or written in Russian or Chinese, even though we asked for English. Steam goes by the language the reviewer *selected*, not what they actually wrote.

    A quick check is the **letter ratio**: the share of characters that are A–Z letters. Normal English text is mostly letters; ASCII art, emoji, and other alphabets aren't.

    **What to look for:** move the cutoff and check whether the reviews below it really are junk. If they are, a ratio cutoff is a cheap filter.
    """)
    return


@app.cell
def _(reviews):
    letter_ratio = reviews["review"].str.count(r"[A-Za-z]") / reviews["review"].str.len().clip(lower=1)
    return (letter_ratio,)


@app.cell
def _(mo):
    ratio_cutoff = mo.ui.slider(0.05, 0.9, step=0.05, value=0.5, label="Letter ratio cutoff", show_value=True)
    ratio_cutoff
    return (ratio_cutoff,)


@app.cell
def _(letter_ratio, mo, ratio_cutoff, reviews):
    _junk = reviews[letter_ratio < ratio_cutoff.value].assign(letter_ratio=letter_ratio.round(2))
    mo.vstack([
        mo.md(f"**{len(_junk):,}** reviews (**{len(_junk) / len(reviews):.1%}**) have a letter ratio below {ratio_cutoff.value}"),
        _junk[["game", "voted_up", "letter_ratio", "review"]].sample(min(15, len(_junk)), random_state=42),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Playtime

    Players with under 2 hours may be reacting to a first impression, a bad launch, or performance problems. Players with hundreds of hours clearly like the game enough to keep playing, even when they leave a negative review.

    **What to look for:** how the percent positive changes across playtime groups. These are sample percentages, so they carry the helpful-sort bias. Compare groups *within* a game rather than reading the numbers as exact.
    """)
    return


@app.cell
def _(pd, reviews):
    playtime_group = pd.cut(
        reviews["playtime_at_review_h"],
        bins=[0, 2, 10, 50, 200, float("inf")],
        labels=["<2h", "2-10h", "10-50h", "50-200h", "200h+"],
        right=False,
    )
    pd.crosstab(reviews["game"], playtime_group, values=reviews["voted_up"], aggfunc="mean").mul(100).round(0)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Sentiment over time (Steam's exact totals)

    These numbers come from Steam's per-month totals in `data/<appid>.json`, not from our samples, so they're exact. Look for sudden drops: a bad patch, a controversy, or a **review bomb** (a spike in volume *and* negativity at the same time). Try Helldivers 2 around May 2024.
    """)
    return


@app.cell
def _(GAMES, metas, mo):
    _options = {GAMES[appid]: appid for appid in metas}
    game_picker = mo.ui.dropdown(
        options=_options,
        value="Cyberpunk 2077" if "Cyberpunk 2077" in _options else next(iter(_options)),
        label="Game",
    )
    game_picker
    return (game_picker,)


@app.cell
def _(GAMES, game_picker, metas, pd, plt):
    _periods = pd.DataFrame(metas[game_picker.value]["periods"])
    _periods = _periods[_periods["sample"] == "monthly"].copy()
    _periods["start"] = pd.to_datetime(_periods["start"])
    _periods["total"] = _periods["positive"] + _periods["negative"]
    _periods["pct_positive"] = 100 * _periods["positive"] / _periods["total"]

    _fig, (_top, _bottom) = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    _top.plot(_periods["start"], _periods["pct_positive"])
    _top.set(ylabel="% positive", ylim=(0, 100), title=GAMES[game_picker.value])
    _bottom.bar(_periods["start"], _periods["total"], width=25)
    _bottom.set(ylabel="reviews per month")
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Hardware info

    Some reviews include the reviewer's GPU, OS, and RAM, mostly recent ones, since Steam only started attaching hardware info recently. It's too sparse for training, but it could help later, for example to check whether recent performance complaints cluster on certain GPUs.
    """)
    return


@app.cell
def _(mo, reviews):
    mo.vstack([
        mo.md(f"Reviews with GPU info: **{reviews['gpu'].notna().mean():.0%}**"),
        reviews["gpu"].value_counts().head(10).rename_axis("gpu").reset_index(name="reviews"),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## What we learned / decisions to make

    Fill these in after exploring:

    - **Minimum length:** drop reviews with fewer than __ words?
    - **Junk filter:** drop reviews with a letter ratio below __?
    - **Class imbalance:** which games have too few negatives to learn from?
    - **Playtime:** is the <2h vs 50h+ difference big enough to show users?
    - **Trends:** any review bombs or big recoveries worth flagging?

    The cleaning rules live in `src/model.py` (`MIN_WORDS`, `MIN_LETTER_RATIO`), set to provisional values for now. Update them once you've decided.

    **Next:** `02_text_to_numbers.py` shows how a review becomes numbers a model can learn from.
    """)
    return


if __name__ == "__main__":
    app.run()
