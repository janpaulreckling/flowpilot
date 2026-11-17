import { AlertTriangle, Check, CircleDashed, Clock, Minus, X } from 'lucide-react'
import type { StoredAlert, Verdict } from '@/lib/api'

const VERDICT = {
  ship: { label: 'Ship', icon: Check, cls: 'text-positive border-positive/40' },
  dont_ship: { label: "Don't ship", icon: X, cls: 'text-negative border-negative/40' },
  no_meaningful_effect: { label: 'No meaningful effect', icon: Minus, cls: 'text-muted-foreground border-border' },
  keep_testing: { label: 'Keep testing', icon: Clock, cls: 'text-muted-foreground border-border' },
  invalid: { label: 'Invalid test', icon: AlertTriangle, cls: 'text-negative border-negative/40' },
  not_decision_grade: { label: 'Interim, no verdict', icon: Clock, cls: 'text-muted-foreground border-border' },
} as const

export function VerdictChip({ verdict }: { verdict: Verdict }) {
  const v = VERDICT[verdict]
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap ${v.cls}`}>
      <v.icon className="size-3.5" aria-hidden />
      {v.label}
    </span>
  )
}

const STATUS: Record<StoredAlert['status'], string> = {
  open: 'New',
  investigating: 'Ready for review',
  reviewed: 'Decided',
  closed: 'Closed',
}

export function StatusChip({ status }: { status: StoredAlert['status'] }) {
  const emphasis = status === 'investigating'
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs whitespace-nowrap ${
        emphasis ? 'bg-evidence/10 font-medium text-evidence' : 'bg-muted text-muted-foreground'
      }`}
    >
      <CircleDashed className="size-3" aria-hidden />
      {STATUS[status]}
    </span>
  )
}

export type Confidence = 'supported' | 'suggestive' | 'not_supported'

export function ConfidenceLabel({ level }: { level: Confidence | 'ruled_out' | 'inconclusive' }) {
  const text = {
    supported: 'Supported',
    suggestive: 'Suggestive',
    not_supported: 'Not supported',
    ruled_out: 'Ruled out',
    inconclusive: 'Inconclusive',
  }[level]
  const cls = {
    supported: 'text-positive',
    suggestive: 'text-muted-foreground',
    not_supported: 'text-negative',
    ruled_out: 'text-muted-foreground',
    inconclusive: 'text-muted-foreground',
  }[level]
  return <span className={`text-xs font-medium tracking-wide uppercase ${cls}`}>{text}</span>
}
