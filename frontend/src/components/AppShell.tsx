import { useQuery } from '@tanstack/react-query'
import {
  BookOpen,
  Database,
  FileSearch,
  Filter,
  FlaskConical,
  Inbox,
  LayoutDashboard,
  Monitor,
  Moon,
  Sun,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { NavLink } from 'react-router'
import { fetchDataset } from '@/lib/api'
import { formatCount } from '@/lib/format'
import { applyTheme, readPreference, savePreference, type ThemePreference } from '@/lib/theme'

export const NAV = [
  { to: '/', label: 'Decision Center', icon: Inbox },
  { to: '/overview', label: 'Overview', icon: LayoutDashboard },
  { to: '/funnels', label: 'Funnels & Retention', icon: Filter },
  { to: '/experiments', label: 'Experiments', icon: FlaskConical },
  { to: '/investigations', label: 'Investigations', icon: FileSearch },
  { to: '/metrics', label: 'Metrics', icon: BookOpen },
  { to: '/data', label: 'About the data', icon: Database },
] as const

function ThemeSwitch() {
  const [pref, setPref] = useState<ThemePreference>(readPreference)
  useEffect(() => {
    applyTheme(pref)
    savePreference(pref)
    if (pref !== 'system') return
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)')
    const onChange = () => applyTheme('system')
    mq?.addEventListener('change', onChange)
    return () => mq?.removeEventListener('change', onChange)
  }, [pref])
  const options = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'system', label: 'System', icon: Monitor },
    { value: 'dark', label: 'Dark', icon: Moon },
  ] as const
  return (
    <div role="radiogroup" aria-label="Theme" className="inline-flex rounded-md border border-sidebar-border p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          role="radio"
          aria-checked={pref === o.value}
          aria-label={o.label}
          title={o.label}
          onClick={() => setPref(o.value)}
          className="rounded p-1.5 text-muted-foreground aria-checked:bg-sidebar-accent aria-checked:text-sidebar-foreground"
        >
          <o.icon className="size-3.5" aria-hidden />
        </button>
      ))}
    </div>
  )
}

function DatasetFooter() {
  const q = useQuery({ queryKey: ['dataset'], queryFn: fetchDataset, retry: false })
  if (q.isPending) return <p className="text-xs text-muted-foreground">Loading dataset…</p>
  if (q.isError)
    return (
      <p className="text-xs text-destructive" role="status">
        API unavailable: {q.error.message}
      </p>
    )
  const d = q.data
  return (
    <p className="text-xs leading-relaxed text-muted-foreground">
      Synthetic data · seed {d.seed}
      <br />
      {formatCount(d.row_counts.workspaces ?? 0)} workspaces ·{' '}
      {formatCount(d.row_counts.events ?? 0)} events
    </p>
  )
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-svh md:grid md:grid-cols-[15rem_1fr]">
      <aside className="border-b border-sidebar-border bg-sidebar text-sidebar-foreground md:sticky md:top-0 md:flex md:h-svh md:flex-col md:border-r md:border-b-0">
        <div className="flex items-center justify-between px-4 py-4 md:px-5 md:py-6">
          <div>
            <div className="font-serif text-xl font-semibold tracking-tight">FlowPilot</div>
            <div className="text-xs text-muted-foreground">Product decisions for Tasklane</div>
          </div>
          <div className="md:hidden">
            <ThemeSwitch />
          </div>
        </div>
        <nav aria-label="Main" className="overflow-x-auto px-2 pb-2 md:flex-1 md:overflow-visible md:px-3">
          <ul className="flex gap-1 md:flex-col">
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 whitespace-nowrap rounded-md px-3 py-2 text-sm transition-colors ${
                      isActive
                        ? 'bg-sidebar-accent font-medium text-sidebar-accent-foreground'
                        : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground'
                    }`
                  }
                >
                  <item.icon className="size-4 shrink-0" aria-hidden />
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="hidden space-y-3 border-t border-sidebar-border px-5 py-4 md:block">
          <DatasetFooter />
          <ThemeSwitch />
        </div>
      </aside>
      <div className="min-w-0">
        <div className="border-b border-border bg-muted/60 px-4 py-1.5 text-center text-xs text-muted-foreground md:px-10">
          All data is synthetic: a simulated SaaS product with documented, injected scenarios.
        </div>
        <main className="mx-auto max-w-5xl px-4 py-8 md:px-10 md:py-10">{children}</main>
      </div>
    </div>
  )
}
