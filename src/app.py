import altair as alt
import base64
import html
from datetime import datetime
import pandas as pd
import re
import streamlit as st
from urllib.parse import urlencode
from export import EXPORT_DIR, INDEX_NAME, flagged_events, load_index, load_summary
from fetch import DATA_DIR, HELPFUL_REVIEWS, HISTORY_REVIEWS, RECENT_DAYS, RECENT_REVIEWS, cached_games
from model import MODEL_PATH
from pathlib import Path
from summarize import (SURGE_EXTRA_NEGATIVES, FLAG_LOOKBACK_MONTHS, SURGE_NEGATIVE_RATIO, SURGE_SCORE_DROP, DROP_MIN_REVIEWS, DROP_SCORE_POINTS,
                       build_summary, display_name, pct_positive)
from themes import FLIP_TO_COMPLAINT, FLIP_TO_PRAISE, PROBLEM_THEMES, THEMES

# Page setup, with a PNG of the logo mark as the favicon since Safari ignores SVG ones
ASSET_DIR = Path(__file__).resolve().parent / "assets"
st.set_page_config(page_title="SteamTLDR",page_icon=ASSET_DIR / "favicon.png", layout="wide", initial_sidebar_state=260)

# Chart colours and the score change worth calling out
PRAISE_COLOR = "#4c9be8"
COMPLAINT_COLOR = "#e05d5d"
MIXED_COLOR = "#c99a2e"
BIG_CHANGE_POINTS = 10
DANGER_CHANGE_POINTS = 20

# Project repository, linked from the home page
REPO_URL = "https://github.com/jntm7/steam-tldr"

# Larger sidebar page links and icons, lighter text, trimmed page bottom padding, and larger home buttons
SIDEBAR_CSS = """<style>
[data-testid="stSidebarHeader"] { height: auto; padding: 2.75rem 1rem 0.5rem; }
[data-testid="stSidebarHeader"] { position: relative; }
[data-testid="stSidebarHeader"] > div:first-child { height: auto !important; width: 100%; flex: 1; }
[data-testid="stSidebarCollapseButton"] { position: absolute; top: 0.5rem; right: 0.75rem; }
[data-testid="stSidebarHeader"] img { height: 3.4rem !important; width: auto !important; max-width: 100%; }
[data-testid="stSidebarNav"] ul { gap: 0.25rem; }
[data-testid="stSidebarNavLink"] { padding: 0.6rem 0.9rem; gap: 1.5rem; border-radius: 0.6rem; }
[data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] { font-size: 1.7rem; width: 1.7rem; height: 1.7rem; flex: none; opacity: 0.8; }
[data-testid="stSidebarNavLink"] p { font-size: 1.05rem; line-height: 1.6; font-weight: 400; margin: 0; }
[data-testid="stSidebarNavLink"][aria-current="page"] { background: color-mix(in srgb, #3d8fd1 18%, transparent); }
[data-testid="stSidebarNavLink"][aria-current="page"] p, [data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"] { color: #3d8fd1; opacity: 1; font-weight: 600; }
[data-testid="stSidebarContent"] { display: flex; flex-direction: column; }
[data-testid="stSidebarUserContent"], [data-testid="stSidebarUserContent"] > div { flex: 1; display: flex; flex-direction: column; }
[data-testid="stSidebarUserContent"] { padding-bottom: 1.25rem; }
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] { flex: 1; }
[data-testid="stLayoutWrapper"]:has(> .st-key-sidebar_footer) { order: 1; margin-top: auto; }
.theme-switch { display: flex; gap: 2px; padding: 3px; border-radius: 0.7rem; background: color-mix(in srgb, currentColor 9%, transparent); }
.theme-switch a, .theme-switch a:hover { flex: 1; display: flex; align-items: center; justify-content: center; gap: 0.25rem;
  padding: 0.4rem 0; border-radius: 0.5rem; font-size: 0.85rem; color: inherit; text-decoration: none; opacity: 0.65; }
.theme-switch a.on { opacity: 1; font-weight: 600; background: color-mix(in srgb, currentColor 16%, transparent); box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2); }
.theme-switch .material { font-family: 'Material Symbols Rounded'; font-weight: 400; font-size: 1.3rem; line-height: 1; font-feature-settings: 'liga'; }
[data-testid="stApp"] { animation: app-fade-in 0.4s ease backwards; }
html.theme-fading [data-testid="stApp"] { opacity: 0; transition: opacity 0.2s ease; }
@keyframes app-fade-in { from { opacity: 0; } to { opacity: 1; } }
[data-testid="stMainBlockContainer"] { padding-top: 3.5rem; padding-bottom: 3rem; }
.st-key-home_cta button { min-height: 3.25rem; padding: 0 1.75rem; font-size: 1.15rem; }
.st-key-home_cta button p { font-size: 1.15rem; }
.st-key-home_cta [data-testid="stIconMaterial"] { font-size: 1.5rem; width: 1.5rem; height: 1.5rem; }
.st-key-home_cta button > div > span { gap: 1rem; }
.st-key-home_cta [data-testid="stBaseButton-secondary"] { color: #3d8fd1; background: color-mix(in srgb, #66c0f4 16%, transparent); border-color: color-mix(in srgb, #66c0f4 55%, transparent); }
.st-key-home_cta [data-testid="stBaseButton-secondary"]:hover { background: color-mix(in srgb, #66c0f4 26%, transparent); border-color: #66c0f4; color: #3d8fd1; }
.repo-button, .repo-button:hover { display: flex; align-items: center; justify-content: center; gap: 0.6rem; flex: none; width: fit-content; height: 3.25rem; padding: 0 1.75rem; border-radius: 0.5rem;
  font-size: 1.15rem; text-decoration: none;
  border: 1px solid color-mix(in srgb, currentColor 20%, transparent); color: inherit; transition: border-color 0.15s, color 0.15s; }
.repo-button:hover { border-color: #3d8fd1; color: #3d8fd1; }
.sidebar-tools { display: flex; flex-direction: column; gap: 0.4rem; padding-top: 0.75rem; border-top: 1px solid color-mix(in srgb, currentColor 15%, transparent); }
.home-library { display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 1.25rem 1rem; }
@media (max-width: 1000px) { .home-library { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (max-width: 560px) { .home-library { grid-template-columns: repeat(3, minmax(0, 1fr)); } .home-library .game-card:nth-child(n+7) { display: none; } }
.home-library .game-name { font-size: 0.85rem; }
.home-library .game-score { font-size: 0.75rem; }
.home-library .game-reviews { font-size: 0.7rem; }
.st-key-library_sort [data-testid="stSelectbox"] { display: flex; align-items: stretch; }
.st-key-library_sort [data-testid="stSelectbox"]::before { content: "Sort by"; display: flex; align-items: center; flex: none; box-sizing: border-box; height: 40px; padding: 0 12px;
  font-size: 14px; border-radius: 8px 0 0 8px; background: color-mix(in srgb, currentColor 12%, transparent); opacity: 0.75; user-select: none; pointer-events: none; }
.st-key-library_sort [data-testid="stSelectbox"] > div:last-child { flex: 1; min-width: 0; }
.st-key-library_sort [role="group"] { border-top-left-radius: 0; border-bottom-left-radius: 0; }
.st-key-library_search [data-testid="stTextInputRootElement"], .st-key-library_paste [data-testid="stTextInputRootElement"] { padding-left: 0; }
.st-key-library_search [data-testid="stTextInputRootElement"] > div:first-child, .st-key-library_paste [data-testid="stTextInputRootElement"] > div:first-child {
  display: flex; align-items: center; justify-content: center; align-self: stretch; flex: none; width: 40px; height: auto; margin: -1px 0 -1px -1px;
  border-radius: 8px 0 0 8px; background: color-mix(in srgb, currentColor 12%, transparent); opacity: 0.75; pointer-events: none; }
.st-key-library_view [role="radiogroup"]::before { content: "View"; display: flex; align-items: center; flex: none; box-sizing: border-box; height: 40px; padding: 0 12px;
  margin-right: -1px; font-size: 14px; border: 1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius: 8px 0 0 8px;
  background: color-mix(in srgb, currentColor 12%, transparent); opacity: 0.75; user-select: none; pointer-events: none; }
.st-key-library_view [role="radiogroup"] button { height: 40px; min-height: 40px; }
.st-key-library_view [role="radiogroup"] button:first-child { border-top-left-radius: 0; border-bottom-left-radius: 0; }
</style>"""

