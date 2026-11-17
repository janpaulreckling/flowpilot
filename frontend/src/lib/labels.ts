import type { Alert } from './api'
import { formatCount, formatPp, formatRate, formatRelative } from './format'

export const METRIC_LABELS: Record<string, string> = {
  activation_rate: 'Activation rate',
  project_rate: 'Project created (7 days)',
  week1_retention: 'Week-1 retention',
  week2_retention: 'Week-2 retention',
  week4_retention: 'Week-4 retention',
  trial_to_paid: 'Trial to paid',
  signups: 'Signups',
  active_users: 'Active users',
  stickiness: 'Stickiness',
  event_volume: 'Event volume',
  session_volume: 'Sessions',
  timeline_adoption: 'Timeline adoption',
  integration_usage: 'Integration usage',
}

const VALUE_LABELS: Record<string, string> = {
  ios: 'iOS',
  android: 'Android',
  web: 'Web',
  paid_social: 'Paid social',
  paid_search: 'Paid search',
  organic_search: 'Organic search',
  referral: 'Referral',
  partner: 'Partner',
  signup_platform: 'Platform',
  acquisition_channel: 'Channel',
  company_size: 'Company size',
  platform: 'Platform',
  event_name: 'Event',
}

export const metricLabel = (m: string) => METRIC_LABELS[m] ?? m
export const valueLabel = (v: string) => VALUE_LABELS[v] ?? v

export function segmentText(segment: Record<string, string>): string {
  const parts = Object.entries(segment).map(([k, v]) =>
    k === 'event_name' ? v : `${valueLabel(k)} ${valueLabel(v)}`,
  )
  return parts.length ? parts.join(', ') : 'All signups'
}

export function alertHeadline(a: Alert): string {
  const seg = Object.keys(a.segment).length ? ` (${segmentText(a.segment)})` : ''
  if (a.kind === 'tracking_gap') return `Possible tracking gap: ${segmentText(a.segment)}`
  const verb = a.direction === 'decline' ? 'fell' : 'rose'
  return `${metricLabel(a.metric)} ${verb}${seg}`
}

export function alertChange(a: Alert): string {
  if (a.kind === 'rate') {
    return `${formatRate(a.expected)} → ${formatRate(a.observed)} · ${formatPp(a.observed - a.expected)} (${formatRelative((a.observed - a.expected) / a.expected)})`
  }
  const rel = a.expected ? (a.observed - a.expected) / a.expected : 0
  return `${formatCount(Math.round(a.expected))} → ${formatCount(Math.round(a.observed))} per day · ${formatRelative(rel, 0)}`
}

export function shortDate(iso: string): string {
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })
}

/** Exclusive end date -> the last included day, for display. */
export function periodText(start: string, endExclusive: string): string {
  const last = new Date(`${endExclusive}T00:00:00Z`)
  last.setUTCDate(last.getUTCDate() - 1)
  return `${shortDate(start)} – ${shortDate(last.toISOString())}`
}

export function longDate(iso: string): string {
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

/** The window that triggered the alert, e.g. "1-week window, signups Oct 26 – Nov 1: 36.6% → 23.1% (−13.5 pp)". */
export function peakChange(a: Alert): string | null {
  if (!a.peak_window || !a.peak_period_start || !a.peak_period_end) return null
  const kind = a.peak_window === '1w' ? '1-week window' : a.peak_window === '4w' ? '4-week window' : 'day'
  if (a.kind !== 'rate') return null
  return `${kind}, signups ${periodText(a.peak_period_start, a.peak_period_end)}: ${formatRate(a.peak_expected)} → ${formatRate(a.peak_observed)} (${formatPp(a.peak_observed - a.peak_expected)})`
}
