export interface DatasetInfo {
  synthetic: boolean
  seed: number
  scale: number
  period_start: string
  period_end_exclusive: string
  row_counts: Record<string, number>
}

export async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = (await res.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // keep the status line
    }
    throw new Error(detail)
  }
  return (await res.json()) as T
}

export const fetchDataset = () => fetchJson<DatasetInfo>('/api/dataset')
