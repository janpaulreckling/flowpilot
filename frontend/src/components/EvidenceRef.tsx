import { createContext, useContext, useRef, useState, type ReactNode } from 'react'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import type { Claim, Evidence } from '@/lib/api'

interface EvidenceCtx {
  items: Evidence[]
  open: (id: string) => void
}

// What each read-only tool does, in plain language (shown before the technical details).
const TOOL_TEXT: Record<string, string> = {
  get_alert: 'Read the alert that started this investigation.',
  get_metric_definition: "Looked up the metric's definition: what is counted, over which window.",
  compare_periods: 'Compared the metric in the alert period with the weeks before.',
  segment_breakdown: 'Split the change by segment and tested whether one segment moved differently from the rest.',
  funnel: "Compared each onboarding step for this segment with everyone else, before and after.",
  retention_cohorts: 'Read weekly retention for each signup week.',
  feature_adoption: 'Read how many active users used a feature each week.',
  get_releases: "Listed the platform's app releases and their dates.",
  experiment_result: 'Checked running experiments and how much of the change they could explain.',
  data_quality_report: 'Checked for tracking gaps: events per session by app version, against sessions.',
  query_metric: 'Queried a metric from the metric catalog.',
}

const Ctx = createContext<EvidenceCtx | null>(null)

function show(v: unknown): string {
  if (v === null || v === undefined) return '–'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

function factValue(v: number): string {
  return Number.isInteger(v) ? v.toLocaleString('en-US') : v.toFixed(4)
}

/** Holds the evidence of one investigation and the side panel that shows one item. */
export function EvidenceProvider({
  items,
  citedBy = {},
  children,
}: {
  items: Evidence[]
  citedBy?: Record<string, string[]>
  children: ReactNode
}) {
  const [selected, setSelected] = useState<string | null>(null)
  // The panel opens from a footnote, not from a dialog trigger, so remember where the reader
  // was and return keyboard focus there when it closes.
  const opener = useRef<HTMLElement | null>(null)
  const open = (id: string) => {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    setSelected(id)
  }
  const item = items.find((e) => e.evidence_id === selected) ?? null
  return (
    <Ctx.Provider value={{ items, open }}>
      {children}
      <Sheet open={item !== null} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent
          className="w-full overflow-y-auto sm:max-w-lg"
          onCloseAutoFocus={(e) => {
            if (opener.current) {
              e.preventDefault()
              opener.current.focus()
            }
          }}
        >
          {item && (
            <>
              <SheetHeader>
                <SheetTitle className="font-serif text-xl">Evidence {item.evidence_id}</SheetTitle>
                <SheetDescription>
                  Step {item.step}: read-only tool <code className="font-mono">{item.tool}</code> ·{' '}
                  {item.duration_ms} ms
                </SheetDescription>
              </SheetHeader>
              <div className="space-y-5 px-4 pb-6 text-sm">
                <p className="leading-relaxed">{TOOL_TEXT[item.tool] ?? item.output?.summary}</p>
                {item.error && <p className="text-destructive">This step failed: {item.error}</p>}
                {(citedBy[item.evidence_id] ?? []).length > 0 && (
                  <section>
                    <h3 className="mb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                      Used for these statements
                    </h3>
                    <ul className="list-disc space-y-1 pl-5 leading-relaxed">
                      {citedBy[item.evidence_id].map((t, i) => (
                        <li key={i}>{t}</li>
                      ))}
                    </ul>
                  </section>
                )}
                <details className="group rounded-md border border-border px-3 py-2">
                  <summary className="cursor-pointer rounded font-medium focus-visible:outline-2 focus-visible:outline-ring">
                    Technical details: inputs, facts, hash
                  </summary>
                  <div className="mt-3 space-y-5">
                    {item.output && <p className="text-muted-foreground">{item.output.summary}</p>}
                    <section>
                      <h3 className="mb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">Input</h3>
                      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                        {Object.entries(item.input).map(([k, v]) => (
                          <div key={k} className="contents">
                            <dt className="font-mono text-muted-foreground">{k}</dt>
                            <dd className="break-all">{show(v)}</dd>
                          </div>
                        ))}
                      </dl>
                    </section>
                    {item.output && Object.keys(item.output.facts).length > 0 && (
                      <section>
                        <h3 className="mb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                          Facts (what claims may cite)
                        </h3>
                        <table className="w-full border-collapse tabular-nums">
                          <tbody>
                            {Object.entries(item.output.facts).map(([k, v]) => (
                              <tr key={k} className="border-b border-border/60 last:border-0">
                                <td className="py-1 pr-4 font-mono text-xs break-all text-muted-foreground">{k}</td>
                                <td className="py-1 text-right">{factValue(v)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </section>
                    )}
                    {item.output_sha256 && (
                      <p className="font-mono text-xs break-all text-muted-foreground">sha256 {item.output_sha256}</p>
                    )}
                  </div>
                </details>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </Ctx.Provider>
  )
}

/** Footnote-style marker after a claim; opens the evidence panel. */
export function EvidenceRef({ id }: { id: string }) {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('EvidenceRef must be used inside EvidenceProvider')
  const known = ctx.items.some((e) => e.evidence_id === id)
  return (
    <button
      type="button"
      onClick={() => ctx.open(id)}
      disabled={!known}
      className="ml-0.5 align-super text-[0.7em] font-medium text-evidence underline decoration-dotted underline-offset-2 hover:decoration-solid focus-visible:outline-2 focus-visible:outline-ring disabled:text-destructive"
      aria-label={known ? `Show evidence ${id}` : `Missing evidence ${id}`}
    >
      {id}
    </button>
  )
}

/** A claim followed by one marker per cited evidence item. */
export function ClaimText({ claim }: { claim: Claim }) {
  const ids = [...new Set(claim.citations.map((c) => c.evidence_id))]
  return (
    <>
      {claim.text}
      {ids.map((id) => (
        <EvidenceRef key={id} id={id} />
      ))}
    </>
  )
}
