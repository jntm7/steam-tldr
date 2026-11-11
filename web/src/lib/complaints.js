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
