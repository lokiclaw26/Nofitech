import { useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { CATEGORIES, isCategory, categoryColor } from "@/lib/categories"
import { sourceBadge, confidenceBadge } from "@/lib/sources"
import { getPref, setPref } from "@/lib/storage"
import { imageUrl, API_BASE } from "@/lib/url"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Component {
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

// ---------------------------------------------------------------------------
// Small chip
// ---------------------------------------------------------------------------

function Chip({ label, color }: { label: string; color?: string }) {
  const cls = color ?? "bg-slate-200 text-slate-700"
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium mr-1 mb-1 ${cls}`}
    >
      {label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Card view (large image, all details)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Stage 9: inline quantity editor (click to edit, Enter or blur to save)
// ---------------------------------------------------------------------------

function QuantityEditor({
  value,
  onSave,
  size = "md",
}: {
  value: number
  onSave: (n: number) => Promise<void> | void
  size?: "sm" | "md"
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(String(value))
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  // Keep draft in sync if the upstream value changes (e.g. after a save)
  useEffect(() => {
    if (!editing) setDraft(String(value))
  }, [value, editing])

  const start = () => {
    setDraft(String(value))
    setErr(null)
    setEditing(true)
  }
  const cancel = () => {
    setEditing(false)
    setDraft(String(value))
    setErr(null)
  }
  const commit = async () => {
    const n = parseInt(draft, 10)
    if (Number.isNaN(n) || n < 1) {
      setErr("must be >= 1")
      return
    }
    if (n === value) {
      setEditing(false)
      return
    }
    setBusy(true)
    setErr(null)
    try {
      await onSave(n)
      setEditing(false)
    } catch (e) {
      setErr(e instanceof Error ? e.message : "save failed")
    } finally {
      setBusy(false)
    }
  }

  const sizeCls = size === "sm" ? "text-xs px-1.5 py-0.5 w-12" : "text-sm px-2 py-1 w-20"

  if (!editing) {
    return (
      <button
        type="button"
        data-testid="qty-edit-button"
        onClick={start}
        className={`${sizeCls} bg-slate-100 hover:bg-slate-200 text-slate-800 rounded font-medium transition-colors`}
        title="Click to edit quantity"
      >
        Qty {value}
      </button>
    )
  }

  return (
    <div className="flex items-center gap-1" data-testid="qty-edit-input">
      <input
        type="number"
        min={1}
        value={draft}
        autoFocus
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault()
            void commit()
          } else if (e.key === "Escape") {
            e.preventDefault()
            cancel()
          }
        }}
        onBlur={() => void commit()}
        disabled={busy}
        className={`${sizeCls} border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:opacity-50`}
      />
      {err && <span className="text-red-600 text-xs">{err}</span>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Stage 9: small delete button + handler
// ---------------------------------------------------------------------------

function DeleteButton({
  onClick,
  size = "md",
  testid = "delete-button",
}: {
  onClick: () => void
  size?: "sm" | "md"
  testid?: string
}) {
  const cls =
    size === "sm"
      ? "p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded"
      : "p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded"
  return (
    <button
      type="button"
      data-testid={testid}
      onClick={(e) => {
        e.stopPropagation()
        onClick()
      }}
      className={cls}
      title="Delete component"
      aria-label="Delete component"
    >
      <svg className={size === "sm" ? "w-3.5 h-3.5" : "w-4 h-4"} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3"
        />
      </svg>
    </button>
  )
}

function InventoryCard({ c, onQuantityChange, onDeleteClick }: { c: Component; onQuantityChange: (id: number, n: number) => Promise<void>; onDeleteClick: (c: Component) => void }) {
  const src = sourceBadge(c.source)
  const conf = confidenceBadge(c.confidence)
  const cat = c.category && isCategory(c.category) ? c.category : null
  const catColor = cat ? categoryColor[cat] : "bg-gray-100 text-gray-800"

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden flex flex-col"
      data-testid="inventory-card"
    >
      {/* Image area */}
      <div className="relative bg-slate-100 h-44 flex items-center justify-center">
        {imageUrl(c.image_url) ? (
          <img
            src={imageUrl(c.image_url)!}
            alt={c.name}
            className="max-h-full max-w-full object-contain"
            loading="lazy"
            referrerPolicy="no-referrer"
            onError={(e) => {
              // Swap to placeholder on load error
              (e.currentTarget as HTMLImageElement).style.display = "none"
            }}
          />
        ) : (
          <div className="text-slate-400 text-sm flex flex-col items-center">
            <svg
              className="w-10 h-10 mb-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <span>No image</span>
          </div>
        )}
        {/* Source + confidence badges overlay (top-right) */}
        <div className="absolute top-2 right-2 flex flex-col gap-1 items-end">
          <Chip label={src.label} color={src.color} />
          <Chip label={conf.label} color={conf.color} />
        </div>
      </div>

      {/* Body */}
      <div className="p-3 flex-1 flex flex-col gap-2 text-sm">
        <div>
          <div className="font-semibold text-slate-900 truncate" title={c.name}>
            {c.name}
          </div>
          {c.model_number && (
            <div className="text-xs text-slate-500 truncate" title={c.model_number}>
              {c.model_number}
            </div>
          )}
        </div>

        <div className="text-xs text-slate-600 space-y-0.5">
          {c.manufacturer && (
            <div>
              <span className="text-slate-400">Mfr: </span>
              <span className="text-slate-700">{c.manufacturer}</span>
            </div>
          )}
          {c.voltage && (
            <div>
              <span className="text-slate-400">V: </span>
              <span className="text-slate-700">{c.voltage}</span>
            </div>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-slate-400">Qty:</span>
            <QuantityEditor
              value={c.quantity ?? 1}
              onSave={(n) => onQuantityChange(c.id, n)}
            />
            {c.location && (
              <span className="text-slate-700 truncate" title={c.location}>
                · {c.location}
              </span>
            )}
          </div>
        </div>

        {cat && (
          <div className="flex flex-wrap">
            <Chip label={cat} color={catColor} />
          </div>
        )}

        {(c.interfaces ?? []).length > 0 && (
          <div className="flex flex-wrap">
            {(c.interfaces ?? []).slice(0, 4).map((s) => (
              <Chip key={s} label={s} />
            ))}
            {(c.interfaces ?? []).length > 4 && (
              <Chip label={`+${(c.interfaces ?? []).length - 4} more`} />
            )}
          </div>
        )}

        {(c.tags ?? []).length > 0 && (
          <div className="flex flex-wrap">
            {(c.tags ?? []).slice(0, 4).map((s) => (
              <Chip key={s} label={`#${s}`} color="bg-slate-100 text-slate-600" />
            ))}
            {(c.tags ?? []).length > 4 && (
              <Chip label={`+${(c.tags ?? []).length - 4} more`} />
            )}
          </div>
        )}
      </div>
      {/* Stage 9: footer with delete button */}
      <div className="px-3 py-2 border-t border-slate-100 flex items-center justify-between bg-slate-50/40">
        <span className="text-xs text-slate-400">ID #{c.id}</span>
        <DeleteButton onClick={() => onDeleteClick(c)} testid="delete-button-card" />
      </div>
    </motion.div>
  )
}

