import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 03 · Your first model: logistic regression

    In regular programming you write the rules: `if "refund" in review: return "negative"`. In machine learning you give the computer lots of **examples with the right answer**, and it works out the rules itself. Those rules end up as a set of numbers called **weights** (or **parameters**). Finding them is called **training**.

    Our examples are Steam reviews, and the right answer is free: every review has a thumbs up or down (`voted_up`). The answer we're trying to predict is called the **label**.

    This notebook walks through:

    1. Splitting data into a **training set** and a **test set**
    2. How **logistic regression** turns a review into a probability
    3. Training the model
    4. Trying it on your own text
    5. Looking inside: which words the model thinks are positive or negative
    6. Where it gets things wrong
    """)
    return


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import sys
    import time

    sys.path.insert(0, str(mo.notebook_dir().parent / "src"))
    from games import GAMES
    from model import TEST_GAMES, build_model, clean, load_dataset, split_by_game
    return (
        GAMES,
        TEST_GAMES,
        build_model,
        clean,
        load_dataset,
        mo,
        np,
        pd,
        plt,
        split_by_game,
        time,
    )


@app.cell
def _(clean, load_dataset, mo):
    _raw = load_dataset()
    reviews = clean(_raw)
    mo.md(f"Loaded **{len(_raw):,}** reviews; **{len(reviews):,}** remain after cleaning out very short and junky ones.")
    return (reviews,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Train and test sets

    If you write a function and only test it with the exact inputs you used while writing it, passing tests don't prove much. The same goes for models: a model can **memorize** its training examples without learning anything general. That's called **overfitting**.

    So we hide some data from the model during training (the **test set**) and only use it at the end to check how well the model does on reviews it has never seen.

    **We hold out whole games, not random reviews.** If Stardew Valley reviews were in both sets, the model could learn that the word "stardew" means positive, then look great on the test set for a useless reason. Holding out entire games checks what we actually want: *does it work on a game it has never seen?* Using information during training that you shouldn't have is called **leakage**.

    Pick which games to hold out. Everything below retrains automatically.
    """)
    return


@app.cell
def _(GAMES, TEST_GAMES, mo, reviews):
    test_picker = mo.ui.multiselect(
        options={GAMES[appid]: appid for appid in GAMES if appid in set(reviews["appid"])},
        value=[GAMES[appid] for appid in TEST_GAMES],
        label="Held-out test games",
    )
    test_picker
    return (test_picker,)


@app.cell
def _(mo, pd, reviews, split_by_game, test_picker):
    mo.stop(not test_picker.value, mo.md("Pick at least one test game."))
    train, test = split_by_game(reviews, test_picker.value)
    pd.DataFrame({
        "reviews": [len(train), len(test)],
        "games": [train["game"].nunique(), test["game"].nunique()],
        "% positive": [round(100 * train["voted_up"].mean(), 1), round(100 * test["voted_up"].mean(), 1)],
    }, index=["train", "test"])
    return test, train


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. How logistic regression works

    Despite the name, **logistic regression** answers yes/no questions (that's called **classification**). Here the question is "is this review positive?" It works in two steps:

    **Step 1: a weighted sum.** Every token in the vocabulary has a weight. Positive words like "masterpiece" get positive weights, negative words like "refund" get negative weights, and neutral words sit near 0. To score a review, take each token's TF-IDF value (from notebook 02), multiply it by that token's weight, and add everything up. Then add one extra number, the **intercept**, which is the score a review would get with no words at all.

    **Step 2: squash it into a probability.** The score can be any number, like -3.2 or 5.1. The **sigmoid** function squashes it into the range 0 to 1, so it reads as a probability: large positive scores get close to 1 (very likely positive), large negative scores get close to 0, and a score of 0 means 50/50.

    Drag the slider to see the sigmoid in action:
    """)
    return


@app.cell
def _(mo):
    score_slider = mo.ui.slider(-8, 8, step=0.5, value=2, label="Score (weighted sum)", show_value=True)
    score_slider
    return (score_slider,)


@app.cell
def _(np, plt, score_slider):
    _x = np.linspace(-8, 8, 200)
    _p = 1 / (1 + np.exp(-score_slider.value))
    _fig, _ax = plt.subplots(figsize=(8, 3))
    _ax.plot(_x, 1 / (1 + np.exp(-_x)))
    _ax.scatter([score_slider.value], [_p], zorder=3)
    _ax.axhline(0.5, linestyle="--", linewidth=0.8, color="gray")
    _ax.set(xlabel="score", ylabel="probability positive", title=f"score {score_slider.value:+.1f} → {_p:.0%} positive")
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Training** means finding the weights that make these probabilities match the real labels as closely as possible across all training reviews. The library does this by repeatedly nudging the weights in whichever direction reduces the error, a bit like a loop that runs until the result stops improving.

    One setting worth knowing: `class_weight="balanced"`. Our training data has more positive reviews than negative ones. Without this setting, the model can get lazy and lean towards "positive" because that's usually right. Balancing makes each mistake on the rarer class count for more, so the model takes negatives seriously.

    ## 3. Train the model

    `build_model()` in `src/model.py` chains the two steps into one **pipeline**: TF-IDF vectorizing (unigrams and bigrams, from notebook 02), then logistic regression. Calling `.fit()` trains both on the training set.
    """)
    return


