import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 06 · Is a transformer better than our baseline?

    Our baseline (TF-IDF + logistic regression) reads a review as a bag of words: it never knows *which* word "not" belongs to. **Transformers** are the kind of model behind modern AI tools. They read the whole sentence and use word order and context, so in theory they should handle "not good" and mixed reviews much better.

    This notebook tests that claim on our Steam data:

    1. What a transformer is, in plain terms
    2. Trying both models side by side
    3. Hand-written tricky cases (negation, sarcasm, slang)
    4. Scores on the held-out games
    5. Why the "smarter" model loses here
    6. Speed and cost
    7. What would make it better: **fine-tuning**

    It reads scores saved by `uv run python src/compare.py` (about 3 minutes), so run that first.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import sys
    import time

    sys.path.insert(0, str(mo.notebook_dir().parent / "src"))
    from compare import RESULTS_PATH, SHORT_MAX_WORDS, SHORT_MIN_WORDS, TRICKY_PATH, scores
    from model import build_model, clean, load_dataset, split_by_game
    from transformer import DEVICE, MODEL_NAME, TransformerSentiment
    return (
        DEVICE,
        MODEL_NAME,
        RESULTS_PATH,
        SHORT_MAX_WORDS,
        SHORT_MIN_WORDS,
        TRICKY_PATH,
        TransformerSentiment,
        build_model,
        clean,
        load_dataset,
        mo,
        np,
        pd,
        plt,
        scores,
        split_by_game,
        time,
    )


@app.cell
def _(RESULTS_PATH, TRICKY_PATH, mo, pd):
    mo.stop(not RESULTS_PATH.exists(), mo.md("**No comparison results yet.** Run `uv run python src/compare.py` in a terminal, then re-run this cell."))
    results = pd.read_parquet(RESULTS_PATH)
    tricky = pd.read_parquet(TRICKY_PATH)
    return results, tricky


@app.cell(hide_code=True)
def _(MODEL_NAME, mo):
    mo.md(rf"""
    ## 1. What is a transformer?

    Three ideas cover most of it:

    - **Tokens are word pieces.** Instead of whole words, text is split into common chunks, so a word it doesn't know, like "unoptimised", becomes `uno`, `##pt`, `##imi`, `##sed` (`##` means "joined to the piece before"). That means the model never meets a word it can't handle.
    - **Attention: every word looks at every other word.** For each token, the model works out which other tokens matter for its meaning. In "the game is not good", the token `good` pays attention to `not`. That's how it can tell "not good" from "good" in a way bag of words can't. A transformer is many layers of this stacked up.
    - **Pretrained, then specialised.** Training one from scratch takes enormous amounts of text and computing power. Instead, someone **pretrains** it once on huge amounts of general text (books, Wikipedia) so it learns how language works. Then it gets **fine-tuned**: trained a bit more on a specific task with labels. Reusing a pretrained model like this is called **transfer learning**.

    The model we're using is `{MODEL_NAME}`. **DistilBERT** is a smaller, faster version of a famous transformer called BERT. It was fine-tuned on **SST-2**, a dataset of short *movie review* sentences labelled positive or negative. We use it **off the shelf**: it has never seen a Steam review.
    """)
    return


