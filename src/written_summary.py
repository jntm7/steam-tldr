import argparse
import hashlib
import json
import re
from datetime import date
from llm import ModelError, complete, model_name
from summarize import SAME_SCORE_POINTS

# Field in site_data/<appid>.json that holds the written summary
WRITTEN_FIELD = "written_summary"

# Bump when the prompt or facts change, so every game is written again
PROMPT_VERSION = 7

# How long each part may be, in sentences, words and numbers
TLDR_SENTENCES = 2
TLDR_MAX_WORDS = 40
TLDR_MAX_NUMBERS = 2

# A last-30-days change this big, in points, must be in the TL;DR (the game page's warning uses the same cut-off)
BIG_CHANGE_POINTS = 10
DETAIL_SENTENCES = 2
DETAILS_MAX_NUMBERS = 3
DETAILS_MAX_QUOTES = 1
SENTENCE_MAX_NUMBERS = 2
MAX_SENTENCE_WORDS = 40

# How many times to ask the model before giving up on a game, and how many unreachable games in a row end the run
ATTEMPTS = 3
MAX_UNREACHABLE_IN_A_ROW = 3

# Readable names for Steam's playtime groups
PLAYTIME_NAMES = {"<2h": "under 2 hours", "2-10h": "2 to 10 hours", "10-50h": "10 to 50 hours", "50h+": "over 50 hours"}

# Patterns for numbers and quoted phrases in the model's sentences
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
QUOTED = re.compile(r"[\"“”]([^\"“”]+)[\"“”]")
CITE_ID = re.compile(r"\b[FQ]\d+\b")

# Hype and absolute claims kept out of the neutral tone, outside quotes
HYPE_WORDS = re.compile(r"\b(?:masterpiece|massive hit|must[- ]play|universally|beloved|widely loved|stunning|incredible|amazing|phenomenal|"
                        r"flawless|legendary|gem|boast(?:s|ing)?|exceptional(?:ly)?|pays off|perfect(?:ly)?|"
                        r"no complaints|zero complaints|everyone|everybody|nobody|all players|every player)\b", re.IGNORECASE)
SWEARING = re.compile(r"\b(?:shit\w*|dogshit|bullshit|fuck\w*|damn|crap\w*|ass|asshole|bitch\w*|piss\w*|wtf|stfu)\b", re.IGNORECASE)
PERCENT_OF_PLAYERS = re.compile(r"\d+% of (?:all )?(?:players|people|gamers|users)\b", re.IGNORECASE)

# Rows of an exported table as dicts
def rows(table: dict | None) -> list[dict]:
    return [] if table is None else [dict(zip(table["columns"], row)) for row in table["data"]]

# "2024-05" as "May 2024", and the trend's last row as "the last 30 days"
def month_text(label: str) -> str:
    return date.fromisoformat(f"{label}-01").strftime("%b %Y") if re.fullmatch(r"\d{4}-\d{2}", label) else "the last 30 days"

# Numbered fact lines (F1, F2, ...) and quote lines (Q1, Q2, ...) taken from one exported game
def build_facts(data: dict) -> tuple[dict, dict]:
    facts, quotes = {}, {}

    def fact(text: str) -> None:
        facts[f"F{len(facts) + 1}"] = text

    def quote(text: str | None, label: str) -> None:
        if text:
            quotes[f"Q{len(quotes) + 1}"] = f'({label}) "{text}"'

    overall = round(data["pct_positive"])
    fact(f"Steam rating: {data['score_desc']}, {overall}% positive across {data['total_reviews']:,} English reviews (all time)")
    recent = rows(data["trend"])[-1]
    if recent["reviews"]:
        change = round(recent["pct_positive"]) - overall
        direction = "about the same as" if abs(change) < SAME_SCORE_POINTS else f"{abs(change)} points {'higher' if change > 0 else 'lower'} than"
        fact(f"Last 30 days: {round(recent['pct_positive'])}% positive across {recent['reviews']:,} reviews, {direction} the all-time score")
    for row in rows(data["praise"]):
        fact(f"Praise: {round(row['pct'])}% of all reviews praise {row['theme']}")
        quote(row["example"], f"praise, {row['theme']}")
    for row in rows(data["complaints"]):
        fact(f"Complaint: {round(row['pct'])}% of all reviews complain about {row['theme']}")
        quote(row["example"], f"complaint, {row['theme']}")
    for row in rows(data["recent_complaints"]):
        fact(f"Complaint in the last 30 days: {round(row['pct'])}% of recent reviews complain about {row['theme']}, against {round(row['all_time_pct'])}% all time")
        quote((row["examples"] or [None])[0], f"recent complaint, {row['theme']}")
    for row in rows(data["playtime"]):
        if row["reviews"] and row["pct_positive"] is not None:
            fact(f"Players with {PLAYTIME_NAMES.get(row['group'], row['group'])} at review time: {round(row['pct_positive'])}% positive across {row['reviews']:,} reviews")
    episodes: dict = {}
    for row in rows(data["events"]):
        episodes.setdefault(row["episode"], []).append(row)
    for run in episodes.values():
        when = month_text(run[0]["label"]) + ("" if len(run) == 1 else f" to {month_text(run[-1]['label'])}")
        kind = "negative surge (a wave of negative reviews, often called a review bomb)" if any(r["kind"] == "Negative surge" for r in run) else "score drop"
        lowest = min(r["pct_positive"] for r in run)
        fact(f"Flagged event, {when}: a {kind}; the monthly score fell to {round(lowest)}% positive from a usual {round(run[0]['usual_pct'])}%")
    return facts, quotes

