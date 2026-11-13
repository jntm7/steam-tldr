import { games, summaries } from "./data.js";
import { gameName, monthRange, tableRows } from "./games.js";
import { withImages } from "./images.js";

// Build-time only, like data.js: every flagged event across the games, a run of consecutive flagged months counted once

// When an event happened: a month, a run of months, or the open last-30-days window
function eventWhen(first, last) {
  if (!/^\d{4}-\d{2}$/.test(first.label)) return "Last 30 days (still unfolding)";
  return monthRange(first.label, last.label);
}

// One game's flagged events, oldest first: each run of consecutive flagged months counted once, with its explanation if any
export function gameEvents(summary) {
  const reasons = Object.fromEntries((summary.event_reasons ?? []).map((record) => [record.start, record]));
  const runs = new Map();
  for (const row of tableRows(summary.events)) runs.set(row.episode, [...(runs.get(row.episode) ?? []), row]);
  return [...runs.values()].map((run) => {
    const first = run[0];
    return {
      kind: run.some((row) => row.kind === "Negative surge") ? "Negative surge" : "Score drop",
      when: eventWhen(first, run.at(-1)),
      start: new Date(first.start).getTime(),
      reviews: run.reduce((sum, row) => sum + row.reviews, 0),
      extraNegatives: Math.round(run.reduce((sum, row) => sum + row.extra_negatives, 0)),
      pct: Math.min(...run.map((row) => row.pct_positive)),
      usualPct: first.usual_pct,
      dropPoints: Math.max(...run.map((row) => row.usual_pct - row.pct_positive)),
      record: reasons[first.label] ?? null,
    };
  });
}

// Every game's events as plain objects for the Outliers page, with the game, its banner, and the explanation as text and tags
export async function flaggedEvents() {
  const byAppid = Object.fromEntries(games.map((game) => [game.appid, game]));
  const events = [];
  for (const summary of summaries) {
    const game = byAppid[summary.appid];
    const runs = gameEvents(summary);
    if (!game || runs.length === 0) continue;
    const { thumb } = await withImages(game);
    for (const { record, ...event } of runs) {
      events.push({
        ...event,
        appid: game.appid,
        game: gameName(game),
        thumb,
        reason: record?.reason.map((sentence) => sentence.text).join(" ") ?? null,
        tags: record?.tags.map((tag) => tag.tag) ?? [],
      });
    }
  }
  return events;
}
