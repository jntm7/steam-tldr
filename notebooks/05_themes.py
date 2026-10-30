import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 05 · Finding themes: what do players praise and complain about?

    A score like "79% positive" tells you *how* people feel, not *why*. The point of this project is the why: "players love the co-op, but complain about bugs and updates."

    This notebook shows how `src/themes.py` gets there:

    1. **Keyword themes**: a hand-written list of topics and the words that signal them
    2. **Clauses**: splitting reviews into small pieces so one review can praise one thing and complain about another
    3. **Scoring clauses**: using the review's thumbs up/down *and* the model from notebook 03
    4. **Re-weighting**: correcting for our biased samples
    5. Results per game, spot-checking, and the limits of this approach

    It uses the saved model, so run `uv run python src/model.py` first if you haven't.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    import pandas as pd
    import sys

    sys.path.insert(0, str(mo.notebook_dir().parent / "src"))
    from fetch import load_reviews
    from games import GAMES
    from model import MODEL_PATH, clean, load_model
    from themes import (
        FLIP_TO_COMPLAINT,
        FLIP_TO_PRAISE,
        PROBLEM_THEMES,
        THEMES,
        find_themes,
        review_weights,
        split_clauses,
        summarize_themes,
    )
    return (
        FLIP_TO_COMPLAINT,
        FLIP_TO_PRAISE,
        GAMES,
        MODEL_PATH,
        PROBLEM_THEMES,
        THEMES,
        clean,
        find_themes,
        load_model,
        load_reviews,
        mo,
        pd,
        plt,
        review_weights,
        split_clauses,
        summarize_themes,
    )


@app.cell
def _(MODEL_PATH, load_model, mo):
    mo.stop(not MODEL_PATH.exists(), mo.md("**No saved model yet.** Run `uv run python src/model.py` in a terminal, then re-run this cell."))
    model = load_model()
    return (model,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Keyword themes

    There are two broad ways to find themes:

    - **Topic modeling**: algorithms (like LDA or BERTopic) that group words that tend to appear together, without being told what the topics are. Powerful, but the groups can be hard to interpret and hard to steer.
    - **Keyword lists**: we decide the topics and list words that signal each one. Simple, predictable and easy to debug. If a theme picks up the wrong reviews, you edit a list.

    We use keyword lists. Gamers complain about a fairly standard set of things, so writing them down by hand works well. Here's the list from `src/themes.py`. Edit it there to add words or themes.
    """)
    return


@app.cell
def _(PROBLEM_THEMES, THEMES, pd):
    pd.DataFrame({
        "theme": list(THEMES),
        "keywords": [", ".join(words) for words in THEMES.values()],
        "complaints only": ["yes" if theme in PROBLEM_THEMES else "" for theme in THEMES],
    }).set_index("theme")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Matching uses **whole words**, so "lag" doesn't match "flag", and longer phrases ("frame rate") are checked before shorter ones. Matching ignores capital letters.

    ## 2. Splitting reviews into clauses

    A review like *"Amazing story, but the servers are a disaster"* praises one thing and complains about another. If we tagged the whole review, "story" and "servers" would both inherit the same thumbs up.

    So we split each review into **clauses** at sentence endings (`. ! ? ;`, new lines) and at turning-point words (*but, however, although, though, except, whereas*). Then each clause is checked for themes on its own.

    Try it, and flip the switch to change whether the reviewer gave a thumbs up:
    """)
    return


@app.cell
def _(mo):
    demo_text = mo.ui.text_area(
        value="Amazing story and the combat feels great. But the servers are a disaster and it crashes every hour. Worth it on sale though.",
        label="Review",
        full_width=True,
    )
    demo_thumbs = mo.ui.switch(value=True, label="Reviewer gave a thumbs up")
    mo.vstack([demo_text, demo_thumbs])
    return demo_text, demo_thumbs


@app.cell
def _(FLIP_TO_COMPLAINT, FLIP_TO_PRAISE, PROBLEM_THEMES, demo_text, demo_thumbs, find_themes, model, pd, split_clauses):
    _rows = []
    for _clause in split_clauses(demo_text.value):
        _prob = model.predict_proba([_clause])[0, 1]
        _themes = find_themes(_clause)
        if demo_thumbs.value:
            _verdict = "complaint" if _prob < FLIP_TO_COMPLAINT else "praise"
        else:
            _verdict = "praise" if _prob > FLIP_TO_PRAISE else "complaint"
        _rows.append({
            "clause": _clause,
            "themes": ", ".join(_themes) or "(none)",
            "model score": round(_prob, 2),
            "counts as": ", ".join(f"{t}: {'complaint' if t in PROBLEM_THEMES else _verdict}" for t in _themes) or "ignored",
        })
    pd.DataFrame(_rows)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(rf"""
    ## 3. Deciding if a clause is praise or a complaint

    The obvious idea is to run the model from notebook 03 on each clause. But that model learned from *whole reviews*, and on a short clause it's often unsure: "the optimization could use some work" scores about 0.55, just on the "positive" side.

    The reviewer's own thumbs up or down is much more reliable, so we use it as the **default** and only let the model **overrule** it when it's confident:

    - In a 👍 review, a clause counts as a **complaint** only if the model scores it below **{FLIP_TO_COMPLAINT}**.
    - In a 👎 review, a clause counts as **praise** only if the model scores it above **{FLIP_TO_PRAISE}**.

    The two cut-offs aren't symmetric because the model leans positive on short text. They were picked by reading real clauses from Monster Hunter Wilds: in positive reviews, clauses below 0.4 were nearly all real complaints, and in negative reviews, only clauses above 0.8 were reliably praise.

    Some themes can't really be praised: nobody says "great bugs". **Bugs & crashes** and **cheaters** always count as complaints.

    ## 4. Re-weighting the sample

    Remember from notebook 01: our samples come from Steam's *helpful* sort, which is often far more negative than the game's real score. If we just counted, complaints would look much more common than they are.

    The fix is **re-weighting**: each review counts as more or less than one so the sample's mix of 👍 and 👎 matches Steam's real totals. If the sample is 34% positive but Steam says 81%, each positive review counts for about 81 ÷ 34 ≈ 2.4 reviews and each negative one for 19 ÷ 66 ≈ 0.3. Pollsters do the same thing when a survey under-samples some group.

    Theme percentages then read as "this share of all the game's reviews praise or complain about X".
    """)
    return


