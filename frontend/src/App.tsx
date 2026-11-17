import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router'
import { AppShell } from '@/components/AppShell'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ComingSoon } from '@/pages/ComingSoon'
import { DecisionCenter } from '@/pages/DecisionCenter'
import { InvestigationReport } from '@/pages/InvestigationReport'

const queryClient = new QueryClient()

const LATER = [
  { path: '/overview', title: 'Overview', phase: 'Phase 5 (analytics engine)' },
  { path: '/funnels', title: 'Funnels & Retention', phase: 'Phase 5 (analytics engine)' },
  { path: '/experiments', title: 'Experiments', phase: 'Phase 6 (experimentation engine)' },
  { path: '/investigations', title: 'Investigations', phase: 'Phase 7 (investigations)' },
  { path: '/metrics', title: 'Metrics', phase: 'Phase 5 (metric layer)' },
  { path: '/data', title: 'About the data', phase: 'Phase 5' },
]

export function AppRoutes() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DecisionCenter />} />
        <Route path="/investigations/:id" element={<InvestigationReport />} />
        {LATER.map((p) => (
          <Route key={p.path} path={p.path} element={<ComingSoon title={p.title} phase={p.phase} />} />
        ))}
        <Route path="*" element={<ComingSoon title="Page not found" phase="no planned phase" />} />
      </Routes>
    </AppShell>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={200}>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  )
}
