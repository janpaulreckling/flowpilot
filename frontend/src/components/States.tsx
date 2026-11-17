import { AlertTriangle, Inbox } from 'lucide-react'
import type { ReactNode } from 'react'

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div role="status" className="animate-pulse space-y-3" aria-label={label}>
      <div className="h-4 w-1/3 rounded bg-muted" />
      <div className="h-24 rounded bg-muted" />
    </div>
  )
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error)
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-destructive/40 px-4 py-3 text-sm">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden />
      <div>
        <p className="font-medium">Could not load this data</p>
        <p className="text-muted-foreground">{message}</p>
      </div>
    </div>
  )
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border px-6 py-10 text-center">
      <Inbox className="size-6 text-muted-foreground" aria-hidden />
      <p className="font-medium">{title}</p>
      {children && <div className="max-w-sm text-sm text-muted-foreground">{children}</div>}
    </div>
  )
}

export function PageHeader({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return (
    <header className="space-y-2">
      {eyebrow && <p className="text-sm text-muted-foreground">{eyebrow}</p>}
      <h1 className="font-serif text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
      {children}
    </header>
  )
}

export function SectionTitle({ children, count }: { children: string; count?: number }) {
  return (
    <h2 className="mb-3 flex items-baseline gap-2 font-serif text-lg font-semibold">
      {children}
      {count !== undefined && <span className="font-sans text-sm font-normal text-muted-foreground">{count}</span>}
    </h2>
  )
}