# Styles that split a bordered panel's columns with dividers, which turn horizontal when columns stack on phones
PANEL_CSS = """<style>
.st-key-game_info, .st-key-game_stats { padding: 0 !important; }
.st-key-game_info [data-testid="stHorizontalBlock"], .st-key-game_stats [data-testid="stHorizontalBlock"] { gap: 0; align-items: stretch; }
.st-key-game_info [data-testid="stColumn"], .st-key-game_stats [data-testid="stColumn"] { padding: 1rem; }
@media (min-width: 641px) { .st-key-game_info [data-testid="stColumn"], .st-key-game_stats [data-testid="stColumn"] { min-width: 0; } }
.st-key-game_info [data-testid="stColumn"] + [data-testid="stColumn"],
.st-key-game_stats [data-testid="stColumn"] + [data-testid="stColumn"] { border-left: 1px solid rgba(128, 128, 128, 0.25); }
@media (max-width: 640px) {
  .st-key-game_info [data-testid="stColumn"] + [data-testid="stColumn"],
  .st-key-game_stats [data-testid="stColumn"] + [data-testid="stColumn"] { border-left: none; border-top: 1px solid rgba(128, 128, 128, 0.25); }
}
.cell-icon { font-family: "Material Symbols Rounded"; font-feature-settings: "liga"; font-size: 1.05rem; font-weight: 400; letter-spacing: normal;
  text-transform: none; vertical-align: -0.22em; margin-right: 0.4rem; }
.cell-label { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.07em; text-transform: uppercase; opacity: 0.6; margin-bottom: 0.35rem; }
.cell-value { display: flex; align-items: center; min-height: 2.5rem; font-size: 1.05rem; font-weight: 600; line-height: 1.3; }
.st-key-game_info [data-testid="stColumn"] > [data-testid="stVerticalBlock"], .st-key-game_stats [data-testid="stColumn"] > [data-testid="stVerticalBlock"] { gap: 0; }
.cell-stat { font-size: 1.75rem; font-weight: 600; line-height: 1.2; overflow-wrap: anywhere; }
.cell-stat.word { font-size: 1.2rem; line-height: 1.5; }
.cell-delta { margin-left: 0.5rem; font-size: 0.85rem; font-weight: 600; white-space: nowrap; }
.cell-stack { display: flex; flex-direction: column; gap: 0.7rem; }
.st-key-game_info [data-testid="stColumn"] .stElementContainer, .st-key-game_stats [data-testid="stColumn"] .stElementContainer { width: 100%; }
.st-key-back_to_library { align-items: flex-end; }
[data-testid="stMainBlockContainer"] hr { margin: 1.5rem 0; }
h1#game-title { font-size: 3.75rem; line-height: 4.5rem; padding: 0; }
@media (max-width: 640px) { h1#game-title { font-size: 2.25rem; line-height: 3rem; } }
</style>"""

# Width of the banner beside the game name, which makes it 72px tall to match the name's line height
THUMBNAIL_WIDTH = 154

# Font settings that turn an icon name into a Material Symbols icon, the set Streamlit already loads
MATERIAL_FONT = ('font-family: "Material Symbols Rounded"; font-weight: 400; font-style: normal; line-height: 1; '
                 'letter-spacing: normal; text-transform: none; white-space: nowrap; direction: ltr; '
                 'font-feature-settings: "liga"; -webkit-font-smoothing: antialiased; user-select: none;')

# Styles for the library grid
LIBRARY_CSS = """<style>
.library { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 1.5rem 1.25rem; }
.game-card, .game-card:hover { display: block; color: inherit; text-decoration: none; }
.game-cover { position: relative; aspect-ratio: 2 / 3; border-radius: 6px; overflow: hidden; background: #1b2838;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25); transition: transform 0.15s ease, box-shadow 0.15s ease; }
.game-card:hover .game-cover { transform: translateY(-4px); box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35); }
.game-cover img { display: block; width: 100%; height: 100%; object-fit: cover; }
.game-cover .backdrop { filter: blur(14px) brightness(0.55); transform: scale(1.3); }
.game-cover .front { position: absolute; inset: 0; height: auto; margin: auto; object-fit: contain; }
.game-cover.empty { display: flex; align-items: center; justify-content: center; padding: 1rem; color: #c7d5e0; font-weight: 600; text-align: center; }
.game-name { margin-top: 0.55rem; font-weight: 600; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.game-score { margin-top: 0.1rem; font-size: 0.82rem; }
.game-reviews { margin-top: 0.05rem; font-size: 0.78rem; opacity: 0.65; }
.library-list { display: flex; flex-direction: column; gap: 0.5rem; }
.game-row, .game-row:hover { display: flex; align-items: center; gap: 1rem; padding: 0.4rem 0.75rem 0.4rem 0.4rem;
  color: inherit; text-decoration: none; border: 1px solid rgba(128, 128, 128, 0.25); border-radius: 8px;
  transition: background 0.15s ease; }
.game-row:hover { background: rgba(128, 128, 128, 0.12); }
.game-row img, .row-empty { flex: none; width: 138px; aspect-ratio: 460 / 215; border-radius: 4px; object-fit: cover; background: #1b2838; }
.row-name { flex: 1; min-width: 0; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row-name small { display: block; font-weight: 400; opacity: 0.65; overflow: hidden; text-overflow: ellipsis; }
.row-reviews { flex: none; width: 8rem; text-align: right; font-size: 0.85rem; opacity: 0.7; }
.row-score { flex: none; width: 15rem; text-align: right; font-size: 0.9rem; }
@media (max-width: 640px) { .row-reviews { display: none; } .row-score { width: auto; } .game-row img, .row-empty { width: 96px; } }
</style>"""

# Styles for the event rows, which reuse the library list rows
EVENT_CSS = """<style>
.event-list .row-extra { flex: none; width: 12rem; text-align: right; font-size: 0.85rem; opacity: 0.75; }
.event-list .row-score { width: 9rem; }
.row-drop { flex: none; width: 5rem; text-align: right; font-weight: 600; }
@media (max-width: 1100px) { .event-list img, .event-list .row-empty, .event-list .row-score { display: none; } }
@media (max-width: 640px) { .event-list .row-extra { display: none; } .row-drop { width: auto; } }
.st-key-event_sort [role="radiogroup"]::before { content: "Sort by"; display: flex; align-items: center; box-sizing: border-box; height: 32px; padding: 0 16px;
  margin-right: -1px; font-size: 14px; border: 1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius: 8px 0 0 8px;
  background: color-mix(in srgb, currentColor 6%, transparent); opacity: 0.75; user-select: none; pointer-events: none; }
.st-key-event_sort [role="radiogroup"] button:first-child { border-top-left-radius: 0; border-bottom-left-radius: 0; }
</style>"""

# Colour for each kind of flagged event
EVENT_KIND_COLORS = {"Negative surge": COMPLAINT_COLOR, "Score drop": MIXED_COLOR}

# Kind filter options as option -> kind, and sort orders as option -> column, biggest first
EVENT_KINDS = {"All": None, "Negative surges": "Negative surge", "Score drops": "Score drop"}
EVENT_SORTS = {"Most extra negatives": "extra_negatives", "Biggest drop": "drop_points", "Most recent": "start"}

# Library layouts as option -> icon label
LIBRARY_VIEWS = {"Cards": ":material/grid_view:", "List": ":material/view_list:"}

# Library sort orders as (key, highest first), applied after sorting by name
LIBRARY_SORTS = {
    "Name (A \u2192 Z)": (lambda meta: game_name(meta).lower(), False),
    "Name (Z \u2192 A)": (lambda meta: game_name(meta).lower(), True),
    "Rating (High \u2192 Low)": (lambda meta: game_score(meta), True),
    "Rating (Low \u2192 High)": (lambda meta: game_score(meta), False),
    "Reviews (High \u2192 Low)": (lambda meta: meta.get("summary", {}).get("total_reviews", 0), True),
    "Reviews (Low \u2192 High)": (lambda meta: meta.get("summary", {}).get("total_reviews", 0), False),
}

