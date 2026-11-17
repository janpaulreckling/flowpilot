import { describe, expect, it } from 'vitest'
import { formatPp, formatRate, formatRelative } from './format'

describe('format', () => {
  it('keeps percentage points and percent apart', () => {
    const before = 0.3722
    const after = 0.3444
    expect(formatPp(after - before)).toBe('−2.8 pp')
    expect(formatRelative((after - before) / before)).toBe('−7.5%')
  })

  it('formats rates and signs', () => {
    expect(formatRate(0.239)).toBe('23.9%')
    expect(formatPp(0.009)).toBe('+0.9 pp')
    expect(formatPp(0.0001)).toBe('0.0 pp')
  })
})