// ---------------------------------------------------------------------------
// List view (small image, dense rows)
// ---------------------------------------------------------------------------

function InventoryRow({ c, onQuantityChange, onDeleteClick }: { c: Component; onQuantityChange: (id: number, n: number) => Promise<void>; onDeleteClick: (c: Component) => void }) {
  const src = sourceBadge(c.source)
  const conf = confidenceBadge(c.confidence)
  const cat = c.category && isCategory(c.category) ? c.category : null
  const catColor = cat ? categoryColor[cat] : "bg-gray-100 text-gray-800"
  return (
    <div
      data-testid="inventory-row"
      className="flex items-center gap-3 px-3 py-2 border-b border-slate-200 hover:bg-slate-50"
    >
      {/* Small image (48x48) */}
      <div className="w-12 h-12 bg-slate-100 rounded shrink-0 flex items-center justify-center overflow-hidden">
        {imageUrl(c.image_url) ? (
          <img
            src={imageUrl(c.image_url)!}
            alt={c.name}
            className="max-w-full max-h-full object-contain"
            loading="lazy"
            referrerPolicy="no-referrer"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).style.display = "none"
            }}
          />
        ) : (
          <svg
            className="w-5 h-5 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        )}
      </div>
      {/* Name + model */}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm text-slate-900 truncate" title={c.name}>
          {c.name}
        </div>
        <div className="text-xs text-slate-500 truncate" title={c.model_number ?? ""}>
          {c.model_number ?? "—"}
        </div>
      </div>
      {/* Manufacturer */}
      <div className="hidden md:block text-xs text-slate-600 w-32 truncate" title={c.manufacturer ?? ""}>
        {c.manufacturer ?? "—"}
      </div>
      {/* Category chip */}
      <div className="hidden sm:block w-32">
        {cat ? (
          <Chip label={cat} color={catColor} />
        ) : (
          <span className="text-xs text-slate-400">—</span>
        )}
      </div>
      {/* Qty + location (editable) */}
      <div className="hidden lg:flex text-xs text-slate-600 w-40 items-center gap-2">
        <QuantityEditor
          value={c.quantity ?? 1}
          onSave={(n) => onQuantityChange(c.id, n)}
          size="sm"
        />
        {c.location && <span className="truncate" title={c.location}>· {c.location}</span>}
      </div>
      {/* Badges */}
      <div className="flex gap-1 items-center shrink-0">
        <Chip label={src.label} color={src.color} />
        <Chip label={conf.label} color={conf.color} />
      </div>
      {/* Delete button (small in list view) */}
      <DeleteButton onClick={() => onDeleteClick(c)} size="sm" testid="delete-button-row" />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Inventory() {
  const [components, setComponents] = useState<Component[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [category, setCategory] = useState<string>("__all__")
  // Stage 8: view mode toggle (cards | list), persisted in localStorage
  const [view, setView] = useState<"cards" | "list">(
    () => getPref<"cards" | "list">("inventory-view", "cards")
  )
  // Stage 9: delete dialog state + transient toast
  const [pendingDelete, setPendingDelete] = useState<Component | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [toast, setToast] = useState<{ kind: "ok" | "err"; msg: string } | null>(null)

  // Persist view preference when changed
  useEffect(() => {
    setPref("inventory-view", view)
  }, [view])

  // Auto-dismiss toast after 3s
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 3000)
    return () => clearTimeout(t)
  }, [toast])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/components`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setComponents(data.components ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  // Stage 9: inline quantity save handler
  async function handleQuantityChange(id: number, n: number): Promise<void> {
    const res = await fetch(`${API_BASE}/api/components/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity: n }),
    })
    if (!res.ok) {
      const txt = await res.text().catch(() => "")
      throw new Error(`HTTP ${res.status} ${txt}`)
    }
    const updated = (await res.json()) as Component
    setComponents((prev) => prev.map((c) => (c.id === id ? updated : c)))
    setToast({ kind: "ok", msg: `Updated quantity to ${updated.quantity ?? n}` })
  }

  // Stage 9: confirm + delete
  async function confirmDelete(): Promise<void> {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      const res = await fetch(`${API_BASE}/api/components/${pendingDelete.id}`, {
        method: "DELETE",
      })
      if (!res.ok && res.status !== 204) {
        const txt = await res.text().catch(() => "")
        throw new Error(`HTTP ${res.status} ${txt}`)
      }
      setComponents((prev) => prev.filter((c) => c.id !== pendingDelete.id))
      setToast({ kind: "ok", msg: `Deleted "${pendingDelete.name}"` })
      setPendingDelete(null)
    } catch (e) {
      setToast({
        kind: "err",
        msg: e instanceof Error ? e.message : "delete failed",
      })
    } finally {
      setDeleting(false)
    }
  }

  // Distinct categories present in the loaded data (union with canonical list,
  // so the dropdown always shows the canonical categories too).
  const presentCategories = useMemo(() => {
    const fromData = new Set<string>()
    for (const c of components) {
      if (c.category) fromData.add(c.category)
    }
    // Union with the canonical list (so the dropdown is stable across reloads)
    const all = new Set([...CATEGORIES, ...Array.from(fromData)])
    return Array.from(all).sort()
  }, [components])

  // Filter
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return components.filter((c) => {
      // Category filter
      if (category !== "__all__" && c.category !== category) return false
      // Search filter (substring match on a bunch of fields)
      if (q) {
        const haystack = [
          c.name,
          c.model_number,
          c.category,
          c.location ?? "",
          c.manufacturer ?? "",
          c.description ?? "",
          ...(c.tags ?? []),
          ...(c.interfaces ?? []),
        ]
          .join(" ")
          .toLowerCase()
        if (!haystack.includes(q)) return false
      }
      return true
    })
  }, [components, search, category])

  const totalQty = useMemo(
    () => filtered.reduce((sum, c) => sum + (c.quantity ?? 1), 0),
    [filtered]
  )

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <motion.h1
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-3xl font-bold mb-2"
      >
        Inventory
      </motion.h1>
      <p className="text-slate-600 mb-6">
        All saved components. Search by name, model, tag, or location. Filter
        by category. Click a card to see source links and full details (coming
        in a later stage).
      </p>

      {/* Search + filter bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <input
          data-testid="inventory-search"
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, model, tag, location, notes..."
          className="flex-1 px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
        />
        <select
          data-testid="inventory-category-filter"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 min-w-[180px]"
        >
          <option value="__all__">All categories</option>
          {presentCategories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        {/* Stage 8: view toggle (cards | list) */}
        <div
          className="flex border border-slate-300 rounded-md overflow-hidden"
          role="group"
          aria-label="View mode"
          data-testid="inventory-view-toggle"
        >
          <button
            type="button"
            data-testid="inventory-view-cards"
            onClick={() => setView("cards")}
            className={`px-2 py-2 text-sm flex items-center gap-1 ${
              view === "cards"
                ? "bg-slate-800 text-white"
                : "bg-white text-slate-600 hover:bg-slate-50"
            }`}
            aria-pressed={view === "cards"}
            title="Card view (large images)"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zm10 0a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"
              />
            </svg>
            <span className="hidden sm:inline">Cards</span>
          </button>
          <button
            type="button"
            data-testid="inventory-view-list"
            onClick={() => setView("list")}
            className={`px-2 py-2 text-sm flex items-center gap-1 border-l border-slate-300 ${
              view === "list"
                ? "bg-slate-800 text-white"
                : "bg-white text-slate-600 hover:bg-slate-50"
            }`}
            aria-pressed={view === "list"}
            title="List view (small images, dense rows)"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
            <span className="hidden sm:inline">List</span>
          </button>
        </div>
        <Link to="/add">
          <Button data-testid="inventory-add-button">+ Add Component</Button>
        </Link>
      </div>

      {/* Status row */}
      <div className="text-sm text-slate-500 mb-3 flex items-center gap-3">
        {loading ? (
          <span>Loading inventory…</span>
        ) : error ? (
          <>
            <span className="text-red-600" data-testid="inventory-error">
              {error}
            </span>
            <Button size="sm" variant="outline" onClick={load}>
              Retry
            </Button>
          </>
        ) : (
          <>
            <span data-testid="inventory-count">
              {filtered.length} of {components.length} components
            </span>
            {filtered.length > 0 && (
              <span className="text-slate-400">
                · {totalQty} total in stock
              </span>
            )}
            {(search || category !== "__all__") && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setSearch("")
                  setCategory("__all__")
                }}
                data-testid="inventory-clear-filters"
              >
                Clear filters
              </Button>
            )}
          </>
        )}
      </div>

      {/* Empty states */}
      {!loading && !error && components.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          data-testid="inventory-empty-db"
          className="border-2 border-dashed border-slate-300 rounded-lg p-10 text-center bg-white"
        >
          <div className="text-slate-500 mb-4">
            <svg
              className="w-12 h-12 mx-auto mb-2 text-slate-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
              />
            </svg>
            <p className="text-lg font-medium text-slate-700">
              No components yet
            </p>
            <p className="text-sm mt-1">Add your first component.</p>
          </div>
          <Link to="/add">
            <Button>+ Add Component</Button>
          </Link>
        </motion.div>
      )}

      {!loading && !error && components.length > 0 && filtered.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          data-testid="inventory-empty-filtered"
          className="border rounded-lg p-8 text-center bg-white text-slate-500"
        >
          <p className="text-base font-medium text-slate-700 mb-1">
            No components match your filters
          </p>
          <p className="text-sm">
            Try clearing the search or selecting a different category.
          </p>
        </motion.div>
      )}

      {/* Card grid */}
      {!loading && !error && filtered.length > 0 && (
        view === "cards" ? (
          <div
            data-testid="inventory-grid"
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
          >
            {filtered.map((c) => (
              <InventoryCard
                key={c.id}
                c={c}
                onQuantityChange={handleQuantityChange}
                onDeleteClick={setPendingDelete}
              />
            ))}
          </div>
        ) : (
          <div
            data-testid="inventory-list"
            className="bg-white border border-slate-200 rounded-md overflow-hidden"
          >
            {filtered.map((c) => (
              <InventoryRow
                key={c.id}
                c={c}
                onQuantityChange={handleQuantityChange}
                onDeleteClick={setPendingDelete}
              />
            ))}
          </div>
        )
      )}

      {/* Stage 9: delete confirmation dialog */}
      <Dialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open && !deleting) setPendingDelete(null)
        }}
      >
        <DialogContent data-testid="delete-confirm-dialog">
          <DialogHeader>
            <DialogTitle>Delete component?</DialogTitle>
            <DialogDescription>
              {pendingDelete ? (
                <>
                  This will permanently remove{" "}
                  <span className="font-semibold text-slate-900">
                    {pendingDelete.name}
                  </span>{" "}
                  {pendingDelete.model_number ? (
                    <span className="text-slate-500">
                      ({pendingDelete.model_number})
                    </span>
                  ) : null}{" "}
                  from the inventory. This action cannot be undone.
                </>
              ) : null}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setPendingDelete(null)}
              disabled={deleting}
              data-testid="delete-cancel-button"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => void confirmDelete()}
              disabled={deleting}
              data-testid="delete-confirm-button"
            >
              {deleting ? "Deleting…" : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Stage 9: transient toast (success/error) */}
      {toast && (
        <div
          data-testid="inventory-toast"
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded shadow-lg text-sm font-medium ${
            toast.kind === "ok"
              ? "bg-emerald-600 text-white"
              : "bg-red-600 text-white"
          }`}
        >
          {toast.msg}
        </div>
      )}
    </div>
  )
}
