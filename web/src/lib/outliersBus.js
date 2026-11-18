// Messages between the Outliers page's islands: the timeline and the overview's year columns tell the event list what to show

// A bubble was picked: detail is the event's key
export const FOCUS_EVENT = "outliers:focus";

// A year column was picked: detail is the year
export const YEAR_EVENT = "outliers:year";

// One event's key, unique across games
export const eventKey = (event) => `${event.appid}-${event.start}`;

// Tell the list to show something
export const sendToList = (name, detail) => window.dispatchEvent(new CustomEvent(name, { detail }));
