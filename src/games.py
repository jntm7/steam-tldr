from fetch import load_reviews

# Games for model training and testing
GAMES = {
    570: "Dota 2",
    730: "Counter-Strike 2",
    105600: "Terraria",
    252950: "Rocket League",
    413150: "Stardew Valley",
    553850: "Helldivers 2",
    949230: "Cities: Skylines II",
    1030300: "Hollow Knight: Silksong",
    1086940: "Baldur's Gate 3",
    1091500: "Cyberpunk 2077",
    1808500: "Arc Raiders",
    2246340: "Monster Hunter Wilds",
    2357570: "Overwatch",
    2878980: "NBA 2K25",
    3551340: "Football Manager 26",
}

# Fetch and cache reviews for every game
def fetch_all() -> None:
    for i, (appid, name) in enumerate(GAMES.items(), start=1):
        print(f"[{i}/{len(GAMES)}] {name} ({appid})")
        load_reviews(appid)

# Entry point
if __name__ == "__main__":
    fetch_all()
