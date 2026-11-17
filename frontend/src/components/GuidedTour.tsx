import { ArrowRight, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

const KEY = 'flowpilot-tour-dismissed'

function dismissed(): boolean {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

/** A 90-second path through the iOS case for first-time visitors. */
export function GuidedTour({ alertId }: { alertId: string }) {
  const [hidden, setHidden] = useState(dismissed)
  if (hidden) return null
  const hide = () => {
    setHidden(true)
    try {
      localStorage.setItem(KEY, '1')
    } catch {
      // the box just reappears next time
    }
  }
  return (
    <section aria-labelledby="tour" className="relative rounded-lg border border-evidence/40 bg-evidence/5 p-5">
      <button
        type="button"
        onClick={hide}
        aria-label="Hide the guided start"
        className="absolute top-3 right-3 rounded p-1 text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
      >
        <X className="size-4" aria-hidden />
      </button>
      <h2 id="tour" className="font-serif text-lg font-semibold">
        New here? Start with the iOS case (about 90 seconds)
      </h2>
      <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-relaxed">
        <li>Open the incident: activation fell after iOS release 4.12.</li>
        <li>Read the investigation and click a footnote (E-…) to see the evidence behind a number.</li>
        <li>Scroll to the recommended next action and the decision form.</li>
      </ol>
      <Link
        to={`/alerts/${alertId}?tour=1`}
        className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-evidence underline-offset-2 hover:underline"
      >
        Start with step 1
        <ArrowRight className="size-4" aria-hidden />
      </Link>
    </section>
  )
}

/** Shown on the alert page when arriving from the guided start. */
export function TourHint() {
  return (
    <p role="note" className="rounded-md border border-evidence/40 bg-evidence/5 px-4 py-2 text-sm">
      <span className="font-medium">Step 2 of 3:</span> read the findings below and click a footnote (E-…) to open its
      evidence. <span className="font-medium">Step 3:</span> scroll to “Recommended next action”.
    </p>
  )
}