@app.cell
def _(TransformerSentiment, build_model, clean, load_dataset, split_by_game):
    _train, test_reviews = split_by_game(clean(load_dataset()))
    baseline = build_model().fit(_train["review"], _train["voted_up"])
    transformer = TransformerSentiment()
    return baseline, test_reviews, transformer


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Try both models

    The baseline here is trained without the test games, as in notebook 03. Type anything and compare the two. The token list shows how the transformer splits your text into word pieces.
    """)
    return


@app.cell
def _(mo):
    compare_text = mo.ui.text_area(value="I wouldn't say this game is good, but the soundtrack slaps", label="Your text", full_width=True)
    compare_text
    return (compare_text,)


@app.cell
def _(baseline, compare_text, mo, transformer):
    _baseline_prob = baseline.predict_proba([compare_text.value])[0, 1]
    _transformer_prob = transformer.predict_proba([compare_text.value])[0, 1]
    _tokens = transformer.tokenizer.tokenize(compare_text.value)
    mo.md(f"""
    | model | probability positive | verdict |
    |---|---|---|
    | baseline (TF-IDF + logistic regression) | **{_baseline_prob:.0%}** | {'👍' if _baseline_prob >= 0.5 else '👎'} |
    | transformer (DistilBERT, SST-2) | **{_transformer_prob:.0%}** | {'👍' if _transformer_prob >= 0.5 else '👎'} |

    **Transformer tokens ({len(_tokens)}):** {' · '.join(f'`{t}`' for t in _tokens)}
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Tricky cases

    These are hand-written sentences with obvious answers, grouped by what makes them hard. Think of them as unit tests for the weaknesses we expected: **negation**, **sarcasm**, single **clauses** like the ones theme finding scores, and gamer **slang**.
    """)
    return


@app.cell
def _(mo, tricky):
    _table = tricky.assign(
        expected=tricky["expected"].map({True: "👍", False: "👎"}),
        baseline=[f"{'✅' if (p >= 0.5) == e else '❌'} {p:.2f}" for p, e in zip(tricky["baseline_prob"], tricky["expected"])],
        transformer=[f"{'✅' if (p >= 0.5) == e else '❌'} {p:.2f}" for p, e in zip(tricky["transformer_prob"], tricky["expected"])],
    )[["kind", "text", "expected", "baseline", "transformer"]]
    _correct = tricky.assign(
        baseline=(tricky["baseline_prob"] >= 0.5) == tricky["expected"],
        transformer=(tricky["transformer_prob"] >= 0.5) == tricky["expected"],
    ).groupby("kind")[["baseline", "transformer"]].sum()
    mo.vstack([_table, mo.md("**Correct per group**"), _correct.assign(cases=tricky.groupby("kind").size())])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The transformer does better on classic **negation** ("I wouldn't say this game is good"), as promised. But it's worse on **slang** ("This game slaps", "GOTY, no contest") and on some plain complaints ("The matchmaking takes forever"). Neither model handles **sarcasm**. Sarcasm is hard even for much bigger models, because the words say the opposite of what's meant.

    ## 4. Scores on the held-out games

    Now the real test: every review from the three held-out games, scored by both models, using the negative-review scores from notebook 04. "Short reviews" stand in for the clauses that theme finding scores, since we don't have labels for individual clauses.
    """)
    return


@app.cell
def _(SHORT_MAX_WORDS, SHORT_MIN_WORDS, pd, results, scores):
    _short = results[results["words"].between(SHORT_MIN_WORDS, SHORT_MAX_WORDS)]
    _rows = []
    for _subset, _data in (("all test reviews", results), (f"short reviews ({SHORT_MIN_WORDS}-{SHORT_MAX_WORDS} words)", _short)):
        for _name in ("baseline", "transformer"):
            _rows.append({"test set": _subset, "model": _name, "reviews": len(_data), **scores(_data["voted_up"], _data[f"{_name}_prob"])})
    pd.DataFrame(_rows).round(3).set_index(["test set", "model"])
    return


@app.cell
def _(pd, results, scores):
    _rows = []
    for _game, _data in results.groupby("game"):
        for _name in ("baseline", "transformer"):
            _rows.append({"game": _game, "model": _name, **scores(_data["voted_up"], _data[f"{_name}_prob"])})
    pd.DataFrame(_rows).round(3).set_index(["game", "model"])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **The baseline wins** on every game (Cities: Skylines II is close) and on short reviews. The transformer catches *more* negative reviews (higher recall) but raises far more false alarms (lower precision), so its F1 is lower.

    ## 5. Why the "smarter" model loses

    **Different kind of text.** The transformer learned sentiment from movie review sentences. Steam reviews are full of gamer language where "negative" words are positive: "FEET FIRST INTO HELL", "tornado destroyed it, cried, rebuilt it. 10/10", "too ez, giga poggers". It also treats any criticism as negative, so "Great game, could use a difficulty slider" scores almost 0. Steam reviewers mention flaws constantly, even in glowing reviews. Our baseline learned from 55,000 *Steam* reviews, so it knows that "10/10" and "hell" mean very different things here.

    This is called **domain mismatch**: a model trained on one kind of data doing worse on another. It's one of the most common reasons ML projects disappoint.

    **Overconfidence.** Look at how sure each model is. The baseline spreads its probabilities out; the transformer almost always says 0% or 100%, even when it's wrong. A model whose probabilities match how often it's actually right is called **well calibrated**. Our theme finding relies on probabilities ("only overrule the thumbs up below 0.4"), so calibration matters for us.
    """)
    return


@app.cell
def _(plt, results):
    _fig, _axes = plt.subplots(1, 2, figsize=(10, 3.2), sharey=True)
    for _ax, _name in zip(_axes, ("baseline", "transformer")):
        _ax.hist(results[f"{_name}_prob"], bins=40)
        _ax.set(title=_name, xlabel="probability positive")
    _axes[0].set_ylabel("reviews")
    _fig.tight_layout()
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Read where they disagree. Pick a case:
    """)
    return


