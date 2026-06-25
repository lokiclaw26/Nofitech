/**
 * API helpers for image-related endpoints (DIY-015 / Stage 13).
 *
 * Two helpers here:
 *   - uploadImage(componentId, file)
 *       POST /api/components/<id>/image as multipart/form-data with a
 *       file field named ``image``. Used when NOFI picks a file from
 *       disk in the "Upload file" tab of ManualImageInput.
 *   - setImageUrl(componentId, url)
 *       POST /api/components/<id>/image as application/json with a
 *       ``{"url": "..."}`` body. Used when NOFI pastes an image URL in
 *       the "Paste URL" tab.
 *
 * Both return the updated component row (same shape as the rest of the
 * component API), or throw an Error with the server's 4xx detail.
 */

import { API_BASE } from "./url"

interface ApiError extends Error {
  status?: number
}

function _errFrom(status: number, body: string): ApiError {
  let detail = body
  try {
    const parsed = JSON.parse(body)
    if (parsed && typeof parsed.detail === "string") detail = parsed.detail
  } catch {
    /* body wasn't JSON */
  }
  const e = new Error(detail || `HTTP ${status}`) as ApiError
  e.status = status
  return e
}

/**
 * Upload a file as multipart/form-data to the manual-image endpoint.
 * The server stores it at ``data/images/<componentId>-<uuid8>.<ext>``
 * and updates the component row.
 */
export async function uploadImage(
  componentId: number,
  file: File,
  sourceUrl?: string | null,
): Promise<Record<string, unknown>> {
  const fd = new FormData()
  fd.append("image", file, file.name)
  if (sourceUrl) {
    fd.append("source_url", sourceUrl)
  }
  const res = await fetch(
    `${API_BASE}/api/components/${componentId}/image`,
    {
      method: "POST",
      body: fd,
      // Note: do NOT set Content-Type — the browser must add the
      // boundary itself for multipart/form-data.
    },
  )
  const text = await res.text()
  if (!res.ok) {
    throw _errFrom(res.status, text)
  }
  return JSON.parse(text)
}

/**
 * Send a URL to the manual-image endpoint, which downloads the image
 * server-side, validates the content-type, and saves it.
 */
export async function setImageUrl(
  componentId: number,
  url: string,
): Promise<Record<string, unknown>> {
  const res = await fetch(
    `${API_BASE}/api/components/${componentId}/image`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    },
  )
  const text = await res.text()
  if (!res.ok) {
    throw _errFrom(res.status, text)
  }
  return JSON.parse(text)
}