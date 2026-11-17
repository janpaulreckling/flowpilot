import { useQueries, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { ErrorState, Loading, PageHeader } from '@/components/States'
import { SERIES_COLORS, TrendChart, toPoints } from '@/components/TrendChart'
import { api, type MetricResult } from '@/lib/api'
import { addDays, formatCount, formatPp, formatRate, formatRelative } from '@/lib/format'
import { metricLabel, shortDate } from '@/lib/labels'

const PLATFORMS = [
  { key: 'web', label: 'Web', color: SERIES_COLORS[0] },
  { key: 'ios', label: 'iOS', color: SERIES_COLORS[1] },
  { key: 'android', label: 'Android', color: SERIES_COLORS[2] },
]

function monday(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`)
  return addDays(iso, -((d.getUTCDay() + 6) % 7))
}

function Tile({ metric, result }: { metric: string; result: MetricResult | undefined }) {
  const rows = (result?.rows ?? []).filter((r) => r.complete && r.value !== null)
  const last = rows.at(-1)
  const prior = rows.slice(-5, -1)
  if (!last || prior.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-paper px-4 py-3">
        <div className="text-xs text-muted-foreground">{metricLabel(metric)}</div>
        <div className="mt-1 text-sm text-muted-foreground">Not enough complete weeks</div>
      </div>
    )
  }
  const base = prior.reduce((s, r) => s + (r.value ?? 0), 0) / prior.length
  const isRate = result!.is_rate
  const change = isRate ? formatPp(last.value! - base) : formatRelative((last.value! - base) / base)
  return (
    <div className="rounded-lg border border-border bg-paper px-4 py-3">
      <div className="text-xs text-muted-foreground">
        {metricLabel(metric)}
        {metric === 'active_users' ? ' (weekly)' : ''}
      </div>
      <div className="mt-1 font-serif text-2xl font-semibold tabular-nums">
        {isRate ? formatRate(last.value!) : formatCount(last.value!)}
      </div>
      <div className="mt-0.5 text-xs text-muted-foreground tabular-nums">
        week of {shortDate(last.period)} · {change} vs the 4 weeks before
      </div>
    </div>
  )
}

export function OverviewPage() {
  const [weeks, setWeeks] = useState(16)
  const [platform, setPlatform] = useState<string>('all')
  const dataset = useQuery({ queryKey: ['dataset'], queryFn: api.dataset })
  const end = dataset.data?.period_end_exclusive
  const start = end ? monday(addDays(end, -7 * weeks)) : undefined
  const enabled = Boolean(start && end)
  const cohortFilter: Record<string, string> = platform === 'all' ? {} : { filter: `signup_platform:${platform}` }
  const usageFilter: Record<string, string> = platform === 'all' ? {} : { filter: `platform:${platform}` }
  const tiles = ['activation_rate', 'week1_retention', 'trial_to_paid', 'active_users']
  const tileQueries = useQueries({
    queries: tiles.map((m) => ({
      queryKey: ['metric', m, start, end, platform],
      queryFn: () =>
        api.metric(m, { start: start!, end: end!, ...(m === 'active_users' ? usageFilter : cohortFilter) }),
      enabled,
    })),
  })
  const act = useQuery({
    queryKey: ['metric', 'activation_rate', start, end, 'by-platform'],
    queryFn: () => api.metric('activation_rate', { start: start!, end: end!, group_by: 'signup_platform' }),
    enabled,
  })
  const ret = useQuery({
    queryKey: ['metric', 'week1_retention', start, end, 'by-platform'],
    queryFn: () => api.metric('week1_retention', { start: start!, end: end!, group_by: 'signup_platform' }),
    enabled,
  })
  const wau = useQuery({
    queryKey: ['metric', 'active_users', start, end, 'by-platform'],
    queryFn: () => api.metric('active_users', { start: start!, end: end!, group_by: 'platform' }),
    enabled,
  })

  return (
    <div className="space-y-10">
      <PageHeader title="Overview">
        <p className="max-w-prose text-muted-foreground">
          Weekly signup cohorts; a week appears only once its measurement window is complete.
        </p>
      </PageHeader>
      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-2">
          Range
          <select className="rounded-md border border-input bg-paper px-2 py-1" value={weeks} onChange={(e) => setWeeks(Number(e.target.value))}>
            <option value={8}>8 weeks</option>
            <option value={16}>16 weeks</option>
            <option value={28}>28 weeks</option>
          </select>
        </label>
        <label className="flex items-center gap-2">
          Platform (tiles)
          <select className="rounded-md border border-input bg-paper px-2 py-1" value={platform} onChange={(e) => setPlatform(e.target.value)}>
            <option value="all">All</option>
            {PLATFORMS.map((p) => (
              <option key={p.key} value={p.key}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {dataset.isError && <ErrorState error={dataset.error} />}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map((m, i) =>
          tileQueries[i].isError ? <ErrorState key={m} error={tileQueries[i].error} /> : <Tile key={m} metric={m} result={tileQueries[i].data} />,
        )}
      </section>
      {[
        { q: act, title: 'Activation rate by signup platform', isRate: true },
        { q: ret, title: 'Week-1 retention by signup platform', isRate: true },
        { q: wau, title: 'Weekly active users by platform', isRate: false },
      ].map(({ q, title, isRate }) =>
        q.isPending ? (
          <Loading key={title} />
        ) : q.isError ? (
          <ErrorState key={title} error={q.error} />
        ) : (
          <TrendChart key={title} title={title} data={toPoints(q.data.rows)} series={PLATFORMS} isRate={isRate} />
        ),
      )}
    </div>
  )
}
