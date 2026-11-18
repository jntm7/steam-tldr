import { Fragment, useEffect, useRef, useState } from "react";
import { ChevronDown, LayoutList, Rows3, Search, X } from "lucide-react";
import Pagination from "./Pagination.jsx";
import { useFoldAwareImages } from "../lib/useFoldAwareImages.js";
import { COMPLAINT_COLOR, MIXED_COLOR, formatCount, gameHref } from "../lib/games.js";
import { FOCUS_EVENT, YEAR_EVENT, eventKey } from "../lib/outliersBus.js";

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

// Views and their page sizes; a picked view is remembered
const VIEWS = { Cards: { Icon: LayoutList, size: 10 }, Table: { Icon: Rows3, size: 25 } };
const VIEW_KEY = "steamtldr_events_view";

// Year an event started
const yearOf = (event) => new Date(event.start).getUTCFullYear();

// Tags worth showing as chips
const shownTags = (event) => event.tags.filter((tag) => tag !== UNCLEAR);

// One event as a card: banner, game, kind and when, size, score against the usual and the fall in points, then why it happened below
function EventCard({ event, focused }) {
  const tags = shownTags(event);
  return (
    <a className={`event-row${focused ? " focused" : ""}`} href={gameHref(event.appid)} data-key={eventKey(event)}>
      {event.thumb ? <img src={event.thumb} alt="" width="220" height="103" loading="lazy" decoding="async" /> : <div className="row-empty" />}
      <span className="row-name">{event.game}<small>{event.kind} · {event.when}<span className="event-sub-reviews"> · {formatCount(event.reviews)} reviews</span></small></span>
      <span className="event-extra">
        <span>{formatCount(event.reviews)} reviews</span>
        {event.kind === "Negative surge" && <span>+{formatCount(event.extraNegatives)} extra negatives</span>}
      </span>
      <span className="event-score" title={`Positive reviews: ${event.usualPct.toFixed(0)}% usually, ${event.pct.toFixed(0)}% during the event`}>{event.usualPct.toFixed(0)}% → {event.pct.toFixed(0)}%</span>
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

// Compact table: one row per event, the explanation opens under a row when it is picked
function EventTable({ events, open, onToggle, focusKey }) {
  return (
    <table className="event-table">
      <thead>
        <tr>
          <th className="col-game">Game</th>
          <th className="col-when">When</th>
          <th className="col-drop">Drop</th>
          <th className="col-extra">Extra negatives</th>
          <th className="col-tags">Reasons</th>
          <th className="col-open"><span className="sr-only">Details</span></th>
        </tr>
      </thead>
      <tbody>
        {events.map((event) => {
          const key = eventKey(event);
          const isOpen = open === key;
          const tags = shownTags(event);
          return (
            <Fragment key={key}>
              <tr className={`${isOpen ? "open" : ""}${focusKey === key ? " focused" : ""}`} data-key={key} onClick={() => onToggle(key)}>
                <td className="col-game">
                  <span className="event-table-game">
                    <i className="key-dot" style={{ background: KIND_COLORS[event.kind] }} title={event.kind} />
                    <span className="event-table-name">
                      <a href={gameHref(event.appid)} onClick={(click) => click.stopPropagation()}>{event.game}</a>
                      <small>{event.when}</small>
                    </span>
                  </span>
                </td>
                <td className="col-when">{event.when}</td>
                <td className="col-drop" style={{ color: KIND_COLORS[event.kind] }}>▼ {event.dropPoints.toFixed(0)}</td>
                <td className="col-extra">{event.kind === "Negative surge" ? `+${formatCount(event.extraNegatives)}` : "–"}</td>
                <td className="col-tags">{tags.join(", ") || "–"}</td>
                <td className="col-open">
                  <button aria-expanded={isOpen} aria-label={`${isOpen ? "Hide" : "Show"} why for ${event.game}`} onClick={(click) => { click.stopPropagation(); onToggle(key); }}>
                    <ChevronDown size={16} />
                  </button>
                </td>
              </tr>
              {isOpen && (
                <tr className="event-table-why">
                  <td colSpan={6}>
                    <span className="event-why-meta">{event.kind} · {event.usualPct.toFixed(0)}% → {event.pct.toFixed(0)}% positive · {formatCount(event.reviews)} reviews</span>
                    {event.reason ?? "No explanation yet."}
                    <a href={gameHref(event.appid)}>Open game page →</a>
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}

// Every flagged event, searchable by game, filtered by kind, reason and year, sorted, as cards or a table in pages
export default function EventList({ events }) {
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("All");
  const [reason, setReason] = useState(ANY_REASON);
  const [year, setYear] = useState(null);
  const [sort, setSort] = useState("Newest");
  const [view, setView] = useState("Cards");
  const [paging, setPaging] = useState({ page: 1, key: "" });
  const [open, setOpen] = useState(null);
  const [focus, setFocus] = useState(null);
  const listRef = useRef(null);
  const countRef = useRef(null);
  useFoldAwareImages(listRef);

  // Saved view
  useEffect(() => {
    let saved = null;
    try { saved = localStorage.getItem(VIEW_KEY); } catch {}
    if (saved in VIEWS) setView(saved);
  }, []);
  const pickView = (label) => {
    setView(label);
    try { localStorage.setItem(VIEW_KEY, label); } catch {}
  };

  const rank = SORTS[sort];
  const reasonCounts = {};
  for (const event of events) for (const tag of event.tags) reasonCounts[tag] = (reasonCounts[tag] ?? 0) + 1;
  const reasonOptions = Object.keys(reasonCounts).sort((a, b) => (a === UNCLEAR) - (b === UNCLEAR) || reasonCounts[b] - reasonCounts[a]);
  const query = search.trim().toLowerCase();
  const shown = events
    .filter((event) => !query || event.game.toLowerCase().includes(query))
    .filter((event) => !KINDS[kind] || event.kind === KINDS[kind])
    .filter((event) => reason === ANY_REASON || event.tags.includes(reason))
    .filter((event) => year === null || yearOf(event) === year)
    .sort((a, b) => rank(b) - rank(a));

  // Back to page 1 whenever the search, filters, sort or view change
  const pageSize = VIEWS[view].size;
  const pageKey = [query, kind, reason, year, sort, view].join("|");
  const pageCount = Math.max(1, Math.ceil(shown.length / pageSize));
  const page = Math.min(paging.key === pageKey ? paging.page : 1, pageCount);
  const visible = shown.slice((page - 1) * pageSize, page * pageSize);
  const goToPage = (next) => {
    setPaging({ page: next, key: pageKey });
    countRef.current?.scrollIntoView({ block: "start" });
  };

  // Reset the search and filters, keeping the sort and view
  const filtered = query !== "" || kind !== "All" || reason !== ANY_REASON || year !== null;
  const clearFilters = () => { setSearch(""); setKind("All"); setReason(ANY_REASON); setYear(null); };

  // Messages from the timeline (show one event) and the overview (show one year)
  useEffect(() => {
    const onFocus = ({ detail: key }) => {
      const target = events.find((event) => eventKey(event) === key);
      if (!target) return;
      const all = [...events].sort((a, b) => rank(b) - rank(a));
      const index = all.findIndex((event) => eventKey(event) === key);
      setSearch(""); setKind("All"); setReason(ANY_REASON); setYear(null);
      setPaging({ page: Math.floor(index / pageSize) + 1, key: ["", "All", ANY_REASON, null, sort, view].join("|") });
      setOpen(key);
      setFocus({ key, at: Date.now() });
    };
    const onYear = ({ detail }) => {
      setYear(detail);
      setFocus(null);
      countRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    };
    window.addEventListener(FOCUS_EVENT, onFocus);
    window.addEventListener(YEAR_EVENT, onYear);
    return () => { window.removeEventListener(FOCUS_EVENT, onFocus); window.removeEventListener(YEAR_EVENT, onYear); };
  }, [events, rank, pageSize, sort, view]);

  // Scroll a focused event into view once its page is showing
  useEffect(() => {
    if (!focus) return;
    listRef.current?.querySelector(`[data-key="${focus.key}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focus]);

  const toggle = (key) => setOpen((current) => (current === key ? null : key));
  const focusKey = focus?.key ?? null;

  return (
    <>
      <div className="chart-controls chart-toolbar event-toolbar">
        <div className="event-toolbar-row">
          <label className="field event-search">
            <span className="field-label"><Search size={16} aria-hidden="true" /><span className="sr-only">Search events by game</span></span>
            <input type="search" placeholder="Search by game" value={search} onChange={(change) => setSearch(change.target.value)} />
          </label>
          <div className="field event-view" role="group" aria-label="View">
            {Object.entries(VIEWS).map(([label, { Icon }]) => (
              <button key={label} className={view === label ? "on" : ""} aria-label={label} title={label} aria-pressed={view === label} onClick={() => pickView(label)}>
                <Icon size={17} />
              </button>
            ))}
          </div>
        </div>
        <div className="event-toolbar-row">
          <div className="segmented" role="group" aria-label="Kind">
            {Object.keys(KINDS).map((label) => (
              <button key={label} className={kind === label ? "on" : ""} aria-pressed={kind === label} onClick={() => setKind(label)}>{label}</button>
            ))}
          </div>
          <div className="event-menus">
            {reasonOptions.length > 0 && (
              <label className="field event-sort">
                <span className="field-label">Reason</span>
                <select value={reason} onChange={(change) => setReason(change.target.value)}>
                  <option>{ANY_REASON}</option>
                  {reasonOptions.map((tag) => <option key={tag} value={tag}>{tag} ({reasonCounts[tag]})</option>)}
                </select>
              </label>
            )}
            <label className="field event-sort">
              <span className="field-label">Sort</span>
              <select value={sort} onChange={(change) => setSort(change.target.value)}>
                {Object.keys(SORTS).map((label) => <option key={label}>{label}</option>)}
              </select>
            </label>
          </div>
        </div>
      </div>
      <div className="event-count" ref={countRef}>
        <p className="caption">
          {shown.length} {shown.length === 1 ? "event" : "events"}{pageCount > 1 && `, showing ${(page - 1) * pageSize + 1}–${(page - 1) * pageSize + visible.length}`}
          {year !== null && <button className="chip event-year-chip" onClick={() => setYear(null)} aria-label={`Remove the ${year} filter`}>{year}<X size={12} /></button>}
          {filtered && <button className="link-button" onClick={clearFilters}><X size={14} />Clear filters</button>}
        </p>
        {pageCount > 1 && <Pagination page={page} count={pageCount} onChange={goToPage} />}
      </div>
      <div className="event-list" ref={listRef}>
        {shown.length === 0 ? <p className="caption">No events match{query ? ` “${search}”` : " these filters"}.</p>
          : view === "Table" ? <EventTable events={visible} open={open} onToggle={toggle} focusKey={focusKey} />
          : visible.map((event) => <EventCard key={eventKey(event)} event={event} focused={focusKey === eventKey(event)} />)}
      </div>
      {pageCount > 1 && <Pagination page={page} count={pageCount} onChange={goToPage} className="bottom" />}
    </>
  );
}
