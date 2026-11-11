import { useState } from "react";
import { Pause, Play } from "lucide-react";
import { CHART_COLOR, COMPLAINT_COLOR, formatCount, gameHref, monthName, scoreColor } from "../lib/games.js";
import { capitalize } from "../lib/themes.js";

// Score ring size and circumference
const RING = 34;
const CIRCUMFERENCE = 2 * Math.PI * RING;

// Steam's score as a ring that fills on each new game
function ScoreRing({ pct }) {
  return (
    <svg className="hero-ring" viewBox="0 0 80 80" width="80" height="80" role="img" aria-label={`${pct}% positive`}>
      <circle cx="40" cy="40" r={RING} className="hero-ring-track" />
      <circle cx="40" cy="40" r={RING} className="hero-ring-fill" stroke={scoreColor(pct)} strokeDasharray={CIRCUMFERENCE}
        style={{ "--ring-gap": CIRCUMFERENCE * (1 - pct / 100), "--ring-full": CIRCUMFERENCE }} />
      <text x="40" y="40" dominantBaseline="central" textAnchor="middle">{pct}%</text>
    </svg>
  );
}

// Theme rows with bars sized against the card's biggest theme
function ThemeBars({ title, themes, color, scale }) {
  return (
    <div className="hero-themes">
      <div className="hero-themes-title" style={{ color }}>{title}</div>
      {themes.map(({ theme, pct }, i) => (
        <div className="hero-theme" key={theme}>
          <div className="hero-theme-label"><span>{capitalize(theme)}</span><span>{pct}%</span></div>
          <div className="hero-bar"><div style={{ width: `${(100 * pct) / scale}%`, background: color, animationDelay: `${0.15 + i * 0.1}s` }} /></div>
        </div>
      ))}
    </div>
  );
}

// Monthly % positive as a small line that draws itself
function Sparkline({ values }) {
  const low = Math.max(0, Math.min(...values) - 5);
  const high = Math.min(100, Math.max(...values) + 5);
  const x = (i) => 2 + (396 * i) / (values.length - 1);
  const y = (value) => 44 - (40 * (value - low)) / (high - low || 1);
  const points = values.map((value, i) => `${x(i).toFixed(1)},${y(value).toFixed(1)}`).join(" ");
  return (
    <svg className="hero-spark" viewBox="0 0 400 48" width="400" height="48" aria-hidden="true">
      <polyline points={points} pathLength="1" stroke={CHART_COLOR} />
    </svg>
  );
}

// Live report card for the hero: one game at a time, moving on when the timer bar fills, paused on hover, focus or the pause button
export default function HeroReport({ cards }) {
  const [index, setIndex] = useState(0);
  const [hovered, setHovered] = useState(false);
  const [stopped, setStopped] = useState(false);
  const card = cards[index];
  const paused = hovered || stopped;
  const scale = Math.max(...card.praise.map((t) => t.pct), ...card.complaints.map((t) => t.pct));

  return (
    <div className={`hero-card${paused ? " paused" : ""}`} onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)} onBlur={() => setHovered(false)}>
      <div className="hero-card-body" key={card.appid}>
        {card.banner && <img className="hero-card-banner" src={card.banner} alt="" width="460" height="215" decoding="async" />}
        <div className="hero-card-head">
          <ScoreRing pct={card.pct} />
          <div className="hero-card-title">
            <div className="hero-card-name">{card.name}</div>
            <div className="hero-card-meta">
              <div style={{ color: scoreColor(card.pct) }}>{card.desc}</div>
              <div>{formatCount(card.total)} reviews</div>
            </div>
          </div>
        </div>
        <div className="hero-card-themes">
          <ThemeBars title="Players love" themes={card.praise} color={CHART_COLOR} scale={scale} />
          <ThemeBars title="Players complain about" themes={card.complaints} color={COMPLAINT_COLOR} scale={scale} />
        </div>
        <div className="hero-card-trend">
          <div className="hero-themes-title">Monthly % positive since {monthName(card.trendFrom)}</div>
          <Sparkline values={card.trend} />
        </div>
        <a className="hero-card-link" href={gameHref(card.appid)}>Open the full report <span aria-hidden="true">→</span></a>
      </div>
      <div className="hero-card-controls">
        <div className="hero-card-picks" role="group" aria-label="Example games">
          {cards.map((item, i) => (
            <button type="button" key={item.appid} aria-label={`Show ${item.name}`} aria-pressed={i === index} onClick={() => setIndex(i)}>
              <span className="hero-pick-fill" onAnimationEnd={() => setIndex((index + 1) % cards.length)}
                key={i === index ? `on-${index}` : "off"} />
            </button>
          ))}
        </div>
        <button type="button" className="hero-card-pause" onClick={() => setStopped(!stopped)}
          aria-label={stopped ? "Play the examples" : "Pause the examples"} title={stopped ? "Play" : "Pause"}>
          {stopped ? <Play size={14} /> : <Pause size={14} />}
        </button>
      </div>
    </div>
  );
}
