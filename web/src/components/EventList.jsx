import { useState } from "react";
import { COMPLAINT_COLOR, MIXED_COLOR, formatCount, gameHref } from "../lib/games.js";

// Colour of each kind of event, shared with the timeline
export const KIND_COLORS = { "Negative surge": COMPLAINT_COLOR, "Score drop": MIXED_COLOR };

// Kind filters as label -> kind, and sort orders as label -> what to rank by, biggest first
const KINDS = { "All": null, "Negative surges": "Negative surge", "Score drops": "Score drop" };
const SORTS = {
  "Most extra negatives": (event) => event.extraNegatives,
  "Biggest drop": (event) => event.dropPoints,
  "Most reviews": (event) => event.reviews,
  "Newest": (event) => event.start,
};

// Events shown before the "Show all" button, and how many rows load their banner at once
const FIRST_SHOWN = 20;
const EAGER_ROWS = 6;

// One event as a row: banner, game, kind and when, size, score against the usual, and the fall in points
function EventRow({ event, index }) {
  return (
    <a className="event-row" href={gameHref(event.appid)}>
      {event.thumb ? <img src={event.thumb} alt="" width="220" height="103" loading={index < EAGER_ROWS ? "eager" : "lazy"} decoding="async" /> : <div className="row-empty" />}
      <span className="row-name">{event.game}<small>{event.kind} · {event.when} · {formatCount(event.reviews)} reviews</small></span>
      <span className="event-extra">{event.kind === "Negative surge" ? `+${formatCount(event.extraNegatives)} extra negatives` : ""}</span>
      <span className="event-score">{event.pct.toFixed(0)}% vs usual {event.usualPct.toFixed(0)}%</span>
      <span className="event-drop" style={{ color: KIND_COLORS[event.kind] }}>▼ {event.dropPoints.toFixed(0)} pts</span>
    </a>
  );
}

// Every flagged event as a list, filtered by kind and sorted, with the first few shown
export default function EventList({ events }) {
  const [kind, setKind] = useState("All");
  const [sort, setSort] = useState("Most extra negatives");
  const [all, setAll] = useState(false);

  const rank = SORTS[sort];
  const shown = events.filter((event) => !KINDS[kind] || event.kind === KINDS[kind]).sort((a, b) => rank(b) - rank(a));
  const visible = all ? shown : shown.slice(0, FIRST_SHOWN);

  return (
    <>
      <div className="chart-controls">
        <div className="segmented" role="group" aria-label="Kind">
          {Object.keys(KINDS).map((label) => (
            <button key={label} className={kind === label ? "on" : ""} aria-pressed={kind === label} onClick={() => setKind(label)}>{label}</button>
          ))}
        </div>
        <label className="field event-sort">
          <span className="field-label">Sort</span>
          <select value={sort} onChange={(event) => setSort(event.target.value)}>
            {Object.keys(SORTS).map((label) => <option key={label}>{label}</option>)}
          </select>
        </label>
      </div>
      <p className="caption">{shown.length} {shown.length === 1 ? "event" : "events"}</p>
      <div className="event-list">{visible.map((event, index) => <EventRow key={`${event.appid}-${event.start}`} event={event} index={index} />)}</div>
      {!all && shown.length > FIRST_SHOWN && (
        <button className="button small show-all" onClick={() => setAll(true)}>Show all {shown.length} events</button>
      )}
    </>
  );
}
