import { useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

// Stage 5: a candidate is what a live source returned. The shape is
// permissive — live sources return different fields, so all fields
// are optional. The merge step in live_search.py combines partials.
interface Candidate {
  id: string
  name: string
  model_number?: string
  category?: string
  voltage?: string
  interfaces?: string[]
  key_specs?: string[]
  tags?: string[]
  description?: string
  datasheet_url?: string
  source_url?: string
  image_url?: string | null
  image_source?: string | null
  image_attribution?: { author?: string; license?: string; source_url?: string } | null
  // Stage 5: live-source provenance
  confidence?: number
  matched_sources?: string[]
  wikidata_id?: string
  commons_filename?: string
  platformio_url?: string
  manufacturer?: string
  release_year?: string
  source?: "live" | "mock_fallback"
  wikipedia_title?: string
}

type Status = "idle" | "searching" | "saving" | "saved" | "error"

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ??
  `${window.location.protocol}//${window.location.hostname}:8780`

// ---------------------------------------------------------------------------
// Animation variants — all <300ms, no bounce, per NOFI's brief
// ---------------------------------------------------------------------------

const panelVariants = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1, transition: { duration: 0.15 } },
  exit: { opacity: 0, scale: 0.96, transition: { duration: 0.1 } },
}

const cardVariants = {
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.15 } },
  hover: { scale: 1.02, transition: { duration: 0.15 } },
  tap: { scale: 0.99, transition: { duration: 0.1 } },
}

// ---------------------------------------------------------------------------
// Small chip component for tags / interfaces / specs
// ---------------------------------------------------------------------------

function Chip({ label }: { label: string }) {
  return (
    <span className="inline-block px-2 py-1 rounded-full bg-slate-200 text-slate-700 text-xs font-medium mr-1 mb-1">
      {label}
    </span>
  )
}

