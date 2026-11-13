import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
import pandas as pd
from fetch import cache_paths
from llm import ModelError, complete, model_name
from model import clean
from news import load_news
from written_summary import CITE_ID, HYPE_WORDS, NUMBER, QUOTED, SWEARING, month_text, normalize, numbers_in, rows

# Field in site_data/<appid>.json that holds the event explanations
REASONS_FIELD = "event_reasons"

# Bump when the prompt or facts change, so every event is explained again
PROMPT_VERSION = 2

# How much evidence goes into the prompt
REVIEW_LINES = 15
REVIEW_CHARS = 250
NEWS_DAYS_BEFORE = 14
LATE_EDIT_DAYS = 60
OFFICIAL_LINES = 6
PRESS_LINES = 10
DISTINCTIVE_WORDS = 40

# How long the explanation may be
MIN_SENTENCES, MAX_SENTENCES = 1, 2
MAX_WORDS = 35
MAX_QUOTES = 1
MAX_TAGS = 2
ATTEMPTS = 3
MAX_UNREACHABLE_IN_A_ROW = 3

# Reason tags, each with words one of its cited lines must contain (whole words, any case)
TAGS = {
    "account/DRM": ["account", "accounts", "psn", "playstation network", "login", "log in", "sign in", "launcher", "drm", "denuvo",
                    "ea app", "ubisoft connect", "rockstar launcher", "battle.net", "linking", "link", "epic games", "epic online services",
                    "eos", "telemetry", "spyware", "blocked", "restricted", "restricting access", "region lock", "region locked"],
    "monetization": ["price", "prices", "priced", "microtransaction", "microtransactions", "mtx", "dlc", "pay", "paid", "paying",
                     "monetization", "monetisation", "battle pass", "premium", "money", "greed", "greedy", "shop", "store", "currency",
                     "loot box", "loot boxes", "cosmetics", "skins", "subscription", "free to play", "free-to-play", "f2p", "refund"],
    "bugs/performance": ["bug", "bugs", "buggy", "crash", "crashes", "crashing", "performance", "fps", "lag", "lags", "lagging",
                         "stutter", "stuttering", "broken", "optimization", "optimisation", "optimized", "freeze", "freezes", "glitch",
                         "glitches", "unplayable", "shader", "shaders", "framerate", "frame rate"],
    "game changes": ["nerf", "nerfs", "nerfed", "balance", "balancing", "update", "updates", "patch", "patches", "removed", "removal",
                     "change", "changes", "changed", "rework", "reworked", "buff", "season", "expansion", "remaster", "version", "direction"],
    "developer decision": ["developer", "developers", "dev", "devs", "publisher", "studio", "layoff", "layoffs", "delist", "delisted",
                           "region", "regions", "countries", "country", "policy", "sony", "communication", "ignored", "roadmap",
                           "abandoned", "eula", "tos", "terms", "ceo", "announcement", "announced", "support", "ended", "shutdown",
                           "take-two", "lawsuit", "legal", "cease and desist", "banned", "ban", "bans"],
    "modding": ["mod", "mods", "modding", "modded", "modder", "modders", "openiv", "workshop", "paid mods", "script extender"],
    "cheaters": ["cheat", "cheats", "cheater", "cheaters", "cheating", "hacker", "hackers", "hacks", "anti-cheat", "anticheat",
                 "kernel", "vac", "aimbot", "bots"],
    "servers": ["server", "servers", "online", "connection", "disconnect", "disconnects", "matchmaking", "queue", "queues",
                "always online", "offline", "network", "lobby", "lobbies"],
    "AI content": ["ai", "a.i.", "generative", "ai-generated", "chatgpt"],
    "off-topic protest": ["china", "chinese", "russia", "russian", "politics", "political", "woke", "protest", "review bomb",
                          "review bombing", "boycott", "translation", "localization", "language"],
    "unclear": [],
}
UNCLEAR = "unclear"

# Sentences must sound like a reading of reviews, not a verdict
NEEDS_REVIEWS = re.compile(r"\breview(?:s|ers?)?\b", re.IGNORECASE)
CERTAIN_WORDS = re.compile(r"\b(?:caused|causing|because|due to|the reason|clearly|definitely|obviously|proves?|proved|confirmed|"
                           r"undoubtedly|certainly|all players|everyone)\b", re.IGNORECASE)

