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
import type { Platform, WeeklyRate } from '@/data/prototype'
import { formatRate, formatWeek } from '@/lib/format'

const SERIES: { key: Platform; label: string; color: string }[] = [
  { key: 'web', label: 'Web', color: 'var(--series-web)' },
  { key: 'ios', label: 'iOS', color: 'var(--series-ios)' },
  { key: 'android', label: 'Android', color: 'var(--series-android)' },
]

function ChartTooltip({ active, payload, label }: TooltipContentProps<ValueType, NameType>) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 font-medium">Signups week of {formatWeek(String(label))}</div>
      {SERIES.map((s) => {
        const p = payload.find((x) => x.dataKey === s.key)
        return (
          <div key={s.key} className="flex items-center justify-between gap-6 tabular-nums">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="inline-block h-0.5 w-3 rounded" style={{ background: s.color }} />
              {s.label}
            </span>
            <span>{p ? formatRate(Number(p.value)) : '–'}</span>
          </div>
        )
      })}
    </div>
  )
}

interface EndLabelProps {
  x?: number
  y?: number
  index?: number
  text: string
  last: number
}

function EndLabel({ x, y, index, text, last }: EndLabelProps) {
  if (index !== last || x === undefined || y === undefined) return null
  return (
    <text x={x + 8} y={y} dy={4} fontSize={12} fill="var(--foreground)">
      {text}
    </text>
  )
}

export function ActivationChart({
  data,
  marker,
}: {
  data: WeeklyRate[]
  marker?: { week: string; label: string }
}) {
  const [showTable, setShowTable] = useState(false)
  const last = data.length - 1
  return (
    <figure className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <figcaption className="text-sm">
          <span className="font-medium">Activation rate by signup platform</span>
          <span className="text-muted-foreground"> · weekly signup cohorts, 7-day window</span>
        </figcaption>
        <div className="flex items-center gap-4">
          <ul className="flex gap-3 text-xs text-muted-foreground" aria-label="Legend">
            {SERIES.map((s) => (
              <li key={s.key} className="flex items-center gap-1.5">
                <span className="inline-block h-0.5 w-4 rounded" style={{ background: s.color }} />
                {s.label}
              </li>
            ))}
          </ul>
          <Button variant="ghost" size="sm" onClick={() => setShowTable((v) => !v)}>
            {showTable ? 'Show chart' : 'Show table'}
          </Button>
        </div>
      </div>
      {showTable ? (
        <table className="w-full text-sm tabular-nums">
          <thead>
            <tr className="border-b border-border text-left text-muted-foreground">
              <th className="py-1.5 font-medium">Signup week</th>
              {SERIES.map((s) => (
                <th key={s.key} className="py-1.5 text-right font-medium">
                  {s.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.week} className="border-b border-border/60 last:border-0">
                <td className="py-1.5">{formatWeek(d.week)}</td>
                {SERIES.map((s) => (
                  <td key={s.key} className="py-1.5 text-right">
                    {formatRate(d[s.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="h-64 w-full" role="img" aria-label="Line chart of weekly activation rate by platform; iOS drops from about 38% to about 23% in the week of the iOS 4.12 release while web and Android stay flat.">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 16, right: 64, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey="week"
                tickFormatter={formatWeek}
                tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--border)' }}
              />
              <YAxis
                domain={[0.2, 0.45]}
                ticks={[0.2, 0.25, 0.3, 0.35, 0.4, 0.45]}
                tickFormatter={(v: number) => formatRate(v, 0)}
                tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
                tickLine={false}
                axisLine={false}
                width={44}
              />
              {marker && (
                <ReferenceLine
                  x={marker.week}
                  stroke="var(--muted-foreground)"
                  strokeDasharray="3 3"
                  label={{
                    value: marker.label,
                    position: 'insideTopLeft',
                    fontSize: 12,
                    fill: 'var(--muted-foreground)',
                  }}
                />
              )}
              <Tooltip content={ChartTooltip} cursor={{ stroke: 'var(--border)' }} />
              {SERIES.map((s) => (
                <Line
                  key={s.key}
                  dataKey={s.key}
                  stroke={s.color}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: 'var(--paper)' }}
                  isAnimationActive={false}
                  label={<EndLabel text={s.label} last={last} />}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </figure>
  )
}
