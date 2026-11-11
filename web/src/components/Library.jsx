import { useRef, useState } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, LayoutGrid, List, Search, X } from "lucide-react";
import GameCard from "./GameCard.jsx";
import { useFoldAwareImages } from "../lib/useFoldAwareImages.js";
import { dateValue, formatCount, gameHref, gameName, scoreColor, steamPct } from "../lib/games.js";

// Sort orders as label -> [key, highest first], applied after sorting by name
const SORTS = {
  "Name (A → Z)": [(game) => gameName(game).toLowerCase(), false],
  "Name (Z → A)": [(game) => gameName(game).toLowerCase(), true],
  "Rating (High → Low)": [(game) => steamPct(game) ?? -1, true],
  "Rating (Low → High)": [(game) => steamPct(game) ?? -1, false],
  "Reviews (High → Low)": [(game) => game.summary?.total_reviews ?? 0, true],
  "Reviews (Low → High)": [(game) => game.summary?.total_reviews ?? 0, false],
  "Release date (New → Old)": [(game) => dateValue(game.release_date), true],
  "Release date (Old → New)": [(game) => dateValue(game.release_date), false],
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

// Table headers as [title, the sort that comes first when clicked, its opposite]
const COLUMNS = [
  ["Game", "Name (A → Z)", "Name (Z → A)"],
  ["Score", "Rating (High → Low)", "Rating (Low → High)"],
  ["Reviews", "Reviews (High → Low)", "Reviews (Low → High)"],
  ["Genres", null, null],
];

// Games per page, 5 rows of 10 cards
const PAGE_SIZE = 50;

// Genres need this many games to get an entry in the genre menu, which hides one-off software categories
const MIN_GENRE_GAMES = 2;

// Genre menu entries as [genre, game count], most common first
function genreCounts(games) {
  const counts = {};
  for (const game of games) for (const genre of game.genres ?? []) counts[genre] = (counts[genre] ?? 0) + 1;
  return Object.entries(counts).filter(([, count]) => count >= MIN_GENRE_GAMES).sort((a, b) => b[1] - a[1] || compare(a[0], b[0]));
}

// Ascending order for text or numbers
const compare = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

// Page numbers to show: the first, the last and the ones around the current page, with "…" for the gaps
function pageList(page, count) {
  const wanted = new Set([1, count, page - 1, page, page + 1]);
  const numbers = [...wanted].filter((n) => n >= 1 && n <= count).sort((a, b) => a - b);
  return numbers.flatMap((n, i) => (i > 0 && n - numbers[i - 1] > 1 ? [`gap${n}`, n] : [n]));
}

// Previous / numbered / next page buttons
function Pagination({ page, count, onChange, className = "" }) {
  return (
    <nav className={`pagination ${className}`} aria-label="Pages">
      <button disabled={page === 1} aria-label="Previous page" onClick={() => onChange(page - 1)}><ChevronLeft size={16} /></button>
      {pageList(page, count).map((item) => (
        typeof item === "string" ? <span key={item} className="gap">…</span> : (
          <button key={item} className={item === page ? "on" : ""} aria-current={item === page ? "page" : undefined} onClick={() => onChange(item)}>{item}</button>
        )
      ))}
      <button disabled={page === count} aria-label="Next page" onClick={() => onChange(page + 1)}><ChevronRight size={16} /></button>
    </nav>
  );
}

// Sortable table of games: a small banner with name and studio, a score bar, review count and genres
function GameTable({ games, sort, setSort }) {
  const clickHeader = (first, second) => setSort(sort === first ? second : first);
  return (
    <table className="library-table">
      <thead>
        <tr>
          {COLUMNS.map(([title, first, second]) => {
            const active = sort === first || sort === second;
            const Arrow = sort === second ? ChevronUp : ChevronDown;
            return (
              <th key={title} className={`col-${title.toLowerCase()}`} aria-sort={active ? ((sort === first) === (title === "Game") ? "ascending" : "descending") : undefined}>
                {first ? <button onClick={() => clickHeader(first, second)}>{title}{active && <Arrow size={14} />}</button> : title}
              </th>
            );
          })}
        </tr>
      </thead>
      <tbody>
        {games.map((game) => {
          const pct = steamPct(game);
          return (
            <tr key={game.appid}>
              <td className="col-game">
                <div className="game-cell">
                  {game.header_image ? <img src={game.thumb ?? game.header_image} alt="" width="220" height="103" loading="lazy" decoding="async" /> : <div className="row-empty" />}
                  <span className="row-name"><a href={gameHref(game.appid)}>{gameName(game)}</a><small>{(game.developers ?? []).join(", ")}</small></span>
                </div>
              </td>
              <td className="col-score">
                {pct === null ? "No reviews yet" : (
                  <>
                    <span className="score-line"><b style={{ color: scoreColor(pct) }}>{pct.toFixed(0)}%</b><small>{game.summary.review_score_desc}</small></span>
                    <span className="score-track"><span style={{ width: `${pct}%`, background: scoreColor(pct) }} /></span>
                  </>
                )}
              </td>
              <td className="col-reviews">{formatCount(game.summary?.total_reviews ?? 0)}</td>
              <td className="col-genres">{(game.genres ?? []).slice(0, 2).join(", ")}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// Searchable, sortable game library with genre and score filters, a cards or table view and pages of 50
export default function Library({ games }) {
  const [search, setSearch] = useState("");
  const [genre, setGenre] = useState("");
  const [score, setScore] = useState("Any");
  const [sort, setSort] = useState(Object.keys(SORTS)[0]);
  const [view, setView] = useState("Cards");
  const [paging, setPaging] = useState({ page: 1, key: "" });
  const results = useRef(null);
  useFoldAwareImages(results);

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

  // Show page 1 again whenever the search, filters or sort change
  const pageKey = [search, genre, score, sort].join("|");
  const pageCount = Math.max(1, Math.ceil(shown.length / PAGE_SIZE));
  const page = Math.min(paging.key === pageKey ? paging.page : 1, pageCount);
  const visible = shown.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const goToPage = (next) => {
    setPaging({ page: next, key: pageKey });
    results.current?.scrollIntoView({ block: "start" });
  };

  // Reset the search and both filters, keeping the sort order and view
  const filtered = search.trim() !== "" || genre !== "" || score !== "Any";
  const clearFilters = () => {
    setSearch("");
    setGenre("");
    setScore("Any");
  };
  const clearButton = filtered && <button className="link-button" onClick={clearFilters}><X size={14} />Clear filters</button>;

  return (
    <>
      <div className="library-bar">
      <div className="toolbar">
        <label className="field toolbar-search">
          <span className="field-label"><Search size={18} aria-hidden="true" /><span className="sr-only">Search games</span></span>
          <input type="search" placeholder="Search by name" value={search} onChange={(event) => setSearch(event.target.value)} />
        </label>
        <label className="field">
          <span className="field-label">Genre</span>
          <select value={genre} onChange={(event) => setGenre(event.target.value)}>
            <option value="">All genres</option>
            {genreCounts(games).map(([name, count]) => <option key={name} value={name}>{name} ({count})</option>)}
          </select>
        </label>
        <label className="field">
          <span className="field-label">Score</span>
          <select value={score} onChange={(event) => setScore(event.target.value)}>
            {Object.keys(SCORES).map((label) => <option key={label}>{label}</option>)}
          </select>
        </label>
        <label className="field toolbar-sort">
          <span className="field-label">Sort</span>
          <select value={sort} onChange={(event) => setSort(event.target.value)}>
            {Object.keys(SORTS).map((label) => <option key={label}>{label}</option>)}
          </select>
        </label>
        <div className="field toolbar-view" role="group" aria-label="View">
          {Object.entries(VIEWS).map(([label, Icon]) => (
            <button key={label} className={view === label ? "on" : ""} aria-label={label} aria-pressed={view === label} onClick={() => setView(label)}>
              <Icon size={20} />
            </button>
          ))}
        </div>
      </div>

      {games.length === 0 ? (
        <p>No games analyzed yet.</p>
      ) : shown.length === 0 ? (
        <p className="caption results empty">
          {genre || score !== "Any" ? "No games match these filters." : `No games match “${search}”.`}{clearButton}
        </p>
      ) : (
        <div className="results-bar">
          <p className="caption results">
            {shown.length} of {games.length} games{pageCount > 1 && `, showing ${(page - 1) * PAGE_SIZE + 1}–${(page - 1) * PAGE_SIZE + visible.length}`}{clearButton}
          </p>
          {pageCount > 1 && <Pagination page={page} count={pageCount} onChange={goToPage} />}
        </div>
      )}
      </div>

      {shown.length > 0 && (
        <>
          <div className="library-box" ref={results}>
            {view === "List" ? (
              <GameTable games={visible} sort={sort} setSort={setSort} />
            ) : (
              <div className="library">{visible.map((game) => <GameCard key={game.appid} game={game} compact />)}</div>
            )}
          </div>
          {pageCount > 1 && <Pagination page={page} count={pageCount} onChange={goToPage} className="bottom" />}
        </>
      )}
    </>
  );
}