# Material icon for each theme
THEME_ICONS = {
    "performance": "speed",
    "bugs & crashes": "bug_report",
    "price & monetization": "sell",
    "servers & matchmaking": "dns",
    "cheaters": "gpp_bad",
    "community": "groups",
    "co-op & multiplayer": "sports_esports",
    "story & characters": "menu_book",
    "gameplay & combat": "swords",
    "graphics & art": "palette",
    "music & sound": "music_note",
    "content & grind": "stacks",
    "difficulty": "skull",
    "developers & updates": "build",
    "accounts & launchers": "key",
}

# Styles for the theme rows
THEME_CSS = f"""<style>
.theme-row {{ margin-bottom: 1.1rem; }}
.theme-head {{ display: flex; align-items: center; gap: 0.5rem; font-weight: 600; }}
.theme-icon {{ {MATERIAL_FONT} font-size: 20px; color: var(--accent); }}
.theme-pct {{ margin-left: auto; font-variant-numeric: tabular-nums; }}
.theme-track {{ height: 8px; border-radius: 4px; background: rgba(128, 128, 128, 0.18); margin: 0.35rem 0; }}
.theme-bar {{ height: 100%; border-radius: 4px; background: var(--accent); }}
.theme-quote {{ font-style: italic; opacity: 0.75; font-size: 0.92rem; }}
</style>"""

# Filter choices for the random review
REVIEW_KINDS = ["Any", ":material/thumb_up: Positive", ":material/thumb_down: Negative"]

# Material icon and colour for each section heading, keyed by the heading's anchor
SECTION_ICONS = {
    "overview": ("dashboard", PRAISE_COLOR),
    "the-good": ("thumb_up", PRAISE_COLOR),
    "the-bad": ("thumb_down", COMPLAINT_COLOR),
    "recent-complaints": ("schedule", COMPLAINT_COLOR),
    "opinions-over-time": ("show_chart", PRAISE_COLOR),
    "playtime": ("hourglass", PRAISE_COLOR),
    "review-randomizer": ("casino", PRAISE_COLOR),
    "event-list": ("warning", COMPLAINT_COLOR),
    "why-steamtldr": ("lightbulb", PRAISE_COLOR),
    "data-sources": ("database", PRAISE_COLOR),
    "finding-themes": ("category", PRAISE_COLOR),
    "judging-tone": ("psychology", PRAISE_COLOR),
    "flagged-events": ("warning", COMPLAINT_COLOR),
    "known-limits": ("report", COMPLAINT_COLOR),
    "when-they-happened": ("scatter_plot", COMPLAINT_COLOR),
    "look-closer": ("zoom_in", PRAISE_COLOR),
    "how-its-detected": ("rule", PRAISE_COLOR),
}

# Styles for the sidebar outline: a small label, then one row per section with its heading's icon
OUTLINE_CSS = f"""<style>
.outline-title {{ margin: 0 0 0.4rem 0.6rem; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.6; }}
.outline a {{ display: flex; align-items: center; gap: 0.6rem; padding: 0.35rem 0.6rem; border-radius: 0.5rem;
  color: inherit; font-size: 0.9rem; text-decoration: none; transition: background 0.15s ease; }}
.outline a:hover {{ background: rgba(128, 128, 128, 0.15); text-decoration: none; }}
.outline-icon {{ {MATERIAL_FONT} font-size: 18px; flex: none; }}
.outline-label {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.outline-empty {{ margin: 0 0.6rem; font-size: 0.85rem; opacity: 0.6; }}
</style>"""

# Browser cookie that remembers the last games opened, as app IDs joined by dashes
RECENT_COOKIE = "steamtldr_recent"
MAX_RECENT = 8

# The sidebar outline, with the same icon and colour as each section's heading
def outline_html(sections: dict, header: str | None = None) -> str:
    rows = "".join(f'<a href="#{anchor}"><span class="outline-icon" style="color: {color}">{icon}</span>{label}</a>'
                   for label, anchor in sections.items() if anchor
                   for icon, color in [SECTION_ICONS.get(anchor, ("dashboard", PRAISE_COLOR))])
    return f'{OUTLINE_CSS}{header or '<div class="outline-title">On this page</div>'}<nav class="outline">{rows}</nav>'

# Small banner and name of the open game, shown in place of the outline's label
def sidebar_game(summary: dict) -> str:
    banner = f'<img src="{html.escape(summary["header_image"])}" alt="">' if summary.get("header_image") else ""
    return (f'<style>.sidebar-game {{ display: flex; align-items: center; gap: 0.6rem; margin: 0 0.6rem 0.6rem; }} '
            f'.sidebar-game img {{ width: 64px; flex: none; border-radius: 0.3rem; }} '
            f'.sidebar-game div {{ min-width: 0; font-size: 0.9rem; font-weight: 600; line-height: 1.3; }}</style>'
            f'<div class="sidebar-game">{banner}<div>{html.escape(summary["name"])}</div></div>')

# Browser tab title for the current page
def tab_title(page: str | None = None) -> None:
    st.set_page_config(page_title=f"SteamTLDR - {page}" if page else "SteamTLDR")

# A sidebar list of links in the outline's style, each as (Material icon, label, address)
def sidebar_links(title: str, rows: list[tuple[str, str, str]], empty: str) -> str:
    body = "".join(f'<a href="{html.escape(href)}"><span class="outline-icon" style="color: {PRAISE_COLOR}">{icon}</span>'
                   f'<span class="outline-label">{html.escape(label)}</span></a>' for icon, label, href in rows)
    return f'{OUTLINE_CSS}<div class="outline-title">{title}</div>' + (f'<nav class="outline">{body}</nav>' if rows else f'<div class="outline-empty">{empty}</div>')

# App IDs of the games opened most recently, newest first, read from the browser cookie once per session
def recent_games() -> list[int]:
    if "recent" not in st.session_state:
        saved = st.context.cookies.get(RECENT_COOKIE, "")
        st.session_state["recent"] = [int(part) for part in saved.split("-") if part.isdigit()][:MAX_RECENT]
    return st.session_state["recent"]

# Move a game to the front of the recent list and save the list in the browser cookie
def record_view(appid: int) -> None:
    recent = ([appid] + [other for other in recent_games() if other != appid])[:MAX_RECENT]
    st.session_state["recent"] = recent
    st.html(f'<script>document.cookie = "{RECENT_COOKIE}={"-".join(map(str, recent))}; path=/; max-age=31536000; SameSite=Lax";</script>',
            unsafe_allow_javascript=True)

# Theme choices as (Material icon, label, Streamlit's embed option that forces it)
APPEARANCES = {
    "light": ("light_mode", "Light", "light_theme"),
    "dark": ("dark_mode", "Dark", "dark_theme"),
    "system": ("computer", "System", None),
}

# The chosen theme, remembered for the session once picked from the sidebar
def current_appearance() -> str:
    choice = st.query_params.get("appearance")
    if choice in APPEARANCES:
        st.session_state["appearance"] = choice
    return st.session_state.get("appearance", "system")

# Address parameters that keep the chosen theme: Streamlit reads embed_options, appearance mirrors it for this app
def appearance_params(choice: str | None = None) -> dict:
    choice = choice or st.session_state.get("appearance", "system")
    embed = APPEARANCES[choice][2]
    return {"appearance": choice, "embed_options": embed} if embed else {}

# Segmented light/dark/system switch made of links, since Streamlit has no way to change its theme from Python
def theme_switch() -> str:
    current = current_appearance()
    base = {key: value for key, value in st.query_params.items() if key not in ("appearance", "embed_options")}
    segments = "".join(
        f'<a class="{"on" if key == current else ""}" href="?{urlencode({**base, **appearance_params(key)})}" '
        f'title="{label} theme" aria-label="{label} theme"><span class="material">{icon}</span></a>'
        for key, (icon, label, _) in APPEARANCES.items())
    return f'<div class="sidebar-tools"><div class="theme-switch" role="group" aria-label="Theme">{segments}</div></div>'

