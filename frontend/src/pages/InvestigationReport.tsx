import { ChevronRight } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { ActivationChart } from '@/components/ActivationChart'
import { ConfidenceLabel, type Confidence } from '@/components/Chips'
import { EvidenceProvider, EvidenceRef } from '@/components/EvidenceRef'
import { PrototypeNote } from '@/components/PrototypeNote'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { activationByPlatform, evidence, releaseMarker } from '@/data/prototype'

function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-lg border border-border bg-paper px-4 py-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 font-serif text-2xl font-semibold tabular-nums">{value}</div>
      <div className="mt-0.5 text-xs tabular-nums text-muted-foreground">{detail}</div>
    </div>
  )
}

function Finding({ level, children }: { level: Confidence; children: React.ReactNode }) {
  return (
    <li className="grid gap-1 border-l-2 border-border py-1 pl-4">
      <ConfidenceLabel level={level} />
      <p className="leading-relaxed">{children}</p>
    </li>
  )
}

type Outcome = 'approved' | 'rejected' | 'more_evidence'

function DecisionForm() {
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!outcome) return setError('Choose an outcome.')
    if (!note.trim()) return setError('A note is required so the decision can be understood later.')
    setError(null)
    setSaved(true)
  }

  const options: { value: Outcome; label: string }[] = [
    { value: 'approved', label: 'Approve' },
    { value: 'rejected', label: 'Reject' },
    { value: 'more_evidence', label: 'Need more evidence' },
  ]
  return (
    <form onSubmit={submit} className="space-y-3" aria-label="Decision">
      <div role="radiogroup" aria-label="Outcome" className="flex flex-wrap gap-2">
        {options.map((o) => (
          <Button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={outcome === o.value}
            variant={outcome === o.value ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setOutcome(o.value)
              setSaved(false)
            }}
          >
            {o.label}
          </Button>
        ))}
      </div>
      <label className="block space-y-1.5">
        <span className="text-sm font-medium">Note</span>
        <Textarea
          value={note}
          onChange={(e) => {
            setNote(e.target.value)
            setSaved(false)
          }}
          placeholder="Why you decided this way, and anything to watch."
          rows={3}
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {saved && (
        <p role="status" className="text-sm text-muted-foreground">
          Prototype: the decision is not saved yet. In the finished app it is logged with your note
          and a link to this evidence.
        </p>
      )}
      <Button type="submit">Record decision</Button>
    </form>
  )
}

export function InvestigationReport() {
  return (
    <EvidenceProvider items={evidence}>
      <article className="space-y-10">
        <header className="space-y-3">
          <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm text-muted-foreground">
            <Link to="/investigations" className="hover:text-foreground">
              Investigations
            </Link>
            <ChevronRight className="size-3.5" aria-hidden />
            <span>Alert A-0142</span>
          </nav>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="rounded-full bg-muted px-2 py-0.5">Rule-based analysis (no LLM)</span>
            <span>5 tool calls · finished Nov 16, 2026, 08:12 UTC</span>
            <PrototypeNote />
          </div>
          <h1 className="max-w-3xl font-serif text-2xl leading-tight sm:text-3xl font-semibold tracking-tight">
            Activation fell 2.8 pp after the iOS 4.12 release. The drop sits in the iOS invite step.
          </h1>
        </header>

        <section className="max-w-prose space-y-4 font-serif text-[1.075rem] leading-relaxed">
          <p>
            Signups from October 26 to November 8 activated at 34.4%, down from 37.2% in the four
            weeks before: a change of −2.8 percentage points, or −7.5%.
            <EvidenceRef id="E-1" /> The change is concentrated in iOS signups, whose rate fell
            from 36.2% to 23.9%, while web and Android held steady.
            <EvidenceRef id="E-2" /> Within the onboarding funnel, iOS 4.12 signups create
            projects as often as everyone else, but only 45.7% of them go on to invite a teammate,
            against 68.9% elsewhere.
            <EvidenceRef id="E-3" /> iOS 4.12 shipped on October 26, the first day of the affected
            period.
            <EvidenceRef id="E-5" />
          </p>
        </section>

        <section className="grid gap-3 sm:grid-cols-3">
          <Stat label="Activation, all signups" value="34.4%" detail="was 37.2% · −2.8 pp (−7.5%)" />
          <Stat label="Activation, iOS 4.12 signups" value="23.9%" detail="iOS before: 36.2% · −12.3 pp" />
          <Stat label="Invite sent, of projects" value="45.7%" detail="everyone else: 68.9%" />
        </section>

        <ActivationChart data={activationByPlatform} marker={releaseMarker} />

        <section className="space-y-3">
          <h2 className="font-serif text-xl font-semibold">Findings</h2>
          <ul className="max-w-prose space-y-4">
            <Finding level="supported">
              The activation drop is localized to iOS signups on app version 4.12.
              <EvidenceRef id="E-2" />
              <EvidenceRef id="E-5" />
            </Finding>
            <Finding level="supported">
              The break is at the invite step: project creation and invite acceptance are unchanged.
              <EvidenceRef id="E-3" />
            </Finding>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="font-serif text-xl font-semibold">Hypotheses checked and ruled out</h2>
          <ul className="max-w-prose space-y-3 leading-relaxed">
            <li>
              <span className="font-medium">Seasonality.</span> A calendar effect would move all
              platforms; web and Android did not change.
              <EvidenceRef id="E-2" />
            </li>
            <li>
              <span className="font-medium">Acquisition-channel mix.</span> Paid search grew by
              5.4 pp of signups, but at each channel's earlier rate that explains only −0.2 of the
              −2.8 pp.
              <EvidenceRef id="E-4" />
            </li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="font-serif text-xl font-semibold">Limitations</h2>
          <ul className="max-w-prose list-disc space-y-2 pl-5 leading-relaxed text-muted-foreground">
            <li>Only two complete weekly cohorts exist after the release.</li>
            <li>
              This is observational: it locates the drop, it does not prove the mechanism. The fix
              must be verified after it ships.
            </li>
          </ul>
        </section>

        <section className="space-y-4 rounded-lg border border-border bg-paper p-6">
          <div>
            <h2 className="font-serif text-xl font-semibold">Recommended next action</h2>
            <p className="mt-2 max-w-prose leading-relaxed">
              Fix the invite flow in the next iOS release and confirm that activation of signups on
              the fixed version returns to the pre-release level. No experiment is needed: this is a
              regression fix, verified by comparing cohorts.
            </p>
          </div>
          <DecisionForm />
        </section>

        <section className="space-y-2 border-t border-border pt-6">
          <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Evidence</h2>
          <ol className="space-y-1 text-sm">
            {evidence.map((e) => (
              <li key={e.id} className="flex gap-2">
                <EvidenceRef id={e.id} />
                <span className="font-mono text-muted-foreground">{e.tool}</span>
                <span className="truncate text-muted-foreground">
                  {Object.values(e.input).join(' · ')}
                </span>
              </li>
            ))}
          </ol>
        </section>
      </article>
    </EvidenceProvider>
  )
}
