import { useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from 'recharts'
import type { NameType, ValueType } from 'recharts/types/component/DefaultTooltipContent'
import { Button } from '@/components/ui/button'
import { formatCount, formatRate, formatWeek } from '@/lib/format'

export interface Series {
  key: string
  label: string
  color: string
}
export type Point = { period: string } & Record<string, number | string | null>

// Categorical slots validated for light and dark (dataviz palette, first three all-pairs safe).
export const SERIES_COLORS = ['var(--series-web)', 'var(--series-ios)', 'var(--series-android)']

interface Props {
  title: string
  subtitle?: string
  data: Point[]
  series: Series[]
  isRate: boolean
  marker?: { period: string; label: string }
  height?: number
}

export function TrendChart({ title, subtitle, data, series, isRate, marker, height = 256 }: Props) {
  const [table, setTable] = useState(false)
  const fmt = (v: number) => (isRate ? formatRate(v) : formatCount(Math.round(v)))
  const last = data.length - 1
  const values = data.flatMap((d) => series.map((s) => d[s.key])).filter((v): v is number => typeof v === 'number')
  const lo = values.length ? Math.min(...values) : 0
  const hi = values.length ? Math.max(...values) : 1
  const { domain, ticks } = niceScale(lo, hi)

  function Tip({ active, payload, label }: TooltipContentProps<ValueType, NameType>) {
    if (!active || !payload?.length) return null
    return (
      <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-sm">
        <div className="mb-1 font-medium">Week of {formatWeek(String(label))}</div>
        {series.map((s) => {
          const p = payload.find((x) => x.dataKey === s.key)
          return (
            <div key={s.key} className="flex items-center justify-between gap-6 tabular-nums">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span className="inline-block h-0.5 w-3 rounded" style={{ background: s.color }} />
                {s.label}
              </span>
              <span>{p && typeof p.value === 'number' ? fmt(p.value) : '–'}</span>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <figure className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <figcaption className="text-sm">
          <span className="font-medium">{title}</span>
          {subtitle && <span className="text-muted-foreground"> · {subtitle}</span>}
        </figcaption>
        <div className="flex items-center gap-4">
          {series.length > 1 && (
            <ul className="flex gap-3 text-xs text-muted-foreground" aria-label="Legend">
              {series.map((s) => (
                <li key={s.key} className="flex items-center gap-1.5">
                  <span className="inline-block h-0.5 w-4 rounded" style={{ background: s.color }} />
                  {s.label}
                </li>
              ))}
            </ul>
          )}
          <Button variant="ghost" size="sm" onClick={() => setTable((v) => !v)}>
            {table ? 'Show chart' : 'Show table'}
          </Button>
        </div>
      </div>
      {table ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm tabular-nums">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="py-1.5 font-medium">Week</th>
                {series.map((s) => (
                  <th key={s.key} className="py-1.5 pl-4 text-right font-medium">
                    {s.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.period} className="border-b border-border/60 last:border-0">
                  <td className="py-1.5">{formatWeek(d.period)}</td>
                  {series.map((s) => (
                    <td key={s.key} className="py-1.5 pl-4 text-right">
                      {typeof d[s.key] === 'number' ? fmt(d[s.key] as number) : '–'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="w-full" style={{ height }} role="img" aria-label={`${title}, line chart. Use "Show table" for the values.`}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 16, right: series.length > 1 ? 72 : 16, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey="period"
                tickFormatter={formatWeek}
                tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--border)' }}
                minTickGap={24}
              />
              <YAxis
                domain={domain}
                ticks={ticks}
                tickFormatter={(v: number) =>
                  isRate ? formatRate(v, ticks.length > 1 && ticks[1] - ticks[0] < 0.01 ? 1 : 0) : formatCount(Math.round(v))
                }
                tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
                tickLine={false}
                axisLine={false}
                width={52}
              />
              {marker && (
                <ReferenceLine
                  x={marker.period}
                  stroke="var(--muted-foreground)"
                  strokeDasharray="3 3"
                  label={{ value: marker.label, position: 'insideTopLeft', fontSize: 12, fill: 'var(--muted-foreground)' }}
                />
              )}
              <Tooltip content={Tip} cursor={{ stroke: 'var(--border)' }} />
              {series.map((s) => (
                <Line
                  key={s.key}
                  dataKey={s.key}
                  stroke={s.color}
                  strokeWidth={2}
                  dot={false}
                  connectNulls={false}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: 'var(--paper)' }}
                  isAnimationActive={false}
                  label={
                    series.length > 1
                      ? ({ x, y, index }: { x?: number | string; y?: number | string; index?: number }) =>
                          index === last && typeof x === 'number' && typeof y === 'number' ? (
                            <text x={x + 8} y={y} dy={4} fontSize={12} fill="var(--foreground)">
                              {s.label}
                            </text>
                          ) : null
                      : undefined
                  }
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </figure>
  )
}

/** Turn metric rows grouped by segment into chart points; incomplete periods are dropped. */
export function toPoints(rows: { period: string; segment: string | null; value: number | null; complete: boolean }[]): Point[] {
  const byPeriod = new Map<string, Point>()
  for (const r of rows) {
    if (!r.complete) continue
    const p: Point = byPeriod.get(r.period) ?? { period: r.period }
    p[r.segment ?? 'all'] = r.value
    byPeriod.set(r.period, p)
  }
  return [...byPeriod.values()].sort((a, b) => a.period.localeCompare(b.period))
}

/** Round axis bounds and ticks to 1, 2, 2.5 or 5 times a power of ten (about four steps). */
export function niceScale(lo: number, hi: number): { domain: [number, number]; ticks: number[] } {
  if (hi <= lo) hi = lo + (lo === 0 ? 1 : Math.abs(lo) * 0.1)
  const raw = (hi - lo) / 4
  const power = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * power).find((x) => x >= raw) ?? 10 * power
  const start = Math.max(0, Math.floor(lo / step) * step)
  const end = Math.ceil(hi / step) * step
  const ticks: number[] = []
  for (let v = start; v <= end + step / 2; v += step) ticks.push(Number(v.toFixed(10)))
  return { domain: [start, end], ticks }
}