// Renders the candidate's real image (or a "No real image found" empty
// state if the backend didn't return one). Uses a plain <img> tag with
// onError so 404s / network failures fall back gracefully — there is no
// SVG injection anywhere in this flow.
function CandidateImage({
  url,
  size = 200,
  source,
  attribution,
}: {
  url?: string | null
  size?: number
  source?: string | null
  attribution?: { author?: string; license?: string; source_url?: string } | null
}) {
  const [errored, setErrored] = useState(false)
  if (!url || errored) {
    return (
      <div
        className="rounded-lg overflow-hidden border border-slate-300 bg-slate-100 shrink-0 flex flex-col items-center justify-center text-slate-500"
        style={{ width: size, height: size }}
      >
        <svg
          className="w-12 h-12 mb-1"
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
        <span className="text-xs">No real image found</span>
      </div>
    )
  }
  return (
    <div className="flex flex-col items-start">
      <div
        className="rounded-lg overflow-hidden border border-slate-200 bg-slate-100 shrink-0"
        style={{ width: size, height: size }}
      >
        <img
          src={url}
          alt=""
          className="w-full h-full object-contain"
          onError={() => setErrored(true)}
          referrerPolicy="no-referrer"
        />
      </div>
      {source === "wikipedia" && (
        <p className="text-xs text-slate-500 mt-1">
          Source: Wikipedia{attribution?.license ? ` · ${attribution.license}` : ""}
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function AddComponent() {
  // Form state
  const [query, setQuery] = useState("")
  const [quantity, setQuantity] = useState(1)
  const [location, setLocation] = useState("")

  // Flow state
  const [searchResults, setSearchResults] = useState<Candidate[]>([])
  const [pickedCandidate, setPickedCandidate] = useState<Candidate | null>(null)
  const [showModelPicker, setShowModelPicker] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [showEmpty, setShowEmpty] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<Status>("idle")

  // Stage 7: manual entry state. The empty-state dialog now has 3 buttons:
  // Try offline mock fallback, Enter manually, Cancel. The manual form
  // opens in its own dialog (showManual).
  const [showManual, setShowManual] = useState(false)
  const [manualSaving, setManualSaving] = useState(false)
  // Manual form fields (per NOFI Stage 7 brief)
  const [manualName, setManualName] = useState("")
  const [manualModel, setManualModel] = useState("")
  const [manualManufacturer, setManualManufacturer] = useState("")
  const [manualCategory, setManualCategory] = useState("Other")
  const [manualQty, setManualQty] = useState(1)
  const [manualLocation, setManualLocation] = useState("")
  const [manualVoltage, setManualVoltage] = useState("")
  const [manualInterfaces, setManualInterfaces] = useState("")
  const [manualKeySpecs, setManualKeySpecs] = useState("")
  const [manualTags, setManualTags] = useState("")
  const [manualDescription, setManualDescription] = useState("")
  const [manualImageUrl, setManualImageUrl] = useState("")

  function resetManualForm() {
    setManualName("")
    setManualModel("")
    setManualManufacturer("")
    setManualCategory("Other")
    setManualQty(1)
    setManualLocation("")
    setManualVoltage("")
    setManualInterfaces("")
    setManualKeySpecs("")
    setManualTags("")
    setManualDescription("")
    setManualImageUrl("")
  }

  const formValid = query.trim() !== ""

  // -----------------------------------------------------------------------
  // Step 1: search (live lookup, then optional mock fallback)
  // -----------------------------------------------------------------------
  async function handleAdd() {
    if (!formValid) return
    setError(null)
    setStatus("searching")
    try {
      const res = await fetch(`${API_BASE}/api/components/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() }),
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Search failed (${res.status}): ${text}`)
      }
      const data = await res.json()
      const candidates: Candidate[] = data.candidates ?? []
      setSearchResults(candidates)
      if (candidates.length === 0) {
        setShowEmpty(true)
      } else if (candidates.length === 1) {
        setPickedCandidate(candidates[0])
        setShowConfirm(true)
      } else {
        setShowModelPicker(true)
      }
      setStatus("idle")
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Search failed"
      setError(msg)
      setStatus("error")
    }
  }

  // Operator-triggered mock fallback (only from the empty-state dialog)
  async function handleMockFallback() {
    setError(null)
    setStatus("searching")
    try {
      const res = await fetch(`${API_BASE}/api/components/mock-fallback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() }),
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Fallback failed (${res.status}): ${text}`)
      }
      const data = await res.json()
      const candidates: Candidate[] = data.candidates ?? []
      setSearchResults(candidates)
      setShowEmpty(false)
      if (candidates.length === 1) {
        setPickedCandidate(candidates[0])
        setShowConfirm(true)
      } else if (candidates.length > 1) {
        setShowModelPicker(true)
      }
      setStatus("idle")
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Fallback failed"
      setError(msg)
      setStatus("error")
    }
  }

  // -----------------------------------------------------------------------
  // Step 2: confirmation -> save
  // -----------------------------------------------------------------------
  async function handleSave() {
    if (!pickedCandidate) return
    setError(null)
    setStatus("saving")
    try {
      const res = await fetch(`${API_BASE}/api/components`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: pickedCandidate.name,
          model_number: pickedCandidate.model_number ?? "Unknown",
          category: pickedCandidate.category ?? "Other",
          quantity: quantity,
          location: location.trim() || null,
          voltage: pickedCandidate.voltage ?? "",
          interfaces: pickedCandidate.interfaces ?? [],
          key_specs: pickedCandidate.key_specs ?? [],
          tags: pickedCandidate.tags ?? [],
          description: pickedCandidate.description ?? "",
          datasheet_url: pickedCandidate.datasheet_url ?? "",
          source_url: pickedCandidate.source_url ?? "",
          image_url: pickedCandidate.image_url ?? null,
          // Stage 5: live-source provenance
          wikidata_id: pickedCandidate.wikidata_id ?? null,
          commons_filename: pickedCandidate.commons_filename ?? null,
          manufacturer: pickedCandidate.manufacturer ?? null,
          release_year: pickedCandidate.release_year ?? null,
          confidence: pickedCandidate.confidence ?? null,
          source: pickedCandidate.source ?? "live",
        }),
      })
      if (res.status === 400) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || "Validation failed (400)")
      }
      if (!res.ok) {
        throw new Error(`Save failed (${res.status})`)
      }
      // Success: show success animation, then close + reset.
      setStatus("saved")
      setShowSuccess(true)
      window.setTimeout(() => {
        setShowSuccess(false)
        setShowConfirm(false)
        setPickedCandidate(null)
        setQuery("")
        setQuantity(1)
        setLocation("")
        setError(null)
        setStatus("idle")
      }, 1500)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Save failed"
      setError(msg)
      setStatus("error")
    }
  }

  // -----------------------------------------------------------------------
  // Stage 7: Manual entry save
  // -----------------------------------------------------------------------
  async function handleManualSave() {
    setError(null)
    // Validate required fields
    const name = manualName.trim()
    const model = manualModel.trim()
    if (!name) {
      setError("Name is required")
      return
    }
    if (!model) {
      setError("Model number is required")
      return
    }
    if (manualQty < 1) {
      setError("Quantity must be >= 1")
      return
    }
    setManualSaving(true)
    try {
      // Helper: split a comma-separated chip input into a clean array
      const splitChips = (s: string) =>
        s.split(",")
          .map((x) => x.trim())
          .filter((x) => x.length > 0)

      const payload = {
        name,
        model_number: model,
        manufacturer: manualManufacturer.trim() || "",
        category: manualCategory || "Other",
        quantity: manualQty,
        location: manualLocation.trim() || null,
        voltage: manualVoltage.trim() || "",
        interfaces: splitChips(manualInterfaces),
        key_specs: splitChips(manualKeySpecs),
        tags: splitChips(manualTags),
        description: manualDescription.trim() || "",
        image_url: manualImageUrl.trim() || null,
        source: "manual",
      }
      const res = await fetch(`${API_BASE}/api/components`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (res.status === 400) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || "Validation failed (400)")
      }
      if (!res.ok) {
        throw new Error(`Save failed (${res.status})`)
      }
      // Success: close the manual dialog and reset
      setShowManual(false)
      setShowEmpty(false)
      resetManualForm()
      // Use the existing success animation flow
      setShowSuccess(true)
      window.setTimeout(() => {
        setShowSuccess(false)
      }, 1500)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Manual save failed")
    } finally {
      setManualSaving(false)
    }
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <motion.h1
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-3xl font-bold mb-2"
      >
        Add Component
      </motion.h1>
      <p className="text-slate-600 mb-6">
        Search a live online database, pick a model from the real candidates found,
        and save it to your inventory. Real images and specs come from Wikimedia,
        Wikidata, Wikipedia, PlatformIO, and public GitHub repos.
      </p>

      {/* ------------------- Form ------------------- */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.05 }}
        className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Component <span className="text-red-500">*</span>
            </label>
            <input
              data-testid="input-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. ESP32 DevKit V1, Arduino Uno, Raspberry Pi 4, LM358"
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
            />
            <p className="text-xs text-slate-500 mt-1">
              Just type the component. The system identifies the model, fetches specs, and asks you to pick if there are multiple matches.
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Quantity
            </label>
            <input
              data-testid="input-qty"
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))}
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Location
            </label>
            <input
              data-testid="input-loc"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Drawer A"
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
            />
          </div>
        </div>

        {error && (
          <p data-testid="form-error" className="mt-4 text-sm text-red-600">
            {error}
          </p>
        )}

        <div className="mt-6 flex justify-end">
          <Button
            data-testid="btn-add"
            disabled={!formValid || status === "searching" || status === "saving"}
            onClick={handleAdd}
          >
            {status === "searching" ? "Searching..." : "Add"}
          </Button>
        </div>
      </motion.div>

      {/* ------------------- Model picker dialog ------------------- */}
      <Dialog open={showModelPicker} onOpenChange={setShowModelPicker}>
        <AnimatePresence>
          {showModelPicker && (
            <DialogContent
              forceMount
              // We use Framer Motion as the source of truth; suppress shadcn
              // built-in tailwindcss-animate transitions via a no-op class.
              className="max-w-2xl border border-slate-200 !p-0 overflow-hidden"
              // Avoid Radix + framer double-animation: hide built-in
              // open/close classes by overriding with no animation duration.
              style={{ animation: "none" }}
            >
              <motion.div
                variants={panelVariants}
                initial="initial"
                animate="animate"
                exit="exit"
              >
                <div className="p-6 border-b border-slate-200">
                  <DialogHeader>
                    <DialogTitle>Select a model</DialogTitle>
                    <DialogDescription>
                      {searchResults.length} match
                      {searchResults.length === 1 ? "" : "es"} for &quot;
                      {query.trim()}&quot;
                    </DialogDescription>
                  </DialogHeader>
                </div>
                <div className="p-4 max-h-[60vh] overflow-y-auto">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {searchResults.map((c) => (
                      <motion.button
                        key={c.id}
                        type="button"
                        variants={cardVariants}
                        initial="initial"
                        animate="animate"
                        whileHover="hover"
                        whileTap="tap"
                        onClick={() => {
                          setPickedCandidate(c)
                          setShowModelPicker(false)
                          setShowConfirm(true)
                        }}
                        className="text-left p-3 border border-slate-200 rounded-lg hover:border-slate-400 hover:shadow-sm bg-white"
                      >
                        <div className="flex gap-3 items-center">
                          <CandidateImage
                            url={c.image_url ?? null}
                            source={c.image_source ?? null}
                            attribution={c.image_attribution ?? null}
                            size={48}
                          />
                          <div className="min-w-0 flex-1">
                            <div className="font-medium text-sm truncate">
                              {c.name}
                            </div>
                            <div className="text-xs text-slate-500 truncate">
                              {c.model_number ?? "Unknown"} &middot; {c.category ?? "Other"}
                            </div>
                            {c.matched_sources && c.matched_sources.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {c.matched_sources.slice(0, 3).map((src) => (
                                  <span
                                    key={src}
                                    className="inline-block px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-medium"
                                  >
                                    {src}
                                  </span>
                                ))}
                                {c.confidence != null && (
                                  <span
                                    className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                      c.confidence >= 0.7
                                        ? "bg-green-100 text-green-800"
                                        : c.confidence >= 0.4
                                        ? "bg-amber-100 text-amber-800"
                                        : "bg-red-100 text-red-800"
                                    }`}
                                  >
                                    {Math.round(c.confidence * 100)}%
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </motion.button>
                    ))}
                  </div>
                </div>
                <div className="p-4 border-t border-slate-200 flex justify-end">
                  <Button variant="outline" onClick={() => setShowModelPicker(false)}>
                    Cancel
                  </Button>
                </div>
              </motion.div>
            </DialogContent>
          )}
        </AnimatePresence>
      </Dialog>

      {/* ------------------- Empty state dialog ------------------- */}
      <Dialog open={showEmpty} onOpenChange={setShowEmpty}>
        <AnimatePresence>
          {showEmpty && (
            <DialogContent
              forceMount
              className="max-w-md border border-slate-200 !p-0 overflow-hidden"
              style={{ animation: "none" }}
            >
              <motion.div
                variants={panelVariants}
                initial="initial"
                animate="animate"
                exit="exit"
              >
                <div className="p-6 text-center">
                  <DialogHeader>
                    <DialogTitle>No reliable live result found</DialogTitle>
                    <DialogDescription>
                      Live lookup returned no candidates for &quot;{query.trim()}&quot;.
                      You can try the offline mock fallback, or enter the component manually.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="mt-6 flex flex-col gap-2 items-stretch">
                    <Button
                      data-testid="btn-mock-fallback"
                      variant="outline"
                      onClick={handleMockFallback}
                      disabled={status === "searching"}
                    >
                      {status === "searching" ? "Searching..." : "Try offline mock fallback"}
                    </Button>
                    <Button
                      data-testid="btn-enter-manually"
                      variant="outline"
                      onClick={() => {
                        setShowEmpty(false)
                        setShowManual(true)
                      }}
                    >
                      Enter manually
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => setShowEmpty(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </motion.div>
            </DialogContent>
          )}
        </AnimatePresence>
      </Dialog>

      {/* ------------------- Confirmation dialog ------------------- */}
      <Dialog
        open={showConfirm}
        onOpenChange={(open) => {
          if (!open && status !== "saving" && !showSuccess) {
            setShowConfirm(false)
            setPickedCandidate(null)
          }
        }}
      >
        <AnimatePresence>
          {showConfirm && pickedCandidate && (
            <DialogContent
              forceMount
              className="max-w-2xl border border-slate-200 !p-0 overflow-hidden"
              style={{ animation: "none" }}
            >
              <motion.div
                variants={panelVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                className="relative"
              >
                {/* Green flash on success */}
                <AnimatePresence>
                  {showSuccess && (
                    <motion.div
                      initial={{ backgroundColor: "rgba(34,197,94,0)" }}
                      animate={{ backgroundColor: "rgba(34,197,94,0.25)" }}
                      exit={{ backgroundColor: "rgba(34,197,94,0)" }}
                      transition={{ duration: 0.2 }}
                      className="absolute inset-0 pointer-events-none z-10"
                    />
                  )}
                </AnimatePresence>

                <div className="p-6 border-b border-slate-200">
                  <DialogHeader>
                    <DialogTitle>Confirm component details</DialogTitle>
                    <DialogDescription>
                      Review the live lookup result, then click ADD TO DATABASE to save.
                    </DialogDescription>
                  </DialogHeader>
                </div>

                <div className="p-6">
                  <div className="flex flex-col sm:flex-row gap-6">
                    {/* Image */}
                    <div className="shrink-0 self-start">
                      <CandidateImage
                        url={pickedCandidate.image_url ?? null}
                        source={pickedCandidate.image_source ?? null}
                        attribution={pickedCandidate.image_attribution ?? null}
                        size={200}
                      />
                    </div>

                    {/* Spec fields */}
                    <div className="flex-1 min-w-0 space-y-3 text-sm">
                      <Field label="Name" value={pickedCandidate.name ?? ""} />
                      <Field label="Model" value={pickedCandidate.model_number ?? "Unknown"} />
                      <Field label="Category" value={pickedCandidate.category ?? "Other"} />
                      <Field label="Voltage" value={pickedCandidate.voltage ?? ""} />
                      <Field
                        label="Source"
                        value={pickedCandidate.source === "mock_fallback" ? "Offline mock fallback" : "Live internet lookup"}
                      />
                      <Field
                        label="Confidence"
                        value={
                          pickedCandidate.confidence != null
                            ? `${(pickedCandidate.confidence * 100).toFixed(0)}%`
                            : "—"
                        }
                      />

                      {pickedCandidate.description && (
                        <div>
                          <div className="text-xs font-semibold text-slate-500 uppercase mb-1">
                            Description
                          </div>
                          <p className="text-slate-700 text-sm leading-relaxed">
                            {pickedCandidate.description}
                          </p>
                        </div>
                      )}

                      {(pickedCandidate.interfaces ?? []).length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-slate-500 uppercase mb-1">
                            Interfaces
                          </div>
                          <div>
                            {(pickedCandidate.interfaces ?? []).map((s) => (
                              <Chip key={s} label={s} />
                            ))}
                          </div>
                        </div>
                      )}

                      {(pickedCandidate.key_specs ?? []).length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-slate-500 uppercase mb-1">
                            Key specs
                          </div>
                          <div>
                            {(pickedCandidate.key_specs ?? []).map((s) => (
                              <Chip key={s} label={s} />
                            ))}
                          </div>
                        </div>
                      )}

                      {(pickedCandidate.tags ?? []).length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-slate-500 uppercase mb-1">
                            Tags
                          </div>
                          <div>
                            {(pickedCandidate.tags ?? []).map((s) => (
                              <Chip key={s} label={s} />
                            ))}
                          </div>
                        </div>
                      )}

                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase mb-1">
                          Links
                        </div>
                        <div className="flex flex-col gap-1">
                          {pickedCandidate.datasheet_url && (
                            <a
                              href={pickedCandidate.datasheet_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-slate-700 hover:underline text-sm"
                            >
                              Datasheet &rarr;
                            </a>
                          )}
                          {pickedCandidate.source_url && (
                            <a
                              href={pickedCandidate.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-slate-700 hover:underline text-sm"
                            >
                              Source &rarr;
                            </a>
                          )}
                          {pickedCandidate.wikidata_id && (
                            <a
                              href={`https://www.wikidata.org/wiki/${pickedCandidate.wikidata_id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-slate-700 hover:underline text-sm"
                            >
                              Wikidata &rarr;
                            </a>
                          )}
                          {pickedCandidate.platformio_url && (
                            <a
                              href={pickedCandidate.platformio_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-slate-700 hover:underline text-sm"
                            >
                              PlatformIO &rarr;
                            </a>
                          )}
                          {!pickedCandidate.datasheet_url &&
                            !pickedCandidate.source_url &&
                            !pickedCandidate.wikidata_id &&
                            !pickedCandidate.platformio_url && (
                              <span className="text-slate-400 text-sm">
                                No links for this entry.
                              </span>
                            )}
                        </div>
                      </div>

                      {(pickedCandidate.matched_sources ?? []).length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-slate-500 uppercase mb-1">
                            Live sources
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {(pickedCandidate.matched_sources ?? []).map((src) => (
                              <span
                                key={src}
                                className="inline-block px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-xs font-medium"
                              >
                                {src}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {error && (
                    <p className="mt-4 text-sm text-red-600">{error}</p>
                  )}
                </div>

                <div className="p-4 border-t border-slate-200 flex justify-between items-center">
                  <div className="text-sm text-slate-600">
                    Qty <span className="font-medium">{quantity}</span>
                    {location.trim() && (
                      <>
                        {" "}
                        &middot; Loc <span className="font-medium">{location.trim()}</span>
                      </>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      disabled={status === "saving" || showSuccess}
                      onClick={() => {
                        setShowConfirm(false)
                        setPickedCandidate(null)
                        setError(null)
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      data-testid="btn-save"
                      disabled={status === "saving" || showSuccess}
                      onClick={handleSave}
                    >
                      {status === "saving" ? "Saving..." : "ADD TO DATABASE"}
                    </Button>
                  </div>
                </div>

                {/* Success check mark overlay */}
                <AnimatePresence>
                  {showSuccess && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      className="absolute inset-0 flex items-center justify-center pointer-events-none z-20"
                    >
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ duration: 0.25, ease: "easeOut" }}
                        className="w-20 h-20 rounded-full bg-green-500 text-white flex items-center justify-center shadow-lg"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className="w-10 h-10"
                        >
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      </motion.div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            </DialogContent>
          )}
        </AnimatePresence>
      </Dialog>

      {/* ------------------- Manual entry dialog (Stage 7) ------------------- */}
      <Dialog open={showManual} onOpenChange={(open) => {
        if (!open && !manualSaving) {
          setShowManual(false)
          resetManualForm()
        }
      }}>
        <AnimatePresence>
          {showManual && (
            <DialogContent
              forceMount
              className="max-w-2xl border border-slate-200 !p-0 overflow-hidden"
              style={{ animation: "none" }}
            >
              <motion.div
                variants={panelVariants}
                initial="initial"
                animate="animate"
                exit="exit"
              >
                <div className="p-6 border-b border-slate-200">
                  <DialogHeader>
                    <DialogTitle>Enter component manually</DialogTitle>
                    <DialogDescription>
                      Type the details you know. Leave optional fields blank.
                      This record is saved with source = &quot;manual&quot;.
                    </DialogDescription>
                  </DialogHeader>
                </div>

                <div className="p-6 max-h-[60vh] overflow-y-auto">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Name <span className="text-red-500">*</span>
                      </label>
                      <input
                        data-testid="manual-name"
                        value={manualName}
                        onChange={(e) => setManualName(e.target.value)}
                        placeholder="e.g. Wemos D1 Mini"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Model number <span className="text-red-500">*</span>
                      </label>
                      <input
                        data-testid="manual-model"
                        value={manualModel}
                        onChange={(e) => setManualModel(e.target.value)}
                        placeholder="e.g. D1 Mini V3.1.0"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Manufacturer
                      </label>
                      <input
                        data-testid="manual-manufacturer"
                        value={manualManufacturer}
                        onChange={(e) => setManualManufacturer(e.target.value)}
                        placeholder="e.g. Wemos"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Category
                      </label>
                      <select
                        data-testid="manual-category"
                        value={manualCategory}
                        onChange={(e) => setManualCategory(e.target.value)}
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      >
                        <option value="Microcontroller">Microcontroller</option>
                        <option value="Sensor">Sensor</option>
                        <option value="Display">Display</option>
                        <option value="Motor">Motor</option>
                        <option value="Regulator">Regulator</option>
                        <option value="Op-amp">Op-amp</option>
                        <option value="Connector">Connector</option>
                        <option value="Passive">Passive</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Quantity <span className="text-red-500">*</span>
                      </label>
                      <input
                        data-testid="manual-qty"
                        type="number"
                        min={1}
                        value={manualQty}
                        onChange={(e) => setManualQty(Math.max(1, Number(e.target.value) || 1))}
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Location
                      </label>
                      <input
                        data-testid="manual-location"
                        value={manualLocation}
                        onChange={(e) => setManualLocation(e.target.value)}
                        placeholder="e.g. Drawer A"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Voltage
                      </label>
                      <input
                        data-testid="manual-voltage"
                        value={manualVoltage}
                        onChange={(e) => setManualVoltage(e.target.value)}
                        placeholder="e.g. 3.3V"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Interfaces <span className="text-xs text-slate-500">(comma-separated)</span>
                      </label>
                      <input
                        data-testid="manual-interfaces"
                        value={manualInterfaces}
                        onChange={(e) => setManualInterfaces(e.target.value)}
                        placeholder="e.g. I2C, SPI, UART, USB"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Key specs <span className="text-xs text-slate-500">(comma-separated)</span>
                      </label>
                      <input
                        data-testid="manual-key-specs"
                        value={manualKeySpecs}
                        onChange={(e) => setManualKeySpecs(e.target.value)}
                        placeholder="e.g. 80 MHz, 4MB flash"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Tags <span className="text-xs text-slate-500">(comma-separated)</span>
                      </label>
                      <input
                        data-testid="manual-tags"
                        value={manualTags}
                        onChange={(e) => setManualTags(e.target.value)}
                        placeholder="e.g. esp8266, wifi, smd"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Description
                      </label>
                      <textarea
                        data-testid="manual-description"
                        value={manualDescription}
                        onChange={(e) => setManualDescription(e.target.value)}
                        rows={3}
                        placeholder="Free-form notes, e.g. 'ESP8266-based WiFi board, breadboard-friendly, 4MB flash'"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Image URL <span className="text-xs text-slate-500">(optional, will be downloaded)</span>
                      </label>
                      <input
                        data-testid="manual-image-url"
                        value={manualImageUrl}
                        onChange={(e) => setManualImageUrl(e.target.value)}
                        placeholder="https://example.com/photo.jpg"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                      />
                    </div>
                  </div>

                  {error && (
                    <p data-testid="manual-error" className="mt-4 text-sm text-red-600">
                      {error}
                    </p>
                  )}
                </div>

                <div className="p-4 border-t border-slate-200 flex justify-between items-center">
                  <div className="text-xs text-slate-500">
                    Saved with source = &quot;manual&quot;
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      disabled={manualSaving}
                      onClick={() => {
                        setShowManual(false)
                        resetManualForm()
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      data-testid="btn-manual-save"
                      disabled={manualSaving}
                      onClick={handleManualSave}
                    >
                      {manualSaving ? "Saving..." : "Save to inventory"}
                    </Button>
                  </div>
                </div>
              </motion.div>
            </DialogContent>
          )}
        </AnimatePresence>
      </Dialog>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Local helper
// ---------------------------------------------------------------------------

function Field({ label, value }: { label: string; value: string | undefined }) {
  return (
    <div>
      <div className="text-xs font-semibold text-slate-500 uppercase">{label}</div>
      <div className="text-sm text-slate-800">{value || "—"}</div>
    </div>
  )
}
