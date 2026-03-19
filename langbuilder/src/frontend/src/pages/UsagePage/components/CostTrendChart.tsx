import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { DailyCost } from "@/types/usage";

interface CostTrendChartProps {
  dailyCosts?: DailyCost[];
  truncated?: boolean;
}

export function CostTrendChart({ dailyCosts, truncated }: CostTrendChartProps) {
  if (!dailyCosts || dailyCosts.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-lg border-2 border-dashed border-gray-200 p-8 text-sm text-gray-400">
        No trend data available
      </div>
    );
  }

  return (
    <div>
      {truncated && (
        <div className="mb-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
          Data may be incomplete — showing up to 10,000 traces
        </div>
      )}
      <div aria-label="Daily cost trend">
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={dailyCosts}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(d: string) =>
                new Date(d + "T00:00:00").toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })
              }
              tick={{ fontSize: 11 }}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={(v: number) => `$${v.toFixed(2)}`}
              tick={{ fontSize: 11 }}
              width={60}
            />
            <Tooltip
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(value: any) => [
                `$${Number(value).toFixed(4)}`,
                "Cost",
              ]}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              labelFormatter={(label: any) =>
                new Date(String(label) + "T00:00:00").toLocaleDateString(undefined, {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })
              }
            />
            <Area
              type="monotone"
              dataKey="cost_usd"
              stroke="#6366f1"
              fill="#6366f1"
              fillOpacity={0.1}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
