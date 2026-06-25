// Human-readable labels + badge colors for component source attribution.
// Used by: Inventory page cards, Add Component confirmation popup.
//
// Source values come from the backend's `source` field in the API response.
// Allowed values: "live", "adafruit" (vendor badge), "pololu" (parked),
// "mock_fallback", "manual". The backend defaults to "live" if not set.

export type SourceLabel =
  | "live"
  | "adafruit"
  | "pololu"
  | "mock_fallback"
  | "manual"
  | string

export interface SourceBadge {
  label: string
  color: string
  description: string
}

export const sourceBadge = (src: SourceLabel | undefined): SourceBadge => {
  switch (src) {
    case "adafruit":
      return {
        label: "Adafruit",
        color: "bg-amber-100 text-amber-800",
        description: "Scraped from Adafruit's vendor site",
      }
    case "pololu":
      return {
        label: "Pololu",
        color: "bg-blue-100 text-blue-800",
        description: "Pololu vendor (search disabled, manual paste only)",
      }
    case "mock_fallback":
      return {
        label: "Mock fallback",
        color: "bg-gray-100 text-gray-700",
        description: "Offline mock fallback (not live data)",
      }
    case "manual":
      return {
        label: "Manual",
        color: "bg-sky-100 text-sky-800",
        description: "Entered manually by the operator",
      }
    case "live":
    default:
      return {
        label: "Live",
        color: "bg-emerald-100 text-emerald-800",
        description: "Live internet lookup (Wikimedia/Wikidata/PlatformIO/GitHub)",
      }
  }
}

export const confidenceBadge = (conf: number | null | undefined): SourceBadge => {
  const c = conf ?? 0
  if (c >= 0.7) {
    return {
      label: `${Math.round(c * 100)}% confident`,
      color: "bg-green-100 text-green-800",
      description: "High confidence — multiple sources agreed",
    }
  }
  if (c >= 0.4) {
    return {
      label: `${Math.round(c * 100)}% confident`,
      color: "bg-amber-100 text-amber-800",
      description: "Medium confidence — partial source coverage",
    }
  }
  return {
    label: `${Math.round(c * 100)}% confident`,
    color: "bg-red-100 text-red-800",
    description: "Low confidence — only one source returned data",
  }
}
