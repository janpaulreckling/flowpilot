import { ArrowRight, Inbox } from 'lucide-react'
import { Link } from 'react-router'
import { StatusChip, VerdictChip } from '@/components/Chips'
import { PrototypeNote } from '@/components/PrototypeNote'
import { alerts, pendingDecisions, type AlertItem } from '@/data/prototype'
import { formatCount, formatPp, formatRate, formatRelative } from '@/lib/format'

function Change({ alert }: { alert: AlertItem }) {
  if (alert.before === null || alert.after === null)
    return <span className="text-sm text-muted-foreground">Size pending</span>
  const rel = (alert.after - alert.before) / alert.before
  if (alert.unit === 'rate') {
    return (
      <span className="text-sm tabular-nums">
        {formatRate(alert.before)} → {formatRate(alert.after)}{' '}
        <span className="font-medium text-negative">{formatPp(alert.after - alert.before)}</span>
        <span className="text-muted-foreground"> ({formatRelative(rel)})</span>
      </span>
    )
  }
  return (
    <span className="text-sm tabular-nums">
      {formatCount(alert.before)} → {formatCount(alert.after)} per day{' '}
      <span className="font-medium text-negative">{formatRelative(rel, 0)}</span>
    </span>
  )
}

function SectionTitle({ children, count }: { children: string; count?: number }) {
  return (
    <h2 className="mb-3 flex items-baseline gap-2 font-serif text-lg font-semibold">
      {children}
      {count !== undefined && (
        <span className="font-sans text-sm font-normal text-muted-foreground">{count}</span>
      )}
    </h2>
  )
}

export function DecisionCenter() {
  const review = alerts.find((a) => a.status === 'review')
  return (
    <div className="space-y-10">
      <header className="space-y-2">
        <p className="text-sm text-muted-foreground">Data through Sunday, Nov 15, 2026</p>
        <h1 className="font-serif text-2xl font-semibold tracking-tight sm:text-3xl">Decision Center</h1>
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-muted-foreground">What needs your judgment this week.</p>
          <PrototypeNote />
        </div>
      </header>

      {review && (
        <section aria-labelledby="featured">
          <Link
            to={`/investigations/${review.id}`}
            className="group block rounded-lg border border-border bg-paper p-6 transition-colors hover:border-evidence/50"
          >
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <StatusChip status="review" />
              <span className="text-xs text-muted-foreground">Investigation of alert {review.id}</span>
            </div>
            <h2 id="featured" className="font-serif text-xl font-semibold">
              Activation fell 2.8 pp; the drop sits in the iOS 4.12 invite step
            </h2>
            <p className="mt-2 max-w-prose text-sm text-muted-foreground">
              Five checks, two hypotheses ruled out, one recommended action. Review the evidence and
              decide.
            </p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-evidence">
              Read the investigation
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
            </span>
          </Link>
        </section>
      )}

      <section>
        <SectionTitle count={pendingDecisions.length}>Experiments awaiting a decision</SectionTitle>
        <ul className="divide-y divide-border rounded-lg border border-border bg-paper">
          {pendingDecisions.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-muted-foreground">{d.experiment}</span>
                  <span className="font-medium">{d.name}</span>
                </div>
                <p className="mt-0.5 text-sm text-muted-foreground">{d.summary}</p>
              </div>
              <VerdictChip verdict={d.verdict} />
            </li>
          ))}
        </ul>
      </section>

      <section>
        <SectionTitle count={alerts.length}>Alerts</SectionTitle>
        <ul className="divide-y divide-border rounded-lg border border-border bg-paper">
          {alerts.map((a) => (
            <li key={a.id} className="grid gap-1 px-5 py-4 sm:grid-cols-[1fr_auto] sm:items-start">
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-mono">{a.id}</span>
                  <span>{a.metric}</span>
                  {a.kind === 'data_quality' && (
                    <span className="rounded border border-border px-1.5 py-px">Data quality?</span>
                  )}
                </div>
                <p className="font-medium">{a.headline}</p>
                <Change alert={a} />
                <p className="text-xs text-muted-foreground">
                  {a.period} · {a.segmentHint}
                </p>
              </div>
              <div className="sm:pt-5">
                <StatusChip status={a.status} />
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <SectionTitle>Recently decided</SectionTitle>
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border px-6 py-10 text-center">
          <Inbox className="size-6 text-muted-foreground" aria-hidden />
          <p className="font-medium">No decisions recorded yet</p>
          <p className="max-w-sm text-sm text-muted-foreground">
            Decisions you approve or reject appear here with your note and the evidence they relied
            on.
          </p>
        </div>
      </section>
    </div>
  )
}
