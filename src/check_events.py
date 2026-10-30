import json
import sys
from fetch import cache_paths
from games import GAMES
from summarize import find_flagged_events, monthly_trend

# Well-known controversies the rule must keep flagging as negative surges, as (app ID, month)
KNOWN_SURGES = [
    (553850, "2024-05"),  # Helldivers 2: PlayStation Network account made mandatory
    (730, "2018-12"),     # CS:GO: went free-to-play, angering paying players
    (730, "2023-10"),     # CS2: replaced CS:GO, which players could no longer launch
    (271590, "2017-06"),  # GTA V: Take-Two shut down the OpenIV modding tool
    (289070, "2019-02"),  # Civilization VI: new EULA allowing wide personal data collection
    (949230, "2024-12"),  # Cities: Skylines II: free weekend players hit crashes and poor performance
]

# Flag each known month from the cached totals and report any the rule misses
def main() -> int:
    missed = 0
    for appid, month in KNOWN_SURGES:
        meta = json.loads(cache_paths(appid)[1].read_text())
        flagged = find_flagged_events(monthly_trend(meta))
        hit = flagged[(flagged["label"] == month) & (flagged["kind"] == "Negative surge")]
        missed += hit.empty
        print(f"{'ok  ' if not hit.empty else 'MISS'} {GAMES[appid]} {month}")
    print(f"\n{len(KNOWN_SURGES) - missed} of {len(KNOWN_SURGES)} known negative surges flagged")
    return 1 if missed else 0

# Entry point
if __name__ == "__main__":
    sys.exit(main())
