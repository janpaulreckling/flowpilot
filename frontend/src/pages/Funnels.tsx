import { useQuery } from '@tanstack/react-query'
import { ErrorState, Loading, PageHeader, SectionTitle } from '@/components/States'
import { api } from '@/lib/api'
import { addDays, formatCount, formatRate } from '@/lib/format'
import { periodText, shortDate, valueLabel } from '@/lib/labels'

function monday(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`)
  return addDays(iso, -((d.getUTCDay() + 6) % 7))
}

export function FunnelsPage() {
  const dataset = useQuery({ queryKey: ['dataset'], queryFn: api.dataset })
  const end = dataset.data ? monday(addDays(dataset.data.period_end_exclusive, -7)) : undefined
  const start = end ? addDays(end, -28) : undefined
  const funnel = useQuery({
    queryKey: ['funnel', start, end],
    queryFn: () => api.funnel({ start: start!, end: end!, group_by: 'signup_platform' }),
    enabled: Boolean(start),
  })
  const cohortStart = end ? addDays(end, -7 * 12) : undefined
  const retention = useQuery({
    queryKey: ['retention', cohortStart, dataset.data?.period_end_exclusive],
    queryFn: async () => {
      const params = { start: cohortStart!, end: dataset.data!.period_end_exclusive }
      const [w1, w2, w4] = await Promise.all([1, 2, 4].map((w) => api.metric(`week${w}_retention`, params)))
      return { w1, w2, w4 }
    },
    enabled: Boolean(cohortStart),
  })

  const segments = [...new Set((funnel.data?.steps ?? []).map((s) => s.segment ?? 'all'))]
  const stepNames = [...new Set((funnel.data?.steps ?? []).map((s) => s.step))]

  return (
    <div className="space-y-10">
      <PageHeader title="Funnels & Retention">
        <p className="max-w-prose text-muted-foreground">Onboarding steps within 7 days of signup, and bracketed weekly retention (D26).</p>
      </PageHeader>
      <section>
        <SectionTitle>{start && end ? `Onboarding funnel · signups ${periodText(start, end)}` : 'Onboarding funnel'}</SectionTitle>
        {funnel.isPending ? (
          <Loading />
        ) : funnel.isError ? (
          <ErrorState error={funnel.error} />
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border bg-paper p-4">
            <table className="w-full text-sm tabular-nums">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="py-1.5 font-medium">Step</th>
                  {segments.map((s) => (
                    <th key={s} className="py-1.5 pl-4 font-medium">
                      {valueLabel(s)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {stepNames.map((name) => (
                  <tr key={name} className="border-t border-border/60">
                    <td className="py-2 pr-4 whitespace-nowrap">{name}</td>
                    {segments.map((seg) => {
                      const s = funnel.data.steps.find((x) => x.step === name && (x.segment ?? 'all') === seg)
                      const share = s?.rate_from_start ?? 0
                      return (
                        <td key={seg} className="py-2 pl-4">
                          <div className="flex items-center gap-2">
                            <div className="h-2 w-24 rounded-full bg-muted" aria-hidden>
                              <div className="h-2 rounded-full" style={{ width: `${share * 100}%`, background: 'var(--series-web)' }} />
                            </div>
                            <span>{s ? formatCount(s.users) : '–'}</span>
                            {s?.rate_from_previous != null && (
                              <span className="text-xs text-muted-foreground">{formatRate(s.rate_from_previous)} of previous</span>
                            )}
                          </div>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <SectionTitle>Retention by signup week</SectionTitle>
        {retention.isPending ? (
          <Loading />
        ) : retention.isError ? (
          <ErrorState error={retention.error} />
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border bg-paper p-4">
            <table className="w-full text-sm tabular-nums">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="py-1.5 font-medium">Signup week</th>
                  <th className="py-1.5 pl-4 text-right font-medium">Signups</th>
                  {['Week 1', 'Week 2', 'Week 4'].map((h) => (
                    <th key={h} className="py-1.5 pl-4 text-right font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {retention.data.w1.rows.map((r, i) => {
                  const cells = [retention.data.w1.rows[i], retention.data.w2.rows[i], retention.data.w4.rows[i]]
                  return (
                    <tr key={r.period} className="border-t border-border/60">
                      <td className="py-1.5">{shortDate(r.period)}</td>
                      <td className="py-1.5 pl-4 text-right">{formatCount(r.denominator ?? 0)}</td>
                      {cells.map((c, j) => (
                        <td
                          key={j}
                          className="py-1.5 pl-4 text-right"
                          style={c?.complete && c.value !== null ? { background: `color-mix(in oklab, var(--series-web) ${Math.round(c.value * 60)}%, transparent)` } : undefined}
                        >
                          {c?.complete && c.value !== null ? formatRate(c.value) : <span className="text-muted-foreground">not yet</span>}
                        </td>
                      ))}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
