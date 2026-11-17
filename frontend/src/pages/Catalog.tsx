import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { StatusChip } from '@/components/Chips'
import { Empty, ErrorState, Loading, PageHeader, SectionTitle } from '@/components/States'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { formatCount } from '@/lib/format'
import { alertChange, alertHeadline, longDate, periodText } from '@/lib/labels'

export function MetricsPage() {
  const q = useQuery({ queryKey: ['metrics'], queryFn: api.metrics })
  return (
    <div className="space-y-8">
      <PageHeader title="Metrics">
        <p className="max-w-prose text-muted-foreground">
          One definition per metric. Every page, the monitor and the investigations read these and nothing else.
        </p>
      </PageHeader>
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorState error={q.error} />
      ) : (
        <dl className="divide-y divide-border rounded-lg border border-border bg-paper">
          {q.data.map((m) => (
            <div key={m.name} className="grid gap-1 px-5 py-4 sm:grid-cols-[14rem_1fr]">
              <dt>
                <div className="font-medium">{m.label}</div>
                <div className="font-mono text-xs text-muted-foreground">{m.name}</div>
              </dt>
              <dd className="space-y-1 text-sm">
                <p>{m.description}</p>
                <p className="text-xs text-muted-foreground">
                  Unit: {m.unit} · {m.is_rate ? 'rate' : 'count'} · grains: {m.grains.join(', ')}
                  {m.dimensions.length > 0 && ` · dimensions: ${m.dimensions.join(', ')}`}
                </p>
              </dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  )
}

export function InvestigationsPage() {
  const q = useQuery({ queryKey: ['alerts'], queryFn: api.alerts })
  const investigated = (q.data ?? []).filter((a) => a.status === 'investigating' || a.status === 'reviewed')
  return (
    <div className="space-y-8">
      <PageHeader title="Investigations">
        <p className="max-w-prose text-muted-foreground">Alerts that have been investigated, with their evidence trail.</p>
      </PageHeader>
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorState error={q.error} />
      ) : investigated.length === 0 ? (
        <Empty title="No investigations yet">Open an alert in the Decision Center and run the analysis.</Empty>
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border bg-paper">
          {investigated.map((a) => (
            <li key={a.alert.alert_id}>
              <Link to={`/alerts/${a.alert.alert_id}`} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 hover:bg-muted/50">
                <div>
                  <p className="font-medium">{alertHeadline(a.alert)}</p>
                  <p className="text-sm text-muted-foreground tabular-nums">{alertChange(a.alert)}</p>
                </div>
                <StatusChip status={a.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

interface Truth {
  scenarios: { id: string; kind: string; expected_conclusion: string; start?: string }[]
  experiments: { id: string; expected_verdict: string }[]
}

export function DataPage() {
  const dataset = useQuery({ queryKey: ['dataset'], queryFn: api.dataset })
  const [reveal, setReveal] = useState(false)
  const truth = useQuery({ queryKey: ['ground-truth'], queryFn: api.groundTruth, enabled: reveal })
  const t = truth.data as unknown as Truth | undefined
  return (
    <div className="space-y-10">
      <PageHeader title="About the data">
        <p className="max-w-prose text-muted-foreground">
          Tasklane is a fictional team task-management product. Every number in FlowPilot comes from a seeded simulation with
          documented, injected scenarios. Nothing here is real customer data.
        </p>
      </PageHeader>
      {dataset.isPending ? (
        <Loading />
      ) : dataset.isError ? (
        <ErrorState error={dataset.error} />
      ) : (
        <dl className="grid gap-3 sm:grid-cols-3">
          {[
            ['Period', periodText(dataset.data.period_start, dataset.data.period_end_exclusive)],
            ['Seed', String(dataset.data.seed)],
            ['Workspaces', formatCount(dataset.data.row_counts.workspaces ?? 0)],
            ['Users', formatCount(dataset.data.row_counts.users ?? 0)],
            ['Sessions', formatCount(dataset.data.row_counts.sessions ?? 0)],
            ['Events', formatCount(dataset.data.row_counts.events ?? 0)],
          ].map(([k, v]) => (
            <div key={k} className="rounded-lg border border-border bg-paper px-4 py-3">
              <dt className="text-xs text-muted-foreground">{k}</dt>
              <dd className="mt-1 font-medium tabular-nums">{v}</dd>
            </div>
          ))}
        </dl>
      )}
      <section className="space-y-4">
        <SectionTitle>Injected scenarios (ground truth)</SectionTitle>
        <p className="max-w-prose text-sm text-muted-foreground">
          Hidden by default so the demo is not spoiled. The monitor and the investigations never read this; it is used only to
          score them afterwards.
        </p>
        {!reveal ? (
          <Button variant="outline" onClick={() => setReveal(true)}>
            Reveal the scenarios
          </Button>
        ) : truth.isPending ? (
          <Loading />
        ) : truth.isError ? (
          <ErrorState error={truth.error} />
        ) : (
          <div className="space-y-4">
            <ul className="divide-y divide-border rounded-lg border border-border bg-paper text-sm">
              {t?.scenarios.map((s) => (
                <li key={s.id} className="grid gap-1 px-5 py-3 sm:grid-cols-[4rem_1fr]">
                  <span className="font-mono">{s.id}</span>
                  <span>
                    {s.expected_conclusion}
                    {s.start && <span className="text-muted-foreground"> (from {longDate(s.start)})</span>}
                  </span>
                </li>
              ))}
            </ul>
            <ul className="divide-y divide-border rounded-lg border border-border bg-paper text-sm">
              {t?.experiments.map((e) => (
                <li key={e.id} className="flex justify-between px-5 py-3">
                  <span className="font-mono">{e.id}</span>
                  <span>expected verdict: {e.expected_verdict.replace(/_/g, ' ')}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  )
}
