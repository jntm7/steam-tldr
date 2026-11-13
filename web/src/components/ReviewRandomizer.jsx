import { useEffect, useMemo, useState } from "react";
import { Shuffle, ThumbsDown, ThumbsUp } from "lucide-react";
import { COMPLAINT_COLOR, MONTHS, PRAISE_COLOR, formatCount } from "../lib/games.js";

// Filter choices as label -> which reviews pass
const KINDS = {
  Any: () => true,
  Positive: (review) => review.voted_up,
  Negative: (review) => !review.voted_up,
};

// Age choices: new means written in the last year
const YEAR_MS = 365 * 24 * 60 * 60 * 1000;
const AGES = {
  "Any age": () => true,
  New: (review, cutoff) => Date.parse(review.created) >= cutoff,
  Old: (review, cutoff) => Date.parse(review.created) < cutoff,
};

// A random position in a list, different from the current one when there's a choice
function randomIndex(length, current = -1) {
  let next = Math.floor(Math.random() * length);
  while (length > 1 && next === current) next = Math.floor(Math.random() * length);
  return next;
}

// Playtime as a short bar on a log scale: 1 hour is a sliver, 1,000 hours is full
const playtimeShare = (hours) => Math.min(1, Math.log10(hours + 1) / 3);

// A review as a large pull-quote with its verdict, playtime bar and month; it animates in when the review changes
function ReviewCard({ review }) {
  const Icon = review.voted_up ? ThumbsUp : ThumbsDown;
  const color = review.voted_up ? PRAISE_COLOR : COMPLAINT_COLOR;
  const hours = review.playtime_at_review_h;
  const created = new Date(review.created);
  const long = review.review.split(/\s+/).length > 60;
  return (
    <figure className="review-stage" style={{ "--verdict": color }}>
      <blockquote className={`review-quote${long ? " long" : ""}`}>{review.review}</blockquote>
      <figcaption className="review-foot">
        <span className="review-verdict"><Icon aria-hidden="true" />{review.voted_up ? "Recommended" : "Not recommended"}</span>
        <span className="review-hours">
          <span className="review-hours-track" aria-hidden="true"><i style={{ width: `${(100 * playtimeShare(hours)).toFixed(0)}%` }} /></span>
          {hours < 10 ? hours.toFixed(1) : formatCount(Math.round(hours))} h played
        </span>
        <span className="review-date">{MONTHS[created.getUTCMonth()]} {created.getUTCFullYear()}</span>
      </figcaption>
    </figure>
  );
}

// One random review from the sample, kept until the reader asks for another
export default function ReviewRandomizer({ reviews }) {
  const [kind, setKind] = useState("Any");
  const [age, setAge] = useState("Any age");
  const [pick, setPick] = useState(0);
  const [turns, setTurns] = useState(0);
  const cutoff = useMemo(() => Date.now() - YEAR_MS, []);
  const pool = reviews.filter((review) => KINDS[kind](review) && AGES[age](review, cutoff));

  useEffect(() => setPick(randomIndex(pool.length)), [kind, age]);

  return (
    <div>
      <div className="review-toolbar chart-toolbar">
        <div className="segmented" role="group" aria-label="Kind of review">
          {Object.keys(KINDS).map((label) => (
            <button key={label} className={kind === label ? "on" : ""} aria-pressed={kind === label} onClick={() => setKind(label)}>{label}</button>
          ))}
        </div>
        <div className="segmented" role="group" aria-label="Age of review">
          {Object.keys(AGES).map((label) => (
            <button key={label} className={age === label ? "on" : ""} aria-pressed={age === label} onClick={() => setAge(label)}>{label}</button>
          ))}
        </div>
        <button className="review-another" onClick={() => { setPick(randomIndex(pool.length, pick)); setTurns((n) => n + 1); }} disabled={pool.length < 2}>
          <Shuffle style={{ transform: `rotate(${turns * 180}deg)`, transition: "transform 0.5s ease" }} />Another one
        </button>
      </div>
      {pool.length === 0 ? <p className="caption">No reviews match these filters in the sample.</p> : <ReviewCard key={`${kind}-${pick}`} review={pool[pick] ?? pool[0]} />}
    </div>
  );
}