# The last-30-days fact line when it differs from the all-time score by a lot, else None
def big_change_line(data: dict, facts: dict) -> str | None:
    recent = rows(data["trend"])[-1]
    if not recent["reviews"] or abs(round(recent["pct_positive"]) - round(data["pct_positive"])) < BIG_CHANGE_POINTS:
        return None
    return next(key for key, text in facts.items() if text.startswith("Last 30 days"))

# A short fingerprint of everything the summary is written from, so unchanged games are skipped
def input_hash(data: dict) -> str:
    facts, quotes = build_facts(data)
    text = json.dumps({"version": PROMPT_VERSION, "facts": facts, "quotes": quotes}, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()[:16]

# The instructions, facts and quotes sent to the model
def build_prompt(data: dict, facts: dict, quotes: dict, must_cite: str | None) -> str:
    name, verdict = data["name"], verdict_text(data)
    lines = "\n".join(f"{key}: {text}" for key, text in {**facts, **quotes}.items())
    swing = f"\n- The last 30 days ({must_cite}) differ a lot from the all-time score, so the tldr must say so and cite {must_cite}." if must_cite else ""
    return f"""You write the short summary at the top of a game's page on SteamTLDR, a site that tells gamers why players like or dislike a Steam game.

Facts about {name} (F lines) and short quotes from real Steam reviews (Q lines):
{lines}

Answer with JSON holding two lists of sentences:
- "tldr": exactly {TLDR_SENTENCES} short sentences, at most {TLDR_MAX_WORDS} words in all, that a gamer can read in five seconds. Start with the Steam rating written exactly as "{verdict}" (cite F1), then the main thing players love and the main thing they complain about. Use at most {TLDR_MAX_NUMBERS} numbers in total and no quotes, and leave the rest of the numbers to "details".
- "details": exactly {DETAIL_SENTENCES} more sentences that explain what the tldr left out, the way a friend who read the reviews would: pick the two most useful points from what changed recently, how new and long-time players feel differently, and what a flagged event means for someone buying now. Each sentence makes one point in plain words and backs it with at most {SENTENCE_MAX_NUMBERS} numbers; use at most {DETAILS_MAX_NUMBERS} numbers in all. Leave out review counts, and do not list one number after another; words like "most", "few" or "far more" are fine when the cited line supports them. You may add at most {DETAILS_MAX_QUOTES} short review quote, one that fits the point the sentence makes.
Each sentence is {{"text": "...", "cites": ["F1", "Q2"]}}, listing every F and Q line it uses.

Rules:
- Use only the lines above. Never add anything you know about the game from elsewhere.
- Copy every number exactly as written in a line the sentence cites. Do not round, add, subtract or convert numbers.
- Theme percentages are shares of all reviews: write "23% of reviews praise the co-op", never "23% of players".
- To quote a review, copy a short phrase word for word from a Q line inside double quotes, and cite that Q line.
- Pick quotes without swearing, and write in standard English ("recent reviews", not "recents").
- Name themes in everyday words ("the co-op", "bugs and crashes", "the price"), not as labels joined with "&".
- Write like a short, neutral news brief, at most {MAX_SENTENCE_WORDS} words per sentence. No hype words (masterpiece, massive hit, amazing, beloved), no absolute claims (no complaints, everyone), no emoji or markdown.
- The only rating label you may use is Steam's own, "{data['score_desc']}". Never make up labels like "overwhelmingly liked".{swing}

Example tldr sentence for another game: {{"text": "Mixed (55%): players like the building but find the late game thin.", "cites": ["F1", "F3", "F9"]}}"""

# The Steam rating and all-time percent as the TL;DR must open with them, like "Mostly Positive (79%)"
def verdict_text(data: dict) -> str:
    return f"{data['score_desc']} ({round(data['pct_positive'])}%)"

# Lowercase text with one kind of apostrophe and single spaces, for comparing quotes
def normalize(text: str) -> str:
    return " ".join(text.lower().replace("’", "'").replace("‘", "'").split())

# Every number in a piece of text, without thousands commas
def numbers_in(text: str) -> set[str]:
    return {number.replace(",", "") for number in NUMBER.findall(text)}

# How many numbers a sentence uses outside quotes and the game name
def count_numbers(text: str, name: str) -> int:
    return len(NUMBER.findall(QUOTED.sub("", text).replace(name, "")))

# Problems with one list of sentences: wrong length, missing or unknown citations, numbers or quotes not in the cited lines or the game name
def check_sentences(sentences, part: str, count: int, facts: dict, quotes: dict, name: str) -> list[str]:
    if not isinstance(sentences, list) or len(sentences) != count:
        return [f'"{part}" must be a list of exactly {count} sentences']
    errors = []
    for sentence in sentences:
        text = sentence.get("text", "") if isinstance(sentence, dict) else ""
        cites = sentence.get("cites", []) if isinstance(sentence, dict) else []
        unknown = [cite for cite in cites if cite not in facts and cite not in quotes]
        if not text or not cites or unknown:
            errors.append(f'Sentence "{text}" must cite existing F or Q lines (unknown: {unknown})')
            continue
        cited = " ".join([name] + [facts.get(cite) or quotes[cite] for cite in cites])
        cited_quotes = normalize(" ".join(quotes[cite] for cite in cites if cite in quotes))
        for phrase in QUOTED.findall(text):
            if normalize(phrase) not in cited_quotes:
                errors.append(f'Quoted phrase "{phrase}" is not copied word for word from a cited Q line')
        missing = numbers_in(QUOTED.sub("", text)) - numbers_in(cited)
        if missing:
            errors.append(f'Sentence "{text}" uses {", ".join(sorted(missing))}, which is not in the lines it cites ({", ".join(cites)})')
        if CITE_ID.search(text):
            errors.append(f'Sentence "{text}" has line IDs in its text; put them only in "cites"')
        if len(text.split()) > MAX_SENTENCE_WORDS:
            errors.append(f'Sentence "{text}" is longer than {MAX_SENTENCE_WORDS} words')
    return errors

# Problems with the model's whole answer, empty when it passes every check
def check_answer(raw: str, facts: dict, quotes: dict, data: dict, must_cite: str | None) -> tuple[dict | None, list[str]]:
    name = data["name"]
    try:
        answer = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip()))
    except json.JSONDecodeError:
        return None, ["The answer was not valid JSON"]
    if not isinstance(answer, dict):
        return None, ["The answer must be a JSON object with \"tldr\" and \"details\""]
    errors = (check_sentences(answer.get("tldr"), "tldr", TLDR_SENTENCES, facts, quotes, name)
              + check_sentences(answer.get("details"), "details", DETAIL_SENTENCES, facts, quotes, name))
    if not errors:
        tldr = " ".join(sentence["text"] for sentence in answer["tldr"])
        if len(tldr.split()) > TLDR_MAX_WORDS:
            errors.append(f'"tldr" is {len(tldr.split())} words; keep it to {TLDR_MAX_WORDS}')
        if count_numbers(tldr, name) > TLDR_MAX_NUMBERS:
            errors.append(f'"tldr" uses more than {TLDR_MAX_NUMBERS} numbers; move the rest to "details"')
        details_numbers = [count_numbers(sentence["text"], name) for sentence in answer["details"]]
        if sum(details_numbers) > DETAILS_MAX_NUMBERS or max(details_numbers) > SENTENCE_MAX_NUMBERS:
            errors.append(f'"details" may use at most {SENTENCE_MAX_NUMBERS} numbers per sentence and {DETAILS_MAX_NUMBERS} in all; explain in words instead of listing numbers')
        if must_cite and not any(must_cite in sentence["cites"] for sentence in answer["tldr"]):
            errors.append(f'"tldr" must mention the big change in the last 30 days and cite {must_cite}')
        if not normalize(answer["tldr"][0]["text"]).startswith(normalize(verdict_text(data))):
            errors.append(f'"tldr" must start with the Steam rating written exactly as "{verdict_text(data)}"')
        if QUOTED.search(tldr):
            errors.append('"tldr" must not quote reviews; quotes belong in "details"')
        details = " ".join(sentence["text"] for sentence in answer["details"])
        if len(QUOTED.findall(details)) > DETAILS_MAX_QUOTES:
            errors.append(f'"details" may quote at most {DETAILS_MAX_QUOTES} review')
        unquoted = QUOTED.sub("", f"{tldr} {details}")
        hype = sorted({word.lower() for word in HYPE_WORDS.findall(unquoted)})
        if hype:
            errors.append(f'Remove hype words and absolute claims: {", ".join(hype)}')
        swearing = sorted({word.lower() for word in SWEARING.findall(f"{tldr} {details}")})
        if swearing:
            errors.append(f'Pick a quote without swearing (found: {", ".join(swearing)})')
        if PERCENT_OF_PLAYERS.search(unquoted):
            errors.append('Percentages are shares of reviews: write "% of reviews", never "% of players"')
    return answer, errors

