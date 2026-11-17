import type { Comparison } from '@/lib/api'
import { formatPp } from '@/lib/format'

/** Difference with its 95% and 90% intervals, against zero and the ±MDE band (in pp). */
export function IntervalPlot({ c, mde }: { c: Comparison; mde: number }) {
  const pp = (v: number) => v * 100
  const lo = Math.min(pp(c.ci95[0]), -pp(mde) * 1.4)
  const hi = Math.max(pp(c.ci95[1]), pp(mde) * 1.4)
  const w = 560
  const x = (v: number) => 16 + ((v - lo) / (hi - lo)) * (w - 32)
  const label = `Difference ${formatPp(c.diff)}, 95% interval ${formatPp(c.ci95[0])} to ${formatPp(c.ci95[1])}; minimum detectable effect ±${(mde * 100).toFixed(1)} pp.`
  return (
    <svg viewBox={`0 0 ${w} 84`} className="w-full max-w-xl" role="img" aria-label={label}>
      <rect x={x(-pp(mde))} y={14} width={x(pp(mde)) - x(-pp(mde))} height={40} fill="var(--muted)" rx={4} />
      <text x={x(pp(mde))} y={10} textAnchor="end" fontSize={11} fill="var(--muted-foreground)">
        ±MDE ({(mde * 100).toFixed(1)} pp)
      </text>
      <line x1={x(0)} x2={x(0)} y1={10} y2={58} stroke="var(--muted-foreground)" strokeDasharray="3 3" />
      <line x1={x(pp(c.ci95[0]))} x2={x(pp(c.ci95[1]))} y1={34} y2={34} stroke="var(--foreground)" strokeWidth={2} strokeLinecap="round" />
      <line x1={x(pp(c.ci90[0]))} x2={x(pp(c.ci90[1]))} y1={34} y2={34} stroke="var(--foreground)" strokeWidth={6} strokeLinecap="round" />
      <circle cx={x(pp(c.diff))} cy={34} r={6} fill="var(--evidence)" stroke="var(--paper)" strokeWidth={2} />
      {Math.min(Math.abs(x(0) - x(pp(c.ci95[0]))), Math.abs(x(0) - x(pp(c.ci95[1])))) > 36 && (
        <text x={x(0)} y={74} textAnchor="middle" fontSize={11} fill="var(--muted-foreground)">
          0
        </text>
      )}
      <text x={x(pp(c.ci95[0]))} y={74} textAnchor="middle" fontSize={11} fill="var(--foreground)">
        {formatPp(c.ci95[0])}
      </text>
      <text x={x(pp(c.ci95[1]))} y={74} textAnchor="middle" fontSize={11} fill="var(--foreground)">
        {formatPp(c.ci95[1])}
      </text>
    </svg>
  )
}
