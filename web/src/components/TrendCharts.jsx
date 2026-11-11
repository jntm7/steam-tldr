import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CHART_COLOR, COMPLAINT_COLOR, formatCount, monthName } from "../lib/games.js";
import { useSectionReveal } from "../lib/useSectionReveal.js";

// Range choices as label -> points shown (the last point is the last 30 days)
const RANGES = { "All time": null, "Last 2 years": 25, "Last 12 months": 13 };

// Short axis numbers such as 12K
const compact = new Intl.NumberFormat("en", { notation: "compact" });

// Months between ticks, so labels never crowd
const tickStep = (count) => (count <= 13 ? 2 : count <= 36 ? 3 : count <= 72 ? 6 : 12);

// Hover card: the month, its score, review count and flag
function TrendTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="tooltip-title">{monthName(point.label)}</div>
      <div><strong>{Math.round(point.pct)}%</strong> positive</div>
      <div><strong>{formatCount(point.reviews)}</strong> reviews</div>
      {point.flag && <div className="tooltip-flag">{point.flag}</div>}
    </div>
  );
}

// Red dot with a ring on flagged months, nothing elsewhere
function FlagDot({ cx, cy, payload }) {
  if (!payload.flag) return <g key={payload.label} />;
  return <circle key={payload.label} cx={cx} cy={cy} r={6} fill={COMPLAINT_COLOR} style={{ stroke: "var(--bg)" }} strokeWidth={2} />;
}

// Monthly percent positive with flagged months marked, and monthly review counts below; hovering either shows the top chart's tooltip
export default function TrendCharts({ points, overall }) {
  const [range, setRange] = useState("All time");
  const { ref, go, animate } = useSectionReveal();
  const shown = RANGES[range] ? points.slice(-RANGES[range]) : points;

  const step = tickStep(shown.length);
  const ticks = shown.map((point) => point.label).filter((label) => /^\d{4}-\d{2}$/.test(label) && (Number(label.slice(5)) - 1) % step === 0);
  const xAxis = {
    dataKey: "label", ticks, interval: "preserveStartEnd", tickLine: false, axisLine: false, minTickGap: 12,
    tickFormatter: (label) => (step === 12 ? label.slice(0, 4) : monthName(label)),
  };
  const margin = { top: 8, right: 8, bottom: 0, left: 0 };

  return (
    <div className="chart" ref={ref}>
      <div className="chart-controls">
        <div className="segmented" role="group" aria-label="Range">
          {Object.keys(RANGES).map((label) => (
            <button key={label} className={range === label ? "on" : ""} aria-pressed={range === label} onClick={() => setRange(label)}>{label}</button>
          ))}
        </div>
        <div className="chart-legend">
          <span><i className="key-line" />Monthly % positive</span>
          <span><i className="key-dot" />Flagged month</span>
          <span><i className="key-dash" />All-time score ({Math.round(overall)}%)</span>
        </div>
      </div>

      {!go ? <div style={{ height: 420 }} /> : (
      <>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={shown} syncId="trend" margin={margin}>
          <CartesianGrid vertical={false} />
          <XAxis {...xAxis} />
          <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(value) => `${value}%`} width={52} tickLine={false} axisLine={false} />
          <ReferenceLine y={overall} strokeDasharray="4 4" className="chart-reference" />
          <Tooltip content={<TrendTooltip />} cursor={{ className: "chart-cursor" }} />
          <Line dataKey="pct" stroke={CHART_COLOR} strokeWidth={2} dot={FlagDot} activeDot={{ r: 5, fill: CHART_COLOR }} isAnimationActive={animate} animationDuration={1500} animationEasing="ease-out" />
        </LineChart>
      </ResponsiveContainer>

      <ResponsiveContainer width="100%" height={130}>
        <BarChart data={shown} syncId="trend" margin={margin}>
          <CartesianGrid vertical={false} />
          <XAxis {...xAxis} />
          <YAxis tickFormatter={(value) => compact.format(value)} width={52} tickLine={false} axisLine={false} />
          <Tooltip content={() => null} cursor={{ className: "chart-band" }} />
          <Bar dataKey="reviews" fill={CHART_COLOR} radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={animate} animationDuration={1100} animationEasing="ease-out" />
        </BarChart>
      </ResponsiveContainer>
      </>
      )}
    </div>
  );
}
