// A theme counts as changed when its share moves by this many points
const CHANGE_POINTS = 3;
// A theme is new when it was rare overall but now shows up in this share of reviews
const NEW_OVERALL_MAX = 3;
const NEW_RECENT_MIN = 5;

// How one theme's recent share compares with its all-time share
export function complaintChange(row) {
  const delta = row.pct - row.all_time_pct;
  if (row.all_time_pct < NEW_OVERALL_MAX && row.pct >= NEW_RECENT_MIN) return { delta, status: "new", label: "New" };
  if (delta >= CHANGE_POINTS) return { delta, status: "rising", label: "Rising" };
  if (delta <= -CHANGE_POINTS) return { delta, status: "fading", label: "Fading" };
  return { delta, status: "steady", label: "Steady" };
}

// One plain sentence on the biggest rise and the biggest fall, e.g. "Complaints about cheaters are up from 39% to 44%"
export function complaintVerdict(rows) {
  const changes = rows.map((row) => ({ row, ...complaintChange(row) }));
  const risers = changes.filter((c) => c.status === "new" || c.status === "rising").sort((a, b) => b.delta - a.delta);
  const fallers = changes.filter((c) => c.status === "fading").sort((a, b) => a.delta - b.delta);
  const say = (c, word) => `complaints about ${c.row.theme} are ${word} from ${Math.round(c.row.all_time_pct)}% to ${Math.round(c.row.pct)}%`;
  const parts = [risers[0] && say(risers[0], "up"), fallers[0] && say(fallers[0], "down")].filter(Boolean);
  if (parts.length === 0) return "Complaints look about the same as usual.";
  const sentence = parts.join(", while ");
  return sentence[0].toUpperCase() + sentence.slice(1) + ".";
}
