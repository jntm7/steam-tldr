// Accent colours shared with the Streamlit app
export const PRAISE_COLOR = "#4c9be8";
export const COMPLAINT_COLOR = "#e05d5d";
export const MIXED_COLOR = "#c99a2e";

// Chart mark colour, the logo blue, which passes contrast checks on both themes
export const CHART_COLOR = "#3d8fd1";

// A game's name without trademark symbols
export const gameName = (game) => (game.name ?? `App ${game.appid}`).replace(/[™®]/g, "").trim();

// Steam's percent positive, or null with no reviews
export function steamPct(game) {
  const { total_positive = 0, total_negative = 0 } = game.summary ?? {};
  const total = total_positive + total_negative;
  return total ? (100 * total_positive) / total : null;
}

// Steam's colour bands: positive from 70%, mixed from 40%, negative below
export const scoreColor = (pct) => (pct >= 70 ? PRAISE_COLOR : pct >= 40 ? MIXED_COLOR : COMPLAINT_COLOR);

// Address of a game's page
export const gameHref = (appid) => `/game/${appid}/`;

// Browser storage key holding the app IDs of the games opened most recently, newest first
export const RECENT_KEY = "steamtldr_recent";
export const MAX_RECENT = 8;

// A whole number with thousands separators
export const formatCount = (number) => number.toLocaleString("en");

// Month names for dates and chart axes
export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// A trend label such as "2015-05" as "May 2015", and the last 30 days point by name
export const monthName = (label) =>
  /^\d{4}-\d{2}$/.test(label) ? `${MONTHS[Number(label.slice(5)) - 1]} ${label.slice(0, 4)}` : "Last 30 days";

// A run of months: "Aug 2017", "Aug–Sep 2017" within one year, else "Dec 2024 to Jan 2025"
export function monthRange(first, last) {
  if (first === last) return monthName(first);
  const sameYear = /^\d{4}-\d{2}$/.test(last) && first.slice(0, 4) === last.slice(0, 4);
  return sameYear ? `${MONTHS[Number(first.slice(5)) - 1]}–${monthName(last)}` : `${monthName(first)} to ${monthName(last)}`;
}

// Steam's and our own date strings as "Aug 12, 2012", or unchanged when there's no full date such as "Coming soon"
export function formatDate(text) {
  const dayFirst = text?.match(/^(\d{1,2}) ([A-Za-z]{3})[a-z]*,? (\d{4})$/);
  const monthFirst = text?.match(/^([A-Za-z]{3})[a-z]*\.? (\d{1,2}),? (\d{4})$/);
  const iso = text?.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (dayFirst) return `${dayFirst[2]} ${Number(dayFirst[1])}, ${dayFirst[3]}`;
  if (monthFirst) return `${monthFirst[1]} ${Number(monthFirst[2])}, ${monthFirst[3]}`;
  if (iso) return `${MONTHS[iso[2] - 1]} ${Number(iso[3])}, ${iso[1]}`;
  return text || "Unknown";
}

// A date as a UTC timestamp for sorting, from Steam's day-first, month-first or ISO strings; 0 when unknown
export function dateValue(text) {
  const dayFirst = text?.match(/^(\d{1,2}) ([A-Za-z]{3})[a-z]*,? (\d{4})$/);
  const monthFirst = text?.match(/^([A-Za-z]{3})[a-z]*\.? (\d{1,2}),? (\d{4})$/);
  const iso = text?.match(/^(\d{4})-(\d{2})-(\d{2})/);
  const [year, month, day] = dayFirst ? [dayFirst[3], dayFirst[2], dayFirst[1]]
    : monthFirst ? [monthFirst[3], monthFirst[1], monthFirst[2]]
    : iso ? [iso[1], MONTHS[Number(iso[2]) - 1], iso[3]] : [];
  const monthIndex = MONTHS.indexOf(month);
  return monthIndex === -1 || !day ? 0 : Date.UTC(Number(year), monthIndex, Number(day));
}

// A table saved as {columns, data} turned into one object per row
export const tableRows = (table) =>
  (table?.data ?? []).map((row) => Object.fromEntries(table.columns.map((column, i) => [column, row[i]])));