@app.cell
def _(mo):
    disagreement = mo.ui.dropdown(
        options=["Transformer right, baseline wrong", "Baseline right, transformer wrong"],
        value="Baseline right, transformer wrong",
        label="Show",
    )
    disagreement
    return (disagreement,)


@app.cell
def _(disagreement, results):
    _baseline_right = (results["baseline_prob"] >= 0.5) == results["voted_up"]
    _transformer_right = (results["transformer_prob"] >= 0.5) == results["voted_up"]
    _mask = _transformer_right & ~_baseline_right if disagreement.value.startswith("Transformer") else _baseline_right & ~_transformer_right
    _picked = results[_mask & results["words"].between(5, 40)]
    _picked[["game", "voted_up", "baseline_prob", "transformer_prob", "review"]].sample(min(12, len(_picked)), random_state=7).round(2)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Speed and cost

    Accuracy isn't the only thing that matters. Here's each model timed on the same 300 reviews, right now on your machine:
    """)
    return


@app.cell
def _(DEVICE, baseline, mo, test_reviews, time, transformer):
    _sample = test_reviews["review"].sample(300, random_state=1).tolist()
    _speeds = {}
    for _name, _model in (("baseline", baseline), ("transformer", transformer)):
        _start = time.perf_counter()
        _model.predict_proba(_sample)
        _speeds[_name] = len(_sample) / (time.perf_counter() - _start)
    mo.md(f"""
    | | baseline | transformer |
    |---|---|---|
    | reviews per second | **{_speeds['baseline']:,.0f}** | **{_speeds['transformer']:,.0f}** (on `{DEVICE}`) |
    | model size on disk | ~6 MB | ~260 MB |
    | extra libraries | scikit-learn | PyTorch + transformers (~1 GB) |

    The baseline is about **{_speeds['baseline'] / _speeds['transformer']:.0f}× faster**. Scoring the ~20,000 clauses in one game's themes takes the baseline a second or two; the transformer would take a few minutes. On a web page that matters.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. What would make the transformer better: fine-tuning

    The transformer's problem isn't that it can't understand language. It's that it learned "sentiment" from movie critics. **Fine-tuning** fixes that: start from the pretrained DistilBERT and keep training it on *our* labelled Steam reviews, so it learns that "10/10", "giga poggers" and "feet first into hell" are good signs. That combines the transformer's grasp of word order and negation with the baseline's knowledge of how gamers write. On a task like this, a fine-tuned transformer usually beats both.

    The cost: training takes minutes to hours instead of seconds (on the Mac's GPU, roughly 10–20 minutes on a subset of our reviews), and the slower predictions remain.

    ## Recap

    - **Transformers** split text into word pieces and use **attention** to read words in context. They're **pretrained** on general text, then **fine-tuned** for a task (**transfer learning**).
    - Used **off the shelf**, a movie-review transformer **loses** to our Steam-trained baseline: F1 0.83 vs 0.88 on held-out games, and 0.69 vs 0.79 on short reviews.
    - The main reason is **domain mismatch**: gamer language and constant small complaints confuse a model trained on movie sentences. It's also **overconfident** (poorly calibrated) and about 90× slower.
    - It *is* better at classic negation. Neither model handles sarcasm.
    - **Bigger isn't automatically better. Training data that matches your problem often matters more.**

    **Decision for now:** keep the baseline for themes and the web page. The next experiment worth trying is fine-tuning DistilBERT on our reviews.
    """)
    return


if __name__ == "__main__":
    app.run()
