import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 02 · Turning text into numbers

    A machine learning model is, at heart, a function that does math. It can multiply and add numbers, but it has no idea what the word "boring" means. So before a model can learn anything from reviews, we need a way to turn each review into a list of numbers.

    That list of numbers is called a **feature vector**, and the step that builds it is called **vectorizing**. Think of it like serializing an object: we're picking a fixed format that captures the parts we care about.

    This notebook builds up the approach our model uses, one idea at a time:

    1. **Tokenizing**: splitting text into words
    2. **Bag of words**: counting the words
    3. **TF-IDF**: counting them *smarter*
    4. **N-grams**: keeping some word order
    5. Trying it on our real Steam reviews
    """)
    return


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import pandas as pd
    import sys
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

    sys.path.insert(0, str(mo.notebook_dir().parent / "src"))
    from model import clean, load_dataset
    return CountVectorizer, TfidfVectorizer, clean, load_dataset, mo, np, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Tokenizing

    The first step is splitting text into pieces called **tokens**. For us a token is just a word. The tokenizer also lowercases everything and strips punctuation, so "Great!", "great" and "GREAT" all become the same token.

    Type anything into the box and watch it get tokenized.
    """)
    return


@app.cell
def _(mo):
    sample_text = mo.ui.text_area(
        value="Great game!! But the servers are NOT good, and it crashes every 10 minutes.",
        label="Your review",
        full_width=True,
    )
    sample_text
    return (sample_text,)


@app.cell
def _(CountVectorizer, mo, sample_text):
    _tokenize = CountVectorizer().build_analyzer()
    _tokens = _tokenize(sample_text.value)
    mo.md(f"**{len(_tokens)} tokens:** " + " · ".join(f"`{t}`" for t in _tokens))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Notice what got lost: punctuation, capital letters, and single-character tokens like "a". The default tokenizer keeps only words with 2 or more characters. Some of what's lost carries feeling ("!!", "NOT"), and that's a trade-off we accept to keep things simple.

    ## 2. Bag of words

    The simplest way to turn tokens into numbers: make a list of every word that appears in *any* review (the **vocabulary**), then describe each review by how many times it uses each word.

    It's called a "bag" of words because it throws away word order, like dumping the words into a bag and counting them. Here are three tiny reviews:
    """)
    return


@app.cell
def _():
    toy_reviews = [
        "great game great story",
        "not a great game",
        "the story is boring and the game is boring",
    ]
    return (toy_reviews,)


@app.cell
def _(CountVectorizer, pd, toy_reviews):
    _counter = CountVectorizer()
    _counts = _counter.fit_transform(toy_reviews)
    pd.DataFrame(_counts.toarray(), columns=_counter.get_feature_names_out(), index=[f"review {i + 1}" for i in range(len(toy_reviews))])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Each **row** is a review and each **column** is a word from the vocabulary. Review 1 says "great" twice, so its `great` column is 2.

    Every review becomes a row of the same length, no matter how long it is. That fixed shape is exactly what a model needs as input.

    With real data the vocabulary has *hundreds of thousands* of words, and any one review uses only a few dozen of them. So almost every number is 0. Libraries store this as a **sparse matrix**, which saves memory by only remembering the non-zero values (like a dictionary instead of a giant array).

    ## 3. TF-IDF: counting smarter

    Raw counts have a problem: the most common words aren't the most useful. In Steam reviews "game" shows up everywhere, positive or negative, so it tells us almost nothing. "Refund" or "masterpiece" are rarer but say a lot.

    **TF-IDF** fixes this by giving each word a score instead of a count. The score combines two parts:

    - **TF (term frequency):** how often the word appears in *this* review. More often means more important to this review.
    - **IDF (inverse document frequency):** how *rare* the word is across *all* reviews. A word that appears in every review gets a low IDF; a word that appears in only a few gets a high one.

    Multiply them together: a word scores high when it's used a lot in this review **and** isn't used much elsewhere. Each row is then scaled so long reviews don't automatically get bigger numbers than short ones.
    """)
    return


