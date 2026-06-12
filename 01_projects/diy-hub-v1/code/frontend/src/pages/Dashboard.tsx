import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8780"

export default function Dashboard() {
  const [health, setHealth] = useState<string>("loading…")
  const [pages, setPages] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setError(null)
    try {
      const h = await fetch(`${API_URL}/api/health`).then((r) => r.json())
      setHealth(JSON.stringify(h))
      const p = await fetch(`${API_URL}/api/pages`).then((r) => r.json())
      setPages(p)
    } catch (e) {
      setError(String(e))
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <motion.h1
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-3xl font-bold mb-2"
      >
        Dashboard
      </motion.h1>
      <p className="text-slate-600 mb-6">
        Stage 1 navigable shell. This page proves the stack is wired end-to-end
        by calling the FastAPI backend.
      </p>

      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="bg-red-500 text-white rounded-lg p-6 shadow"
      >
        <div className="text-xs uppercase tracking-wider opacity-80">
          Tailwind pipeline
        </div>
        <div className="text-2xl font-semibold mt-1">
          bg-red-500 — if this is red, Tailwind is live.
        </div>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-4 mt-6">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.15 }}
          className="border rounded-lg p-4 bg-white"
        >
          <div className="text-sm text-slate-500">Backend /api/health</div>
          <pre className="font-mono text-sm mt-1 break-all">{health}</pre>
          {error && (
            <div className="text-red-600 text-sm mt-2">Error: {error}</div>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="border rounded-lg p-4 bg-white"
        >
          <div className="text-sm text-slate-500">Backend /api/pages</div>
          <ul className="mt-1 space-y-1">
            {pages.length === 0 && <li className="text-slate-400">…</li>}
            {pages.map((p) => (
              <li key={p} className="text-sm">
                • {p}
              </li>
            ))}
          </ul>
        </motion.div>
      </div>

      <div className="mt-6 flex gap-2">
        <Button onClick={load}>Refresh</Button>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Reload page
        </Button>
      </div>
    </div>
  )
}
