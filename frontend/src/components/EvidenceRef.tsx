import { createContext, useContext, useState, type ReactNode } from 'react'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import type { Evidence } from '@/data/prototype'

interface EvidenceCtx {
  items: Evidence[]
  open: (id: string) => void
}

const Ctx = createContext<EvidenceCtx | null>(null)

/** Holds the evidence of one report and the side panel that shows a selected item. */
export function EvidenceProvider({ items, children }: { items: Evidence[]; children: ReactNode }) {
  const [selected, setSelected] = useState<string | null>(null)
  const item = items.find((e) => e.id === selected) ?? null
  return (
    <Ctx.Provider value={{ items, open: setSelected }}>
      {children}
      <Sheet open={item !== null} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent className="w-full sm:max-w-lg">
          {item && (
            <>
              <SheetHeader>
                <SheetTitle className="font-serif text-xl">Evidence {item.id}</SheetTitle>
                <SheetDescription>
                  Result of the read-only tool <code className="font-mono">{item.tool}</code>
                </SheetDescription>
              </SheetHeader>
              <div className="space-y-5 px-4 pb-6 text-sm">
                <section>
                  <h3 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Input
                  </h3>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                    {Object.entries(item.input).map(([k, v]) => (
                      <div key={k} className="contents">
                        <dt className="font-mono text-muted-foreground">{k}</dt>
                        <dd>{v}</dd>
                      </div>
                    ))}
                  </dl>
                </section>
                <section>
                  <h3 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Result
                  </h3>
                  <table className="w-full border-collapse tabular-nums">
                    <thead>
                      <tr className="border-b border-border text-left text-muted-foreground">
                        {item.columns.map((c, i) => (
                          <th key={c} className={`py-1.5 font-medium ${i > 0 ? 'pl-4 text-right' : ''}`}>
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {item.rows.map((r, ri) => (
                        <tr key={ri} className="border-b border-border/60 last:border-0">
                          {r.map((cell, ci) => (
                            <td key={ci} className={`py-1.5 ${ci > 0 ? 'pl-4 text-right' : ''}`}>
                              {typeof cell === 'number' ? cell.toLocaleString('en-US') : cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {item.note && <p className="mt-2 text-muted-foreground">{item.note}</p>}
                </section>
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
  const known = ctx.items.some((e) => e.id === id)
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