@app.cell
def _(build_model, mo, time, train):
    model = build_model()
    _start = time.perf_counter()
    model.fit(train["review"], train["voted_up"])
    _seconds = time.perf_counter() - _start
    mo.md(f"Trained on **{len(train):,}** reviews in **{_seconds:.1f}s**, learning a weight for each of **{len(model['tfidf'].vocabulary_):,}** tokens.")
    return (model,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Try it yourself

    Write a review and see what the model predicts. The table shows how much each token pushed the score up (towards positive) or down (towards negative): its TF-IDF value × its weight. Try adding "not", sarcasm, or mixing praise with complaints.
    """)
    return


@app.cell
def _(mo):
    review_input = mo.ui.text_area(
        value="Amazing story and great characters, but the performance is terrible and it crashes constantly.",
        label="Your review",
        full_width=True,
    )
    review_input
    return (review_input,)


@app.cell
def _(mo, model, pd, review_input):
    _vector = model["tfidf"].transform([review_input.value])
    _weights = model["logreg"].coef_[0]
    _names = model["tfidf"].get_feature_names_out()
    _rows = pd.DataFrame({
        "token": _names[_vector.indices],
        "tf-idf": _vector.data,
        "weight": _weights[_vector.indices],
    })
    _rows["push"] = _rows["tf-idf"] * _rows["weight"]
    _rows = _rows.reindex(_rows["push"].abs().sort_values(ascending=False).index).round(3)

    _intercept = model["logreg"].intercept_[0]
    _score = _rows["push"].sum() + _intercept
    _prob = model.predict_proba([review_input.value])[0, 1]
    mo.vstack([
        mo.md(f"Score = {_rows['push'].sum():+.2f} (tokens) {_intercept:+.2f} (intercept) = **{_score:+.2f}** → **{_prob:.0%} positive**, predicted **{'👍 positive' if _prob >= 0.5 else '👎 negative'}**"),
        _rows.reset_index(drop=True),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Tokens the model has never seen (or that appeared in fewer than 5 training reviews) don't show up in the table at all. They have no weight, so they're ignored.

    ## 5. Looking inside the model

    Because each token has exactly one weight, we can read the model directly: sort the weights and look at both ends. This is a big advantage of simple models. Many fancier models are much harder to explain.
    """)
    return


@app.cell
def _(model, pd, plt):
    _weights = pd.Series(model["logreg"].coef_[0], index=model["tfidf"].get_feature_names_out()).sort_values()
    _extremes = pd.concat([_weights.head(20), _weights.tail(20)])
    _fig, _ax = plt.subplots(figsize=(8, 9))
    _ax.barh(_extremes.index, _extremes.values, color=["tab:red"] * 20 + ["tab:blue"] * 20)
    _ax.axvline(0, color="black", linewidth=0.8)
    _ax.set(xlabel="weight (negative ← → positive)", title="Tokens with the strongest weights")
    _fig.tight_layout()
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Look for surprises. Most strong words make sense ("masterpiece", "unplayable", "not worth"), but with the default test games you'll also see game and company names: "terraria" and "minecraft" lean positive, while "blizzard" (Overwatch) and "epic" (Rocket League, after Epic Games bought it) lean negative. Those weights mean the model learned something about *those specific games*, not about reviews in general. It's a mild form of leakage, and one reason we test on games the model has never seen.

    ## 6. Where the model gets it wrong

    These are test reviews the model was **most confident about and still got wrong**. Reading mistakes is one of the most useful things you can do with a model. Look for patterns: sarcasm, negation, mixed reviews, or reviews where the thumbs up doesn't match the text at all.

    *(Strictly speaking, if you change the model based on test-set mistakes, the test set stops being a fair final check. Notebook 04 explains how to avoid that. Here we're only looking to learn.)*
    """)
    return


@app.cell
def _(mo, model, test):
    _results = test[["game", "voted_up", "review"]].assign(prob_positive=model.predict_proba(test["review"])[:, 1].round(3))
    _false_positive = _results[~_results["voted_up"]].nlargest(8, "prob_positive")
    _false_negative = _results[_results["voted_up"]].nsmallest(8, "prob_positive")
    mo.vstack([
        mo.md("**Negative reviews the model was sure were positive**"),
        _false_positive,
        mo.md("**Positive reviews the model was sure were negative**"),
        _false_negative,
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Recap

    - Training finds a **weight** for every token, using reviews with known **labels** (`voted_up`).
    - We keep a **test set** of whole games the model never sees, so we can check it works on new games and avoid **leakage**.
    - **Logistic regression** adds up TF-IDF × weight for every token, plus an **intercept**, then squashes the score with a **sigmoid** to get a probability.
    - `class_weight="balanced"` stops the model from ignoring the rarer negative reviews.
    - Simple models are easy to read: the biggest weights show exactly what the model learned.

    **Next:** `04_evaluating_models.py` answers "how good is this model, really?" and shows why accuracy alone can fool you.
    """)
    return


if __name__ == "__main__":
    app.run()
