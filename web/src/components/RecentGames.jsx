import { useEffect, useState } from "react";
import { History } from "lucide-react";
import { RECENT_KEY, gameHref } from "../lib/games.js";

// Chips shown at most, newest first
const SHOWN = 5;

// Recently viewed games as a row of chips, read from this browser once the page loads
export default function RecentGames({ names }) {
  const [recent, setRecent] = useState(null);
  useEffect(() => {
    try {
      setRecent(JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]").filter((appid) => names[appid]).slice(0, SHOWN));
    } catch {
      setRecent([]);
    }
  }, []);

  return (
    <nav className="recent-chips" aria-label="Recently viewed">
      <span className="recent-label"><History aria-hidden="true" />Recently viewed</span>
      {recent?.length === 0 && <span className="recent-empty">Games you open will show up here.</span>}
      {recent?.map((appid) => <a key={appid} href={gameHref(appid)}>{names[appid]}</a>)}
    </nav>
  );
}
