/**
 * ManualImageInput — DIY-016 (Stage 13 follow-up).
 *
 * A controlled dialog that lets NOFI attach an image to a component that
 * didn't get one from the live lookup. Mirrors the existing Dialog /
 * AnimatePresence / motion pattern used elsewhere in AddComponent.tsx.
 *
 * Two ways to provide an image:
 *   - Upload tab: pick a file from disk (multipart/form-data via uploadImage)
 *   - URL tab:    paste a public URL (JSON via setImageUrl, backend downloads)
 *
 * Props
 *   componentId       numeric DB id of the target component (required).
 *   currentImagePath  optional existing image to show in the preview area.
 *   onSaved(newPath)  called after a successful upload with the new path.
 *   onCancel()        called when the dialog should close without saving.
 *
 * On success: parent closes the modal and updates local candidate state.
 * On error:   an inline red message appears; the modal stays open so NOFI
 *             can fix the input or retry.
 */
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
import { uploadImage, setImageUrl } from "@/lib/api"

type Tab = "upload" | "url"

interface ManualImageInputProps {
  componentId: number
  currentImagePath?: string | null
  onSaved: (newImagePath: string) => void
  onCancel: () => void
}

// Match the panel animation timing used in AddComponent.tsx so dialogs
// feel like one design system.
const panelVariants = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1, transition: { duration: 0.15 } },
  exit: { opacity: 0, scale: 0.96, transition: { duration: 0.1 } },
}

export default function ManualImageInput({
  componentId,
  currentImagePath,
  onSaved,
  onCancel,
}: ManualImageInputProps) {
  const [tab, setTab] = useState<Tab>("upload")
  const [file, setFile] = useState<File | undefined>(undefined)
  const [filePreview, setFilePreview] = useState<string | undefined>(undefined)
  const [url, setUrl] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | undefined>(undefined)

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    setError(undefined)
    const f = e.target.files?.[0]
    if (!f) {
      setFile(undefined)
      setFilePreview(undefined)
      return
    }
    setFile(f)
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result === "string") {
        setFilePreview(reader.result)
      }
    }
    reader.readAsDataURL(f)
  }

  async function handleUpload() {
    if (!file || busy) return
    setBusy(true)
    setError(undefined)
    try {
      const updated = await uploadImage(componentId, file)
      const newPath =
        (updated.image_path as string | undefined) ??
        (updated.image_url as string | undefined) ??
        currentImagePath ??
        ""
      onSaved(newPath)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed")
      setBusy(false)
    }
  }

  async function handleSaveUrl() {
    if (!url.trim() || busy) return
    setBusy(true)
    setError(undefined)
    try {
      const updated = await setImageUrl(componentId, url.trim())
      const newPath =
        (updated.image_path as string | undefined) ??
        (updated.image_url as string | undefined) ??
        currentImagePath ??
        ""
      onSaved(newPath)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "URL save failed")
      setBusy(false)
    }
  }

  return (
    <Dialog open onOpenChange={(open) => { if (!open && !busy) onCancel() }}>
      <AnimatePresence>
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
            <div className="p-6 border-b border-slate-200">
              <DialogHeader>
                <DialogTitle>Add image</DialogTitle>
                <DialogDescription>
                  Attach a photo for component #{componentId}. Pick a file
                  from disk or paste a public image URL — the backend will
                  download it and store it locally.
                </DialogDescription>
              </DialogHeader>
            </div>

            <div className="p-6 space-y-4">
              {/* Tab buttons — plain because we don't ship @radix-ui/react-tabs */}
              <div className="flex gap-2 border-b border-slate-200 -mt-2 pb-0">
                <button
                  type="button"
                  data-testid="tab-upload"
                  onClick={() => { if (!busy) setTab("upload") }}
                  className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                    tab === "upload"
                      ? "border-slate-900 text-slate-900"
                      : "border-transparent text-slate-500 hover:text-slate-700"
                  }`}
                >
                  Upload file
                </button>
                <button
                  type="button"
                  data-testid="tab-url"
                  onClick={() => { if (!busy) setTab("url") }}
                  className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                    tab === "url"
                      ? "border-slate-900 text-slate-900"
                      : "border-transparent text-slate-500 hover:text-slate-700"
                  }`}
                >
                  Paste URL
                </button>
              </div>

              {tab === "upload" && (
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-slate-700">
                    Image file
                  </label>
                  <input
                    data-testid="image-file-input"
                    type="file"
                    accept="image/*"
                    onChange={handleFile}
                    disabled={busy}
                    className="block w-full text-sm text-slate-700 file:mr-3 file:py-2 file:px-3 file:rounded-md file:border file:border-slate-300 file:bg-white file:text-slate-700 hover:file:bg-slate-50"
                  />
                  {filePreview && (
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-2 flex justify-center">
                      <img
                        src={filePreview}
                        alt="preview"
                        className="max-h-48 max-w-full object-contain"
                      />
                    </div>
                  )}
                </div>
              )}

              {tab === "url" && (
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-slate-700">
                    Image URL
                  </label>
                  <input
                    data-testid="image-url-input"
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://example.com/photo.jpg"
                    disabled={busy}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                  />
                </div>
              )}

              {error && (
                <p
                  data-testid="image-input-error"
                  className="text-sm text-red-600"
                >
                  {error}
                </p>
              )}
            </div>

            <div className="p-4 border-t border-slate-200 flex justify-end gap-2">
              <Button
                variant="outline"
                disabled={busy}
                onClick={onCancel}
              >
                Cancel
              </Button>
              {tab === "upload" ? (
                <Button
                  data-testid="btn-upload-save"
                  disabled={!file || busy}
                  onClick={handleUpload}
                >
                  {busy ? "Saving..." : "Save image"}
                </Button>
              ) : (
                <Button
                  data-testid="btn-url-save"
                  disabled={!url.trim() || busy}
                  onClick={handleSaveUrl}
                >
                  {busy ? "Saving..." : "Save image"}
                </Button>
              )}
            </div>
          </motion.div>
        </DialogContent>
      </AnimatePresence>
    </Dialog>
  )
}