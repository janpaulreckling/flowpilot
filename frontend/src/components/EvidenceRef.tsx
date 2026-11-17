import { createContext, useContext, useState, type ReactNode } from 'react'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import type { Claim, Evidence } from '@/lib/api'

interface EvidenceCtx {
  items: Evidence[]
  open: (id: string) => void
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
export function EvidenceProvider({ items, children }: { items: Evidence[]; children: ReactNode }) {
  const [selected, setSelected] = useState<string | null>(null)
  const item = items.find((e) => e.evidence_id === selected) ?? null
  return (
    <Ctx.Provider value={{ items, open: setSelected }}>
      {children}
      <Sheet open={item !== null} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
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
                {item.output && <p>{item.output.summary}</p>}
                {item.error && <p className="text-destructive">Tool error: {item.error}</p>}
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
                  <p className="font-mono text-xs break-all text-muted-foreground">
                    sha256 {item.output_sha256}
                  </p>
                )}
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
