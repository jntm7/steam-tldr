import { gameName, steamPct, tableRows } from "./games.js";

// Build-time only: small report cards for the home page hero, built from the exported summaries
const THEMES_SHOWN = 3;
const TREND_MONTHS = 24;

// One game's card: Steam's score, top praise and complaints, and recent monthly scores
export function reportCard(game, summary) {
  const themes = (table) => tableRows(table).slice(0, THEMES_SHOWN).map(({ theme, pct }) => ({ theme, pct: Math.round(pct) }));
  const trend = tableRows(summary.trend).slice(-TREND_MONTHS);
  return {
    appid: game.appid,
    name: gameName(game),
    pct: Math.round(steamPct(game)),
    desc: game.summary.review_score_desc,
    total: game.summary.total_reviews,
    praise: themes(summary.praise),
    complaints: themes(summary.complaints),
    trend: trend.map((month) => Math.round(month.pct_positive)),
    trendFrom: trend[0].label,
  };
}

// Hero card games, alternating high and mixed scores
// Monster Hunter Wilds, Counter-Strike 2, Cities: Skylines II, Baldur's Gate 3, Helldivers 2
const HERO_GAMES = [2246340, 730, 949230, 1086940, 553850];

// Report cards for the hero games, skipping any missing from the library
export function heroCards(games, summaries) {
  const byAppid = Object.fromEntries(summaries.map((summary) => [summary.appid, summary]));
  return HERO_GAMES
    .map((appid) => games.find((game) => game.appid === appid))
    .filter((game) => game && byAppid[game.appid] && steamPct(game) !== null)
    .map((game) => reportCard(game, byAppid[game.appid]));
}
