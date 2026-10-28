"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const GRID = "#2a2a30";
const AXIS = "#8b8b95";
const SLICES = ["#d9d9df", "#b2b2ba", "#8c8c95", "#6a6a72", "#4d4d54", "#35353b"];

const tooltipStyle = {
  background: "#141418",
  border: "1px solid #2a2a30",
  borderRadius: "8px",
  boxShadow: "0 12px 32px -12px rgba(0,0,0,0.9)",
} as const;

export function AgentCostChart({
  data,
}: {
  data: { agent_name: string; cost_usd: number; total_tokens: number }[];
}) {
  if (!data?.length) return null;
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: 8, right: 8, top: 8, bottom: 48 }}>
          <defs>
            <linearGradient id="barMatte" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f4f4f6" stopOpacity={0.95} />
              <stop offset="100%" stopColor="#f4f4f6" stopOpacity={0.35} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="agent_name"
            tick={{ fill: AXIS, fontSize: 11 }}
            angle={-25}
            textAnchor="end"
            height={60}
            stroke={GRID}
          />
          <YAxis tick={{ fill: AXIS, fontSize: 11 }} stroke={GRID} />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.05)" }}
            contentStyle={tooltipStyle}
            labelStyle={{ color: "#f4f4f6" }}
            itemStyle={{ color: "#c8c8d0" }}
          />
          <Bar
            dataKey="cost_usd"
            fill="url(#barMatte)"
            name="Cost USD"
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ModelMixChart({ data }: { data: { model: string; cost_usd: number }[] }) {
  if (!data?.length) return null;
  const total = data.reduce((sum, d) => sum + (d.cost_usd || 0), 0);
  return (
    <div className="flex h-64 w-full items-center gap-4">
      <div className="h-full min-w-0 flex-1">
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={data}
              dataKey="cost_usd"
              nameKey="model"
              outerRadius={92}
              innerRadius={52}
              paddingAngle={data.length > 1 ? 1.5 : 0}
              stroke="#08080a"
              strokeWidth={2}
              label={false}
              isAnimationActive={false}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={SLICES[i % SLICES.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: "#f4f4f6" }}
              itemStyle={{ color: "#c8c8d0" }}
              formatter={(v: number) => `$${Number(v).toFixed(6)}`}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="w-40 shrink-0 space-y-2 text-xs">
        {data.map((d, i) => (
          <li key={d.model} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-sm"
              style={{ background: SLICES[i % SLICES.length] }}
            />
            <span className="min-w-0 flex-1 truncate font-mono text-paper" title={d.model}>
              {d.model}
            </span>
            <span className="font-mono text-mist">
              {total ? `${Math.round((d.cost_usd / total) * 100)}%` : "0%"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
