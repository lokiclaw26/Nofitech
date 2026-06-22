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
  Radar,
  RefreshCw,
  Search,
  Sparkles,
  Wrench,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { fetchInventory, summarizeInventory, type ComponentItem } from "@/lib/inventory"

const quickActions = [
  { to: "/add", label: "Add a part", icon: Plus, tone: "bg-emerald-500" },
  { to: "/inventory", label: "Find a part", icon: Search, tone: "bg-sky-500" },
  { to: "/ideas", label: "Spin up ideas", icon: Lightbulb, tone: "bg-amber-500" },
]

function StatTile({
  icon,
  label,
  value,
  detail,
  tone,
}: {
  icon: ReactNode
  label: string
  value: string | number
  detail: string
  tone: string
}) {
  return (
    <motion.div
      whileHover={{ y: -4, rotate: -0.4 }}
      transition={{ duration: 0.18 }}
      className="control-surface animate-float-slow rounded-lg p-4"
    >
      <div className="flex items-start justify-between gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-md ${tone}`}>{icon}</div>
        <span className="live-dot" />
      </div>
      <div className="mt-4 text-3xl font-black text-slate-950 dark:text-white">{value}</div>
      <div className="mt-1 text-sm font-semibold text-slate-700 dark:text-slate-200">{label}</div>
      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{detail}</div>
    </motion.div>
  )
}

