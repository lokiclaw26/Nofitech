// Tiny localStorage helper for the DIY HUB CODEX V2 frontend.
// Used by: Inventory page view preference (Stage 8).
//
// Safe to use in any component — wraps try/catch around localStorage
// access (Safari private mode, disabled cookies, etc. all throw on access).

const PREFIX = "diy-hub-codex-v2-"

export function getPref<T extends string>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback
  try {
    const v = window.localStorage.getItem(PREFIX + key)
    if (v == null) return fallback
    return v as T
  } catch {
    return fallback
  }
}

export function setPref(key: string, value: string): void {
  if (typeof window === "undefined") return
  try {
    window.localStorage.setItem(PREFIX + key, value)
  } catch {
    // ignore
  }
}
