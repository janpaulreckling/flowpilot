import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { ErrorState, Loading } from '@/components/States'
import { SERIES_COLORS, TrendChart, toPoints } from '@/components/TrendChart'
import { api } from '@/lib/api'
import { addDays } from '@/lib/format'

const REPO = 'https://github.com/janpaulreckling/flowpilot'

function monday(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`)
  return addDays(iso, -((d.getUTCDay() + 6) % 7))
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="font-serif text-xl font-semibold">{title}</h2>
      <div className="max-w-prose space-y-3 leading-relaxed">{children}</div>
    </section>
  )
}

function Chart() {
  const dataset = useQuery({ queryKey: ['dataset'], queryFn: api.dataset })
  const end = dataset.data?.period_end_exclusive
  const start = end ? monday(addDays(end, -7 * 16)) : undefined
  const q = useQuery({
    queryKey: ['metric', 'activation_rate', start, end, 'by-platform'],
    queryFn: () => api.metric('activation_rate', { start: start!, end: end!, group_by: 'signup_platform' }),
    enabled: Boolean(start),
  })
  if (q.isPending) return <Loading />
  if (q.isError) return <ErrorState error={q.error} />
  return (
    <TrendChart
      title="Activation rate by signup platform"
      subtitle="weekly signup cohorts, complete weeks only"
      data={toPoints(q.data.rows)}
      series={[
        { key: 'web', label: 'Web', color: SERIES_COLORS[0] },
        { key: 'ios', label: 'iOS', color: SERIES_COLORS[1] },
        { key: 'android', label: 'Android', color: SERIES_COLORS[2] },
      ]}
      isRate
      marker={{ period: '2026-10-26', label: 'iOS 4.12' }}
    />
  )
}

export function CaseStudyPage() {
  const incidents = useQuery({ queryKey: ['incidents'], queryFn: api.incidents })
  const lead = incidents.data?.find((i) => i.kind === 'metric')?.lead.alert.alert_id
  return (
    <article className="space-y-10">
      <header className="space-y-3">
        <p className="text-sm text-muted-foreground">Case study · synthetic data</p>
        <h1 className="max-w-3xl font-serif text-3xl leading-tight font-semibold tracking-tight">
          Why did activation drop? Finding a broken iOS release in a week of noise, with every number checkable
        </h1>
        <p className="max-w-prose text-lg leading-relaxed text-muted-foreground">
          A product analytics and decision-support tool for a team task-management product: it detects metric changes,
          explains them with verifiable evidence, and gives experiment verdicts that hold up to scrutiny.
        </p>
        {lead && (
          <Link to={`/alerts/${lead}?tour=1`} className="inline-flex items-center gap-1 font-medium text-evidence hover:underline">
            Open this case in the demo
            <ArrowRight className="size-4" aria-hidden />
          </Link>
        )}
      </header>

      <Section title="The problem and who has it">
        <p>
          A growth PM gets asked “why did activation drop?” every week. The honest answer takes a day of slicing
          dashboards: is the drop real or noise, which segment, which step, is it seasonality or a different mix of
          acquisition channels? Meanwhile experiments get shipped on a p-value even when a guardrail quietly suffered or
          the traffic split was broken.
        </p>
        <p>
          FlowPilot is built for that PM, the head of product who decides, and the analyst who has to defend the numbers.
        </p>
      </Section>

      <Section title="The data">
        <p>
          <em>Tasklane</em> is fictional: 28 weeks, about 71,000 new workspaces, 163,000 users and 6.2 million events,
          generated with a fixed seed. Specific problems were injected and documented before any analysis code was written,
          for example a broken iOS release, a weaker paid-social cohort, an Android tracking gap and four A/B tests. That
          makes every claim checkable against a known truth. It also means results are measured on synthetic data, not on
          customers.
        </p>
      </Section>

      <Section title="The decisions I made as product owner and analyst">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong>What “activated” means:</strong> a new workspace's owner creates a project and an invited teammate
            joins, both within 7 days. A week counts only once its 7 days are over, so incomplete weeks never look like a
            crash.
          </li>
          <li>
            <strong>What “active” means:</strong> doing something (a task, a comment), not just opening the app. As a
            result, a tracking bug shows up as a dip that must be recognized as a data problem.
          </li>
          <li>
            <strong>Rules before results:</strong> alert thresholds, experiment decision rules and the investigation
            playbook were written down and committed before they first ran. Where a later method review found weaknesses,
            the fixes were published as a separate version with before-and-after results.
          </li>
          <li>
            <strong>Experiments are judged like a careful analyst would:</strong> the traffic split is checked first, a
            guardrail can veto a launch, and “no meaningful effect” is a real verdict.
          </li>
        </ul>
      </Section>

      <Section title="The iOS case">
        <p>
          The monitor raised the alert on November 9, the first day the data could show it: activation is measured over
          7 days, so the first full cohort week after the October 26 release had to mature. In that week, iOS activation
          fell from 36.1% to 23.1% (−12.9 percentage points). Two more alerts (all signups, paid search) are folded into
          the same incident.
        </p>
      </Section>
      <Chart />
      <Section title="What the investigation established">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <strong>Where:</strong> the change is concentrated in iOS (−5.4 pp against −0.4 pp for all other signups over
            the alert window), and within iOS in version 4.12, released inside the affected period.
          </li>
          <li>
            <strong>Which step:</strong> iOS 4.12 signups reach “invite sent” at 45.7% against 69.5% for everyone else.
            Against the gap before the release, that step moved by −22.4 pp, while the other steps moved by −0.2 pp.
          </li>
          <li>
            <strong>Ruled out:</strong> seasonality (other platforms barely moved), the acquisition-channel mix (+0.0 pp
            of the change), a tracking gap, and the running experiments.
          </li>
          <li>
            <strong>Recommendation:</strong> fix the invite step in the next iOS release and confirm that activation of
            signups on the fixed version returns to the earlier level. No experiment is needed for a regression fix.
          </li>
        </ul>
        <p>
          Every number in the report is a footnote to the read-only query that produced it. A validator rejects any
          report whose numbers do not match those results, in order and with the right sign.
        </p>
      </Section>

      <Section title="Results across the whole dataset">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            All three monitorable injected problems were detected; the back-test raised one false alarm in 4,624 tests.
          </li>
          <li>
            All four experiments got the verdict their ground truth calls for: ship; no meaningful effect; don't ship (a
            guardrail was breached); invalid (broken traffic split).
          </li>
          <li>
            The rule-based investigation passed 6 of 7 scored alerts. The miss has two overlapping causes; the report
            names both, but the fixed scoring rule counts it as a miss.
          </li>
        </ul>
      </Section>

      <Section title="Limitations">
        <ul className="list-disc space-y-2 pl-5">
          <li>All data is synthetic; the results show the method works on known problems, not real-world accuracy.</li>
          <li>
            The investigations in this demo are rule-based. An AI agent with the same tools and the same evidence checks
            is built and tested with a scripted model, but it has not yet been evaluated against a real model.
          </li>
          <li>
            Detection can only be as fast as a metric's window; the count monitor lags growth and raises many
            improvement notices.
          </li>
        </ul>
      </Section>

      <section className="space-y-2 border-t border-border pt-6 text-sm">
        <h2 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Read more</h2>
        <ul className="space-y-1">
          <li>
            <Link to="/" className="text-evidence underline underline-offset-2">
              The demo's Decision Center
            </Link>
          </li>
          <li>
            <a className="text-evidence underline underline-offset-2" href={`${REPO}/blob/main/docs/METHOD_V2.md`}>
              Method and before/after results
            </a>{' '}
            ·{' '}
            <a className="text-evidence underline underline-offset-2" href={`${REPO}/blob/main/docs/KNOWN_LIMITATIONS.md`}>
              Known limitations
            </a>{' '}
            ·{' '}
            <a className="text-evidence underline underline-offset-2" href={REPO}>
              Code
            </a>
          </li>
        </ul>
      </section>
    </article>
  )
}
