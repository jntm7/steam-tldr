import { games, summaries } from "./data.js";
import { gameName, monthName, tableRows } from "./games.js";
import { withImages } from "./images.js";

// Build-time only, like data.js: every flagged event across the games, a run of consecutive flagged months counted once

// When an event happened: a month, a run of months, or the open last-30-days window
function eventWhen(first, last, months) {
  if (!/^\d{4}-\d{2}$/.test(first.label)) return "Last 30 days (still unfolding)";
  return months > 1 ? `${monthName(first.label)} to ${monthName(last.label)}` : monthName(first.label);
}

// Events as plain objects for the Outliers page: game, kind, when, size, score against the usual, and how far it fell
export async function flaggedEvents() {
  const byAppid = Object.fromEntries(games.map((game) => [game.appid, game]));
  const events = [];
  for (const summary of summaries) {
    const game = byAppid[summary.appid];
    const rows = tableRows(summary.events);
    if (!game || rows.length === 0) continue;
    const { thumb } = await withImages(game);

    const runs = new Map();
    for (const row of rows) runs.set(row.episode, [...(runs.get(row.episode) ?? []), row]);
    for (const run of runs.values()) {
      const first = run[0];
      const last = run.at(-1);
      events.push({
        appid: game.appid,
        game: gameName(game),
        thumb,
        kind: run.some((row) => row.kind === "Negative surge") ? "Negative surge" : "Score drop",
        when: eventWhen(first, last, run.length),
        start: new Date(first.start).getTime(),
        reviews: run.reduce((sum, row) => sum + row.reviews, 0),
        extraNegatives: run.reduce((sum, row) => sum + row.extra_negatives, 0),
        pct: Math.min(...run.map((row) => row.pct_positive)),
        usualPct: first.usual_pct,
        dropPoints: Math.max(...run.map((row) => row.usual_pct - row.pct_positive)),
      });
    }
  }
  return events;
}
