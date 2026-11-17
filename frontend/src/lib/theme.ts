export type ThemePreference = 'system' | 'light' | 'dark'

const KEY = 'flowpilot-theme'

export function readPreference(): ThemePreference {
  try {
    const v = localStorage.getItem(KEY)
    if (v === 'light' || v === 'dark' || v === 'system') return v
  } catch {
    // storage unavailable (private mode, blocked): fall back to the system setting
  }
  return 'system'
}

export function savePreference(pref: ThemePreference): void {
  try {
    localStorage.setItem(KEY, pref)
  } catch {
    // ignore: the choice just won't persist
  }
}

export function applyTheme(pref: ThemePreference): void {
  const dark =
    pref === 'dark' ||
    (pref === 'system' && window.matchMedia?.('(prefers-color-scheme: dark)').matches)
  document.documentElement.classList.toggle('dark', Boolean(dark))
}
