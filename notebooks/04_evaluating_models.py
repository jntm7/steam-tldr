import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 04 · Is the model any good?

    Notebook 03 trained a model. Now we need to measure it honestly. This is where a lot of ML projects fool themselves, usually by trusting one number (**accuracy**) that can look great while the model is useless.

    This notebook covers:

    1. The **accuracy trap**
    2. The **confusion matrix**: the four ways a prediction can turn out
    3. **Precision**, **recall** and **F1**, the numbers we actually report
    4. The **threshold**: trading precision against recall
    5. Results per game
    6. Why you must never tune on the test set, and **cross-validation** as the fix
    """)
    return


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import sys
    from sklearn.metrics import accuracy_score, f1_score, precision_recall_curve, precision_score, recall_score
    from sklearn.model_selection import GroupKFold

    sys.path.insert(0, str(mo.notebook_dir().parent / "src"))
    from model import build_model, clean, load_dataset, split_by_game
    return (
        GroupKFold,
        accuracy_score,
        build_model,
        clean,
        f1_score,
        load_dataset,
        mo,
        np,
        pd,
        plt,
        precision_recall_curve,
        precision_score,
        recall_score,
        split_by_game,
    )


@app.cell
def _(build_model, clean, load_dataset, mo, split_by_game):
    reviews = clean(load_dataset())
    train, test = split_by_game(reviews)
    model = build_model().fit(train["review"], train["voted_up"])
    prob_positive = model.predict_proba(test["review"])[:, 1]
    is_positive = test["voted_up"].to_numpy()
    mo.md(f"Trained on **{len(train):,}** reviews. Testing on **{len(test):,}** reviews from the held-out games: {', '.join(sorted(test['game'].unique()))}.")
    return is_positive, model, prob_positive, reviews, test, train


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. The accuracy trap

    **Accuracy** is the share of predictions that are correct. It sounds like all you need, but look at a "model" that ignores the text and *always* says positive. On a game where 90% of reviews are positive, it scores 90% accuracy while being completely useless: it never catches a single complaint.

    This happens whenever one answer is much more common than the other, called **class imbalance**. Most Steam games are mostly positive, so we're always at risk of it.

    Compare our model with the always-positive "model" on each test game:
    """)
    return


@app.cell
def _(accuracy_score, pd, prob_positive, test):
    _rows = []
    for _game, _group in test.assign(prob=prob_positive).groupby("game"):
        _rows.append({
            "game": _game,
            "% positive in sample": round(100 * _group["voted_up"].mean(), 1),
            "always-positive accuracy": round(100 * _group["voted_up"].mean(), 1),
            "our model's accuracy": round(100 * accuracy_score(_group["voted_up"], _group["prob"] >= 0.5), 1),
        })
    pd.DataFrame(_rows).set_index("game")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    On the most positive game, always guessing "positive" lands close to our model, even though one of them reads the review and the other doesn't. Accuracy alone can't tell them apart well. We need numbers that focus on the reviews we care about.

    ## 2. The confusion matrix

    For this project, the interesting job is **catching negative reviews**, because that's where complaints and themes come from. Think of the model as a spam filter, where "spam" is "negative review". Every prediction lands in one of four boxes:

    | | model says negative | model says positive |
    |---|---|---|
    | **actually negative** | ✅ **caught** | ❌ **missed** |
    | **actually positive** | ❌ **false alarm** | ✅ **correctly passed** |

    This 2×2 table is called a **confusion matrix** (it shows where the model gets "confused"). From it we get:

    - **Precision**: of the reviews we flagged as negative, how many really were? `caught / (caught + false alarms)`. Low precision means lots of false alarms.
    - **Recall**: of all the truly negative reviews, how many did we catch? `caught / (caught + missed)`. Low recall means complaints slip through.
    - **F1**: one number that balances the two (their *harmonic mean*). It's only high when **both** precision and recall are high, so you can't game it by flagging everything or nothing.

    ## 3. The threshold

    The model doesn't output "positive" or "negative". It outputs a probability, and we pick a cut-off: below the **threshold**, call it negative. The default is 0.5, but nothing forces that. Move the slider and watch the boxes and scores change.
    """)
    return


@app.cell
def _(mo):
    threshold = mo.ui.slider(0.05, 0.95, step=0.05, value=0.5, label="Threshold (call it negative below this)", show_value=True)
    threshold
    return (threshold,)


@app.cell
def _(accuracy_score, f1_score, is_positive, mo, pd, precision_score, prob_positive, recall_score, threshold):
    predicted_positive = prob_positive >= threshold.value
    _matrix = pd.DataFrame(
        [[((~is_positive) & (~predicted_positive)).sum(), ((~is_positive) & predicted_positive).sum()],
         [(is_positive & (~predicted_positive)).sum(), (is_positive & predicted_positive).sum()]],
        index=["actually negative", "actually positive"],
        columns=["model says negative", "model says positive"],
    )
    neg_precision = precision_score(is_positive, predicted_positive, pos_label=False)
    neg_recall = recall_score(is_positive, predicted_positive, pos_label=False)
    _scores = mo.md(f"""
    | score | value |
    |---|---|
    | precision (negatives) | **{neg_precision:.1%}** |
    | recall (negatives) | **{neg_recall:.1%}** |
    | F1 (negatives) | **{f1_score(is_positive, predicted_positive, pos_label=False):.3f}** |
    | accuracy | {accuracy_score(is_positive, predicted_positive):.1%} |
    """)
    mo.hstack([_matrix, _scores], justify="start", gap=2)
    return neg_precision, neg_recall


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Raise the threshold and the model flags more reviews as negative: **recall goes up** (fewer missed) but **precision goes down** (more false alarms). Lower it and the reverse happens. You can't max out both, so you pick based on what mistakes cost:

    - A spam filter wants **high precision**: losing a real email is worse than seeing some spam.
    - A fraud detector wants **high recall**: missing fraud is worse than a few false alarms.

    For our summaries, precision matters a bit more: if we show "top complaints", we'd rather they come from reviews that really are complaints.

    The **precision-recall curve** below shows every possible threshold at once. The dot is where the slider is. A better model's curve bulges further towards the top-right corner.
    """)
    return


