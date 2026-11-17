import { AlertTriangle, Check, CircleDashed, Minus, X } from 'lucide-react'
import type { AlertStatus, Verdict } from '@/data/prototype'

const VERDICT = {
  ship: { label: 'Ship', icon: Check, cls: 'text-positive border-positive/40' },
  dont_ship: { label: "Don't ship", icon: X, cls: 'text-negative border-negative/40' },
  no_effect: { label: 'No meaningful effect', icon: Minus, cls: 'text-muted-foreground border-border' },
  invalid: { label: 'Invalid test', icon: AlertTriangle, cls: 'text-negative border-negative/40' },
} as const

export function VerdictChip({ verdict }: { verdict: Verdict }) {
  const v = VERDICT[verdict]
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${v.cls}`}>
      <v.icon className="size-3.5" aria-hidden />
      {v.label}
    </span>
  )
}

const STATUS: Record<AlertStatus, string> = {
  open: 'New',
  investigating: 'Investigating',
  review: 'Ready for review',
  decided: 'Decided',
}

export function StatusChip({ status }: { status: AlertStatus }) {
  const emphasis = status === 'review'
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${
        emphasis ? 'bg-evidence/10 font-medium text-evidence' : 'bg-muted text-muted-foreground'
      }`}
    >
      <CircleDashed className="size-3" aria-hidden />
      {STATUS[status]}
    </span>
  )
}

export type Confidence = 'supported' | 'suggestive' | 'not_supported'

export function ConfidenceLabel({ level }: { level: Confidence }) {
  const text = { supported: 'Supported', suggestive: 'Suggestive', not_supported: 'Not supported' }[level]
  const cls = {
    supported: 'text-positive',
    suggestive: 'text-muted-foreground',
    not_supported: 'text-negative',
  }[level]
  return <span className={`text-xs font-medium uppercase tracking-wide ${cls}`}>{text}</span>
}
