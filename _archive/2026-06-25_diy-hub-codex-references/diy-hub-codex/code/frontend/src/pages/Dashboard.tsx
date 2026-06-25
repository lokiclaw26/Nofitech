import { useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"
import { Link } from "react-router-dom"
import { motion } from "framer-motion"
import {
  AlertTriangle,
  Boxes,
  Cpu,
  ImageOff,
  Lightbulb,
  MapPin,
  Plus,
  RefreshCw,
  Search,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { fetchInventory, summarizeInventory, type ComponentItem } from "@/lib/inventory"

function StatTile({
  icon,
  label,
  value,
  tone,
}: {
  icon: ReactNode
  label: string
  value: string | number
  tone: string
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className={`mb-3 inline-flex h-9 w-9 items-center justify-center rounded-md ${tone}`}>
        {icon}
      </div>
      <div className="text-2xl font-semibold text-slate-950">{value}</div>
      <div className="mt-1 text-sm text-slate-500">{label}</div>
    </div>
  )
}

export default function Dashboard() {
  const [components, setComponents] = useState<ComponentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setComponents(await fetchInventory())
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load inventory")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const summary = useMemo(() => summarizeInventory(components), [components])
  const recent = components.slice(0, 5)

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <p className="text-sm font-medium uppercase tracking-wide text-teal-700">Workshop inventory</p>
          <h1 className="mt-1 text-3xl font-bold text-slate-950">DIY Hub</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            A practical map of what you own, where it is stored, and what you can build from it.
          </p>
        </motion.div>
        <div className="flex flex-wrap gap-2">
          <Button asChild>
            <Link to="/add">
              <Plus className="mr-2 h-4 w-4" />
              Add Component
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/inventory">
              <Search className="mr-2 h-4 w-4" />
              Find Parts
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/ideas">
              <Lightbulb className="mr-2 h-4 w-4" />
              Ideas
            </Link>
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <span>{error}</span>
          <Button size="sm" variant="outline" onClick={() => void load()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={<Boxes className="h-5 w-5" />}
          label="Total parts in stock"
          value={loading ? "..." : summary.totalQuantity}
          tone="bg-teal-100 text-teal-800"
        />
        <StatTile
          icon={<Cpu className="h-5 w-5" />}
          label="Unique component records"
          value={loading ? "..." : summary.uniqueCount}
          tone="bg-indigo-100 text-indigo-800"
        />
        <StatTile
          icon={<MapPin className="h-5 w-5" />}
          label="Items missing a location"
          value={loading ? "..." : summary.missingLocation.length}
          tone="bg-amber-100 text-amber-800"
        />
        <StatTile
          icon={<ImageOff className="h-5 w-5" />}
          label="Records without images"
          value={loading ? "..." : summary.missingImages.length}
          tone="bg-rose-100 text-rose-800"
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-slate-950">Storage Map</h2>
              <p className="text-sm text-slate-500">Where your parts are concentrated.</p>
            </div>
            <Button asChild size="sm" variant="outline">
              <Link to="/inventory">Open inventory</Link>
            </Button>
          </div>
          <div className="space-y-3">
            {summary.locations.slice(0, 7).map(([location, count]) => {
              const max = Math.max(1, summary.locations[0]?.[1] ?? 1)
              return (
                <div key={location}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="font-medium text-slate-700">{location}</span>
                    <span className="text-slate-500">{count}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-teal-600"
                      style={{ width: `${Math.max(8, (count / max) * 100)}%` }}
                    />
                  </div>
                </div>
              )
            })}
            {!loading && summary.locations.length === 0 && (
              <div className="rounded-md border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
                Add components with locations to build your storage map.
              </div>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-950">Needs Attention</h2>
              <p className="text-sm text-slate-500">Small cleanup tasks that make the database more useful.</p>
            </div>
            <AlertTriangle className="h-5 w-5 text-amber-600" />
          </div>
          <div className="space-y-3">
            <div className="rounded-md bg-amber-50 p-3">
              <div className="text-sm font-medium text-amber-900">{summary.lowStock.length} low-stock records</div>
              <div className="mt-1 text-xs text-amber-800">Quantity is 1 or 2. Useful for reorder planning.</div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-sm font-medium text-slate-900">{summary.missingLocation.length} missing locations</div>
              <div className="mt-1 text-xs text-slate-600">Add drawer, bin, shelf, or box names to make search physical.</div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-sm font-medium text-slate-900">{summary.manualCount} manual entries</div>
              <div className="mt-1 text-xs text-slate-600">Manual rows are fine, but images and specs make Idea Lab stronger.</div>
            </div>
          </div>
        </section>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-base font-semibold text-slate-950">Top Categories</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {summary.categories.slice(0, 10).map(([category, count]) => (
              <span key={category} className="rounded-md bg-slate-100 px-2.5 py-1 text-sm text-slate-700">
                {category} <span className="text-slate-500">{count}</span>
              </span>
            ))}
          </div>
        </section>
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-base font-semibold text-slate-950">Recently Added</h2>
          <div className="mt-3 divide-y divide-slate-100">
            {recent.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <div className="min-w-0">
                  <div className="truncate font-medium text-slate-900">{item.name}</div>
                  <div className="truncate text-xs text-slate-500">{item.model_number || item.category || "No model"}</div>
                </div>
                <span className="shrink-0 rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-700">Qty {item.quantity ?? 1}</span>
              </div>
            ))}
            {!loading && recent.length === 0 && (
              <div className="py-6 text-center text-sm text-slate-500">No components yet.</div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
