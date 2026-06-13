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

interface Candidate {
  id: string
  name: string
  model_number: string
  category: string
  voltage: string
  interfaces: string[]
  key_specs: string[]
  tags: string[]
  datasheet_url: string
  source_url: string
  mock_image_data: string
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

// Renders a candidate's SVG mock_image_data inline (it's a raw SVG string).
// The server-generated SVG has width="400" height="400" on the outer <svg>
// tag; we override just those two attributes (not the inner <rect>s) so the
// SVG scales to the container using its viewBox. Otherwise the natural 400x400
// overflows the dialog container and gets clipped (image appears missing).
// Hotfix 2.
function CandidateImage({ svg, size = 200 }: { svg: string; size?: number }) {
  // Match the FIRST <svg ...> tag only (not inner <rect>s).
  const scaled = svg.replace(
    /<svg([^>]*?)\swidth="[^"]*"/,
    '<svg$1 width="100%"',
  ).replace(
    /<svg([^>]*?)\sheight="[^"]*"/,
    '<svg$1 height="100%"',
  )
  return (
    <div
      className="rounded-lg overflow-hidden border border-slate-200 bg-slate-100 shrink-0"
      style={{ width: size, height: size }}
      // svg is generated server-side; safe to inject.
      dangerouslySetInnerHTML={{ __html: scaled }}
    />
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function AddComponent() {
  // Form state
  const [name, setName] = useState("")
  const [modelNumber, setModelNumber] = useState("")
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

  const formValid = name.trim() !== "" && modelNumber.trim() !== ""

  // -----------------------------------------------------------------------
  // Step 1: search
  // -----------------------------------------------------------------------
  async function handleAdd() {
    if (!formValid) return
    setError(null)
    setStatus("searching")
    try {
      const res = await fetch(`${API_BASE}/api/components/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          model_number: modelNumber.trim(),
        }),
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
          model_number: pickedCandidate.model_number,
          category: pickedCandidate.category,
          quantity: quantity,
          location: location.trim() || null,
          voltage: pickedCandidate.voltage,
          interfaces: pickedCandidate.interfaces,
          key_specs: pickedCandidate.key_specs,
          tags: pickedCandidate.tags,
          datasheet_url: pickedCandidate.datasheet_url,
          source_url: pickedCandidate.source_url,
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
        setName("")
        setModelNumber("")
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
        Search a local catalog, pick a model, and save it to your inventory.
        No network calls — everything is mocked locally.
      </p>

      {/* ------------------- Form ------------------- */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.05 }}
        className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Component name <span className="text-red-500">*</span>
            </label>
            <input
              data-testid="input-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. ESP32"
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Model number <span className="text-red-500">*</span>
            </label>
            <input
              data-testid="input-model"
              value={modelNumber}
              onChange={(e) => setModelNumber(e.target.value)}
              placeholder="e.g. DevKit V1"
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
            />
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
                      {name.trim()} {modelNumber.trim()}&quot;
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
                          <div
                            className="w-12 h-12 rounded overflow-hidden bg-slate-100 shrink-0 border border-slate-200"
                            dangerouslySetInnerHTML={{ __html: c.mock_image_data }}
                          />
                          <div className="min-w-0">
                            <div className="font-medium text-sm truncate">
                              {c.name}
                            </div>
                            <div className="text-xs text-slate-500 truncate">
                              {c.model_number} &middot; {c.category}
                            </div>
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
                    <DialogTitle>No matches</DialogTitle>
                    <DialogDescription>
                      No components found for &quot;{name.trim()} {modelNumber.trim()}&quot;.
                      Try a different name or model.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="mt-6 flex justify-center">
                    <Button onClick={() => setShowEmpty(false)}>OK</Button>
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
                    <DialogTitle>Confirm component</DialogTitle>
                    <DialogDescription>
                      Review the details below, then save to your inventory.
                    </DialogDescription>
                  </DialogHeader>
                </div>

                <div className="p-6">
                  <div className="flex flex-col sm:flex-row gap-6">
                    {/* Image */}
                    <div className="shrink-0 self-start">
                      <CandidateImage svg={pickedCandidate.mock_image_data} size={200} />
                    </div>

                    {/* Spec fields */}
                    <div className="flex-1 min-w-0 space-y-3 text-sm">
                      <Field label="Name" value={pickedCandidate.name} />
                      <Field label="Model" value={pickedCandidate.model_number} />
                      <Field label="Category" value={pickedCandidate.category} />
                      <Field label="Voltage" value={pickedCandidate.voltage} />

                      {pickedCandidate.interfaces.length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-slate-500 uppercase mb-1">
                            Interfaces
                          </div>
                          <div>
                            {pickedCandidate.interfaces.map((s) => (
                              <Chip key={s} label={s} />
                            ))}
                          </div>
                        </div>
                      )}

                      {pickedCandidate.key_specs.length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-slate-500 uppercase mb-1">
                            Key specs
                          </div>
                          <div>
                            {pickedCandidate.key_specs.map((s) => (
                              <Chip key={s} label={s} />
                            ))}
                          </div>
                        </div>
                      )}

                      {pickedCandidate.tags.length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-slate-500 uppercase mb-1">
                            Tags
                          </div>
                          <div>
                            {pickedCandidate.tags.map((s) => (
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
                          {!pickedCandidate.datasheet_url &&
                            !pickedCandidate.source_url && (
                              <span className="text-slate-400 text-sm">
                                No links for this entry.
                              </span>
                            )}
                        </div>
                      </div>
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
                      {status === "saving" ? "Saving..." : "Add to database"}
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
    </div>
  )
}

// ---------------------------------------------------------------------------
// Local helper
// ---------------------------------------------------------------------------

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs font-semibold text-slate-500 uppercase">{label}</div>
      <div className="text-sm text-slate-800">{value}</div>
    </div>
  )
}
