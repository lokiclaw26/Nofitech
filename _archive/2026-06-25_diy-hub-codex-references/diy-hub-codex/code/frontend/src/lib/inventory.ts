import { API_BASE } from "./url"

export interface ComponentItem {
  id: number
  name: string
  model_number?: string
  category?: string
  quantity?: number
  location?: string | null
  voltage?: string
  interfaces?: string[]
  key_specs?: string[]
  tags?: string[]
  description?: string
  manufacturer?: string | null
  confidence?: number | null
  source?: string
  image_url?: string | null
  image_path?: string | null
  wikidata_id?: string | null
  commons_filename?: string | null
  source_url?: string | null
  datasheet_url?: string | null
  created_at?: string
  updated_at?: string
}

export interface InventoryResponse {
  components: ComponentItem[]
  total: number
}

export async function fetchInventory(): Promise<ComponentItem[]> {
  const res = await fetch(`${API_BASE}/api/components`)
  if (!res.ok) throw new Error(`Inventory request failed (${res.status})`)
  const data = (await res.json()) as Partial<InventoryResponse>
  return Array.isArray(data.components) ? data.components : []
}

export function quantityOf(component: ComponentItem): number {
  return Math.max(0, Number(component.quantity ?? 1) || 0)
}

export function componentText(component: ComponentItem): string {
  return [
    component.name,
    component.model_number,
    component.category,
    component.location ?? "",
    component.manufacturer ?? "",
    component.description ?? "",
    component.voltage ?? "",
    ...(component.tags ?? []),
    ...(component.interfaces ?? []),
    ...(component.key_specs ?? []),
  ]
    .join(" ")
    .toLowerCase()
}

export function summarizeInventory(components: ComponentItem[]) {
  const totalQuantity = components.reduce((sum, item) => sum + quantityOf(item), 0)
  const categories = new Map<string, number>()
  const locations = new Map<string, number>()
  const lowStock = components
    .filter((item) => quantityOf(item) <= 2)
    .sort((a, b) => quantityOf(a) - quantityOf(b))

  for (const item of components) {
    categories.set(item.category || "Unsorted", (categories.get(item.category || "Unsorted") ?? 0) + 1)
    locations.set(item.location || "No location", (locations.get(item.location || "No location") ?? 0) + quantityOf(item))
  }

  return {
    totalQuantity,
    uniqueCount: components.length,
    categories: [...categories.entries()].sort((a, b) => b[1] - a[1]),
    locations: [...locations.entries()].sort((a, b) => b[1] - a[1]),
    lowStock,
    missingLocation: components.filter((item) => !item.location),
    missingImages: components.filter((item) => !item.image_url && !item.image_path),
    manualCount: components.filter((item) => item.source === "manual").length,
  }
}