# Link to a game's page that keeps the chosen theme
def page_href(appid: int) -> str:
    return "/game?" + urlencode({"app": appid, **appearance_params()})

# Cover art: the portrait library image, else the banner on a blurred backdrop
def game_cover(meta: dict, name: str) -> str:
    if meta.get("library_image"):
        return f'<div class="game-cover"><img src="{html.escape(meta["library_image"])}" alt="{name}" loading="lazy"></div>'
    if meta.get("header_image"):
        src = html.escape(meta["header_image"])
        return f'<div class="game-cover"><img class="backdrop" src="{src}" alt=""><img class="front" src="{src}" alt="{name}"></div>'
    return f'<div class="game-cover empty">{name}</div>'

# A cached game's name without trademark symbols
def game_name(meta: dict) -> str:
    return display_name(meta, meta["appid"])

# Steam's percent positive for a cached game, or None with no reviews
def steam_pct(meta: dict) -> float | None:
    steam = meta.get("summary", {})
    return pct_positive(steam.get("total_positive", 0), steam.get("total_negative", 0))

# Percent positive for sorting, with games without reviews last
def game_score(meta: dict) -> float:
    pct = steam_pct(meta)
    return -1 if pct is None else pct

# Steam's colour bands: positive from 70%, mixed from 40%, negative below
def score_color(pct: float) -> str:
    return PRAISE_COLOR if pct >= 70 else MIXED_COLOR if pct >= 40 else COMPLAINT_COLOR

# One library card with cover art, name and Steam score
def game_card(meta: dict) -> str:
    name = html.escape(game_name(meta))
    steam = meta.get("summary", {})
    pct = steam_pct(meta)
    if pct is None:
        score = '<div class="game-score">No reviews yet</div>'
    else:
        score = f'<div class="game-score" style="color: {score_color(pct)}">{pct:.0f}% · {html.escape(steam.get("review_score_desc", ""))}</div>'
    reviews = f'<div class="game-reviews">{steam.get("total_reviews", 0):,} reviews</div>' if pct is not None else ""
    return (f'<a class="game-card" href="{page_href(meta["appid"])}">'
            f'{game_cover(meta, name)}<div class="game-name">{name}</div>{score}{reviews}</a>')

# One list row with a small banner, name, studio, review count and Steam score
def game_row(meta: dict) -> str:
    name = html.escape(game_name(meta))
    steam = meta.get("summary", {})
    pct = steam_pct(meta)
    banner = (f'<img src="{html.escape(meta["header_image"])}" alt="" loading="lazy">' if meta.get("header_image")
              else '<div class="row-empty"></div>')
    studio = html.escape(", ".join(meta.get("developers") or []))
    if pct is None:
        score = '<span class="row-score">No reviews yet</span>'
    else:
        score = (f'<span class="row-score" style="color: {score_color(pct)}">{pct:.0f}% · '
                 f'{html.escape(steam.get("review_score_desc", ""))}</span>')
    reviews = f'{steam.get("total_reviews", 0):,} reviews'
    return (f'<a class="game-row" href="{page_href(meta["appid"])}">{banner}'
            f'<span class="row-name">{name}<small>{studio}</small></span>'
            f'<span class="row-reviews">{reviews}</span>{score}</a>')

# Landing page: search the cached games, paste a link, or pick a game
def library_page() -> None:
    tab_title("Games")
    names = {meta["appid"]: game_name(meta) for meta in library_games()}
    recent = [("history", names[appid], page_href(appid)) for appid in recent_games() if appid in names]
    with st.sidebar:
        st.html(sidebar_links("Recently viewed", recent, "Games you open will show up here."))
    st.title("Games", anchor=False)
    with st.container(key="library_toolbar", border=True):
        search_col, paste_col, sort_col, view_col = st.columns([3.2, 3, 3.3, 2.5], vertical_alignment="center")
        search = search_col.text_input("Search games", type="search", live=True, placeholder="Search by name",
                                       label_visibility="collapsed", key="library_search")
        sort = sort_col.selectbox("Sort by", options=list(LIBRARY_SORTS), label_visibility="collapsed", key="library_sort")
        paste_col.text_input("Add or open any Steam game", icon=":material/link:", disabled=True,
                                      placeholder="Paste a link (coming soon)", label_visibility="collapsed", key="library_paste")
        view = view_col.segmented_control("View", options=list(LIBRARY_VIEWS), default="Cards",
                                          format_func=LIBRARY_VIEWS.get, width="stretch", label_visibility="collapsed",
                                          key="library_view") or "Cards"

    games = sorted(library_games(), key=lambda meta: game_name(meta).lower())
    key, highest_first = LIBRARY_SORTS[sort]
    games.sort(key=key, reverse=highest_first)
    shown = [meta for meta in games if search.strip().lower() in game_name(meta).lower()]
    if not games:
        st.info("No games analyzed yet.")
    elif not shown:
        st.caption(f"No games match \u201c{search}\u201d.")
    else:
        st.caption(f"{len(shown)} of {len(games)} games")
        if view == "List":
            st.html(LIBRARY_CSS + '<div class="library-list">' + "".join(game_row(meta) for meta in shown) + "</div>")
        else:
            st.html(LIBRARY_CSS + '<div class="library">' + "".join(game_card(meta) for meta in shown) + "</div>")

