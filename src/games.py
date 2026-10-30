from fetch import load_reviews

# Games for model training and testing
GAMES = {
    440: "Team Fortress 2",
    550: "Left 4 Dead 2",
    570: "Dota 2",
    730: "Counter-Strike 2",
    105600: "Terraria",
    230410: "Warframe",
    252490: "Rust",
    252950: "Rocket League",
    271590: "Grand Theft Auto V",
    275850: "No Man's Sky",
    289070: "Sid Meier's Civilization VI",
    359550: "Tom Clancy's Rainbow Six Siege",
    413150: "Stardew Valley",
    427520: "Factorio",
    440900: "Conan Exiles",
    489830: "The Elder Scrolls V: Skyrim Special Edition",
    548430: "Deep Rock Galactic",
    553850: "Helldivers 2",
    578080: "PUBG: BATTLEGROUNDS",
    892970: "Valheim",
    949230: "Cities: Skylines II",
    1030300: "Hollow Knight: Silksong",
    1055540: "A Short Hike",
    1085660: "Destiny 2",
    1086940: "Baldur's Gate 3",
    1091500: "Cyberpunk 2077",
    1145360: "Hades",
    1172470: "Apex Legends",
    1174180: "Red Dead Redemption 2",
    1245620: "Elden Ring",
    1293830: "Forza Horizon 4",
    1363080: "Manor Lords",
    1426210: "It Takes Two",
    1517290: "Battlefield 2042",
    1551360: "Forza Horizon 5",
    1599340: "Lost Ark",
    1623730: "Palworld",
    1716740: "Starfield",
    1808500: "Arc Raiders",
    1868140: "Dave the Diver",
    1966720: "Lethal Company",
    2246340: "Monster Hunter Wilds",
    2357570: "Overwatch",
    2358720: "Black Myth: Wukong",
    2379780: "Balatro",
    2483190: "Forza Horizon 6",
    2507950: "Delta Force",
    2567870: "Chained Together",
    2694490: "Path of Exile 2",
    2767030: "Marvel Rivals",
    2835570: "Buckshot Roulette",
    2878980: "NBA 2K25",
    2881650: "Content Warning",
    3159330: "Assassin's Creed Shadows",
    3164500: "Schedule I",
    3241660: "R.E.P.O.",
    3527290: "PEAK",
    3551340: "Football Manager 26",
    4080220: "EA SPORTS FC 27",
    4384550: "Call of Duty: Black Ops 6",
}

# Fetch and cache reviews for every game
def fetch_all() -> None:
    for i, (appid, name) in enumerate(GAMES.items(), start=1):
        print(f"[{i}/{len(GAMES)}] {name} ({appid})")
        load_reviews(appid)

# Entry point
if __name__ == "__main__":
    fetch_all()
