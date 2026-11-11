import { useEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";
import { RECENT_KEY, gameHref, scoreColor } from "../lib/games.js";

// Results shown at most
const SHOWN = 8;

// Rank games for a query: name starts with it, then a word in the name starts with it, then the name, developer or genre contains it
function rank(games, query) {
  const needle = query.trim().toLowerCase();
  if (!needle) return [];
  const scored = [];
  for (const game of games) {
    const name = game.name.toLowerCase();
    let score = 0;
    if (name.startsWith(needle)) score = 4;
    else if (name.split(/[\s:\-–—]+/).some((word) => word.startsWith(needle))) score = 3;
    else if (name.includes(needle)) score = 2;
    else if ([...game.developers, ...game.genres].some((text) => text.toLowerCase().includes(needle))) score = 1;
    if (score) scored.push({ game, score });
  }
  return scored.sort((a, b) => b.score - a.score || b.game.reviews - a.game.reviews).slice(0, SHOWN).map((entry) => entry.game);
}

// Nav search: a button plus a Cmd+K (Ctrl+K) palette that jumps to a game's page
export default function SearchPalette() {
  const dialog = useRef(null);
  const input = useRef(null);
  const [games, setGames] = useState(null);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [hint, setHint] = useState("⌘ K");

  // Show Ctrl on other systems, and toggle with the shortcut from any page
  useEffect(() => {
    if (!/Mac|iPhone|iPad/.test(navigator.platform)) setHint("Ctrl K");
    const onKey = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        dialog.current?.open ? dialog.current.close() : open();
      }
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, []);

  // Fetch the game list the first time the palette opens
  const open = () => {
    dialog.current?.showModal();
    setQuery("");
    setActive(0);
    if (!games) fetch("/search.json").then((response) => response.json()).then(setGames).catch(() => setGames([]));
    requestAnimationFrame(() => input.current?.focus());
  };

  const results = useMemo(() => {
    if (!games) return [];
    if (query.trim()) return rank(games, query);
    try {
      const recent = JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]");
      return recent.map((appid) => games.find((game) => game.appid === appid)).filter(Boolean).slice(0, SHOWN);
    } catch {
      return [];
    }
  }, [games, query]);

  const go = (game) => { if (game) location.href = gameHref(game.appid); };
  const onInputKey = (event) => {
    if (event.key === "ArrowDown") { event.preventDefault(); setActive((i) => Math.min(i + 1, results.length - 1)); }
    else if (event.key === "ArrowUp") { event.preventDefault(); setActive((i) => Math.max(i - 1, 0)); }
    else if (event.key === "Enter") { event.preventDefault(); go(results[active]); }
  };

  return (
    <>
      <button type="button" className="nav-search" onClick={open} aria-label="Search games" title="Search games">
        <Search aria-hidden="true" /><span className="nav-search-label">Search</span><kbd>{hint}</kbd>
      </button>
      <dialog ref={dialog} className="search-dialog" aria-label="Search games" onClick={(event) => event.target === dialog.current && dialog.current.close()}>
        <div className="search-box">
          <Search aria-hidden="true" />
          <input ref={input} type="search" value={query} placeholder="Search games, developers or genres" autoComplete="off" spellCheck={false}
            onChange={(event) => { setQuery(event.target.value); setActive(0); }} onKeyDown={onInputKey} />
          <kbd>Esc</kbd>
        </div>
        <ul className="search-results" role="listbox">
          {!query.trim() && results.length > 0 && <li className="search-heading">Recently viewed</li>}
          {results.map((game, i) => (
            <li key={game.appid} role="option" aria-selected={i === active}>
              <a href={gameHref(game.appid)} className={i === active ? "on" : ""} onMouseMove={() => setActive(i)}>
                <span className="search-name">{game.name}</span>
                <span className="search-meta">{game.genres.slice(0, 2).join(" · ")}</span>
                {game.pct !== null && <span className="search-pct" style={{ color: scoreColor(game.pct) }}>{Math.round(game.pct)}%</span>}
              </a>
            </li>
          ))}
          {query.trim() && games && results.length === 0 && <li className="search-empty">No games match “{query.trim()}”.</li>}
          {!query.trim() && results.length === 0 && <li className="search-empty">{games ? "Type a game name to jump to it." : "Loading…"}</li>}
        </ul>
      </dialog>
    </>
  );
}
