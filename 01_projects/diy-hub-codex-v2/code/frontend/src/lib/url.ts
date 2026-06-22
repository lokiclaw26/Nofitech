/**
 * URL helpers for building absolute URLs from backend-relative paths.
 *
 * Why: Vite dev server (port 5173) does NOT proxy /api/* to the FastAPI
 * backend (port 8780). Any image src like "/api/images/foo.jpg" will 404
 * silently in dev mode. In production, the SPA could be served from the
 * same origin as the API and relative paths would work, but for now we
 * always go through the absolute API_BASE.
 *
 * Stage 9: added because cards in Inventory.tsx were showing
 * "No image" even though the backend was serving 75KB JPEGs.
 */
const API_BASE: string =
  (import.meta.env.VITE_API_URL as string | undefined) ??
  `${window.location.protocol}//${window.location.hostname}:8780`

/**
 * Build an absolute URL for a backend-relative path such as
 * "/api/images/foo.jpg". Returns null for null/empty input so callers
 * can do `{imageUrl(c.image_url) ? <img /> : <Placeholder />}`.
 */
export function imageUrl(path: string | null | undefined): string | null {
  if (!path) return null
  // Already absolute (http:// or https://) — leave as-is
  if (path.startsWith("http://") || path.startsWith("https://")) return path
  // Prepend API_BASE, ensuring exactly one slash between them
  if (path.startsWith("/")) return `${API_BASE}${path}`
  return `${API_BASE}/${path}`
}

export { API_BASE }
