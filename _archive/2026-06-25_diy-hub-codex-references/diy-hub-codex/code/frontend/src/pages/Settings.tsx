import { useEffect, useMemo, useState } from "react"
import { Download, FileJson, RefreshCw, Save, TableProperties, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { API_BASE } from "@/lib/url"
import { fetchInventory, summarizeInventory, type ComponentItem } from "@/lib/inventory"

const sampleCsv = `name,model_number,category,quantity,location,manufacturer,voltage,interfaces,tags,description
ESP32 DevKit V1,ESP32-WROOM-32,Microcontroller,3,Drawer A,Espressif,3.3V,"WiFi; Bluetooth; GPIO","esp32; wifi","Main dev board"`

function downloadText(filename: string, text: string, type: string) {
  const blob = new Blob([text], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function csvEscape(value: unknown) {
  const raw = Array.isArray(value) ? value.join("; ") : String(value ?? "")
  return /[",\n]/.test(raw) ? `"${raw.split('"').join('""')}"` : raw
}

function splitCsvLine(line: string) {
  const cells: string[] = []
  let cell = ""
  let quoted = false
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i]
    const next = line[i + 1]
    if (char === '"' && quoted && next === '"') {
      cell += '"'
      i += 1
    } else if (char === '"') {
      quoted = !quoted
    } else if (char === "," && !quoted) {
      cells.push(cell.trim())
      cell = ""
    } else {
      cell += char
    }
  }
  cells.push(cell.trim())
  return cells
}

function parseList(value: string | undefined) {
  return (value ?? "")
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseCsv(text: string) {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  if (lines.length < 2) return []
  const headers = splitCsvLine(lines[0]).map((header) => header.toLowerCase())
  return lines.slice(1).map((line) => {
    const cells = splitCsvLine(line)
    const row = Object.fromEntries(headers.map((header, index) => [header, cells[index] ?? ""]))
    return {
      name: row.name || "",
      model_number: row.model_number || "Unknown",
      category: row.category || "Other",
      quantity: Math.max(1, Number(row.quantity) || 1),
      location: row.location || null,
      manufacturer: row.manufacturer || "",
      voltage: row.voltage || "",
      interfaces: parseList(row.interfaces),
      tags: parseList(row.tags),
      key_specs: parseList(row.key_specs),
      description: row.description || "",
      image_url: row.image_url || null,
      source: "manual",
    }
  }).filter((row) => row.name.trim())
}

export default function Settings() {
  const [components, setComponents] = useState<ComponentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [csv, setCsv] = useState(sampleCsv)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
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
  const parsedRows = useMemo(() => parseCsv(csv), [csv])

  function exportJson() {
    downloadText("diy-hub-inventory.json", JSON.stringify({ exported_at: new Date().toISOString(), components }, null, 2), "application/json")
  }

  function exportCsv() {
    const headers = ["id", "name", "model_number", "category", "quantity", "location", "manufacturer", "voltage", "interfaces", "tags", "description"]
    const rows = components.map((item) => {
      const row: Record<string, unknown> = {
        id: item.id,
        name: item.name,
        model_number: item.model_number,
        category: item.category,
        quantity: item.quantity,
        location: item.location,
        manufacturer: item.manufacturer,
        voltage: item.voltage,
        interfaces: item.interfaces,
        tags: item.tags,
        description: item.description,
      }
      return headers.map((header) => csvEscape(row[header])).join(",")
    })
    downloadText("diy-hub-inventory.csv", [headers.join(","), ...rows].join("\n"), "text/csv")
  }

  async function importCsv() {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      if (parsedRows.length === 0) throw new Error("No valid component rows found")
      for (const row of parsedRows) {
        const res = await fetch(`${API_BASE}/api/components`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(row),
        })
        if (!res.ok) {
          const text = await res.text()
          throw new Error(`Import failed for ${row.name}: ${text || res.status}`)
        }
      }
      setMessage(`Imported ${parsedRows.length} component${parsedRows.length === 1 ? "" : "s"}`)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <div className="mb-6">
        <p className="text-sm font-medium uppercase tracking-wide text-teal-700">Settings</p>
        <h1 className="mt-1 text-3xl font-bold text-slate-950">Data tools</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          Import batches, export backups, and keep the component database tidy.
        </p>
      </div>

      {(error || message) && (
        <div className={`mb-4 rounded-lg border p-3 text-sm ${error ? "border-red-200 bg-red-50 text-red-700" : "border-teal-200 bg-teal-50 text-teal-800"}`}>
          {error || message}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-slate-950">Database Snapshot</h2>
              <p className="text-sm text-slate-500">Quick health check before importing or exporting.</p>
            </div>
            <Button size="sm" variant="outline" onClick={() => void load()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-2xl font-semibold text-slate-950">{loading ? "..." : summary.uniqueCount}</div>
              <div className="text-sm text-slate-500">component records</div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-2xl font-semibold text-slate-950">{loading ? "..." : summary.totalQuantity}</div>
              <div className="text-sm text-slate-500">total quantity</div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-2xl font-semibold text-slate-950">{loading ? "..." : summary.missingLocation.length}</div>
              <div className="text-sm text-slate-500">missing locations</div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-2xl font-semibold text-slate-950">{loading ? "..." : summary.missingImages.length}</div>
              <div className="text-sm text-slate-500">missing images</div>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <Button variant="outline" onClick={exportJson} disabled={components.length === 0}>
              <FileJson className="mr-2 h-4 w-4" />
              Export JSON
            </Button>
            <Button variant="outline" onClick={exportCsv} disabled={components.length === 0}>
              <Download className="mr-2 h-4 w-4" />
              Export CSV
            </Button>
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <Upload className="h-5 w-5 text-teal-700" />
            <div>
              <h2 className="text-base font-semibold text-slate-950">Bulk CSV Import</h2>
              <p className="text-sm text-slate-500">Paste rows from a spreadsheet. Use semicolons inside list fields.</p>
            </div>
          </div>
          <textarea
            value={csv}
            onChange={(e) => setCsv(e.target.value)}
            className="min-h-[280px] w-full rounded-md border border-slate-300 p-3 font-mono text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400"
            spellCheck={false}
          />
          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <TableProperties className="h-4 w-4" />
              {parsedRows.length} valid row{parsedRows.length === 1 ? "" : "s"} detected
            </div>
            <Button onClick={() => void importCsv()} disabled={busy || parsedRows.length === 0}>
              <Save className="mr-2 h-4 w-4" />
              {busy ? "Importing..." : "Import rows"}
            </Button>
          </div>
        </section>
      </div>
    </div>
  )
}
