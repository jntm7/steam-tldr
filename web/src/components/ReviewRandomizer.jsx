import { useEffect, useState } from "react";
import { Dices, ThumbsDown, ThumbsUp } from "lucide-react";
import { COMPLAINT_COLOR, MONTHS, PRAISE_COLOR, formatCount } from "../lib/games.js";

// Filter choices as label -> which reviews pass
const KINDS = {
  Any: () => true,
  Positive: (review) => review.voted_up,
  Negative: (review) => !review.voted_up,
};

// A random position in a list, different from the current one when there's a choice
function randomIndex(length, current = -1) {
  let next = Math.floor(Math.random() * length);
  while (length > 1 && next === current) next = Math.floor(Math.random() * length);
  return next;
}

// A review card with its verdict, playtime and month
function ReviewCard({ review }) {
  const Icon = review.voted_up ? ThumbsUp : ThumbsDown;
  const hours = review.playtime_at_review_h;
  const created = new Date(review.created);
  return (
    <div className="review-card">
      <div className="review-meta">
        <Icon size={18} color={review.voted_up ? PRAISE_COLOR : COMPLAINT_COLOR} />
        <span>
          <strong>{review.voted_up ? "Recommended" : "Not recommended"}</strong> · {hours < 10 ? hours.toFixed(1) : formatCount(Math.round(hours))} h played
          · {MONTHS[created.getUTCMonth()]} {created.getUTCFullYear()}
        </span>
      </div>
      <div className="review-text">{review.review}</div>
    </div>
  );
}

// One random review from the sample, kept until the reader asks for another
export default function ReviewRandomizer({ reviews }) {
  const [kind, setKind] = useState("Any");
  const [pick, setPick] = useState(0);
  const pool = reviews.filter(KINDS[kind]);

  useEffect(() => setPick(randomIndex(pool.length)), [kind]);

  return (
    <div>
      <div className="chart-controls">
        <div className="segmented" role="group" aria-label="Kind of review">
          {Object.keys(KINDS).map((label) => (
            <button key={label} className={kind === label ? "on" : ""} aria-pressed={kind === label} onClick={() => setKind(label)}>{label}</button>
          ))}
        </div>
        <button className="button small" onClick={() => setPick(randomIndex(pool.length, pick))} disabled={pool.length < 2}>
          <Dices />Another one
        </button>
      </div>
      {pool.length === 0 ? <p className="caption">No reviews of this kind in the sample.</p> : <ReviewCard review={pool[pick] ?? pool[0]} />}
    </div>
  );
}
