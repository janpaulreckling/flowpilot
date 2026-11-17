import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router'
import { AppShell } from '@/components/AppShell'
import { Empty } from '@/components/States'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AlertPage } from '@/pages/AlertPage'
import { DataPage, InvestigationsPage, MetricsPage } from '@/pages/Catalog'
import { DecisionCenter } from '@/pages/DecisionCenter'
import { ExperimentPage, ExperimentsPage } from '@/pages/Experiments'
import { FunnelsPage } from '@/pages/Funnels'
import { OverviewPage } from '@/pages/Overview'

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: 1 } } })

export function AppRoutes() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DecisionCenter />} />
        <Route path="/alerts/:alertId" element={<AlertPage />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/funnels" element={<FunnelsPage />} />
        <Route path="/experiments" element={<ExperimentsPage />} />
        <Route path="/experiments/:experimentId" element={<ExperimentPage />} />
        <Route path="/investigations" element={<InvestigationsPage />} />
        <Route path="/metrics" element={<MetricsPage />} />
        <Route path="/data" element={<DataPage />} />
        <Route path="*" element={<Empty title="Page not found" />} />
      </Routes>
    </AppShell>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={200}>
        <BrowserRouter basename={import.meta.env.BASE_URL}>
          <AppRoutes />
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  )
}
