import { games } from "../lib/data.js";
import { gameName, steamPct } from "../lib/games.js";

// Small list of every game for the nav search, fetched the first time it opens
export function GET() {
  const list = games.map((game) => ({
    appid: game.appid,
    name: gameName(game),
    pct: steamPct(game),
    reviews: game.summary?.total_reviews ?? 0,
    genres: game.genres ?? [],
    developers: game.developers ?? [],
  }));
  return new Response(JSON.stringify(list), { headers: { "Content-Type": "application/json" } });
}
