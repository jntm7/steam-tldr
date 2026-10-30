import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from fetch import cache_is_fresh, cache_paths
from games import GAMES

# Progress bar width, how often --watch redraws, and the longest gap between games that still counts toward the pace
BAR_WIDTH = 30
REFRESH_SECONDS = 5
MAX_GAP_MINUTES = 30

# How many finished and waiting games the short view lists
SHORT_DONE = 3
SHORT_PENDING = 5

# When a game was fetched, or None when it has no fresh cache
def fetched_at(appid: int) -> datetime | None:
    data_path, meta_path = cache_paths(appid)
    if not (data_path.exists() and cache_is_fresh(meta_path)):
        return None
    return datetime.fromisoformat(json.loads(meta_path.read_text())["fetched_at"])

# Median minutes between consecutive fetches, ignoring long pauses, or None with too little to go on
def minutes_per_game(times: list[datetime]) -> float | None:
    gaps = [(b - a).total_seconds() / 60 for a, b in zip(sorted(times), sorted(times)[1:])]
    gaps = [gap for gap in gaps if gap < MAX_GAP_MINUTES]
    return statistics.median(gaps) if gaps else None

# Draw a text bar for a share between 0 and 1
def bar(share: float) -> str:
    filled = round(share * BAR_WIDTH)
    return "█" * filled + "░" * (BAR_WIDTH - filled)

# Show a number of minutes as minutes or hours
def duration(minutes: float) -> str:
    return f"{minutes:.0f} min" if minutes < 90 else f"{minutes / 60:.1f} h"

# One game's line: its state mark, name and when it finished
def line(mark: str, appid: int, note: str = "") -> str:
    return f"  {mark} {GAMES[appid]:<32} {note}".rstrip()

# Build the progress report for every game in the list, and whether all are cached
def report(show_all: bool) -> tuple[list[str], bool]:
    fetched = {appid: fetched_at(appid) for appid in GAMES}
    done = [appid for appid in GAMES if fetched[appid]]
    pending = [appid for appid in GAMES if not fetched[appid]]
    share = len(done) / len(GAMES)

    lines = [f"Fetching {len(GAMES)} games", f"{bar(share)} {len(done)}/{len(GAMES)} ({share:.0%})"]
    pace = minutes_per_game([fetched[appid] for appid in done])
    if pending and pace:
        lines.append(f"About {duration(pace)} per game, roughly {duration(pace * len(pending))} left")
    if not pending:
        return lines + ["All games cached"], True

    lines += ["", f"Now: {GAMES[pending[0]]} ({pending[0]})", ""]
    if show_all:
        lines += [line("✓", appid, f"{fetched[appid].astimezone():%b %-d %H:%M}") if fetched[appid]
                  else line("→" if appid == pending[0] else "·", appid) for appid in GAMES]
    else:
        latest = sorted(done, key=lambda appid: fetched[appid])[-SHORT_DONE:]
        lines += [line("✓", appid, f"{fetched[appid].astimezone():%b %-d %H:%M}") for appid in latest]
        lines += [line("→" if i == 0 else "·", appid) for i, appid in enumerate(pending[:SHORT_PENDING])]
        if len(pending) > SHORT_PENDING:
            lines.append(f"    ...and {len(pending) - SHORT_PENDING} more (use --all to list every game)")
    return lines, False

# Overwrite the previous report in place: move up over it, rewrite each line, and clear anything left below
def redraw(lines: list[str], previous: int) -> None:
    if previous:
        print(f"\033[{previous}F", end="")
    print("".join(f"{text}\033[K\n" for text in lines), end="\033[J", flush=True)

# Show progress once, or keep one report updating in place until every game is cached
def main() -> None:
    parser = argparse.ArgumentParser(description="Show how far fetching the game list has got.")
    parser.add_argument("--watch", action="store_true", help=f"update in place every {REFRESH_SECONDS} seconds until done")
    parser.add_argument("--all", action="store_true", help="list every game, not just the latest and next")
    args = parser.parse_args()

    if not args.watch:
        print("\n".join(report(args.all)[0]))
        return

    printed = 0
    print("\033[?25l", end="")
    try:
        while True:
            lines, finished = report(args.all)
            lines += [] if finished else ["", f"Updated {datetime.now(timezone.utc).astimezone():%H:%M:%S}, Ctrl-C to stop"]
            redraw(lines, printed)
            printed = len(lines)
            if finished:
                return
            time.sleep(REFRESH_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        print("\033[?25h", end="")

# Entry point
if __name__ == "__main__":
    main()
