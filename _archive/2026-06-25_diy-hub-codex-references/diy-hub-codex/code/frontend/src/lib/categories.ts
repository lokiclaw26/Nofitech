// Canonical category list for DIY Hub V1.
// Used by: Inventory page filter, Add Component manual form, candidate picker.
//
// Keep in sync with _CATEGORY_HINTS in backend/app/live_search.py
// (the backend uses a different matching strategy but the same set of names).

export const CATEGORIES = [
  "Microcontroller",
  "Sensor",
  "Display",
  "Motor",
  "Regulator",
  "Op-amp",
  "Connector",
  "Passive",
  "Other",
] as const

export type Category = typeof CATEGORIES[number]

export const isCategory = (s: string): s is Category =>
  (CATEGORIES as readonly string[]).includes(s)

export const categoryColor: Record<Category, string> = {
  Microcontroller: "bg-indigo-100 text-indigo-800",
  Sensor: "bg-emerald-100 text-emerald-800",
  Display: "bg-amber-100 text-amber-800",
  Motor: "bg-rose-100 text-rose-800",
  Regulator: "bg-yellow-100 text-yellow-800",
  "Op-amp": "bg-purple-100 text-purple-800",
  Connector: "bg-slate-100 text-slate-800",
  Passive: "bg-stone-100 text-stone-800",
  Other: "bg-gray-100 text-gray-800",
}
