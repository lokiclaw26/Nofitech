import { useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import { Grid2X2, List, Plus, Search, SlidersHorizontal, Trash2 } from "lucide-react"
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
      className={`mb-1 mr-1 inline-block rounded-md px-2 py-0.5 text-xs font-bold ${cls}`}
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
        className={`${sizeCls} rounded-md bg-slate-950 text-white font-bold transition hover:-translate-y-0.5 hover:bg-teal-700`}
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
        className={`${sizeCls} rounded-md border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-teal-400 disabled:opacity-50`}
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
      className={`${cls} transition hover:-translate-y-0.5`}
      title="Delete component"
      aria-label="Delete component"
    >
      <Trash2 className={size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4"} />
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
      whileHover={{ y: -5 }}
      transition={{ duration: 0.2 }}
      className="group flex flex-col overflow-hidden rounded-lg border border-slate-900/10 bg-white/90 shadow-[0_12px_34px_rgba(15,23,42,0.08)] backdrop-blur dark:border-white/10 dark:bg-slate-900/80"
      data-testid="inventory-card"
    >
      {/* Image area */}
      <div className="relative flex h-44 items-center justify-center overflow-hidden bg-gradient-to-br from-slate-100 via-white to-teal-50 dark:from-slate-950 dark:via-slate-900 dark:to-teal-950/50">
        <div className="metal-line absolute inset-x-0 top-0 h-6 opacity-60" />
        <motion.div
          aria-hidden
          className="absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-transparent via-white/35 to-transparent opacity-0 transition group-hover:opacity-100 dark:via-teal-200/10"
          animate={{ x: ["-120%", "520%"] }}
          transition={{ duration: 3.6, repeat: Infinity, ease: "linear" }}
        />
        {imageUrl(c.image_url) ? (
          <img
            src={imageUrl(c.image_url)!}
            alt={c.name}
            className="max-h-full max-w-full object-contain transition duration-300 group-hover:scale-105"
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
        <div className="absolute right-2 top-2 flex flex-col items-end gap-1">
          <Chip label={src.label} color={src.color} />
          <Chip label={conf.label} color={conf.color} />
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-1 flex-col gap-2 p-3 text-sm">
        <div>
          <div className="truncate font-black text-slate-950 dark:text-white" title={c.name}>
            {c.name}
          </div>
          {c.model_number && (
            <div className="truncate text-xs text-slate-500 dark:text-slate-400" title={c.model_number}>
              {c.model_number}
            </div>
          )}
        </div>

        <div className="space-y-0.5 text-xs text-slate-600 dark:text-slate-300">
          {c.manufacturer && (
            <div>
              <span className="text-slate-400">Mfr: </span>
              <span className="text-slate-700 dark:text-slate-300">{c.manufacturer}</span>
            </div>
          )}
          {c.voltage && (
            <div>
              <span className="text-slate-400">V: </span>
              <span className="text-slate-700 dark:text-slate-300">{c.voltage}</span>
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
      <div className="flex items-center justify-between border-t border-slate-900/10 bg-slate-50/80 px-3 py-2 dark:border-white/10 dark:bg-white/5">
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
      className="flex items-center gap-3 border-b border-slate-900/10 px-3 py-2 transition hover:bg-teal-50/50 dark:border-white/10 dark:hover:bg-teal-400/10"
    >
      {/* Small image (48x48) */}
      <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-md border border-slate-900/10 bg-gradient-to-br from-white to-slate-100 dark:border-white/10 dark:from-slate-950 dark:to-slate-900">
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
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <motion.section
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="panel-surface mb-5 rounded-lg p-5"
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="inline-flex items-center gap-2 rounded-md bg-teal-50 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-teal-800">
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Parts finder
            </p>
            <h1 className="mt-3 text-3xl font-black text-slate-950 dark:text-white">Inventory</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-400">
              Search across names, models, tags, specs, interfaces, and storage locations. Flip between visual inspection and dense shelf mode.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:flex">
            <div className="rounded-md bg-slate-950 px-3 py-2 text-white dark:bg-white dark:text-slate-950">
              <div className="text-lg font-black">{loading ? "..." : components.length}</div>
              <div className="text-[11px] font-semibold uppercase text-slate-400 dark:text-slate-500">records</div>
            </div>
            <div className="rounded-md bg-amber-100 px-3 py-2 text-amber-950">
              <div className="text-lg font-black">{loading ? "..." : totalQty}</div>
              <div className="text-[11px] font-semibold uppercase text-amber-700">in stock</div>
            </div>
          </div>
        </div>
      </motion.section>

      {/* Search + filter bar */}
      <div className="panel-surface mb-5 flex flex-col gap-3 rounded-lg p-3 sm:flex-row">
        <label className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            data-testid="inventory-search"
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, model, tag, location, notes..."
            className="h-11 w-full rounded-md border border-slate-900/10 bg-white pl-9 pr-3 text-sm font-medium outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
          />
        </label>
        <select
          data-testid="inventory-category-filter"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="h-11 min-w-[180px] rounded-md border border-slate-900/10 bg-white px-3 text-sm font-semibold outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
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
          className="flex h-11 overflow-hidden rounded-md border border-slate-900/10 bg-white"
          role="group"
          aria-label="View mode"
          data-testid="inventory-view-toggle"
        >
          <button
            type="button"
            data-testid="inventory-view-cards"
            onClick={() => setView("cards")}
            className={`flex items-center gap-1 px-3 py-2 text-sm font-bold transition ${
              view === "cards"
                ? "bg-slate-950 text-white"
                : "bg-white text-slate-600 hover:bg-slate-50"
            }`}
            aria-pressed={view === "cards"}
            title="Card view (large images)"
          >
            <Grid2X2 className="h-4 w-4" />
            <span className="hidden sm:inline">Cards</span>
          </button>
          <button
            type="button"
            data-testid="inventory-view-list"
            onClick={() => setView("list")}
            className={`flex items-center gap-1 border-l border-slate-900/10 px-3 py-2 text-sm font-bold transition ${
              view === "list"
                ? "bg-slate-950 text-white"
                : "bg-white text-slate-600 hover:bg-slate-50"
            }`}
            aria-pressed={view === "list"}
            title="List view (small images, dense rows)"
          >
            <List className="h-4 w-4" />
            <span className="hidden sm:inline">List</span>
          </button>
        </div>
        <Link to="/add">
          <Button data-testid="inventory-add-button" className="h-11 gap-2 bg-teal-700 hover:bg-teal-800">
            <Plus className="h-4 w-4" />
            Add
          </Button>
        </Link>
      </div>

      {/* Status row */}
      <div className="mb-3 flex flex-wrap items-center gap-3 text-sm text-slate-500">
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
          className="rounded-lg border-2 border-dashed border-slate-300 bg-white/80 p-10 text-center"
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
          className="rounded-lg border border-slate-900/10 bg-white/80 p-8 text-center text-slate-500"
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
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
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
            className="overflow-hidden rounded-lg border border-slate-900/10 bg-white/90 shadow-[0_12px_34px_rgba(15,23,42,0.08)] backdrop-blur dark:border-white/10 dark:bg-slate-900/80"
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
