import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from '@/App'
import { TooltipProvider } from '@/components/ui/tooltip'

beforeAll(() => {
  // jsdom lacks these browser APIs used by Recharts and Radix.
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  window.matchMedia = vi.fn().mockReturnValue({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: 503,
    statusText: 'Service Unavailable',
    json: async () => ({ detail: 'store missing' }),
  })
})

function renderAt(path: string) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <TooltipProvider>
        <MemoryRouter initialEntries={[path]}>
          <AppRoutes />
        </MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  )
}

describe('investigation report', () => {
  it('opens the evidence behind a claim', async () => {
    renderAt('/investigations/A-0142')
    fireEvent.click(screen.getAllByRole('button', { name: 'Show evidence E-3' })[0])
    const panel = await screen.findByRole('dialog')
    expect(within(panel).getByText('Evidence E-3')).toBeInTheDocument()
    expect(within(panel).getByText('Invite sent (of projects)')).toBeInTheDocument()
    expect(within(panel).getByText('45.7%')).toBeInTheDocument()
  })

  it('refuses a decision without a note', () => {
    renderAt('/investigations/A-0142')
    fireEvent.click(screen.getByRole('radio', { name: 'Approve' }))
    fireEvent.click(screen.getByRole('button', { name: 'Record decision' }))
    expect(screen.getByRole('alert')).toHaveTextContent('A note is required')
  })

  it('labels prototype content and synthetic data', () => {
    renderAt('/')
    expect(screen.getAllByText('Prototype · sample content').length).toBeGreaterThan(0)
    expect(screen.getByText(/All data is synthetic/)).toBeInTheDocument()
  })

  it('shows an error state when the API is down', async () => {
    renderAt('/')
    expect(await screen.findByText(/API unavailable: store missing/)).toBeInTheDocument()
  })
})
