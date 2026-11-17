import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router'
import { StatusChip, VerdictChip } from '@/components/Chips'
import { GuidedTour } from '@/components/GuidedTour'
import { Empty, ErrorState, Loading, PageHeader, SectionTitle } from '@/components/States'
import { api, type Incident } from '@/lib/api'
import { addDays, formatPp } from '@/lib/format'
import { alertChange, alertHeadline, longDate, metricLabel, peakChange, periodText, segmentText, shortDate } from '@/lib/labels'

function IncidentCard({ inc, featured = false }: { inc: Incident; featured?: boolean }) {
  const a = inc.lead.alert
  const peak = peakChange(a)
  return (
    <li>
      <Link
        to={`/alerts/${a.alert_id}`}
        className={`group block space-y-2 transition-colors hover:bg-muted/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring ${featured ? 'p-6' : 'px-5 py-4'}`}
      >
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <StatusChip status={inc.status} />
          {inc.kind === 'data_quality' && <span className="rounded border border-border px-1.5 py-px">Data quality</span>}
          <span>
            detected {shortDate(a.first_detected_on)} · strength |z| {inc.severity.toFixed(1)}
          </span>
        </div>
        <p className={featured ? 'font-serif text-xl font-semibold' : 'font-medium'}>{alertHeadline(a)}</p>
        <p className="text-sm tabular-nums">{peak ?? alertChange(a)}</p>
        {inc.related.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Also flagged: {inc.related.map((r) => segmentText(r.alert.segment)).join(', ')}
          </p>
        )}
        {featured && (
          <span className="inline-flex items-center gap-1 text-sm font-medium text-evidence">
            {inc.status === 'investigating' ? 'Read the investigation and decide' : 'Open and investigate'}
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
          </span>
        )}
      </Link>
    </li>
  )
}

export function DecisionCenter() {
  const dataset = useQuery({ queryKey: ['dataset'], queryFn: api.dataset })
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: api.alerts })
  const incidents = useQuery({ queryKey: ['incidents'], queryFn: api.incidents })
  const experiments = useQuery({ queryKey: ['experiments'], queryFn: api.experiments })
  const decisions = useQuery({ queryKey: ['decisions'], queryFn: api.decisions })

  const all = alerts.data ?? []
  const open = (incidents.data ?? []).filter((i) => i.status !== 'reviewed' && i.status !== 'closed')
  const [lead, ...rest] = open
  const notices = all.filter((a) => a.alert.direction === 'improvement')
  const decided = new Set((decisions.data ?? []).filter((d) => d.subject_type === 'experiment').map((d) => d.subject_id))
  const pending = (experiments.data ?? []).filter((e) => !decided.has(e.experiment_id))

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow={dataset.data ? `Data through ${longDate(addDays(dataset.data.period_end_exclusive, -1))}` : undefined}
        title="Decision Center"
      >
        <p className="text-muted-foreground">What needs your judgment: alerts, investigations and experiment verdicts.</p>
      </PageHeader>

      {lead && lead.kind === 'metric' && <GuidedTour alertId={lead.lead.alert.alert_id} />}

      <section>
        <SectionTitle count={open.length}>Open incidents</SectionTitle>
        {incidents.isPending ? (
          <Loading />
        ) : incidents.isError ? (
          <ErrorState error={incidents.error} />
        ) : open.length === 0 ? (
          <Empty title="No open incidents">Every decline the monitor found has been decided.</Empty>
        ) : (
          <div className="space-y-3">
            <ul className="rounded-lg border border-border bg-paper">
              <IncidentCard inc={lead} featured />
            </ul>
            {rest.length > 0 && (
              <ul className="divide-y divide-border rounded-lg border border-border bg-paper">
                {rest.map((i) => (
                  <IncidentCard key={i.incident_id} inc={i} />
                ))}
              </ul>
            )}
            <p className="text-xs text-muted-foreground">
              Related alerts on the same metric and period are grouped; incidents are ordered by the strength of their
              strongest detection, data-quality issues last.
            </p>
          </div>
        )}
      </section>

      <section>
        <SectionTitle count={pending.length}>Experiments awaiting a decision</SectionTitle>
        {experiments.isPending ? (
          <Loading />
        ) : experiments.isError ? (
          <ErrorState error={experiments.error} />
        ) : pending.length === 0 ? (
          <Empty title="No experiment waiting">All finished experiments have a recorded decision.</Empty>
        ) : (
          <ul className="divide-y divide-border rounded-lg border border-border bg-paper">
            {pending.map((e) => (
              <li key={e.experiment_id}>
                <Link
                  to={`/experiments/${e.experiment_id}`}
                  className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 transition-colors hover:bg-muted/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-muted-foreground">{e.experiment_id}</span>
                      <span className="font-medium">{e.name}</span>
                    </div>
                    <p className="mt-0.5 text-sm text-muted-foreground tabular-nums">
                      {metricLabel(e.primary_metric)}
                      {e.diff !== null && e.verdict !== 'invalid' ? ` ${formatPp(e.diff)}` : ''} · ran{' '}
                      {periodText(e.started, e.ended)}
                    </p>
                  </div>
                  <VerdictChip verdict={e.verdict} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <SectionTitle count={(decisions.data ?? []).length}>Recently decided</SectionTitle>
        {decisions.isPending ? (
          <Loading />
        ) : decisions.isError ? (
          <ErrorState error={decisions.error} />
        ) : decisions.data.length === 0 ? (
          <Empty title="No decisions recorded yet">
            Decisions you approve or reject appear here with your note and the evidence they relied on.
          </Empty>
        ) : (
          <ul className="divide-y divide-border rounded-lg border border-border bg-paper text-sm">
            {decisions.data.slice(0, 8).map((d) => (
              <li key={d.decision_id} className="space-y-1 px-5 py-3">
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-mono">{d.subject_id}</span>
                  <span>{d.outcome.replace('_', ' ')}</span>
                  <span>{shortDate(d.decided_at)}</span>
                </div>
                <p>{d.note}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {notices.length > 0 && (
        <details className="rounded-lg border border-border bg-paper px-5 py-3 text-sm">
          <summary className="cursor-pointer font-medium">
            {notices.length} improvement notices <span className="font-normal text-muted-foreground">(not alerts; see Known limitations)</span>
          </summary>
          <ul className="mt-3 divide-y divide-border">
            {notices.map((a) => (
              <li key={a.alert.alert_id} className="flex flex-wrap justify-between gap-2 py-2">
                <span>
                  <span className="font-mono text-xs text-muted-foreground">{a.alert.alert_id}</span> {alertHeadline(a.alert)}
                </span>
                <span className="text-muted-foreground tabular-nums">{alertChange(a.alert)}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
