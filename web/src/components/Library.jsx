import { useState } from "react";
import { LayoutGrid, List, Search, X } from "lucide-react";
import GameCard from "./GameCard.jsx";
import { formatCount, gameHref, gameName, scoreColor, steamPct } from "../lib/games.js";

// Sort orders as label -> [key, highest first], applied after sorting by name
const SORTS = {
  "Name (A → Z)": [(game) => gameName(game).toLowerCase(), false],
  "Name (Z → A)": [(game) => gameName(game).toLowerCase(), true],
  "Rating (High → Low)": [(game) => steamPct(game) ?? -1, true],
  "Rating (Low → High)": [(game) => steamPct(game) ?? -1, false],
  "Reviews (High → Low)": [(game) => game.summary?.total_reviews ?? 0, true],
  "Reviews (Low → High)": [(game) => game.summary?.total_reviews ?? 0, false],
};

// Score filters as label -> which Steam percent passes, in Steam's colour bands
const SCORES = {
  "Any": () => true,
  "Positive (70%+)": (pct) => pct >= 70,
  "Mixed (40–69%)": (pct) => pct >= 40 && pct < 70,
  "Negative (under 40%)": (pct) => pct < 40,
};

// Layouts as label -> icon
const VIEWS = { Cards: LayoutGrid, List: List };

// Genres need this many games to get a chip, which hides one-off software categories
const MIN_GENRE_GAMES = 2;

// Genre chips as [genre, game count], most common first
function genreCounts(games) {
  const counts = {};
  for (const game of games) for (const genre of game.genres ?? []) counts[genre] = (counts[genre] ?? 0) + 1;
  return Object.entries(counts).filter(([, count]) => count >= MIN_GENRE_GAMES).sort((a, b) => b[1] - a[1] || compare(a[0], b[0]));
}

// Ascending order for text or numbers
const compare = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

// One list row with a small banner, name, studio, review count and Steam score
function GameRow({ game }) {
  const pct = steamPct(game);
  return (
    <a className="game-row" href={gameHref(game.appid)}>
      {game.header_image ? <img src={game.header_image} alt="" loading="lazy" /> : <div className="row-empty" />}
      <span className="row-name">{gameName(game)}<small>{(game.developers ?? []).join(", ")}</small></span>
      <span className="row-reviews">{formatCount(game.summary?.total_reviews ?? 0)} reviews</span>
      {pct === null ? (
        <span className="row-score">No reviews yet</span>
      ) : (
        <span className="row-score" style={{ color: scoreColor(pct) }}>{pct.toFixed(0)}% · {game.summary.review_score_desc}</span>
      )}
    </a>
  );
}

// Searchable, sortable game library with genre and score filters and a cards or list view
export default function Library({ games }) {
  const [search, setSearch] = useState("");
  const [genre, setGenre] = useState(null);
  const [score, setScore] = useState("Any");
  const [sort, setSort] = useState(Object.keys(SORTS)[0]);
  const [view, setView] = useState("Cards");

  const [key, highestFirst] = SORTS[sort];
  const sorted = [...games]
    .sort((a, b) => compare(gameName(a).toLowerCase(), gameName(b).toLowerCase()))
    .sort((a, b) => (highestFirst ? compare(key(b), key(a)) : compare(key(a), key(b))));
  const shown = sorted.filter((game) => {
    const pct = steamPct(game);
    return gameName(game).toLowerCase().includes(search.trim().toLowerCase())
      && (!genre || game.genres?.includes(genre))
      && (score === "Any" || (pct !== null && SCORES[score](pct)));
  });

  // Reset the search and both filters, keeping the sort order and view
  const filtered = search.trim() !== "" || genre !== null || score !== "Any";
  const clearFilters = () => {
    setSearch("");
    setGenre(null);
    setScore("Any");
  };
  const clearButton = filtered && <button className="link-button" onClick={clearFilters}><X size={14} />Clear filters</button>;

  return (
    <>
      <div className="toolbar">
        <label className="field toolbar-search">
          <span className="field-label"><Search size={18} /></span>
          <input type="search" placeholder="Search by name" aria-label="Search games" value={search} onChange={(event) => setSearch(event.target.value)} />
        </label>
        <label className="field toolbar-sort">
          <span className="field-label">Sort by</span>
          <select value={sort} onChange={(event) => setSort(event.target.value)}>
            {Object.keys(SORTS).map((label) => <option key={label}>{label}</option>)}
          </select>
        </label>
        <label className="field toolbar-score">
          <span className="field-label">Score</span>
          <select value={score} onChange={(event) => setScore(event.target.value)}>
            {Object.keys(SCORES).map((label) => <option key={label}>{label}</option>)}
          </select>
        </label>
        <div className="field toolbar-view" role="group" aria-label="View">
          <span className="field-label">View</span>
          {Object.entries(VIEWS).map(([label, Icon]) => (
            <button key={label} className={view === label ? "on" : ""} aria-label={label} aria-pressed={view === label} onClick={() => setView(label)}>
              <Icon size={20} />
            </button>
          ))}
        </div>
        <div className="chips" role="group" aria-label="Genre">
          <button className={genre === null ? "on" : ""} aria-pressed={genre === null} onClick={() => setGenre(null)}>All</button>
          {genreCounts(games).map(([name, count]) => (
            <button key={name} className={genre === name ? "on" : ""} aria-pressed={genre === name} onClick={() => setGenre(genre === name ? null : name)}>
              {name}<span>{count}</span>
            </button>
          ))}
        </div>
      </div>

      {games.length === 0 ? (
        <p>No games analyzed yet.</p>
      ) : shown.length === 0 ? (
        <p className="caption results">
          {genre || score !== "Any" ? "No games match these filters." : `No games match “${search}”.`}{clearButton}
        </p>
      ) : (
        <>
          <p className="caption results">{shown.length} of {games.length} games{clearButton}</p>
          {view === "List" ? (
            <div className="library-list">{shown.map((game) => <GameRow key={game.appid} game={game} />)}</div>
          ) : (
            <div className="library">{shown.map((game) => <GameCard key={game.appid} game={game} />)}</div>
          )}
        </>
      )}
    </>
  );
}
