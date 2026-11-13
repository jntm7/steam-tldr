import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { KIND_COLORS } from "./EventList.jsx";
import { formatCount } from "../lib/games.js";
import { useSectionReveal } from "../lib/useSectionReveal.js";
import { useCleanChartTabindex } from "../lib/useCleanChartTabindex.js";
import { useWidth } from "../lib/useWidth.js";

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

// Year labels: one per ~48px of chart, stepping 1, 2, 5 or 10 years
const YEAR_PIXELS = 48;
const YEAR_STEPS = [1, 2, 5, 10];

// Axis titles: small muted caps, matching the chart labels above the charts
const AXIS_TITLE = { fill: "var(--muted)", fontSize: 10, letterSpacing: "0.1em" };

// Bubble chart of every event: when it happened, how far the score fell, sized by reviews and coloured by kind
export default function EventTimeline({ events }) {
  const { ref, go, animate } = useSectionReveal();
  useCleanChartTabindex(ref);
  const startYears = events.map((event) => new Date(event.start).getUTCFullYear());
  const first = Math.min(...startYears);
  const last = Math.max(...startYears) + 1;
  const years = Array.from({ length: last - first + 1 }, (_, i) => first + i);

  // Fewer year labels on narrow charts
  const width = useWidth(ref);
  const step = YEAR_STEPS.find((n) => years.length / n <= (width - 70) / YEAR_PIXELS) ?? YEAR_STEPS.at(-1);
  const ticks = years.filter((year) => year % step === 0 || year === first).map((year) => Date.UTC(year, 0, 1));
  const domain = [Date.UTC(first, 0, 1), Date.UTC(last, 0, 1)];

  return (
    <div className="chart" ref={ref}>
      <div className="chart-controls chart-toolbar legend-toolbar">
        <div className="chart-legend">
          {Object.entries(KIND_COLORS).map(([kind, color]) => <span key={kind}><i className="key-dot" style={{ background: color }} />{kind}</span>)}
          <span><i className="key-size" />Bigger = more reviews</span>
        </div>
      </div>
      <div className="chart-label">Score drop by start date</div>
      {!go ? <div style={{ height: 320 }} /> : (
      <ResponsiveContainer width="100%" height={320}>
        <ScatterChart accessibilityLayer={false} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
          <CartesianGrid horizontal={false} strokeDasharray="2 4" />
          <CartesianGrid vertical={false} />
          <XAxis type="number" dataKey="start" domain={domain} ticks={ticks} tickLine={{ stroke: "var(--border)" }} tickSize={5}
                 axisLine={{ stroke: "var(--border)" }} height={46} tick={{ fontSize: 11, fill: "var(--muted)" }} tickMargin={4}
                 tickFormatter={(time) => new Date(time).getUTCFullYear()}
                 label={{ value: "YEAR THE EVENT STARTED", position: "insideBottom", offset: 0, style: AXIS_TITLE }} />
          <YAxis type="number" dataKey="dropPoints" width={52} tick={{ fontSize: 11, fill: "var(--muted)" }} tickLine={false} axisLine={false}
                 label={{ value: "POINTS BELOW USUAL SCORE", angle: -90, position: "insideLeft", offset: 6, style: { ...AXIS_TITLE, textAnchor: "middle" } }} />
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
