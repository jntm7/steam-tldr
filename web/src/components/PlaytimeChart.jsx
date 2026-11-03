import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CHART_COLOR, formatCount } from "../lib/games.js";

// Playtime groups as shown on the chart
const LABELS = { "<2h": "Under 2 hours", "2-10h": "2 to 10 hours", "10-50h": "10 to 50 hours", "50h+": "50+ hours" };

// Axis label: the group, with its review count underneath
function GroupTick({ x, y, payload, groups }) {
  const group = groups.find((row) => row.group === payload.value);
  return (
    <text x={x} y={y + 14} textAnchor="middle" className="chart-tick">
      <tspan x={x} className="chart-tick-strong">{LABELS[payload.value] ?? payload.value}</tspan>
      <tspan x={x} dy={18}>{formatCount(group.reviews)} reviews</tspan>
    </text>
  );
}

// Hover card: the group, its score and review count
function PlaytimeTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="tooltip-title">{LABELS[row.group] ?? row.group} played</div>
      <div><strong>{Math.round(row.pct_positive)}%</strong> positive</div>
      <div><strong>{formatCount(row.reviews)}</strong> reviews</div>
    </div>
  );
}

// Percent positive by playtime group, labelled at each bar's top
export default function PlaytimeChart({ groups }) {
  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={groups} margin={{ top: 24, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="group" tickLine={false} axisLine={false} height={48} interval={0} tick={<GroupTick groups={groups} />} />
          <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(value) => `${value}%`} width={52} tickLine={false} axisLine={false} />
          <Tooltip content={<PlaytimeTooltip />} cursor={{ className: "chart-band" }} />
          <Bar dataKey="pct_positive" fill={CHART_COLOR} radius={[4, 4, 0, 0]} maxBarSize={40} isAnimationActive={false}>
            <LabelList dataKey="pct_positive" position="top" offset={8} className="chart-value" formatter={(value) => `${Math.round(value)}%`} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
