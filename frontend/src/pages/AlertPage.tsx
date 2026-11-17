import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronRight, Sparkles, Wrench } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router'
import { ConfidenceLabel, StatusChip } from '@/components/Chips'
import { DecisionForm } from '@/components/DecisionForm'
import { ClaimText, EvidenceProvider, EvidenceRef } from '@/components/EvidenceRef'
import { TourHint } from '@/components/GuidedTour'
import { Empty, ErrorState, Loading } from '@/components/States'
import { StatusNote } from '@/components/StatusNote'
import { SERIES_COLORS, TrendChart, toPoints } from '@/components/TrendChart'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { api, DEMO, type Alert, type InvestigationRecord } from '@/lib/api'
import { addDays } from '@/lib/format'
import { alertChange, alertHeadline, metricLabel, peakChange, periodText, segmentText, shortDate, valueLabel } from '@/lib/labels'

const REC_LABEL: Record<string, string> = {
  fix_and_verify: 'Fix and verify',
  experiment: 'Run an experiment',
  fix_tracking: 'Fix tracking',
  investigate_segment: 'Investigate the segment',
  no_action: 'No action',
}

function AlertTrend({ alert }: { alert: Alert }) {
  const start = addDays(alert.first_period_start, -7 * 10)
  const end = addDays(alert.last_period_end, 14)
  const [dim, value] = Object.entries(alert.segment)[0] ?? []
  const overall = useQuery({
    queryKey: ['metric', alert.metric, start, end],
    queryFn: () => api.metric(alert.metric, { start, end }),
  })
  const seg = useQuery({
    queryKey: ['metric', alert.metric, start, end, dim, value],
    queryFn: () => api.metric(alert.metric, { start, end, filter: `${dim}:${value}` }),
    enabled: Boolean(dim),
  })
  if (overall.isPending) return <Loading />
  if (overall.isError) return <ErrorState error={overall.error} />
  const points = toPoints(overall.data.rows)
  const series = [{ key: 'all', label: 'All signups', color: SERIES_COLORS[0] }]
  if (dim && seg.data) {
    const segPoints = new Map(toPoints(seg.data.rows).map((p) => [p.period, p.all]))
    for (const p of points) p.segment = segPoints.get(p.period) ?? null
    series.push({ key: 'segment', label: valueLabel(value), color: SERIES_COLORS[1] })
  }
  return (
    <TrendChart
      title={metricLabel(alert.metric)}
      subtitle="weekly signup cohorts, complete weeks only"
      data={points}
      series={series}
      isRate
      marker={{ period: alert.first_period_start, label: 'alert window' }}
    />
  )
}