# Common words left out when finding what an event's reviews talk about
STOPWORDS = set("""a about after again all also am an and any are as at be been before being but by can could did do does doing
don't for from game games get got had has have he her his how i i'm if in into is it it's its just like me more most my no not now
of on one only or other our out over play played playing really so some still than that the their them then there these they
this to too up us very was we were what when which who will with would you your even much make made back time way well
""".split())

# A Unix time as a short date for the evidence lines
def day_text(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")

# One flagged event per run of consecutive flagged months: its months, kind and numbers
def events_of(data: dict) -> list[dict]:
    runs: dict = {}
    for row in rows(data["events"]):
        runs.setdefault(row["episode"], []).append(row)
    fetched = pd.Timestamp(data["fetched_at"], tz="UTC") + pd.Timedelta(days=1)
    events = []
    for run in runs.values():
        first, last = run[0], run[-1]
        start = pd.Timestamp(first["start"])
        end = fetched if last["label"] == "last 30d" else pd.Timestamp(last["start"]) + pd.DateOffset(months=1)
        surge = any(row["kind"] == "Negative surge" for row in run)
        events.append({"start_label": first["label"], "end_label": last["label"], "months": run, "start": start, "end": end,
                       "kind": "Negative surge" if surge else "Score drop"})
    return events

# Numbered fact lines (F1, F2, ...) about one event, from the exported events table only
def event_facts(event: dict, name: str) -> dict:
    run = event["months"]
    when = month_text(run[0]["label"]) + ("" if len(run) == 1 else f" to {month_text(run[-1]['label'])}")
    kind = ("a negative surge (far more negative reviews than usual, often called a review bomb)" if event["kind"] == "Negative surge"
            else "a score drop (the monthly score fell well below its usual level)")
    facts = {"F1": f"{name} had {kind}, {when}"}
    for row in run:
        facts[f"F{len(facts) + 1}"] = (f"{month_text(row['label'])}: {round(row['pct_positive'])}% positive across {row['reviews']:,} reviews "
                                       f"({row['negative']:,} negative), against a usual {round(row['usual_pct'])}% positive and "
                                       f"{round(row['usual_negative']):,} negative a month")
    return facts

# A short fingerprint of an event's facts, so unchanged events are skipped (and checkable from site_data alone)
def facts_hash(event: dict, name: str) -> str:
    text = json.dumps({"version": PROMPT_VERSION, "facts": event_facts(event, name)}, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()[:16]

# Whether each review was written during the event
def during(df: pd.DataFrame, event: dict) -> pd.Series:
    return (df["created"] >= event["start"]) & (df["created"] < event["end"])

# Negative reviews written during the event, most upvoted first, with ones edited long afterwards last
def event_reviews(df: pd.DataFrame, event: dict) -> pd.DataFrame:
    negative = clean(df[during(df, event) & ~df["voted_up"]])
    edited_late = (negative["updated"] - negative["created"]) > pd.Timedelta(days=LATE_EDIT_DAYS)
    return negative.assign(edited_late=edited_late).sort_values(["edited_late", "votes_up"], ascending=[True, False])

# A review cut to a short excerpt on a word boundary, on one line
def excerpt(text: str, limit: int) -> str:
    text = " ".join(str(text).replace('"', "'").split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."

# Words that show up far more in the event's negative reviews than in the game's other reviews
def distinctive_words(df: pd.DataFrame, event: dict, event_texts: list[str]) -> set[str]:
    other = df[~during(df, event)]["review"].head(3000)

    def counts(texts) -> Counter:
        return Counter(word for text in texts for word in set(re.findall(r"[a-z][a-z'-]{2,}", str(text).lower())) if word not in STOPWORDS)

    def share(word: str, counter: Counter, total: int) -> float:
        return (counter[word] + 1) / (total + 1)

    inside, outside = counts(event_texts), counts(other)
    scored = {word: share(word, inside, len(event_texts)) / share(word, outside, len(other)) for word, n in inside.items() if n >= 3}
    return set(sorted(scored, key=scored.get, reverse=True)[:DISTINCTIVE_WORDS])

# Mostly English titles, so foreign-language press does not crowd the prompt
def looks_english(text: str) -> bool:
    letters = re.findall(r"[^\W\d_]", text)
    return bool(letters) and sum(letter.isascii() for letter in letters) / len(letters) > 0.9

# The news lines to show the model: official posts and press titles that match what the reviews talk about
def pick_news(news: list[dict], words: set[str]) -> list[dict]:
    def score(item) -> int:
        return len(words & set(re.findall(r"[a-z][a-z'-]{2,}", f"{item['title']} {item['snippet']}".lower())))

    usable = [item for item in news if looks_english(item["title"]) and "Top Sellers" not in item["title"]]
    official = sorted((item for item in usable if item["official"]), key=score, reverse=True)[:OFFICIAL_LINES]
    press = [item for item in sorted((item for item in usable if not item["official"]), key=score, reverse=True) if score(item) > 0][:PRESS_LINES]
    return sorted(official + press, key=lambda item: item["date"])

# Every line the model sees for one event: facts (F), reviews (R) and news (N), plus the news items behind the N lines
def event_lines(appid: int, data: dict, event: dict) -> tuple[dict, dict]:
    lines, items = event_facts(event, data["name"]), {}
    path, _ = cache_paths(appid)
    if not path.exists():
        return lines, items
    df = pd.read_parquet(path).drop_duplicates("recommendationid")
    reviews = event_reviews(df, event)
    if reviews.empty:
        return lines, items
    for i, (_, review) in enumerate(reviews.head(REVIEW_LINES).iterrows(), 1):
        lines[f"R{i}"] = f'(negative review, {review["playtime_at_review_h"]:.0f}h played) "{excerpt(review["review"], REVIEW_CHARS)}"'
    start = int((event["start"] - pd.Timedelta(days=NEWS_DAYS_BEFORE)).timestamp())
    news = load_news(appid, start, int(event["end"].timestamp()))
    for item in pick_news(news, distinctive_words(df, event, reviews["review"].tolist())):
        key = f"N{len(items) + 1}"
        details = f" - {excerpt(item['snippet'], 200)}" if item["official"] and item["snippet"] else ""
        lines[key] = f"{day_text(item['date'])}, {item['source']}: {item['title']}{details}"
        items[key] = item
    return lines, items

# The instructions and evidence sent to the model
def build_prompt(data: dict, lines: dict) -> str:
    evidence = "\n".join(f"{key}: {text}" for key, text in lines.items())
    tags = ", ".join(f'"{tag}"' for tag in TAGS)
    return f"""You explain, in one or two short sentences, why a Steam game had a flagged event on SteamTLDR, a site that tells gamers why players like or dislike a game.

Evidence about {data['name']}: facts about the event (F lines), negative Steam reviews written during it (R lines) and Steam news from around that time (N lines: official announcements and press headlines):
{evidence}

Answer with JSON:
- "reason": {MIN_SENTENCES} or {MAX_SENTENCES} sentences, each {{"text": "...", "cites": ["R2", "N1"]}}, listing every line it uses. Say what the negative reviews were about, and link it to a news item only when an N line clearly covers the same thing.
- "tags": 1 or {MAX_TAGS} reason tags from this fixed list: {tags}. Each is {{"tag": "...", "cites": ["R1", "R4"]}}, citing R or N lines that show the reason.

Rules:
- Use only the lines above. Never add anything you know about the game, its developer or the news from elsewhere.
- Report what reviews say, not what is true: write "reviews blame...", "negative reviews focus on...", "reviews tie this to...". Every sentence cites at least one R or N line, and the first sentence mentions reviews.
- Never state a cause as fact: no "caused", "because", "due to", "the reason", "clearly", "confirmed".
- Only N lines marked "Official announcement" are announcements; call every other N line a news report or headline.
- Copy every number exactly as written in a line the sentence cites; at most 2 numbers per sentence. Do not round or compute numbers.
- You may quote at most {MAX_QUOTES} short phrase, copied word for word from an R line inside double quotes. Pick one without swearing.
- At most {MAX_WORDS} words per sentence. Neutral, plain news-brief tone; no hype, no emoji or markdown, no line IDs in the text.
- If the reviews do not agree on a reason, write one sentence saying reviews from this time do not point to one clear reason, and use the single tag "{UNCLEAR}" with no cites.

Example: {{"reason": [{{"text": "Negative reviews in this period mostly object to a new account requirement, which an official announcement from the same week covers.", "cites": ["R1", "R3", "N2"]}}], "tags": [{{"tag": "account/DRM", "cites": ["R1", "N2"]}}]}}"""

# Whether a line contains one of a tag's words as a whole word
def mentions(text: str, words: list[str]) -> bool:
    return any(re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", text, re.IGNORECASE) for word in words)

# Problems with the model's answer, empty when it passes every check; also used offline by check_site_data.py
def check_reason(answer, lines: dict) -> list[str]:
    if not isinstance(answer, dict):
        return ['The answer must be a JSON object with "reason" and "tags"']
    sentences, tags = answer.get("reason"), answer.get("tags")
    if not isinstance(sentences, list) or not MIN_SENTENCES <= len(sentences) <= MAX_SENTENCES:
        return [f'"reason" must be a list of {MIN_SENTENCES} or {MAX_SENTENCES} sentences']
    if not isinstance(tags, list) or not 1 <= len(tags) <= MAX_TAGS:
        return [f'"tags" must be a list of 1 or {MAX_TAGS} tags']
    errors, unclear = [], any(isinstance(tag, dict) and tag.get("tag") == UNCLEAR for tag in tags)
    for i, sentence in enumerate(sentences):
        text = sentence.get("text") if isinstance(sentence, dict) else None
        cites = sentence.get("cites") if isinstance(sentence, dict) else None
        if not isinstance(text, str) or not text or not isinstance(cites, list):
            errors.append('Each sentence must be {"text": "...", "cites": [...]}')
            continue
        unknown = [cite for cite in cites if not isinstance(cite, str) or cite not in lines]
        if unknown:
            errors.append(f'Sentence "{text}" cites lines that do not exist: {unknown}')
            continue
        if not unclear and not any(cite[0] in "RN" for cite in cites):
            errors.append(f'Sentence "{text}" must cite at least one R or N line')
        if i == 0 and not NEEDS_REVIEWS.search(text):
            errors.append(f'The first sentence must say it is reading reviews ("reviews blame...", "negative reviews focus on..."): "{text}"')
        cited = " ".join(lines[cite] for cite in cites)
        cited_reviews = normalize(" ".join(lines[cite] for cite in cites if cite.startswith("R")))
        for phrase in QUOTED.findall(text):
            if normalize(phrase) not in cited_reviews:
                errors.append(f'Quoted phrase "{phrase}" is not copied word for word from a cited R line')
        unquoted = QUOTED.sub("", text)
        missing = numbers_in(unquoted) - numbers_in(cited)
        if missing:
            errors.append(f'Sentence "{text}" uses {", ".join(sorted(missing))}, which is not in the lines it cites')
        if len(NUMBER.findall(unquoted)) > 2:
            errors.append(f'Sentence "{text}" uses more than 2 numbers')
        if CITE_ID.search(text) or re.search(r"\b[RN]\d+\b", text):
            errors.append(f'Sentence "{text}" has line IDs in its text; put them only in "cites"')
        if len(text.split()) > MAX_WORDS:
            errors.append(f'Sentence "{text}" is longer than {MAX_WORDS} words')
        certain = sorted({word.lower() for word in CERTAIN_WORDS.findall(unquoted)})
        if certain:
            errors.append(f'Report what reviews say instead of stating a cause; remove: {", ".join(certain)}')
        hype = sorted({word.lower() for word in HYPE_WORDS.findall(unquoted)})
        if hype:
            errors.append(f'Remove hype words: {", ".join(hype)}')
        if SWEARING.search(text):
            errors.append("Pick a quote without swearing")
    quotes = sum(len(QUOTED.findall(s.get("text", ""))) for s in sentences if isinstance(s, dict) and isinstance(s.get("text"), str))
    if quotes > MAX_QUOTES:
        errors.append(f"Quote at most {MAX_QUOTES} review phrase in all")
    for tag in tags:
        name = tag.get("tag") if isinstance(tag, dict) else None
        cites = tag.get("cites", []) if isinstance(tag, dict) else []
        if name not in TAGS:
            errors.append(f'Tag {name!r} is not in the list; use only: {", ".join(TAGS)}')
        elif name == UNCLEAR:
            if len(tags) > 1:
                errors.append(f'"{UNCLEAR}" must be the only tag')
        elif not isinstance(cites, list) or not cites or any(not isinstance(c, str) or c not in lines or c[0] not in "RN" for c in cites):
            errors.append(f'Tag "{name}" must cite existing R or N lines')
        elif not any(mentions(lines[cite], TAGS[name]) for cite in cites):
            errors.append(f'None of the lines cited for tag "{name}" talk about it; cite lines that do, or pick another tag')
    return errors

# Parse the model's reply, allowing a ```json fence
def parse(raw: str):
    try:
        return json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip()))
    except json.JSONDecodeError:
        return None

# Explain one event, retrying with the problems listed; returns the saved record or None, plus the last problems
def explain_event(appid: int, data: dict, event: dict) -> tuple[dict | None, list[str]]:
    lines, items = event_lines(appid, data, event)
    if not any(key.startswith("R") for key in lines):
        return None, ["no negative reviews from this period in the sample"]
    prompt, feedback, errors = build_prompt(data, lines), "", []
    for _ in range(ATTEMPTS):
        raw = complete(prompt + feedback)
        answer = parse(raw)
        errors = ["The answer was not valid JSON"] if answer is None else check_reason(answer, lines)
        if not errors:
            cited = sorted({cite for part in answer["reason"] + answer["tags"] for cite in part.get("cites", [])},
                           key=lambda cite: (cite[0], int(cite[1:])))
            return {
                "start": event["start_label"], "end": event["end_label"], "kind": event["kind"],
                "reason": [{"text": s["text"].strip(), "cites": s["cites"]} for s in answer["reason"]],
                "tags": [{"tag": t["tag"], "cites": t.get("cites", [])} for t in answer["tags"]],
                "lines": {key: text for key, text in lines.items() if key in cited or key.startswith("F")},
                "news": [{"id": key, "title": items[key]["title"], "date": day_text(items[key]["date"]), "source": items[key]["source"],
                          "url": items[key]["url"]} for key in cited if key in items],
                "model": model_name(), "generated": date.today().isoformat(),
                "input_hash": facts_hash(event, data["name"]), "prompt_version": PROMPT_VERSION,
            }, []
        feedback = "\n\nYour previous answer broke these rules. Fix every one:\n- " + "\n- ".join(errors) + f"\n\nPrevious answer:\n{raw}"
    return None, errors

# Old explanations whose event facts have not changed, keyed by the event's first month
def current_reasons(data: dict) -> dict:
    events = {event["start_label"]: event for event in events_of(data)}
    return {old["start"]: old for old in data.get(REASONS_FIELD) or []
            if old["start"] in events and old.get("input_hash") == facts_hash(events[old["start"]], data["name"])}

# Explain the flagged events of the given exported games, skipping unchanged ones
def main() -> None:
    from export import EXPORT_DIR

    parser = argparse.ArgumentParser(description="Explain each flagged event from its reviews and Steam news, checked in code.")
    parser.add_argument("appids", type=int, nargs="*", help="app IDs to explain (default: every exported game with events)")
    parser.add_argument("--only", help="explain only the event starting in this month, like 2024-05")
    parser.add_argument("--force", action="store_true", help="explain again even when the facts have not changed")
    parser.add_argument("--prompt", action="store_true", help="print the prompts and stop, without calling the model")
    parser.add_argument("--limit", type=int, help="stop after asking the model about this many events")
    args = parser.parse_args()

    paths = [EXPORT_DIR / f"{appid}.json" for appid in args.appids] or sorted(p for p in EXPORT_DIR.glob("*.json") if p.stem.isdigit())
    asked = written = failed = unreachable = 0
    for path in paths:
        data, appid = json.loads(path.read_text()), int(path.stem)
        kept, changed = current_reasons(data), False
        for event in events_of(data):
            label = f"{data['name']}, {event['start_label']}"
            if args.only and event["start_label"] != args.only:
                continue
            if args.prompt:
                print(build_prompt(data, event_lines(appid, data, event)[0]), "\n")
                continue
            if event["start_label"] in kept and not args.force:
                print(f"{label}: unchanged, skipped")
                continue
            if args.limit is not None and asked >= args.limit:
                break
            asked += 1
            try:
                record, errors = explain_event(appid, data, event)
            except ModelError as error:
                failed += 1
                unreachable += 1
                print(f"{label}: the model could not be reached ({error}), left as it was")
                if unreachable >= MAX_UNREACHABLE_IN_A_ROW:
                    print(f"Stopping: the model could not be reached {unreachable} times in a row, probably a rate limit")
                    return
                continue
            unreachable = 0
            if record is None:
                failed += 1
                print(f"{label}: no explanation ({'; '.join(errors)})")
                continue
            written += 1
            kept[event["start_label"]], changed = record, True
            print(f"{label} [{', '.join(t['tag'] for t in record['tags'])}]:\n  " + " ".join(s["text"] for s in record["reason"]))
        if changed or len(kept) != len(data.get(REASONS_FIELD) or []):
            data[REASONS_FIELD] = sorted(kept.values(), key=lambda record: record["start"])
            path.write_text(json.dumps(data, separators=(",", ":")))
    if not args.prompt:
        print(f"Explained {written}, failed {failed} (model {model_name()})")

# Entry point
if __name__ == "__main__":
    main()
