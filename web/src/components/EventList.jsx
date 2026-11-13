import { useRef, useState } from "react";
import Pagination from "./Pagination.jsx";
import { useFoldAwareImages } from "../lib/useFoldAwareImages.js";
import { COMPLAINT_COLOR, MIXED_COLOR, formatCount, gameHref } from "../lib/games.js";

// Colour of each kind of event, shared with the timeline
export const KIND_COLORS = { "Negative surge": COMPLAINT_COLOR, "Score drop": MIXED_COLOR };

// Kind filters as label -> kind, and sort orders as label -> what to rank by, biggest first
const KINDS = { "All": null, "Negative surges": "Negative surge", "Score drops": "Score drop" };
const SORTS = {
  "Newest": (event) => event.start,
  "Most extra negatives": (event) => event.extraNegatives,
  "Biggest drop": (event) => event.dropPoints,
  "Most reviews": (event) => event.reviews,
};

// The tag for events whose reviews do not agree on a reason, and the reason filter's "no filter" choice
const UNCLEAR = "unclear";
const ANY_REASON = "Any reason";

// Events per page
const PAGE_SIZE = 10;

// One event as a card: banner, game, kind and when, size, score against the usual and the fall in points, then why it happened below
function EventRow({ event }) {
  const tags = event.tags.filter((tag) => tag !== UNCLEAR);
  return (
    <a className="event-row" href={gameHref(event.appid)}>
      {event.thumb ? <img src={event.thumb} alt="" width="220" height="103" loading="lazy" decoding="async" /> : <div className="row-empty" />}
      <span className="row-name">{event.game}<small>{event.kind} · {event.when} · {formatCount(event.reviews)} reviews</small></span>
      <span className="event-extra">{event.kind === "Negative surge" ? `+${formatCount(event.extraNegatives)} extra negatives` : ""}</span>
      <span className="event-score">{event.pct.toFixed(0)}% vs usual {event.usualPct.toFixed(0)}%</span>
      <span className="event-drop" style={{ color: KIND_COLORS[event.kind] }}>▼ {event.dropPoints.toFixed(0)} pts</span>
      {event.reason && (
        <span className="event-why">
          <span className="event-why-label">Why</span>
          <span className="event-why-text">{event.reason}</span>
          {tags.length > 0 && <span className="chips event-tags">{tags.map((tag) => <span key={tag} className="chip">{tag}</span>)}</span>}
        </span>
      )}
    </a>
  );
}

// Every flagged event as a list, filtered by kind and reason, sorted, in pages of 10
export default function EventList({ events }) {
  const [kind, setKind] = useState("All");
  const [reason, setReason] = useState(ANY_REASON);
  const [sort, setSort] = useState("Newest");
  const [paging, setPaging] = useState({ page: 1, key: "" });
  const listRef = useRef(null);
  const countRef = useRef(null);
  useFoldAwareImages(listRef);

  const rank = SORTS[sort];
  const reasonCounts = {};
  for (const event of events) for (const tag of event.tags) reasonCounts[tag] = (reasonCounts[tag] ?? 0) + 1;
  const reasonOptions = Object.keys(reasonCounts).sort((a, b) => (a === UNCLEAR) - (b === UNCLEAR) || reasonCounts[b] - reasonCounts[a]);
  const shown = events
    .filter((event) => !KINDS[kind] || event.kind === KINDS[kind])
    .filter((event) => reason === ANY_REASON || event.tags.includes(reason))
    .sort((a, b) => rank(b) - rank(a));
  // Back to page 1 whenever the filters or sort change
  const pageKey = [kind, reason, sort].join("|");
  const pageCount = Math.max(1, Math.ceil(shown.length / PAGE_SIZE));
  const page = Math.min(paging.key === pageKey ? paging.page : 1, pageCount);
  const visible = shown.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const goToPage = (next) => {
    setPaging({ page: next, key: pageKey });
    countRef.current?.scrollIntoView({ block: "start" });
  };

  return (
    <>
      <div className="chart-controls chart-toolbar event-toolbar">
        <div className="segmented" role="group" aria-label="Kind">
          {Object.keys(KINDS).map((label) => (
            <button key={label} className={kind === label ? "on" : ""} aria-pressed={kind === label} onClick={() => setKind(label)}>{label}</button>
          ))}
        </div>
        <div className="event-menus">
        {reasonOptions.length > 0 && (
          <label className="field event-sort">
            <span className="field-label">Reason</span>
            <select value={reason} onChange={(event) => setReason(event.target.value)}>
              <option>{ANY_REASON}</option>
              {reasonOptions.map((tag) => <option key={tag} value={tag}>{tag} ({reasonCounts[tag]})</option>)}
            </select>
          </label>
        )}
        <label className="field event-sort">
          <span className="field-label">Sort</span>
          <select value={sort} onChange={(event) => setSort(event.target.value)}>
            {Object.keys(SORTS).map((label) => <option key={label}>{label}</option>)}
          </select>
        </label>
        </div>
      </div>
      <div className="event-count" ref={countRef}>
        <p className="caption">{shown.length} {shown.length === 1 ? "event" : "events"}{pageCount > 1 && `, showing ${(page - 1) * PAGE_SIZE + 1}–${(page - 1) * PAGE_SIZE + visible.length}`}</p>
        {pageCount > 1 && <Pagination page={page} count={pageCount} onChange={goToPage} />}
      </div>
      <div className="event-list" ref={listRef}>{visible.map((event) => <EventRow key={`${event.appid}-${event.start}`} event={event} />)}</div>
      {pageCount > 1 && <Pagination page={page} count={pageCount} onChange={goToPage} className="bottom" />}
    </>
  );
}