# Write and check one game's summary, retrying with the problems listed, or None when it still fails
def write_summary(data: dict) -> tuple[dict | None, list[str]]:
    facts, quotes = build_facts(data)
    must_cite = big_change_line(data, facts)
    prompt = build_prompt(data, facts, quotes, must_cite)
    feedback = ""
    for _ in range(ATTEMPTS):
        raw = complete(prompt + feedback)
        answer, errors = check_answer(raw, facts, quotes, data, must_cite)
        if not errors:
            def keep(sentences):
                return [{"text": s["text"].strip(), "cites": s["cites"]} for s in sentences]
            return {
                "tldr": keep(answer["tldr"]), "details": keep(answer["details"]), "model": model_name(),
                "generated": date.today().isoformat(), "input_hash": input_hash(data), "prompt_version": PROMPT_VERSION,
            }, []
        feedback = "\n\nYour previous answer broke these rules. Fix every one:\n- " + "\n- ".join(errors) + f"\n\nPrevious answer:\n{raw}"
    return None, errors

# Write summaries for the given exported games, skipping ones whose facts have not changed
def main() -> None:
    from export import EXPORT_DIR

    parser = argparse.ArgumentParser(description="Write a short, fact-checked summary into each exported game file.")
    parser.add_argument("appids", type=int, nargs="*", help="app IDs to write (default: every exported game)")
    parser.add_argument("--force", action="store_true", help="write again even when the facts have not changed")
    parser.add_argument("--prompt", action="store_true", help="print the prompt and stop, without calling the model")
    parser.add_argument("--limit", type=int, help="stop after asking the model about this many games")
    args = parser.parse_args()

    paths = [EXPORT_DIR / f"{appid}.json" for appid in args.appids] or sorted(p for p in EXPORT_DIR.glob("*.json") if p.stem.isdigit())
    written = failed = unreachable = 0
    for i, path in enumerate(paths, start=1):
        data = json.loads(path.read_text())
        if args.prompt:
            facts, quotes = build_facts(data)
            print(build_prompt(data, facts, quotes, big_change_line(data, facts)))
            continue
        current = data.get(WRITTEN_FIELD)
        if current and current.get("input_hash") == input_hash(data) and not args.force:
            print(f"[{i}/{len(paths)}] {data['name']}: unchanged, skipped")
            continue
        if args.limit is not None and written + failed >= args.limit:
            print(f"Stopping: reached --limit {args.limit}")
            break
        try:
            summary, errors = write_summary(data)
        except ModelError as error:
            failed += 1
            unreachable += 1
            print(f"[{i}/{len(paths)}] {data['name']}: the model could not be reached ({error}), left as it was")
            if unreachable >= MAX_UNREACHABLE_IN_A_ROW:
                print(f"Stopping: the model could not be reached {unreachable} times in a row, probably a rate limit")
                break
            continue
        unreachable = 0
        if summary is None:
            failed += 1
            data.pop(WRITTEN_FIELD, None)
            print(f"[{i}/{len(paths)}] {data['name']}: failed the checks {ATTEMPTS} times, left without a summary\n  - " + "\n  - ".join(errors))
        else:
            written += 1
            data[WRITTEN_FIELD] = summary
            print(f"[{i}/{len(paths)}] {data['name']}:\n  " + " ".join(s["text"] for s in summary["tldr"])
                  + "\n  More: " + " ".join(s["text"] for s in summary["details"]))
        path.write_text(json.dumps(data, separators=(",", ":")))
    if not args.prompt:
        print(f"Written {written}, failed {failed} (model {model_name()})")

# Entry point
if __name__ == "__main__":
    main()
