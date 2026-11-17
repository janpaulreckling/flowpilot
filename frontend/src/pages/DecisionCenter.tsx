import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router'
import { StatusChip, VerdictChip } from '@/components/Chips'
import { Empty, ErrorState, Loading, PageHeader, SectionTitle } from '@/components/States'
import { api, type StoredAlert } from '@/lib/api'
import { addDays, formatPp } from '@/lib/format'
import { alertChange, alertHeadline, longDate, metricLabel, periodText, shortDate } from '@/lib/labels'

function AlertRow({ a }: { a: StoredAlert }) {
  const dq = a.alert.kind === 'tracking_gap' || a.alert.data_quality_suspect
  return (
    <li>
      <Link
        to={`/alerts/${a.alert.alert_id}`}
        className="grid gap-1 px-5 py-4 transition-colors hover:bg-muted/50 sm:grid-cols-[1fr_auto] sm:items-start"
      >
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="font-mono">{a.alert.alert_id}</span>
            <span>detected {shortDate(a.alert.first_detected_on)}</span>
            {dq && <span className="rounded border border-border px-1.5 py-px">Data quality</span>}
          </div>
          <p className="font-medium">{alertHeadline(a.alert)}</p>
          <p className="text-sm tabular-nums">{alertChange(a.alert)}</p>
          <p className="text-xs text-muted-foreground">
            Cohorts {periodText(a.alert.first_period_start, a.alert.last_period_end)}
          </p>
        </div>
        <div className="sm:pt-5">
          <StatusChip status={a.status} />
        </div>
      </Link>
    </li>
  )
}

export function DecisionCenter() {
  const dataset = useQuery({ queryKey: ['dataset'], queryFn: api.dataset })
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: api.alerts })
  const experiments = useQuery({ queryKey: ['experiments'], queryFn: api.experiments })
  const decisions = useQuery({ queryKey: ['decisions'], queryFn: api.decisions })

  const all = alerts.data ?? []
  const declines = all.filter((a) => a.alert.direction === 'decline')
  const open = declines.filter((a) => a.status !== 'reviewed' && a.status !== 'closed')
  const ready = open.filter((a) => a.status === 'investigating')
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

      {ready.length > 0 && (
        <section aria-labelledby="ready" className="space-y-3">
          <h2 id="ready" className="sr-only">
            Investigations ready for review
          </h2>
          {ready.slice(0, 3).map((a) => (
            <Link
              key={a.alert.alert_id}
              to={`/alerts/${a.alert.alert_id}`}
              className="group block rounded-lg border border-border bg-paper p-6 transition-colors hover:border-evidence/50"
            >
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <StatusChip status={a.status} />
                <span className="text-xs text-muted-foreground">Investigation of alert {a.alert.alert_id}</span>
              </div>
              <p className="font-serif text-xl font-semibold">{alertHeadline(a.alert)}</p>
              <p className="mt-1 text-sm tabular-nums text-muted-foreground">{alertChange(a.alert)}</p>
              <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-evidence">
                Read the investigation and decide
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
              </span>
            </Link>
          ))}
        </section>
      )}

      <section>
        <SectionTitle count={open.length}>Open alerts</SectionTitle>
        {alerts.isPending ? (
          <Loading />
        ) : alerts.isError ? (
          <ErrorState error={alerts.error} />
        ) : open.length === 0 ? (
          <Empty title="No open alerts">Every decline the monitor found has been decided.</Empty>
        ) : (
          <ul className="divide-y divide-border rounded-lg border border-border bg-paper">
            {open.map((a) => (
              <AlertRow key={a.alert.alert_id} a={a} />
            ))}
          </ul>
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
                  className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 transition-colors hover:bg-muted/50"
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