# Steam's and our own date strings as "Aug 12, 2012", or unchanged when there's no full date such as "Coming soon"
def format_date(text: str | None) -> str:
    for pattern in ("%d %b, %Y", "%b %d, %Y", "%d %B, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            date = datetime.strptime(text or "", pattern)
        except ValueError:
            continue
        return f"{date:%b} {date.day}, {date.year}"
    return text or "Unknown"

# A small uppercase label above a bold value
def labelled(label: str, value: str) -> str:
    return f'<div><div class="cell-label">{label}</div><div class="cell-value">{html.escape(value)}</div></div>'

# A label above a big number, with an optional colour and a change badge beside it
def stat_cell(label: str, value: str, icon: str | None = None, color: str | None = None, delta: str | None = None, tip: str = "") -> str:
    style = f' style="color: {color}"' if color else ""
    size = " word" if not value[0].isdigit() and value != "n/a" else ""
    badge = ""
    if delta is not None:
        points = float(delta)
        arrow, shade = ("\u25b2", PRAISE_COLOR) if points >= 0 else ("\u25bc", COMPLAINT_COLOR)
        badge = f'<span class="cell-delta" style="color: {shade}">{arrow} {abs(points):.0f} pts</span>'
    mark = f'<span class="cell-icon">{icon}</span>' if icon else ""
    return (f'<div title="{html.escape(tip)}"><div class="cell-label">{mark}{label}</div>'
            f'<div class="cell-stat{size}"{style}>{html.escape(value)}{badge}</div></div>')

# Address value for the FAQ page
ABOUT_PAGE = "faq"

# About: what the app does, where its numbers come from, and where it can be wrong
def about_page() -> None:
    tab_title("FAQ")
    st.title("FAQ", anchor=False)
    st.caption("SteamTLDR is a personal project and isn't affiliated with Valve or Steam. "
               "Game names, images and reviews belong to their respective owners.")

    sections = {"Why SteamTLDR?": "why-steamtldr", "Data sources": "data-sources", "Finding themes": "finding-themes",
                "Judging tone": "judging-tone", "Flagged events": "flagged-events", "Known limits": "known-limits"}
    with st.sidebar:
        st.html(outline_html(sections))
    st.html(section_icon_css())

    st.divider()
    st.subheader("Why SteamTLDR?", anchor="why-steamtldr")
    st.markdown("Steam gives you one score, so finding out why players love or hate a game means reading dozens of reviews or watching a video, "
                "and a single number hides what they praise, what they complain about, and whether opinion is changing. "
                "SteamTLDR reads thousands of reviews per game and sums up the *why*: top themes, recent trends, and how new players compare with veterans.")

    st.divider()
    st.subheader("Data sources", anchor="data-sources")
    st.markdown(f"""
- Reviews come from Steam's public review API, English only.
- Scores, monthly trends and the playtime split are **Steam's exact totals**, not estimates.
- The text sample per game: the {HELPFUL_REVIEWS:,} most helpful reviews, {RECENT_REVIEWS:,} from the last {RECENT_DAYS} days, and up to {HISTORY_REVIEWS:,} spread across earlier months.
- Each game is a snapshot, and its page shows when it was last updated.
""")

    st.divider()
    st.subheader("Finding themes", anchor="finding-themes")
    st.markdown(f"""
- Reviews are split into clauses at punctuation and turning-point words like *but* and *however*, so
  "great story but constant crashes" is praise for the story and a complaint about crashes.
- Each clause is matched against {len(THEMES)} themes, each a hand-picked keyword list.
- A clause takes its review's thumbs up or down, unless the sentiment model is confident it's the opposite
  (below {FLIP_TO_COMPLAINT:.0%} positive in a thumbs-up review, above {FLIP_TO_PRAISE:.0%} in a thumbs-down one).
- {" and ".join(sorted(PROBLEM_THEMES)).capitalize()} always count as complaints.
- Results are re-weighted to match the game's real score, so "23%" means about 23% of all its reviews.
""")
    cards = "".join(f'<div class="theme-row"><div class="theme-head"><span class="theme-icon">{THEME_ICONS.get(theme, "circle")}</span>'
                    f'{html.escape(theme.capitalize())}</div><div class="theme-quote">{html.escape(", ".join(words[:4]))}…</div></div>'
                    for theme, words in THEMES.items())
    st.html(f'{THEME_CSS}<div style="--accent: {PRAISE_COLOR}; margin-top: 1.5rem; display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 0 1.5rem">{cards}</div>')

    st.divider()
    st.subheader("Judging tone", anchor="judging-tone")
    st.markdown("""
- A TF-IDF and logistic regression model, trained on about 250,000 reviews from 57 games with each review's thumbs up or down as its label.
- Tested on three games it never saw (Helldivers 2, Cities: Skylines II, Hollow Knight: Silksong), it was right about 91% of the time.
""")

    st.divider()
    st.subheader("Flagged events", anchor="flagged-events")
    st.markdown(f"""
- "Usual" is the median of the previous {FLAG_LOOKBACK_MONTHS} months.
- **Negative surge** (a review bomb): negative reviews at least {SURGE_NEGATIVE_RATIO:g}\u00d7 usual and {SURGE_EXTRA_NEGATIVES} more, with the score at least {SURGE_SCORE_DROP} points below usual.
- **Score drop**: {DROP_MIN_REVIEWS:,}+ reviews and the score at least {DROP_SCORE_POINTS} points below usual, without that surge.
""")

    st.divider()
    st.subheader("Known limits", anchor="known-limits")
    st.markdown("""
- Keywords can't read context: Helldivers 2's enemy "bugs" count as bug complaints, and Stardew Valley's "money" is in-game gold.
- Sarcasm and negation ("not bad at all") can fool the model.
- The text sample leans toward helpful reviews, so scores come from Steam's totals.
- A flag shows something happened, not why, or whether it was fair.
""")

# Pull an app ID out of a number or a store link
def parse_appid(text: str) -> int | None:
    match = re.search(r"app/(\d+)", text) or re.fullmatch(r"\s*(\d+)\s*", text)
    return int(match.group(1)) if match else None

# A game's exported summary, else built from its cached reviews, reused for an hour
@st.cache_data(ttl=3600, show_spinner=False)
def cached_summary(appid: int) -> dict | None:
    return load_summary(appid) or build_summary(appid)

# Library entries from the exported index, else from the cached review data
def library_games() -> list[dict]:
    return load_index() if (EXPORT_DIR / INDEX_NAME).exists() else cached_games()

# One theme as an icon, name, percent bar and example quote
def theme_row(row, scale: float) -> str:
    icon = THEME_ICONS.get(row.theme, "circle")
    quote = f'<div class="theme-quote">“{html.escape(row.example)}”</div>' if row.example else ""
    return (f'<div class="theme-row">'
            f'<div class="theme-head"><span class="theme-icon">{icon}</span>{html.escape(row.theme.capitalize())}'
            f'<span class="theme-pct">{row.pct:.0f}%</span></div>'
            f'<div class="theme-track"><div class="theme-bar" style="width: {100 * row.pct / scale:.0f}%"></div></div>'
            f'{quote}</div>')

# Theme rows in one colour, with bars scaled to the biggest theme
def show_themes(rows: pd.DataFrame | None, color: str) -> None:
    if rows is None or rows.empty:
        st.caption("Nothing stands out.")
        return
    scale = max(rows["pct"].max(), 1)
    body = "".join(theme_row(row, scale) for row in rows.itertuples())
    st.html(f'{THEME_CSS}<div style="--accent: {color}">{body}</div>')

# Time axis with ticks only on month boundaries, spaced so a month label never repeats on wide screens
def month_axis(months: int) -> alt.Axis:
    step = 1 if months <= 13 else 3 if months <= 36 else 6 if months <= 72 else 12
    return alt.Axis(format="%Y" if step == 12 else "%b %Y", labelAngle=0, tickCount={"interval": "month", "step": step})

# Monthly percent positive with flagged months marked, and monthly review counts
def trend_charts(trend: pd.DataFrame, flagged: pd.DataFrame, overall: float) -> tuple[alt.LayerChart, alt.Chart]:
    data = trend.dropna(subset=["pct_positive"]).assign(start=lambda t: t["start"].dt.tz_localize(None))
    marked = flagged.assign(start=lambda f: f["start"].dt.tz_localize(None))
    tooltip = [
        alt.Tooltip("label:N", title="Month"),
        alt.Tooltip("pct_positive:Q", title="% positive", format=".0f"),
        alt.Tooltip("reviews:Q", title="Reviews", format=","),
    ]
    x = alt.X("start:T", title=None, axis=month_axis(len(data)))
    line = alt.Chart(data).mark_line(point=True).encode(x=x, y=alt.Y("pct_positive:Q", title="% positive", scale=alt.Scale(domain=[0, 100])), tooltip=tooltip)
    average = alt.Chart(pd.DataFrame({"overall": [overall]})).mark_rule(strokeDash=[4, 4], color="gray").encode(y="overall:Q")
    spikes = alt.Chart(marked).mark_circle(size=140, color=COMPLAINT_COLOR).encode(x=x, y="pct_positive:Q", tooltip=tooltip)
    volume = alt.Chart(data).mark_bar(opacity=0.7).encode(x=x, y=alt.Y("reviews:Q", title="Reviews"), tooltip=tooltip)
    return (line + average + spikes).properties(height=280), volume.properties(height=130)

# Bar chart of percent positive by playtime group
def playtime_chart(playtime: pd.DataFrame) -> alt.LayerChart:
    base = alt.Chart(playtime).encode(
        x=alt.X("group:N", sort=list(playtime["group"]), title="Playtime at time of review", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("pct_positive:Q", title="% positive", scale=alt.Scale(domain=[0, 100])),
        tooltip=[alt.Tooltip("group:N", title="Playtime"), alt.Tooltip("pct_positive:Q", title="% positive", format=".0f"),
                 alt.Tooltip("reviews:Q", title="Reviews", format=",")],
    )
    bars = base.mark_bar(color=PRAISE_COLOR, cornerRadiusEnd=3)
    labels = base.mark_text(dy=-10, color=PRAISE_COLOR, fontSize=14, fontWeight="bold").encode(text=alt.Text("pct_positive:Q", format=".0f"))
    return (bars + labels).properties(height=260)

# CSS that puts each section's Material icon before its heading
def section_icon_css() -> str:
    selectors = ", ".join(f"h3#{anchor}::before" for anchor in SECTION_ICONS)
    rules = "".join(f'h3#{anchor}::before {{ content: "{icon}"; color: {color}; }}' for anchor, (icon, color) in SECTION_ICONS.items())
    return f"<style>{selectors} {{ {MATERIAL_FONT} display: inline-block; margin-right: 0.35em; vertical-align: -0.12em; }}{rules}</style>"

# A review card with its verdict, playtime and date
def show_review(row: pd.Series) -> None:
    icon, color, verdict = ("thumb_up", PRAISE_COLOR, "Recommended") if row["voted_up"] else ("thumb_down", COMPLAINT_COLOR, "Not recommended")
    hours = row["playtime_at_review_h"]
    played = f"{hours:.1f}" if hours < 10 else f"{hours:,.0f}"
    with st.container(border=True):
        st.html(f'<div style="display: flex; align-items: center; gap: 0.4rem">'
                f'<span style=\'{MATERIAL_FONT} font-size: 18px; color: {color}\'>{icon}</span>'
                f'<span><b>{verdict}</b> · {played} h played · {row["created"]:%B %Y}</span></div>')
        st.html(f'<div style="white-space: pre-wrap; line-height: 1.6">{html.escape(row["review"])}</div>')

# One random sampled review, kept until the reader asks for another
@st.fragment
def random_review(reviews: pd.DataFrame, appid: int) -> None:
    kind_col, button_col = st.columns([3, 1], vertical_alignment="center")
    kind = kind_col.segmented_control("Kind of review", options=REVIEW_KINDS, default="Any", label_visibility="collapsed")
    another = button_col.button("Another one", icon=":material/casino:", width="stretch")
    pool = reviews if kind in (None, "Any") else reviews[reviews["voted_up"] == (kind == REVIEW_KINDS[1])]
    if pool.empty:
        st.caption("No reviews of this kind in the sample.")
        return
    key = f"random_review_{appid}"
    if another or st.session_state.get(key) not in pool.index:
        st.session_state[key] = pool.sample(1).index[0]
    show_review(pool.loc[st.session_state[key]])

# A game's page: header panels, themes, charts and a random review
def game_page(appid: int) -> None:
    # Stop early when there is neither an exported summary nor a model to build one
    exported = (EXPORT_DIR / f"{appid}.json").exists()
    if not exported and not MODEL_PATH.exists():
        st.info(f"App {appid} isn't in the library yet. Pick one of the games we've analyzed.", icon=":material/search_off:")
        if st.button("All games", icon=":material/arrow_back:"):
            st.switch_page(games_nav)
        return

    # Load the summary, fetching from Steam on a first visit
    is_cached = exported or (DATA_DIR / f"{appid}.parquet").exists()
    with st.spinner("Reading reviews..." if is_cached else "First look at this game: fetching reviews from Steam. This takes a few minutes..."):
        summary = cached_summary(appid)
    if summary is None:
        st.error(f"No English reviews found for app {appid}. Check the ID on the game's store page.")
        return
    record_view(appid)
    tab_title(summary["name"])

    # Header: the game's banner beside its name, both the same height
    st.html(PANEL_CSS)
    with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
        if summary.get("header_image"):
            st.image(summary["header_image"], width=THUMBNAIL_WIDTH)
        st.title(summary["name"], anchor="game-title")
        with st.container(key="back_to_library"):
            if st.button("All games", icon=":material/arrow_back:"):
                st.switch_page(games_nav)

    st.divider()
    st.subheader("Overview", anchor="overview")
    st.caption("Who made it, when it came out, and how players rate it overall and right now")

    # Who made it, when it came out, its genres and the store page, as one panel split by dividers
    developers = ", ".join(summary.get("developers") or []) or "Unknown"
    publishers = ", ".join(summary.get("publishers") or []) or "Unknown"
    credits = [("Developer & publisher", developers)] if developers == publishers else [("Developer", developers), ("Publisher", publishers)]
    with st.container(border=True, key="game_info"):
        columns = st.columns(len(credits) + 3)
        for column, (label, value) in zip(columns, credits):
            column.html(labelled(label, value))
        released_col, genres_col, store_col = columns[-3:]
        released_col.html(labelled("Released", format_date(summary.get("release_date"))))
        genres_col.html(labelled("Genres", " \u00b7 ".join(summary.get("genres") or []) or "Unknown"))
        store_col.html('<div class="cell-label">Steam store page</div>')
        store_col.link_button("Open", f"https://store.steampowered.com/app/{appid}/", icon=":material/open_in_new:",
                              icon_position="right", width="stretch")

    # Headline numbers, as one panel split by dividers
    recent = summary["recent"]
    change = recent["pct_positive"] - summary["pct_positive"] if recent["reviews"] else None
    with st.container(border=True, key="game_stats"):
        all_time, rating, last_days, volume, updated_col = st.columns(5)
        all_time.html(stat_cell("All-time positive", f"{summary['pct_positive']:.0f}%", icon="thumb_up"))
        rating.html(stat_cell("Steam rating", summary["score_desc"], icon="star", color=score_color(summary["pct_positive"])))
        last_days.html(stat_cell(f"Last {RECENT_DAYS} days", f"{recent['pct_positive']:.0f}%" if change is not None else "n/a",
                                 icon="trending_up", delta=f"{change:.2f}" if change is not None else None,
                                 tip=f"Percent positive over the last {RECENT_DAYS} days. The badge compares it with the all-time score."))
        volume.html(stat_cell("English reviews", f"{summary['total_reviews']:,}", icon="forum"))
        updated_col.html(stat_cell("Last updated", format_date(summary["fetched_at"]), icon="update"))

    if change is not None and change <= -DANGER_CHANGE_POINTS:
        st.error(f"Recent reviews are far more negative than usual ({change:+.0f} points). Check what players are complaining about lately below.",
                 icon=":material/dangerous:")
    elif change is not None and change <= -BIG_CHANGE_POINTS:
        st.warning(f"Recent reviews are much more negative than usual ({change:+.0f} points). Check what players are complaining about lately below.",
                   icon=":material/warning:")
    elif change is not None and change >= BIG_CHANGE_POINTS:
        st.success(f"Recent reviews are much more positive than usual ({change:+.0f} points). The game may have improved.",
                   icon=":material/check_circle:")

    # Sidebar outline linking to each section
    has_recent = summary["recent_complaints"] is not None and not summary["recent_complaints"].empty
    sections = {
        "Overview": "overview",
        "The Good": "the-good",
        "The Bad": "the-bad",
        "Recent complaints": "recent-complaints" if has_recent else None,
        "Opinions over time": "opinions-over-time",
        "Playtime": "playtime",
        "Review Randomizer": "review-randomizer",
    }
    with st.sidebar:
        st.html(outline_html(sections, sidebar_game(summary)))

    # What players like and dislike, with Material icons on every section heading
    st.html(section_icon_css())
    st.divider()
    praise_col, _, complaint_col = st.columns([10, 1.5, 10], gap="medium")
    with praise_col:
        st.subheader("The Good", anchor="the-good")
        st.caption("The most praised themes, as a share of all this game's reviews")
        show_themes(summary["praise"], PRAISE_COLOR)
    with complaint_col:
        st.subheader("The Bad", anchor="the-bad")
        st.caption("The most common complaints, as a share of all this game's reviews")
        show_themes(summary["complaints"], COMPLAINT_COLOR)

    if has_recent:
        window = f"{recent['start']:%b %-d} to {pd.Timestamp(summary['fetched_at']):%b %-d}"
        st.divider()
        st.subheader("Recent complaints", anchor="recent-complaints")
        st.caption(f"Top complaints in reviews from the last {RECENT_DAYS} days ({window}), to spot new problems or recent fixes")
        show_themes(summary["recent_complaints"], COMPLAINT_COLOR)

    # Sentiment over time
    st.divider()
    st.subheader("Opinions over time", anchor="opinions-over-time")
    st.caption("Percent positive each month, with the number of reviews below. The dashed line is the all-time score, "
               f"and the last point covers the last {RECENT_DAYS} days.")
    span = st.segmented_control("Range", options=["All time", "Last 2 years", "Last 12 months"], default="All time", label_visibility="collapsed")
    months = {"All time": None, "Last 2 years": 25, "Last 12 months": 13}[span or "All time"]
    trend = summary["trend"] if months is None else summary["trend"].tail(months)
    flagged = summary["events"][summary["events"]["start"] >= trend["start"].min()]
    sentiment, volume_chart = trend_charts(trend, flagged, summary["pct_positive"])
    st.altair_chart(sentiment, width="stretch")
    st.altair_chart(volume_chart, width="stretch")

    if not summary["events"].empty:
        lines = [f"- **{row.label}** ({row.kind.lower()}): {row.reviews:,} reviews, {row.pct_positive:.0f}% positive vs a usual {row.usual_pct:.0f}%"
                 + (f", {row.extra_negatives:,.0f} more negative reviews than usual" if row.kind == "Negative surge" else "")
                 for row in summary["events"].itertuples()]
        st.warning("**Flagged events** (red dots): months with a surge of negative reviews or a sharp drop in score.\n\n" + "\n".join(lines))

    # Playtime split
    st.divider()
    st.subheader("Playtime", anchor="playtime")
    st.caption("Percent positive by how many hours reviewers had played when they wrote their review")
    if summary["playtime"].empty:
        st.caption("No playtime data for this game yet.")
    else:
        st.altair_chart(playtime_chart(summary["playtime"].dropna()), width="stretch")
        st.caption("A low score under 2 hours often means a rough first impression, a bad launch, or performance problems.")

    # A random review to read in full
    st.divider()
    st.subheader("Review Randomizer", anchor="review-randomizer")
    st.caption("A random review from this game's sample, which leans toward reviews other players found helpful")
    if summary.get("shown_reviews") is None or summary["shown_reviews"].empty:
        st.caption("No reviews short enough to show here.")
    else:
        random_review(summary["shown_reviews"], appid)

# Negative surge events across every exported game, reused for an hour
@st.cache_data(ttl=3600, show_spinner=False)
def cached_flagged_events() -> pd.DataFrame:
    return flagged_events()

# When an event happened: a month, a run of months, or the open last-30-days window
def event_when(event) -> str:
    if event.label.startswith("last"):
        return f"Last {RECENT_DAYS} days (still unfolding)"
    return f"{event.start:%b %Y} to {event.end:%b %Y}" if event.months > 1 else f"{event.start:%B %Y}"

# One event as a list row with the game's banner, kind, when, size, score and drop
def event_row(event) -> str:
    banner = (f'<img src="{html.escape(event.header_image)}" alt="" loading="lazy">' if event.header_image
              else '<div class="row-empty"></div>')
    extra = f"+{event.extra_negatives:,.0f} extra negatives" if event.kind == "Negative surge" else ""
    return (f'<a class="game-row" href="{page_href(event.appid)}">{banner}'
            f'<span class="row-name">{html.escape(event.game)}'
            f'<small>{event.kind} \u00b7 {event_when(event)} \u00b7 {event.reviews:,.0f} reviews</small></span>'
            f'<span class="row-extra">{extra}</span>'
            f'<span class="row-score">{event.pct_positive:.0f}% vs usual {event.usual_pct:.0f}%</span>'
            f'<span class="row-drop" style="color: {EVENT_KIND_COLORS[event.kind]}">\u25bc {event.drop_points:.0f} pts</span></a>')

# Bubble chart of every event: when it happened, how far the score fell, sized by reviews and coloured by kind
def event_timeline(events: pd.DataFrame) -> alt.Chart:
    data = events.assign(start=lambda e: e["start"].dt.tz_localize(None), month=lambda e: [event_when(row) for row in e.itertuples()])
    return alt.Chart(data).mark_circle(opacity=0.7).encode(
        x=alt.X("start:T", title=None, axis=alt.Axis(format="%Y", labelAngle=0, tickCount={"interval": "year", "step": 1})),
        y=alt.Y("drop_points:Q", title="Points below the usual score"),
        size=alt.Size("reviews:Q", legend=None, scale=alt.Scale(range=[80, 1400])),
        color=alt.Color("kind:N", title=None, scale=alt.Scale(domain=list(EVENT_KIND_COLORS), range=list(EVENT_KIND_COLORS.values())),
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("game:N", title="Game"), alt.Tooltip("kind:N", title="Kind"), alt.Tooltip("month:N", title="When"),
                 alt.Tooltip("reviews:Q", title="Reviews", format=","), alt.Tooltip("extra_negatives:Q", title="Extra negatives", format=","),
                 alt.Tooltip("pct_positive:Q", title="% positive", format=".0f"), alt.Tooltip("usual_pct:Q", title="Usual %", format=".0f")],
    ).properties(height=300)

# Flagged events: every one across the games, when they happened, and how they are found
def events_page() -> None:
    tab_title("Outliers")
    st.title("Outliers", anchor=False)
    st.caption("Months when a game got a surge of negative reviews or its score dropped sharply, across every game analyzed.")
    if not (EXPORT_DIR / INDEX_NAME).exists():
        st.info("No exported game data yet. Run `uv run python src/export.py` in a terminal, then reload this page.")
        return
    events = cached_flagged_events()
    games = load_index()

    sections = {"Overview": "overview", "Event list": "event-list", "When they happened": "when-they-happened",
                "Look closer": "look-closer", "How it's detected": "how-its-detected"}
    with st.sidebar:
        st.html(outline_html(sections))
    st.html(section_icon_css() + PANEL_CSS + LIBRARY_CSS + EVENT_CSS)

    # Headline numbers, as one panel split by dividers
    st.divider()
    st.subheader("Overview", anchor="overview")
    st.caption("How many events there are, and which were the most dramatic")
    if events.empty:
        st.success("No flagged events in any game.", icon=":material/check_circle:")
        return
    worst, biggest = events.loc[events["drop_points"].idxmax()], events.loc[events["extra_negatives"].idxmax()]
    kinds = events["kind"].value_counts()
    with st.container(border=True, key="game_stats"):
        count, affected, drop, surge = st.columns(4)
        count.html(stat_cell("Flagged events", f"{len(events)}", icon="warning", color=COMPLAINT_COLOR,
                             tip=f"{kinds.get('Negative surge', 0)} negative surges and {kinds.get('Score drop', 0)} score drops"))
        affected.html(stat_cell("Games affected", f"{events['appid'].nunique()} of {len(games)}", icon="sports_esports"))
        drop.html(stat_cell("Biggest drop", worst["game"], icon="trending_down", delta=f"{-worst['drop_points']:.2f}",
                            tip=f"{event_when(worst)}: {worst['pct_positive']:.0f}% positive vs a usual {worst['usual_pct']:.0f}%"))
        surge.html(stat_cell("Most extra negatives", f"{biggest['extra_negatives']:,.0f}", icon="bolt",
                             tip=f"{biggest['game']}, {event_when(biggest)}: negative reviews beyond the usual number"))

    # Every flagged event, as list rows linking to the game
    st.divider()
    st.subheader("Event list", anchor="event-list")
    st.caption("Select a game to open its page. Runs of consecutive flagged months count as one event.")
    kind_col, sort_col = st.columns(2, vertical_alignment="center")
    kind = kind_col.segmented_control("Kind", options=list(EVENT_KINDS), default="All", label_visibility="collapsed")
    with sort_col.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center"):
        sort = st.segmented_control("Sort by", options=list(EVENT_SORTS), default="Most extra negatives", label_visibility="collapsed",
                                    key="event_sort")
    wanted = EVENT_KINDS[kind or "All"]
    shown = (events if wanted is None else events[events["kind"] == wanted]).sort_values(EVENT_SORTS[sort or "Most extra negatives"], ascending=False)
    st.html('<div class="library-list event-list">' + "".join(event_row(event) for event in shown.itertuples()) + "</div>")

    # When they happened
    st.divider()
    st.subheader("When they happened", anchor="when-they-happened")
    st.caption("Each dot is an event. Higher means a bigger fall in score, and bigger means more reviews.")
    st.altair_chart(event_timeline(events), width="stretch")

    # One game's trend with its flagged months marked
    st.divider()
    st.subheader("Look closer", anchor="look-closer")
    st.caption("Pick a game to see its score month by month, with the flagged months marked")
    ranked = events.sort_values("extra_negatives", ascending=False).drop_duplicates("appid")
    names = dict(zip(ranked["game"], ranked["appid"]))
    choice = st.selectbox("Game", options=list(names), label_visibility="collapsed")
    summary = cached_summary(int(names[choice]))
    sentiment, volume_chart = trend_charts(summary["trend"], summary["events"], summary["pct_positive"])
    st.altair_chart(sentiment, width="stretch")
    st.altair_chart(volume_chart, width="stretch")
    if st.button("Open the game page", icon=":material/open_in_new:"):
        st.switch_page(game_nav, query_params={"app": str(names[choice])})

    # How a month gets flagged, and what a flag can't tell you
    st.divider()
    st.subheader("How it's detected", anchor="how-its-detected")
    st.caption("The rules behind the flags, and what to keep in mind when reading them")
    st.markdown(f"""
- A **negative surge** (often called a review bomb) is a month where negative reviews are at least **{SURGE_NEGATIVE_RATIO:g}\u00d7 the usual** and at least **{SURGE_EXTRA_NEGATIVES} more than usual**,
  with a score at least **{SURGE_SCORE_DROP} points below the usual**. Usual means the median of the previous {FLAG_LOOKBACK_MONTHS} months.
- A **score drop** is a month at least **{DROP_SCORE_POINTS} points below the usual** with {DROP_MIN_REVIEWS:,} or more reviews but without that surge of negatives:
  a slide in opinion, or a controversy that didn't bring a flood.
- A game needs at least 3 earlier months to be judged, so launch months are never flagged.
- Runs of consecutive flagged months are shown as one event. The last {RECENT_DAYS} days are checked the same way, so a flag there can still be unfolding.
- Review counts and scores are Steam's exact totals for each month, not samples.
""")
    st.markdown("""
**What a flag can and can't tell you**
- It tells you something happened: a controversy, a bad update, a launch problem, a change in how the game is sold.
  Helldivers 2's May 2024 flag, for example, is the PlayStation Network sign-in requirement.
- It can't tell whether the reviews are off-topic or deserved. Steam's own off-topic filter didn't change the totals even for that Helldivers 2 episode, so flags are found from review counts and scores alone.
- A steady game with many reviews can still be flagged when a real problem lands. Check the game's page for what players were saying at the time.
""")

# Library page, forwarding old game links that still use /games?app=<id>
def games_page() -> None:
    appid = parse_appid(st.query_params.get("app", ""))
    if appid is not None:
        st.switch_page(game_nav, query_params={"app": str(appid)})
    library_page()

# Hidden page for one game, so the Games link in the sidebar leads back to the library
def game_entry() -> None:
    appid = parse_appid(st.query_params.get("app", ""))
    if appid is None:
        st.switch_page(games_nav)
    game_page(appid)

# CSS that draws each sidebar page's bundled Lucide icon in place of Streamlit's Material one, which nav links can't swap
def nav_icon_css() -> str:
    icons = {"1": "house", "2": "gamepad-2", "3": "triangle-alert", "4": "circle-help"}
    rules = []
    for position, name in icons.items():
        data = base64.b64encode((ASSET_DIR / f"lucide-{name}.svg").read_bytes().replace(b"currentColor", b"black")).decode()
        mask = f"url(data:image/svg+xml;base64,{data}) center / contain no-repeat"
        rules.append(f'[data-testid="stSidebarNav"] li:nth-child({position}) [data-testid="stIconMaterial"] '
                     f'{{ font-size: 0; background: currentColor; -webkit-mask: {mask}; mask: {mask}; }}')
    return "<style>" + "\n".join(rules) + "</style>"

# Square button that opens the repository, with the bundled Lucide GitHub icon drawn as a mask because st.html strips inline SVG
def repo_button() -> str:
    icon = base64.b64encode((ASSET_DIR / "github.svg").read_bytes().replace(b"currentColor", b"black")).decode()
    return (f'<style>.repo-button span {{ width: 1.5rem; height: 1.5rem; flex: none; background: currentColor; '
            f'-webkit-mask: url(data:image/svg+xml;base64,{icon}) center / contain no-repeat; '
            f'mask: url(data:image/svg+xml;base64,{icon}) center / contain no-repeat; }}</style>'
            f'<a class="repo-button" href="{REPO_URL}" target="_blank" rel="noreferrer" title="View the source on GitHub" '
            f'aria-label="GitHub"><span></span>GitHub</a>')

# Unique sampled reviews across every game, the ones the themes are read from
@st.cache_data(ttl=3600, show_spinner=False)
def analyzed_reviews() -> int:
    if (EXPORT_DIR / INDEX_NAME).exists():
        return sum(meta["sampled_reviews"] for meta in load_index())
    return sum(len(pd.read_parquet(path, columns=["recommendationid"]).drop_duplicates())
               for path in DATA_DIR.glob("*.parquet") if path.stem.isdigit())

# Home page: what the app is, headline numbers, and a few popular games
def home_page() -> None:
    tab_title()
    games = library_games()
    steam_reviews = sum(meta.get("summary", {}).get("total_reviews", 0) for meta in games)
    flagged = len(cached_flagged_events()) if (EXPORT_DIR / INDEX_NAME).exists() else 0
    popular = sorted(games, key=lambda meta: meta.get("summary", {}).get("total_reviews", 0), reverse=True)[:8]
    with st.sidebar:
        st.html(sidebar_links("Popular games", [("trending_up", game_name(meta), page_href(meta["appid"])) for meta in popular], ""))
    st.title("SteamTLDR", anchor=False)
    st.markdown("Steam shows one score. SteamTLDR shows *why*: what players love, what they complain about, and how opinion is changing, "
                "boiled down from thousands of reviews you don't have to read.")
    with st.container(horizontal=True, key="home_cta"):
        if st.button("Browse games", icon=":material/sports_esports:", type="primary"):
            st.switch_page(games_nav)
        if st.button("FAQ", icon=":material/help:"):
            st.switch_page(about_nav)
        st.html(repo_button())
    st.html(PANEL_CSS)
    with st.container(border=True, key="game_stats"):
        for column, (label, value) in zip(st.columns(4), [("Games analyzed", f"{len(games)}"),
                                                          ("Reviews analyzed", f"{analyzed_reviews():,}"),
                                                          ("English reviews on Steam", f"{steam_reviews:,}"),
                                                          ("Flagged events", f"{flagged}")]):
            column.html(stat_cell(label, value))
    st.subheader("Popular games", anchor=False)
    st.html(LIBRARY_CSS + '<div class="home-library">' + "".join(game_card(meta) for meta in popular) + "</div>")

# Copyright line and ownership note shown at the bottom of every page
FOOTER_HTML = """<style>
.site-footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid color-mix(in srgb, currentColor 15%, transparent);
  display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.25rem 1.5rem; font-size: 0.8rem; opacity: 0.6; }
</style>
<footer class="site-footer"><span>\u00a9 2026 Jonathan Tam</span>
<span>Not affiliated with Valve or Steam. Game names, images and reviews belong to their respective owners.</span></footer>"""

# Fades the page out before a theme link reloads it, once per browser page; the new page fades in from the CSS above
THEME_FADE_JS = """<script>
if (!window.themeFadeReady) {
  window.themeFadeReady = true;
  document.addEventListener("click", (event) => {
    const link = event.target.closest(".theme-switch a");
    if (!link || link.classList.contains("on")) return;
    event.preventDefault();
    document.documentElement.classList.add("theme-fading");
    setTimeout(() => { window.location.href = link.href; }, 200);
  });
}
</script>"""

# Full logo in the header, even when the sidebar is closed
st.logo(ASSET_DIR / "logo.svg", size="large", icon_image=ASSET_DIR / "logo.svg")
with st.sidebar:
    st.html(SIDEBAR_CSS + nav_icon_css())
    st.html(THEME_FADE_JS, unsafe_allow_javascript=True)
    with st.container(key="sidebar_footer"):
        st.html(theme_switch())

home_nav = st.Page(home_page, title="Home", icon=":material/home:", url_path="", default=True)
games_nav = st.Page(games_page, title="Games", icon=":material/sports_esports:", url_path="games")
game_nav = st.Page(game_entry, title="Game", url_path="game", visibility="hidden")
events_nav = st.Page(events_page, title="Outliers", icon=":material/warning:", url_path="outliers")
about_nav = st.Page(about_page, title="FAQ", icon=":material/help:", url_path=ABOUT_PAGE)
st.navigation([home_nav, games_nav, game_nav, events_nav, about_nav]).run()

# Thin footer under every page
st.html(FOOTER_HTML)
