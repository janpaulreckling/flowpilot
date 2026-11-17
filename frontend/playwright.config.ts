import { defineConfig, devices } from '@playwright/test'

// Runs the demo journey against the static demo build (npm run build:demo), the same
// artifact that is published.
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  use: { baseURL: 'http://localhost:4173/flowpilot/', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'phone', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    command: 'npx vite preview --base=/flowpilot/ --port 4173 --strictPort',
    url: 'http://localhost:4173/flowpilot/',
    reuseExistingServer: false,
  },
})