function MiniPart({ item }: { item: ComponentItem }) {
  return (
    <motion.div
      whileHover={{ x: 4 }}
      className="flex items-center justify-between gap-3 rounded-md border border-slate-900/10 bg-white/70 p-3 dark:border-white/10 dark:bg-white/5"
    >
      <div className="min-w-0">
        <div className="truncate text-sm font-bold text-slate-950 dark:text-white">{item.name}</div>
        <div className="truncate text-xs text-slate-500 dark:text-slate-400">{item.model_number || item.category || "Unlabeled model"}</div>
      </div>
      <div className="shrink-0 rounded-md bg-slate-950 px-2 py-1 text-xs font-bold text-white">
        x{item.quantity ?? 1}
      </div>
    </motion.div>
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
  const cleanupCount = summary.missingLocation.length + summary.missingImages.length + summary.lowStock.length
  const health = components.length
    ? Math.max(8, Math.round(100 - (cleanupCount / Math.max(1, components.length * 3)) * 100))
    : 0

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <section className="relative overflow-hidden rounded-lg border border-slate-900/10 bg-slate-950 p-5 text-white shadow-[0_24px_80px_rgba(15,23,42,0.25)] sm:p-7">
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-teal-400 via-amber-300 to-rose-400" />
        <motion.div
          aria-hidden
          className="absolute bottom-0 left-0 h-px w-1/3 bg-gradient-to-r from-transparent via-teal-300 to-transparent"
          animate={{ x: ["-40%", "340%"] }}
          transition={{ duration: 4.5, repeat: Infinity, ease: "linear" }}
        />
        <div className="absolute right-6 top-6 hidden h-28 w-28 rounded-full border border-white/10 md:block" />
        <div className="absolute right-16 top-16 hidden h-12 w-12 rounded-full border border-teal-300/30 md:block" />
        <div className="relative grid gap-6 lg:grid-cols-[1fr_360px] lg:items-end">
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
            <p className="inline-flex items-center gap-2 rounded-md bg-white/10 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-teal-100">
              <Radar className="h-3.5 w-3.5" />
              Workshop command deck
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-black leading-tight sm:text-5xl">
              Turn the parts you already own into the next build.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
              DIY HUB CODEX V2 maps your drawers, watches weak spots in the database, and matches inventory against project ideas.
            </p>
          </motion.div>

          <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-1">
            {quickActions.map((action) => {
              const Icon = action.icon
              return (
                <Button
                  key={action.to}
                  asChild
                  className="h-12 justify-start gap-3 border border-white/10 bg-white/10 text-white hover:bg-white/18"
                >
                  <Link to={action.to}>
                    <span className={`flex h-7 w-7 items-center justify-center rounded-md ${action.tone}`}>
                      <Icon className="h-4 w-4" />
                    </span>
                    {action.label}
                  </Link>
                </Button>
              )
            })}
          </div>
        </div>
      </section>

      {error && (
        <div className="mt-4 flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <span>{error}</span>
          <Button size="sm" variant="outline" onClick={() => void load()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </div>
      )}

      <section className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={<Boxes className="h-5 w-5 text-white" />}
          label="Parts in stock"
          value={loading ? "..." : summary.totalQuantity}
          detail="Total usable quantity"
          tone="bg-teal-600"
        />
        <StatTile
          icon={<Cpu className="h-5 w-5 text-white" />}
          label="Unique records"
          value={loading ? "..." : summary.uniqueCount}
          detail="Searchable components"
          tone="bg-slate-950"
        />
        <StatTile
          icon={<MapPin className="h-5 w-5 text-white" />}
          label="Need locations"
          value={loading ? "..." : summary.missingLocation.length}
          detail="Add drawer or bin names"
          tone="bg-amber-500"
        />
        <StatTile
          icon={<ImageOff className="h-5 w-5 text-white" />}
          label="Need images"
          value={loading ? "..." : summary.missingImages.length}
          detail="Visual search fuel"
          tone="bg-rose-500"
        />
      </section>

      <section className="mt-5 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="panel-surface rounded-lg p-4">
          <div className="mb-4 flex items-center justify-between gap-3">
          <div>
              <h2 className="text-base font-black text-slate-950 dark:text-white">Storage Signal</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">A quick read on where your parts are physically concentrated.</p>
            </div>
            <Button asChild size="sm" variant="outline">
              <Link to="/inventory">Open inventory</Link>
            </Button>
          </div>
          <div className="space-y-3">
            {summary.locations.slice(0, 7).map(([location, count], index) => {
              const max = Math.max(1, summary.locations[0]?.[1] ?? 1)
              return (
                <div key={location} className="rounded-md bg-slate-50 p-3 dark:bg-white/5">
                  <div className="mb-2 flex justify-between text-sm">
                    <span className="font-bold text-slate-800 dark:text-slate-200">{location}</span>
                    <span className="font-semibold text-slate-500 dark:text-slate-400">{count}</span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-white dark:bg-slate-950">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.max(8, (count / max) * 100)}%` }}
                      transition={{ duration: 0.5, delay: index * 0.04 }}
                      className="animate-meter h-3 rounded-full bg-gradient-to-r from-teal-500 via-amber-300 to-teal-500"
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
        </div>

        <div className="panel-surface rounded-lg p-4">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-black text-slate-950 dark:text-white">Inventory Health</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">Clean records make Idea Lab smarter.</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-amber-100 text-amber-700">
              <AlertTriangle className="h-5 w-5" />
            </div>
          </div>
          <div className="rounded-lg bg-slate-950 p-4 text-white">
            <div className="flex items-end justify-between">
              <div>
                <div className="text-4xl font-black">{loading ? "..." : `${health}%`}</div>
                <div className="text-xs font-semibold uppercase text-slate-400">Workbench readiness</div>
              </div>
              <Sparkles className="h-6 w-6 text-amber-300" />
            </div>
            <div className="mt-4 h-2 rounded-full bg-white/10">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${health}%` }}
                transition={{ duration: 0.5 }}
                className="animate-meter h-2 rounded-full bg-gradient-to-r from-rose-400 via-amber-300 to-teal-300"
              />
            </div>
          </div>
          <div className="mt-3 grid gap-2">
            <div className="rounded-md bg-amber-50 p-3 text-sm">
              <span className="font-bold text-amber-900">{summary.lowStock.length}</span>{" "}
              <span className="text-amber-800">low-stock records</span>
            </div>
            <div className="rounded-md bg-slate-50 p-3 text-sm">
              <span className="font-bold text-slate-900">{summary.manualCount}</span>{" "}
              <span className="text-slate-600 dark:text-slate-300">manual entries to enrich later</span>
            </div>
          </div>
        </div>
      </section>

      <section className="mt-5 grid gap-4 lg:grid-cols-2">
        <div className="panel-surface rounded-lg p-4">
          <div className="mb-3 flex items-center gap-2">
            <Wrench className="h-5 w-5 text-teal-700" />
            <h2 className="text-base font-black text-slate-950 dark:text-white">Top Categories</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {summary.categories.slice(0, 10).map(([category, count]) => (
              <span key={category} className="rounded-md border border-slate-900/10 bg-white px-2.5 py-1 text-sm font-semibold text-slate-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-200">
                {category} <span className="text-slate-400">{count}</span>
              </span>
            ))}
          </div>
        </div>
        <div className="panel-surface rounded-lg p-4">
          <h2 className="text-base font-black text-slate-950 dark:text-white">Recently Added</h2>
          <div className="mt-3 space-y-2">
            {recent.map((item) => (
              <MiniPart key={item.id} item={item} />
            ))}
            {!loading && recent.length === 0 && (
              <div className="rounded-md border border-dashed border-slate-300 py-6 text-center text-sm text-slate-500">
                No components yet.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