@app.cell
def _(GAMES, mo):
    theme_game = mo.ui.dropdown(options={name: appid for appid, name in GAMES.items()}, value="Monster Hunter Wilds", label="Game")
    theme_game
    return (theme_game,)


@app.cell
def _(clean, load_reviews, mo, model, review_weights, summarize_themes, theme_game):
    _df, _meta = load_reviews(theme_game.value)
    game_reviews = clean(_df.drop_duplicates("recommendationid").reset_index(drop=True))
    _summary = _meta["summary"]
    steam_share = _summary["total_positive"] / _summary["total_reviews"]
    game_themes, game_mentions = summarize_themes(game_reviews, model, steam_share)

    _weights = review_weights(game_reviews, steam_share)
    _sample_share = game_reviews["voted_up"].mean()
    mo.md(f"""
    Steam says **{steam_share:.1%}** positive; our sample of {len(game_reviews):,} reviews is **{_sample_share:.1%}** positive.
    So each 👍 review counts as **{_weights[game_reviews['voted_up'].to_numpy()].iloc[0]:.2f}** reviews and each 👎 as **{_weights[~game_reviews['voted_up'].to_numpy()].iloc[0]:.2f}**.
    """)
    return game_mentions, game_themes


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Praise vs complaints

    Each bar shows the share of the game's reviews that **praise** (right) or **complain about** (left) that theme. One review can do both, for example a positive review with one complaint.
    """)
    return


@app.cell
def _(GAMES, game_themes, plt, theme_game):
    _order = game_themes.assign(total=game_themes["praise_pct"] + game_themes["complaint_pct"]).sort_values("total")
    _fig, _ax = plt.subplots(figsize=(9, 6))
    _ax.barh(_order.index, -_order["complaint_pct"], color="tab:red", label="complaints")
    _ax.barh(_order.index, _order["praise_pct"], color="tab:blue", label="praise")
    _ax.axvline(0, color="black", linewidth=0.8)
    _limit = max(_order["praise_pct"].max(), _order["complaint_pct"].max()) * 1.1
    _ax.set(xlim=(-_limit, _limit), xlabel="% of reviews (complaints ← → praise)", title=GAMES[theme_game.value])
    _ax.legend(loc="lower right")
    _fig.tight_layout()
    _fig
    return


@app.cell
def _(game_themes):
    game_themes.round(1).sort_values("complaint_pct", ascending=False)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Spot-check it

    Numbers from keyword matching can look convincing while being quietly wrong, so **read the clauses behind them**. Pick a theme and check: does each clause really talk about that theme, and is it labelled right?

    A good habit is to check about 50 clauses for a theme and count how many are right. That's a rough **precision** for the theme (notebook 04), measured by hand.
    """)
    return


@app.cell
def _(THEMES, mo):
    check_theme = mo.ui.dropdown(options=list(THEMES), value="performance", label="Theme")
    check_theme
    return (check_theme,)


@app.cell
def _(check_theme, game_mentions, mo):
    _theme = game_mentions[game_mentions["theme"] == check_theme.value]
    _praise = _theme[_theme["positive"]]
    _complaints = _theme[~_theme["positive"]]
    _columns = ["voted_up", "prob_positive", "clause"]
    mo.vstack([
        mo.md(f"**Praise** ({len(_praise):,} clauses)"),
        _praise[_columns].sample(min(10, len(_praise)), random_state=42).round(2),
        mo.md(f"**Complaints** ({len(_complaints):,} clauses)"),
        _complaints[_columns].sample(min(10, len(_complaints)), random_state=42).round(2),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. Limits of this approach

    Try these in the dropdowns above to see the problems for yourself:

    - **Words with game-specific meanings.** In Helldivers 2 the "bugs" are an alien enemy faction, so *bugs & crashes* picks up combat talk. In Stardew Valley, "money" is in-game gold, not the price.
    - **Missed synonyms.** "Runs like a slideshow" is a performance complaint with no keyword in it. Keyword lists only catch what you thought to write down.
    - **Clause scores are rough.** The model learned from whole reviews, not clauses. The thumbs-up default covers most of this, but sarcasm and negation inside clauses still slip through.
    - **Percentages are estimates.** They come from about 5,000 sampled reviews, re-weighted. Treat 22% vs 24% as a tie.

    Possible improvements later: game-specific stop words (ignore "bugs" for Helldivers 2), more keywords found by reading complaints, or a **transformer** model that understands whole sentences and could score clauses much better (build plan stage 3).

    ## Recap

    - **Keyword themes** are simple and controllable: edit `THEMES` in `src/themes.py`.
    - Reviews are split into **clauses** so one review can praise and complain.
    - Each clause takes its review's **thumbs up/down by default**, and the model only **overrules** it when confident.
    - **Re-weighting** corrects for our helpful-sorted samples so percentages reflect the real review mix.
    - Always **spot-check** the clauses behind a number before trusting it.

    **Next:** a summary command (`src/summarize.py`) that puts the score, trend and themes together for any game, then the Streamlit page.
    """)
    return


if __name__ == "__main__":
    app.run()