@app.cell
def _(TfidfVectorizer, pd, toy_reviews):
    _tfidf = TfidfVectorizer()
    _scores = _tfidf.fit_transform(toy_reviews)
    pd.DataFrame(_scores.toarray(), columns=_tfidf.get_feature_names_out(), index=[f"review {i + 1}" for i in range(len(toy_reviews))]).round(2)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Compare this to the counts table above. `game` appears in all three reviews, so its score is lower than you'd expect from its count. `boring` only appears in review 3, so it gets a high score there. That's TF-IDF doing its job: pulling out the words that make each review *different*.

    ## 4. N-grams: keeping a little word order

    Bag of words throws away order, which hurts with **negation**: "not good" becomes two separate words, `not` and `good`, and `good` looks positive.

    A cheap partial fix is to also count pairs of neighbouring words, called **bigrams** (single words are **unigrams**; in general these are **n-grams**). Now "not good" becomes its own token, and the model can learn that it's negative.

    Here's your review from the box at the top, with unigrams *and* bigrams:
    """)
    return


@app.cell
def _(CountVectorizer, mo, sample_text):
    _tokenize = CountVectorizer(ngram_range=(1, 2)).build_analyzer()
    _tokens = _tokenize(sample_text.value)
    _bigrams = [t for t in _tokens if " " in t]
    mo.md(f"**{len(_tokens)} tokens** ({len(_bigrams)} bigrams): " + " · ".join(f"`{t}`" for t in _bigrams))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Bigrams help with short negations like "not good", but not with longer ones like "I wouldn't say this is good", or with sarcasm ("great, another crash"). That's a known weakness of this whole approach, and why later we may compare against a **transformer** model that reads whole sentences.

    The cost: the vocabulary gets much bigger. Our model uses unigrams and bigrams, and ignores any token that appears in fewer than 5 reviews (`min_df=5`). That drops typos and one-off words that would just add noise.

    ## 5. On our real reviews

    Now let's vectorize all our cleaned Steam reviews. Cleaning drops very short and junky reviews (see notebook 01; the thresholds live in `src/model.py`).
    """)
    return


@app.cell
def _(clean, load_dataset):
    reviews = clean(load_dataset())
    return (reviews,)


@app.cell
def _(TfidfVectorizer, mo, reviews):
    real_tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=5, stop_words="english")
    real_matrix = real_tfidf.fit_transform(reviews["review"])
    _filled = real_matrix.nnz / (real_matrix.shape[0] * real_matrix.shape[1])
    mo.md(f"""
    - **{real_matrix.shape[0]:,}** reviews × **{real_matrix.shape[1]:,}** tokens in the vocabulary
    - Only **{_filled:.4%}** of the numbers are non-zero, which is why it's stored as a sparse matrix
    - Here we also drop **stop words** (very common words like "the", "and", "is") so the next table is easier to read
    """)
    return real_matrix, real_tfidf


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Which words separate praise from complaints?

    For one game, average the TF-IDF scores of its negative reviews, do the same for its positive reviews, and subtract. Tokens with the biggest difference are the ones that show up much more on one side. (Plain averages aren't enough: generic words like "game" and "just" top both lists.) This is a preview of theme finding, done with nothing but TF-IDF. Pick a game:
    """)
    return


@app.cell
def _(mo, reviews):
    word_game = mo.ui.dropdown(options=sorted(reviews["game"].unique()), value="Cyberpunk 2077", label="Game")
    word_game
    return (word_game,)


@app.cell
def _(np, pd, real_matrix, real_tfidf, reviews, word_game):
    _rows = (reviews["game"] == word_game.value).to_numpy()
    _positive = reviews["voted_up"].to_numpy()
    _negative_mean = np.asarray(real_matrix[_rows & ~_positive].mean(axis=0)).ravel()
    _positive_mean = np.asarray(real_matrix[_rows & _positive].mean(axis=0)).ravel()
    _difference = _negative_mean - _positive_mean
    _names = real_tfidf.get_feature_names_out()
    pd.DataFrame({
        "more in negative reviews": _names[_difference.argsort()[::-1][:15]],
        "more in positive reviews": _names[_difference.argsort()[:15]],
    })
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Try Monster Hunter Wilds (crashes, performance, unplayable) or Cyberpunk 2077 (broken, promised, npcs). Complaints are often about the developer or publisher by name ("capcom", "blizzard", "cdpr"), while praise mentions what's actually in the game. Even this simple approach starts to answer "what do players complain about?" You'll also see some noise (swearing, "just", "don"), which is why proper theme finding comes later.

    ## Recap

    - Models only understand numbers, so each review becomes a **feature vector**.
    - **Tokenizing** splits text into lowercase words.
    - **Bag of words** counts each vocabulary word per review. Every review becomes a row of the same length, mostly zeros (a **sparse matrix**).
    - **TF-IDF** scores words higher when they're frequent in a review but rare overall.
    - **Bigrams** keep some word order, which helps with "not good" but not with sarcasm.

    **Next:** `03_first_model.py` feeds these vectors to a model that learns which words mean positive and which mean negative.
    """)
    return


if __name__ == "__main__":
    app.run()
