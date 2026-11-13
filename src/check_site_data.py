import json
import sys
from pathlib import Path
from written_summary import PROMPT_VERSION, WRITTEN_FIELD, big_change_line, build_facts, check_answer, input_hash

# Where the exported summaries live (same folder as export.py writes to)
SITE_DATA = Path(__file__).resolve().parent.parent / "site_data"

# Fields every game file must have, and the ones that are tables saved as columns + data
REQUIRED_FIELDS = ["appid", "name", "fetched_at", "score_desc", "pct_positive", "total_reviews", "sampled_reviews"]
TABLE_FIELDS = ["trend", "events", "playtime", "praise", "complaints", "recent_complaints", "playtime_complaints", "shown_reviews"]

# Problems with one game's fields and tables
def check_fields(data: dict) -> list[str]:
    problems = [f"missing field {field}" for field in REQUIRED_FIELDS if field not in data]
    for field in TABLE_FIELDS:
        table = data.get(field, "missing")
        if table == "missing":
            problems.append(f"missing table {field}")
        elif table is not None and not (isinstance(table, dict) and {"columns", "data"} <= table.keys()):
            problems.append(f"table {field} is not saved as columns + data")
    return problems

# Problems with one game's written summary, re-running the same checks used when it was generated
def check_written(data: dict) -> list[str]:
    written = data[WRITTEN_FIELD]
    if written.get("prompt_version") != PROMPT_VERSION:
        return [f"written summary is on prompt version {written.get('prompt_version')}, not {PROMPT_VERSION}"]
    if written.get("input_hash") != input_hash(data):
        return ["written summary is out of date (its facts changed); run src/written_summary.py"]
    facts, quotes = build_facts(data)
    raw = json.dumps({"tldr": written["tldr"], "details": written["details"]})
    _, errors = check_answer(raw, facts, quotes, data, big_change_line(data, facts))
    return [f"written summary: {error}" for error in errors]

# Every problem in site_data/, plus games that have no written summary yet
def check_all() -> tuple[list[str], list[str]]:
    problems, unwritten = [], []
    game_files = {int(path.stem): path for path in SITE_DATA.glob("*.json") if path.stem.isdigit()}
    index_ids = {entry["appid"] for entry in json.loads((SITE_DATA / "index.json").read_text())}
    problems += [f"{appid}: in index.json but has no game file" for appid in sorted(index_ids - game_files.keys())]
    problems += [f"{appid}: has a game file but is missing from index.json" for appid in sorted(game_files.keys() - index_ids)]
    if not (SITE_DATA / "site.json").exists():
        problems.append("site.json is missing")
    for appid, path in sorted(game_files.items()):
        data = json.loads(path.read_text())
        game_problems = check_fields(data)
        if not game_problems and data.get(WRITTEN_FIELD):
            game_problems = check_written(data)
        elif not game_problems:
            unwritten.append(f"{appid} ({data['name']})")
        problems += [f"{appid} ({data.get('name')}): {problem}" for problem in game_problems]
    return problems, unwritten

# Print the results and fail (exit 1) when anything is wrong
def main() -> None:
    problems, unwritten = check_all()
    if unwritten:
        print(f"Note: {len(unwritten)} games have no written summary yet: {', '.join(unwritten)}")
    if problems:
        print(f"{len(problems)} problems in site_data/:")
        print("\n".join(f"- {problem}" for problem in problems))
        sys.exit(1)
    games = len(list(SITE_DATA.glob("[0-9]*.json")))
    print(f"site_data/ looks good: {games} games checked")

if __name__ == "__main__":
    main()