function InvestigationView({ record }: { record: InvestigationRecord }) {
  const r = record.report
  if (record.status === 'running' || !r) {
    return (
      <p role="status" className="rounded-md border border-border px-4 py-3 text-sm text-muted-foreground">
        {record.status === 'running'
          ? `Investigation ${record.investigation_id} is still running.`
          : `Investigation ${record.investigation_id} did not complete: ${record.failure_reason ?? 'unknown error'}`}
      </p>
    )
  }
  return (
    <EvidenceProvider items={record.evidence}>
      <article className="space-y-8">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="rounded-full bg-muted px-2 py-0.5">
            {record.mode === 'llm' ? `AI investigation (${record.model ?? 'LLM'})` : 'Rule-based analysis (no LLM)'}
          </span>
          <span>
            {record.evidence.length} tool calls · {record.investigation_id} · {shortDate(record.finished_at)}
          </span>
          {record.cost_usd !== null && <span>cost ${record.cost_usd.toFixed(2)}</span>}
        </div>
        {record.status === 'failed' && (
          <p role="alert" className="rounded-md border border-destructive/40 px-4 py-3 text-sm">
            This investigation did not complete: {record.failure_reason}
          </p>
        )}
        <h2 className="max-w-3xl font-serif text-2xl leading-tight font-semibold sm:text-3xl">{r.title}</h2>
        <section className="max-w-prose space-y-3 font-serif text-[1.075rem] leading-relaxed">
          {r.summary.map((c, i) => (
            <p key={i}>
              <ClaimText claim={c} />
            </p>
          ))}
        </section>

        {r.findings.length > 0 && (
          <section className="space-y-3">
            <h3 className="font-serif text-xl font-semibold">Findings</h3>
            <ul className="max-w-prose space-y-4">
              {r.findings.map((f, i) => (
                <li key={i} className="grid gap-1 border-l-2 border-border py-1 pl-4">
                  <ConfidenceLabel level={f.confidence} />
                  <p className="leading-relaxed">
                    <ClaimText claim={f.claim} />
                  </p>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="space-y-3">
          <h3 className="font-serif text-xl font-semibold">Hypotheses checked</h3>
          <ul className="max-w-prose space-y-3 leading-relaxed">
            {r.hypotheses.map((h, i) => (
              <li key={i} className="grid gap-0.5">
                <span className="flex items-baseline gap-2">
                  <span className="font-medium">{h.name}</span>
                  <ConfidenceLabel level={h.status} />
                </span>
                <span>
                  <ClaimText claim={h.claim} />
                </span>
              </li>
            ))}
          </ul>
        </section>

        {r.limitations.length > 0 && (
          <section className="space-y-3">
            <h3 className="font-serif text-xl font-semibold">Limitations</h3>
            <ul className="max-w-prose list-disc space-y-2 pl-5 leading-relaxed text-muted-foreground">
              {r.limitations.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          </section>
        )}

        <section className="space-y-4 rounded-lg border border-border bg-paper p-6">
          <div>
            <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Recommended next action · {REC_LABEL[r.recommendation.kind] ?? r.recommendation.kind}
            </p>
            <p className="mt-2 max-w-prose leading-relaxed">
              <ClaimText claim={r.recommendation.claim} />
            </p>
          </div>
          {record.status === 'completed' && <DecisionForm subjectType="proposal" subjectId={record.investigation_id} />}
        </section>

        <section className="space-y-2 border-t border-border pt-6">
          <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Evidence trail</h3>
          <ol className="space-y-1 text-sm">
            {record.evidence.map((e) => (
              <li key={e.evidence_id} className="flex gap-2">
                <EvidenceRef id={e.evidence_id} />
                <span className="font-mono text-muted-foreground">{e.tool}</span>
                <span className="truncate text-muted-foreground">{e.output?.summary ?? e.error}</span>
              </li>
            ))}
          </ol>
        </section>
      </article>
    </EvidenceProvider>
  )
}

export function AlertPage() {
  const { alertId = '' } = useParams()
  const [search] = useSearchParams()
  const qc = useQueryClient()
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: api.alerts })
  const caps = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities })
  const ids = useQuery({ queryKey: ['investigations', alertId], queryFn: () => api.alertInvestigations(alertId) })
  const latest = ids.data?.at(-1)
  const record = useQuery({
    queryKey: ['investigation', latest],
    queryFn: () => api.investigation(latest!),
    enabled: Boolean(latest),
  })
  const run = useMutation({
    mutationFn: (mode: 'rule_based' | 'llm') => api.investigate(alertId, mode),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['investigations', alertId] })
      void qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  if (alerts.isPending) return <Loading />
  if (alerts.isError) return <ErrorState error={alerts.error} />
  const stored = alerts.data.find((a) => a.alert.alert_id === alertId)
  if (!stored) return <Empty title={`No alert ${alertId}`} />
  const a = stored.alert
  const llm = caps.data?.llm_enabled ?? false

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm text-muted-foreground">
          <Link to="/" className="hover:text-foreground">
            Decision Center
          </Link>
          <ChevronRight className="size-3.5" aria-hidden />
          <span>Alert {a.alert_id}</span>
        </nav>
        <div className="flex flex-wrap items-center gap-2">
          <StatusChip status={stored.status} />
          <span className="text-xs text-muted-foreground">
            {segmentText(a.segment)} · detected {shortDate(a.first_detected_on)} · |z| {a.max_abs_z.toFixed(1)} · window{' '}
            {a.windows.join(', ')}
          </span>
        </div>
        <h1 className="font-serif text-2xl font-semibold tracking-tight sm:text-3xl">{alertHeadline(a)}</h1>
        <p className="tabular-nums">{peakChange(a) ?? alertChange(a)}</p>
        {peakChange(a) && <p className="text-sm tabular-nums text-muted-foreground">Whole alert window: {alertChange(a)}</p>}
        <p className="text-sm text-muted-foreground">Cohorts {periodText(a.first_period_start, a.last_period_end)}</p>
      </header>

      {search.get('tour') === '1' && <TourHint />}
      <StatusNote llmEnabled={llm} />

      {a.kind === 'rate' && <AlertTrend alert={a} />}

      <section className="flex flex-wrap items-center gap-3">
        <Button onClick={() => run.mutate('rule_based')} disabled={run.isPending || DEMO} variant={latest ? 'outline' : 'default'}>
          <Wrench className="size-4" aria-hidden />
          {latest ? 'Re-run rule-based analysis' : 'Investigate (rule-based)'}
        </Button>
        <Tooltip>
          <TooltipTrigger asChild>
            <span tabIndex={llm ? -1 : 0}>
              <Button onClick={() => run.mutate('llm')} disabled={!llm || run.isPending || DEMO} variant="outline">
                <Sparkles className="size-4" aria-hidden />
                Investigate with AI
              </Button>
            </span>
          </TooltipTrigger>
          {!llm && (
            <TooltipContent>Not enabled: the AI agent needs an API key on the server (see the note above).</TooltipContent>
          )}
        </Tooltip>
        {run.isPending && <span role="status" className="text-sm text-muted-foreground">Investigating…</span>}
        {run.isError && <span role="alert" className="text-sm text-destructive">{run.error.message}</span>}
      </section>

      {ids.isPending || (latest && record.isPending) ? (
        <Loading label="Loading investigation" />
      ) : ids.isError ? (
        <ErrorState error={ids.error} />
      ) : record.isError ? (
        <ErrorState error={record.error} />
      ) : record.data ? (
        <InvestigationView record={record.data} />
      ) : (
        <Empty title="Not investigated yet">
          Run the rule-based analysis: it checks segments, the funnel, releases, data quality and running experiments, and
          records every number it uses as evidence.
        </Empty>
      )}
    </div>
  )
}