@app.cell
def _(is_positive, neg_precision, neg_recall, plt, precision_recall_curve, prob_positive, threshold):
    _precision, _recall, _ = precision_recall_curve(~is_positive, 1 - prob_positive)
    _fig, _ax = plt.subplots(figsize=(6, 4.5))
    _ax.plot(_recall, _precision)
    _ax.scatter([neg_recall], [neg_precision], zorder=3, s=60)
    _ax.set(xlabel="recall (negatives caught)", ylabel="precision (flags that were right)", xlim=(0, 1), ylim=(0, 1.02),
            title=f"Precision vs recall (threshold {threshold.value:.2f})")
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Results per game

    Averages can hide problems. Here's each test game at the default threshold of 0.5. If one game is much worse, read its mistakes (notebook 03) to find out why. Maybe its reviews use slang, or its complaints are about something no training game had.
    """)
    return


@app.cell
def _(f1_score, pd, precision_score, prob_positive, recall_score, test):
    _rows = []
    for _game, _group in test.assign(predicted=prob_positive >= 0.5).groupby("game"):
        _rows.append({
            "game": _game,
            "reviews": len(_group),
            "negatives": int((~_group["voted_up"]).sum()),
            "precision": round(precision_score(_group["voted_up"], _group["predicted"], pos_label=False), 3),
            "recall": round(recall_score(_group["voted_up"], _group["predicted"], pos_label=False), 3),
            "F1": round(f1_score(_group["voted_up"], _group["predicted"], pos_label=False), 3),
        })
    pd.DataFrame(_rows).set_index("game")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Never tune on the test set

    It's tempting to move the threshold slider until the test score looks best, then report that score. **Don't.** The moment you make choices based on the test set, it stops being "data the model has never seen". Your choices have leaked information from it, and the score becomes too optimistic. It's like writing your code to pass one specific test case: the test passes, but it no longer proves the code works.

    The fix: make decisions using the **training data only**, and touch the test set once, at the very end.

    **Cross-validation** is how you get a trustworthy score from the training data:

    1. Split the training games into a few groups called **folds**.
    2. Hold one fold out, train on the rest, and score on the held-out fold. That held-out fold acts as a **validation set**: a practice test.
    3. Repeat so every fold gets a turn, then average the scores.

    Because we split by game (`GroupKFold`), every score is still "on games the model hasn't seen". This is where you'd compare settings like thresholds or bigrams vs no bigrams. Training 4 models takes about half a minute:
    """)
    return


@app.cell
def _(mo):
    run_cv = mo.ui.run_button(label="Run 4-fold cross-validation")
    run_cv
    return (run_cv,)


@app.cell
def _(GroupKFold, build_model, f1_score, mo, pd, run_cv, train):
    mo.stop(not run_cv.value, mo.md("*Click the button to run it.*"))
    _rows = []
    for _fold, (_train_idx, _val_idx) in enumerate(GroupKFold(n_splits=4).split(train, groups=train["appid"]), start=1):
        _fit_part, _val_part = train.iloc[_train_idx], train.iloc[_val_idx]
        _fold_model = build_model().fit(_fit_part["review"], _fit_part["voted_up"])
        _rows.append({
            "fold": _fold,
            "validation games": ", ".join(sorted(_val_part["game"].unique())),
            "F1 (negatives)": round(f1_score(_val_part["voted_up"], _fold_model.predict(_val_part["review"]), pos_label=False), 3),
        })
    _cv = pd.DataFrame(_rows).set_index("fold")
    mo.vstack([_cv, mo.md(f"**Average F1: {_cv['F1 (negatives)'].mean():.3f}** (± {_cv['F1 (negatives)'].std():.3f} between folds)")])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The spread between folds is useful too: if it's large, the score depends a lot on *which* games you test on, so any single number should be taken with a grain of salt.

    ## Recap

    - **Accuracy** can look good while the model is useless, whenever one class dominates (**class imbalance**).
    - The **confusion matrix** sorts predictions into caught, missed, false alarm and correctly passed.
    - **Precision**: how many flags were right. **Recall**: how many negatives we caught. **F1** balances both. We report all three for negative reviews.
    - The **threshold** trades precision for recall. Choose it based on which mistakes cost more.
    - **Never tune on the test set.** Use **cross-validation** on the training data to make choices, and look at the test set once at the end.

    **Next steps for the project:** settle the cleaning thresholds from notebook 01, then use cross-validation to compare a couple of model settings before the final test-set check.
    """)
    return


if __name__ == "__main__":
    app.run()
