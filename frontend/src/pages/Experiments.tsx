import { useQuery } from '@tanstack/react-query'
import { Check, ChevronRight, X } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { VerdictChip } from '@/components/Chips'
import { DecisionForm } from '@/components/DecisionForm'
import { IntervalPlot } from '@/components/IntervalPlot'
import { Empty, ErrorState, Loading, PageHeader, SectionTitle } from '@/components/States'
import { api, type Comparison } from '@/lib/api'
import { formatCount, formatP, formatPp, formatRate, formatRelative } from '@/lib/format'
import { metricLabel, periodText } from '@/lib/labels'

export function ExperimentsPage() {
  const q = useQuery({ queryKey: ['experiments'], queryFn: api.experiments })
  return (
    <div className="space-y-8">
      <PageHeader title="Experiments">
        <p className="max-w-prose text-muted-foreground">
          Randomized by workspace, analyzed at the planned horizon. Integrity checks come first; guardrails can stop a launch
          whatever the primary metric says.
        </p>
      </PageHeader>
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorState error={q.error} />
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border bg-paper">
          {q.data.map((e) => (
            <li key={e.experiment_id}>
              <Link
                to={`/experiments/${e.experiment_id}`}
                className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 transition-colors hover:bg-muted/50"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-muted-foreground">{e.experiment_id}</span>
                    <span className="font-medium">{e.name}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {metricLabel(e.primary_metric)} · {periodText(e.started, e.ended)}
                  </p>
                </div>
                <VerdictChip verdict={e.verdict} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Arms({ c }: { c: Comparison }) {
  return (
    <table className="w-full text-sm tabular-nums">
      <thead>
        <tr className="border-b border-border text-left text-muted-foreground">
          <th className="py-1.5 font-medium">Arm</th>
          <th className="py-1.5 pl-4 text-right font-medium">Workspaces</th>
          <th className="py-1.5 pl-4 text-right font-medium">Rate</th>
        </tr>
      </thead>
      <tbody>
        <tr className="border-b border-border/60">
          <td className="py-1.5">Control</td>
          <td className="py-1.5 pl-4 text-right">{formatCount(c.control.units)}</td>
          <td className="py-1.5 pl-4 text-right">{formatRate(c.control.rate)}</td>
        </tr>
        <tr>
          <td className="py-1.5">Treatment</td>
          <td className="py-1.5 pl-4 text-right">{formatCount(c.treatment.units)}</td>
          <td className="py-1.5 pl-4 text-right">{formatRate(c.treatment.rate)}</td>
        </tr>
      </tbody>
    </table>
  )
}

export function ExperimentPage() {
  const { experimentId = '' } = useParams()
  const q = useQuery({ queryKey: ['experiment', experimentId], queryFn: () => api.experiment(experimentId) })
  if (q.isPending) return <Loading />
  if (q.isError) return <ErrorState error={q.error} />
  const x = q.data
  const p = x.primary
  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm text-muted-foreground">
          <Link to="/experiments" className="hover:text-foreground">
            Experiments
          </Link>
          <ChevronRight className="size-3.5" aria-hidden />
          <span>{x.experiment_id}</span>
        </nav>
        <h1 className="font-serif text-2xl font-semibold tracking-tight sm:text-3xl">{x.name}</h1>
        <p className="max-w-prose text-muted-foreground">{x.hypothesis}</p>
        <p className="text-sm text-muted-foreground">
          Ran {periodText(x.started, x.ended)} · randomized by {x.randomization_unit} · planned{' '}
          {formatCount(x.planned_units_per_arm)} per arm for an MDE of {(x.mde_abs * 100).toFixed(1)} pp
        </p>
      </header>

      <section className="space-y-3 rounded-lg border border-border bg-paper p-6">
        <div className="flex flex-wrap items-center gap-3">
          <VerdictChip verdict={x.verdict} />
          {!x.decision_grade && <span className="text-sm text-muted-foreground">Interim results; no decision is made yet.</span>}
        </div>
        <ul className="max-w-prose space-y-1 leading-relaxed">
          {x.rationale.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </section>

      <section>
        <SectionTitle>Integrity checks</SectionTitle>
        <ul className="divide-y divide-border rounded-lg border border-border bg-paper text-sm">
          {x.integrity.map((c) => (
            <li key={c.name} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3">
              <span className="flex items-center gap-2">
                {c.passed ? <Check className="size-4 text-positive" aria-label="passed" /> : <X className="size-4 text-negative" aria-label="failed" />}
                <span className="font-medium">{c.name}</span>
                <span className="text-muted-foreground">{c.detail}</span>
              </span>
              <span className="tabular-nums text-muted-foreground">{formatP(c.p_value)}</span>
            </li>
          ))}
        </ul>
      </section>

      {p && x.verdict !== 'invalid' ? (
        <section className="space-y-4">
          <SectionTitle>{`Primary metric: ${metricLabel(x.primary_metric)}`}</SectionTitle>
          <p className="tabular-nums">
            {formatPp(p.diff)} ({p.rel_diff !== null ? formatRelative(p.rel_diff) : '–'}), 95% interval{' '}
            {formatPp(p.ci95[0])} to {formatPp(p.ci95[1])}, {formatP(p.p_two_sided)}
          </p>
          <IntervalPlot c={p} mde={x.mde_abs} />
          <p className="text-xs text-muted-foreground">
            Thin line: 95% interval (ship / don't ship). Thick line: 90% interval (equivalence: inside the shaded ±MDE band means
            no effect worth acting on).
          </p>
          <Arms c={p} />
        </section>
      ) : (
        <Empty title="Effects are not interpreted">The integrity checks failed, so the comparison between arms is not trustworthy.</Empty>
      )}

      {x.guardrails.length > 0 && x.verdict !== 'invalid' && (
        <section>
          <SectionTitle>Guardrails (Holm-adjusted, one-sided for harm)</SectionTitle>
          <ul className="divide-y divide-border rounded-lg border border-border bg-paper text-sm">
            {x.guardrails.map((g) => (
              <li key={g.metric} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 tabular-nums">
                <span className="flex items-center gap-2">
                  {g.breached ? <X className="size-4 text-negative" aria-label="breached" /> : <Check className="size-4 text-positive" aria-label="ok" />}
                  <span className="font-medium">{metricLabel(g.metric)}</span>
                </span>
                <span className="text-muted-foreground">
                  {g.comparison ? `${formatPp(g.comparison.diff)} · Holm p ${g.holm_p_harm!.toFixed(3)}` : 'not measurable yet'}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-3 rounded-lg border border-border bg-paper p-6">
        <h2 className="font-serif text-lg font-semibold">Your decision</h2>
        <DecisionForm subjectType="experiment" subjectId={x.experiment_id} />
      </section>
    </div>
  )
}
