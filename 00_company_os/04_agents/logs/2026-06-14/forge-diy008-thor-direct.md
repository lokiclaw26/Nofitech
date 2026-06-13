# DIY-008 Forge Report (Thor-direct)

## Bugs reported by NOFI
1. "Enter manually" button only shows in empty-state dialog. When live search returns 1+ candidates, the confirm dialog has no way to bail to manual entry.
2. Inventory page is card-only. NOFI wants a list/card toggle (small image dense rows vs. large image cards).
3. Many old records have no images. (NOT a code bug — those records were saved before Stage 5's image lookup. Not in scope.)

## Files changed
- MODIFIED: code/frontend/src/pages/AddComponent.tsx
  - Added "Enter manually instead" button to the Confirm dialog footer (between Cancel and ADD TO DATABASE)
  - Added "Enter manually instead" button to the Model Picker dialog footer (left of Cancel)
  - Empty-state dialog already had "Enter manually" (regression test: still there)
  - All 3 buttons set showConfirm/picker/empty=false, setShowManual=true, resetManualForm()
- MODIFIED: code/frontend/src/pages/Inventory.tsx
  - Added `view` state, initialized from localStorage via getPref("inventory-view", "cards")
  - useEffect to persist view changes via setPref
  - Added view toggle UI (Cards/List button group) in the action bar with data-testids
  - Added new InventoryRow component (small 48x48 image, name, model, mfr, category chip, qty+location, source/confidence badges)
  - Switched the rendering: view === "cards" -> grid of InventoryCard, view === "list" -> list of InventoryRow
- NEW: code/frontend/src/lib/storage.ts (773 bytes)
  - getPref<T>(key, fallback): reads localStorage with try/catch
  - setPref(key, value): writes localStorage with try/catch
  - All keys prefixed with "diy-hub-v1-" to avoid collisions
