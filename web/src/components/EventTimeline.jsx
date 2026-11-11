import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { KIND_COLORS } from "./EventList.jsx";
import { formatCount } from "../lib/games.js";
import { useSectionReveal } from "../lib/useSectionReveal.js";
import { useCleanChartTabindex } from "../lib/useCleanChartTabindex.js";

// Hover card: the game, kind, when, size and score against the usual
function EventTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const event = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div><strong>{event.game}</strong></div>
      <div className="tooltip-title">{event.kind} · {event.when}</div>
      <div><strong>{formatCount(event.reviews)}</strong> reviews</div>
      {event.kind === "Negative surge" && <div><strong>+{formatCount(event.extraNegatives)}</strong> extra negatives</div>}
      <div><strong>{event.pct.toFixed(0)}%</strong> positive vs a usual <strong>{event.usualPct.toFixed(0)}%</strong></div>
    </div>
  );
}

// Bubble chart of every event: when it happened, how far the score fell, sized by reviews and coloured by kind
export default function EventTimeline({ events }) {
  const { ref, go, animate } = useSectionReveal();
  useCleanChartTabindex(ref);
  const years = events.map((event) => new Date(event.start).getUTCFullYear());
  const first = Math.min(...years);
  const last = Math.max(...years) + 1;
  const ticks = Array.from({ length: last - first + 1 }, (_, i) => Date.UTC(first + i, 0, 1));

  return (
    <div className="chart" ref={ref}>
      <div className="chart-controls">
        <div className="chart-legend">
          {Object.entries(KIND_COLORS).map(([kind, color]) => <span key={kind}><i className="key-dot" style={{ background: color }} />{kind}</span>)}
        </div>
      </div>
      {!go ? <div style={{ height: 320 }} /> : (
      <ResponsiveContainer width="100%" height={320}>
        <ScatterChart accessibilityLayer={false} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis type="number" dataKey="start" domain={[ticks[0], ticks.at(-1)]} ticks={ticks} tickLine={false} axisLine={false}
                 tickFormatter={(time) => new Date(time).getUTCFullYear()} />
          <YAxis type="number" dataKey="dropPoints" tickFormatter={(value) => `${value} pts`} width={60} tickLine={false} axisLine={false} />
          <ZAxis type="number" dataKey="reviews" range={[60, 900]} />
          <Tooltip content={<EventTooltip />} cursor={{ strokeDasharray: "3 3" }} />
          {Object.entries(KIND_COLORS).map(([kind, color]) => (
            <Scatter key={kind} data={events.filter((event) => event.kind === kind)} fill={color} fillOpacity={0.7} isAnimationActive={animate} animationDuration={1000} />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
      )}
    </div>
  );
}
