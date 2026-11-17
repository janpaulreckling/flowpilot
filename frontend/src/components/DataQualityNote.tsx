import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { Link } from 'react-router'
import { api } from '@/lib/api'
import { periodText, valueLabel } from '@/lib/labels'

/** Shows tracking gaps that overlap a chart's period, next to the chart they affect. */
export function DataQualityNote({ start, end }: { start?: string; end?: string }) {
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: api.alerts })
  if (!start || !end || !alerts.data) return null
  const gaps = alerts.data.filter(
    (a) =>
      a.alert.kind === 'tracking_gap' &&
      a.alert.direction === 'decline' &&
      a.alert.first_period_start < end &&
      start < a.alert.last_period_end,
  )
  if (gaps.length === 0) return null
  return (
    <div role="note" className="flex gap-2 rounded-md border border-border px-3 py-2 text-sm">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-negative" aria-hidden />
      <div>
        <span className="font-medium">Data quality: </span>
        {gaps.map((g, i) => (
          <span key={g.alert.alert_id}>
            {i > 0 && '; '}
            {g.alert.segment.event_name} events from {valueLabel(g.alert.segment.platform ?? '')} were missing{' '}
            {periodText(g.alert.first_period_start, g.alert.last_period_end)} (
            <Link to={`/alerts/${g.alert.alert_id}`} className="text-evidence underline underline-offset-2">
              {g.alert.alert_id}
            </Link>
            )
          </span>
        ))}
        . Activity and retention for that platform in those days are unreliable.
      </div>
    </div>
  )
}
