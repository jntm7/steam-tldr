import { useEffect, useState } from "react";
import { History } from "lucide-react";
import { RECENT_KEY, gameHref } from "../lib/games.js";

// Sidebar list of recently viewed games, read from this browser once the page loads
export default function RecentGames({ names }) {
  const [recent, setRecent] = useState(null);
  useEffect(() => {
    try {
      setRecent(JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]").filter((appid) => names[appid]));
    } catch {
      setRecent([]);
    }
  }, []);

  return (
    <div>
      <div className="outline-title">Recently viewed</div>
      {recent?.length === 0 && <div className="outline-empty">Games you open will show up here.</div>}
      {recent?.length > 0 && (
        <nav className="outline">
          {recent.map((appid) => <a key={appid} href={gameHref(appid)}><History /><span>{names[appid]}</span></a>)}
        </nav>
      )}
    </div>
  );
}
