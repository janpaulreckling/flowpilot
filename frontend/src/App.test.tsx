import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from '@/App'
import { TooltipProvider } from '@/components/ui/tooltip'
import type { InvestigationRecord, StoredAlert } from '@/lib/api'

const alert: StoredAlert = {
  status: 'investigating',
  alert: {
    alert_id: 'A-0067', metric: 'activation_rate', kind: 'rate', segment: {}, direction: 'decline',
    severity: 'alert', first_period_start: '2026-10-12', last_period_end: '2026-11-09',
    first_detected_on: '2026-11-16', observed: 0.355, expected: 0.377, max_abs_z: 3.5,
    windows: ['4w'], detections: 1, data_quality_suspect: false,
  },
}
const record: InvestigationRecord = {
  investigation_id: 'INV-0067-1', alert_id: 'A-0067', mode: 'rule_based', model: null, cost_usd: null,
  status: 'completed', failure_reason: null, started_at: '2026-11-17T08:00:00Z', finished_at: '2026-11-17T08:00:01Z',
  report: {
    alert_id: 'A-0067', mode: 'rule_based', title: 'Activation rate fell; the change sits in iOS 4.12 signups',
    summary: [{ text: 'Activation rate was 35.5%.', citations: [{ evidence_id: 'E-1', fact: 'current_rate' }] }],
    findings: [], hypotheses: [], limitations: [],
    recommendation: { kind: 'fix_and_verify', claim: { text: 'Fix the invite step.', citations: [] } },
    conclusion_supported: true,
  },
  evidence: [{
    evidence_id: 'E-1', step: 1, tool: 'compare_periods', input: { metric: 'activation_rate' },
    output: { summary: 'Activation rate: 35.5% now vs 37.7% before', data: {}, facts: { current_rate: 0.355 } },
    error: null, output_sha256: 'abc', duration_ms: 12,
  }],
}

const routes: Record<string, unknown> = {
  '/api/dataset': { synthetic: true, seed: 1, scale: 1, period_start: '2026-05-04', period_end_exclusive: '2026-11-16', row_counts: { workspaces: 10, events: 100 } },
  '/api/alerts': [alert],
  '/api/experiments': [{ experiment_id: 'E4', name: 'Pricing page redesign', primary_metric: 'trial_to_paid', verdict: 'invalid', diff: 0.003, started: '2026-10-05', ended: '2026-11-02' }],
  '/api/decisions': [],
  '/api/capabilities': { llm_enabled: false, model: null },
  '/api/alerts/A-0067/investigations': ['INV-0067-1'],
  '/api/investigations/INV-0067-1': record,
}

beforeEach(() => {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  window.matchMedia = vi.fn().mockReturnValue({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input).split('?')[0]
    if (path.startsWith('/api/metrics/')) {
      return new Response(JSON.stringify({ metric: 'activation_rate', label: 'Activation rate', unit: 'signup', is_rate: true, grain: 'week', rows: [] }))
    }
    if (path in routes) return new Response(JSON.stringify(routes[path]))
    return new Response(JSON.stringify({ detail: `no route ${path}` }), { status: 404 })
  }) as typeof fetch
})

function renderAt(path: string) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <TooltipProvider>
        <MemoryRouter initialEntries={[path]}>
          <AppRoutes />
        </MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  )
}

describe('Decision Center', () => {
  it('lists real alerts and experiments from the API', async () => {
    renderAt('/')
    expect(await screen.findByText('Read the investigation and decide')).toBeInTheDocument()
    expect(screen.getAllByText('Activation rate fell').length).toBeGreaterThan(0)
    expect(await screen.findByText('Invalid test')).toBeInTheDocument()
    expect(screen.getByText('No decisions recorded yet')).toBeInTheDocument()
    expect(screen.getByText(/All data is synthetic/)).toBeInTheDocument()
  })

  it('shows an error state when the API fails', async () => {
    routes['/api/alerts'] = undefined
    delete routes['/api/alerts']
    renderAt('/')
    expect(await screen.findByText('Could not load this data')).toBeInTheDocument()
    routes['/api/alerts'] = [alert]
  })
})

describe('Alert page', () => {
  it('opens the evidence behind a claim', async () => {
    renderAt('/alerts/A-0067')
    fireEvent.click((await screen.findAllByRole('button', { name: 'Show evidence E-1' }))[0])
    const panel = await screen.findByRole('dialog')
    expect(within(panel).getByText('Evidence E-1')).toBeInTheDocument()
    expect(within(panel).getByText('current_rate')).toBeInTheDocument()
  })

  it('refuses a decision without a note', async () => {
    renderAt('/alerts/A-0067')
    fireEvent.click(await screen.findByRole('radio', { name: 'Approve' }))
    fireEvent.click(screen.getByRole('button', { name: 'Record decision' }))
    expect(screen.getByRole('alert')).toHaveTextContent('A note is required')
  })

  it('disables the AI investigation without a server key', async () => {
    renderAt('/alerts/A-0067')
    expect(await screen.findByRole('button', { name: /Investigate with AI/ })).toBeDisabled()
    expect(await screen.findByText('Rule-based analysis (no LLM)')).toBeInTheDocument()
  })
})
