// Typed access to the FlowPilot API. In the static demo build (VITE_DEMO=1) reads come from
// JSON snapshots exported from the real API, and writes are disabled.

export const DEMO = import.meta.env.VITE_DEMO === '1'

export interface DatasetInfo {
  synthetic: boolean
  seed: number
  scale: number
  period_start: string
  period_end_exclusive: string
  row_counts: Record<string, number>
}

export interface Alert {
  alert_id: string
  metric: string
  kind: 'rate' | 'count' | 'tracking_gap'
  segment: Record<string, string>
  direction: 'decline' | 'improvement'
  severity: 'alert' | 'notice'
  first_period_start: string
  last_period_end: string
  first_detected_on: string
  observed: number
  expected: number
  max_abs_z: number
  windows: string[]
  detections: number
  data_quality_suspect: boolean
}

export interface StoredAlert {
  alert: Alert
  status: 'open' | 'investigating' | 'reviewed' | 'closed'
}

export interface Citation {
  evidence_id: string
  fact: string
}
export interface Claim {
  text: string
  citations: Citation[]
}
export interface Report {
  alert_id: string
  mode: 'rule_based' | 'llm'
  title: string
  summary: Claim[]
  findings: { claim: Claim; confidence: 'supported' | 'suggestive' | 'not_supported' }[]
  hypotheses: { name: string; status: 'supported' | 'ruled_out' | 'inconclusive'; claim: Claim }[]
  limitations: string[]
  recommendation: { kind: string; claim: Claim }
  conclusion_supported: boolean
}
export interface Evidence {
  evidence_id: string
  step: number
  tool: string
  input: Record<string, unknown>
  output: { summary: string; data: Record<string, unknown>; facts: Record<string, number> } | null
  error: string | null
  output_sha256: string | null
  duration_ms: number
}
export interface InvestigationRecord {
  investigation_id: string
  alert_id: string
  mode: 'rule_based' | 'llm'
  model: string | null
  cost_usd: number | null
  status: 'running' | 'completed' | 'failed'
  failure_reason: string | null
  report: Report | null
  evidence: Evidence[]
  started_at: string
  finished_at: string
}

export interface ArmEstimate {
  units: number
  users: number
  rate: number
  variance: number
}
export interface Comparison {
  metric: string
  control: ArmEstimate
  treatment: ArmEstimate
  diff: number
  rel_diff: number | null
  se: number
  ci95: [number, number]
  ci90: [number, number]
  p_two_sided: number
  p_harm: number
}
export type Verdict =
  | 'ship'
  | 'dont_ship'
  | 'no_meaningful_effect'
  | 'keep_testing'
  | 'invalid'
  | 'not_decision_grade'
export interface ExperimentSummary {
  experiment_id: string
  name: string
  primary_metric: string
  verdict: Verdict
  diff: number | null
  started: string
  ended: string
}
export interface ExperimentAnalysis {
  experiment_id: string
  name: string
  hypothesis: string
  randomization_unit: string
  primary_metric: string
  mde_abs: number
  planned_units_per_arm: number
  started: string
  ended: string
  as_of: string
  decision_grade: boolean
  integrity: {
    name: string
    control: number
    treatment: number
    p_value: number
    passed: boolean
    detail: string
  }[]
  primary: Comparison | null
  guardrails: {
    metric: string
    comparison: Comparison | null
    holm_p_harm: number | null
    breached: boolean
  }[]
  achieved_mde: number | null
  verdict: Verdict
  rationale: string[]
}

export interface MetricInfo {
  name: string
  label: string
  description: string
  unit: string
  is_rate: boolean
  grains: string[]
  dimensions: string[]
}
export interface MetricRow {
  period: string
  segment: string | null
  numerator: number
  denominator: number | null
  value: number | null
  complete: boolean
}
export interface MetricResult {
  metric: string
  label: string
  unit: string
  is_rate: boolean
  grain: 'day' | 'week'
  rows: MetricRow[]
}
export interface FunnelResult {
  window_days: number
  complete: boolean
  steps: {
    step: string
    segment: string | null
    users: number
    rate_from_start: number | null
    rate_from_previous: number | null
  }[]
}
export interface Decision {
  decision_id: string
  subject_type: 'finding' | 'proposal' | 'experiment'
  subject_id: string
  outcome: 'approved' | 'rejected' | 'more_evidence'
  note: string
  decided_by: string
  decided_at: string
}
export interface Capabilities {
  llm_enabled: boolean
  model: string | null
}

export class ApiError extends Error {}

/** Snapshot file for a GET path in the static demo: /api/x?a=1 -> demo-data/x__a=1.json */
export function snapshotName(path: string): string {
  return (
    path
      .replace(/^\/api\//, '')
      .replace(/[/?&]/g, '__')
      .replace(/[^\w=.-]/g, '_') + '.json'
  )
}

export async function fetchJson<T>(path: string): Promise<T> {
  const url = DEMO ? `${import.meta.env.BASE_URL}demo-data/${snapshotName(path)}` : path
  const res = await fetch(url)
  if (!res.ok) throw new ApiError(await errorDetail(res))
  return (await res.json()) as T
}

export async function postJson<T>(path: string, body?: unknown): Promise<T> {
  if (DEMO) throw new ApiError('This is the static demo: actions are not saved.')
  const res = await fetch(path, {
    method: 'POST',
    // The custom header makes the browser preflight cross-site requests, which the API refuses.
    headers: { 'Content-Type': 'application/json', 'X-FlowPilot': '1' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new ApiError(await errorDetail(res))
  return (await res.json()) as T
}

async function errorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: { msg?: string }) => d.msg ?? '').join('; ')
    }
  } catch {
    // fall through to the status line
  }
  return `${res.status} ${res.statusText}`
}

const enc = encodeURIComponent

export const api = {
  dataset: () => fetchJson<DatasetInfo>('/api/dataset'),
  capabilities: () => fetchJson<Capabilities>('/api/capabilities'),
  alerts: () => fetchJson<StoredAlert[]>('/api/alerts'),
  alertInvestigations: (id: string) => fetchJson<string[]>(`/api/alerts/${enc(id)}/investigations`),
  investigation: (id: string) => fetchJson<InvestigationRecord>(`/api/investigations/${enc(id)}`),
  investigate: (id: string, mode: 'rule_based' | 'llm') =>
    postJson<InvestigationRecord>(`/api/alerts/${enc(id)}/investigate?mode=${mode}`),
  experiments: () => fetchJson<ExperimentSummary[]>('/api/experiments'),
  experiment: (id: string) => fetchJson<ExperimentAnalysis>(`/api/experiments/${enc(id)}`),
  metrics: () => fetchJson<MetricInfo[]>('/api/metrics'),
  metric: (name: string, params: Record<string, string | string[]>) => {
    const q = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      for (const item of Array.isArray(v) ? v : [v]) q.append(k, item)
    }
    return fetchJson<MetricResult>(`/api/metrics/${enc(name)}?${q.toString()}`)
  },
  funnel: (params: Record<string, string | string[]>) => {
    const q = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      for (const item of Array.isArray(v) ? v : [v]) q.append(k, item)
    }
    return fetchJson<FunnelResult>(`/api/funnel?${q.toString()}`)
  },
  decisions: () => fetchJson<Decision[]>('/api/decisions'),
  decide: (body: Omit<Decision, 'decision_id' | 'decided_at' | 'decided_by'>) =>
    postJson<Decision>('/api/decisions', body),
  groundTruth: () => fetchJson<Record<string, unknown>>('/api/ground-truth'),
}
