// Number formatting. Percentage points (absolute change of a rate) and percent (relative
// change) are never mixed: every change shows which one it is.

const MINUS = '−'

function signed(value: number, digits: number): string {
  const abs = Math.abs(value).toFixed(digits)
  if (Number(abs) === 0) return abs
  return value < 0 ? `${MINUS}${abs}` : `+${abs}`
}

/** A rate such as 0.3721 -> "37.2%". */
export function formatRate(rate: number, digits = 1): string {
  return `${(rate * 100).toFixed(digits)}%`
}

/** Absolute change between two rates, in percentage points: -0.028 -> "−2.8 pp". */
export function formatPp(delta: number, digits = 1): string {
  return `${signed(delta * 100, digits)} pp`
}

/** Relative change: (new - old) / old, e.g. -0.075 -> "−7.5%". */
export function formatRelative(change: number, digits = 1): string {
  return `${signed(change * 100, digits)}%`
}

export function formatCount(n: number): string {
  return new Intl.NumberFormat('en-US').format(n)
}

export function formatWeek(isoMonday: string): string {
  const d = new Date(`${isoMonday}T00:00:00Z`)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}
