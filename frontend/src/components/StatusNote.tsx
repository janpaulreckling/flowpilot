import { Info } from 'lucide-react'
import { DEMO } from '@/lib/api'

const REPO = 'https://github.com/janpaulreckling/flowpilot/blob/main/docs'

/** Always-visible context for what the reader is looking at (not hidden in a tooltip). */
export function StatusNote({ llmEnabled }: { llmEnabled: boolean }) {
  return (
    <aside
      aria-label="About this page"
      className="flex gap-3 rounded-lg border border-border bg-muted/50 px-4 py-3 text-sm leading-relaxed"
    >
      <Info className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
      <ul className="space-y-0.5">
        <li>All data is synthetic, with documented, injected scenarios.</li>
        {DEMO && <li>This live demo shows recorded results; actions are not saved.</li>}
        <li>The investigation shown is rule-based (no LLM): the same read-only tools, fixed rules.</li>
        <li>
          {llmEnabled
            ? 'The AI agent is enabled on this server. It has not yet been evaluated against a real model.'
            : 'The AI agent is built and tested with a scripted model and runs locally with an API key; it has not yet been evaluated against a real model.'}{' '}
          <a className="text-evidence underline underline-offset-2" href={`${REPO}/METHOD_V2.md`}>
            Method
          </a>{' '}
          ·{' '}
          <a className="text-evidence underline underline-offset-2" href={`${REPO}/KNOWN_LIMITATIONS.md`}>
            Known limitations
          </a>
        </li>
      </ul>
    </aside>
  )
}
