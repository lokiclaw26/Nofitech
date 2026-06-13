# DIY-008 Argus Report (UX bug fixes)

## Live verification (operator-facing)

### Fix 1: Enter manually on every search
- [x] Empty-state dialog has "Enter manually" button (data-testid="btn-enter-manually") — REGRESSION OK
- [x] Confirm dialog (1 candidate) has "Enter manually instead" button (data-testid="btn-enter-manually-from-confirm")
- [x] Model picker dialog (2+ candidates) has "Enter manually instead" button (data-testid="btn-enter-manually-from-picker")
- [x] All 3 buttons call setShowManual(true) and resetManualForm()
- [x] All 3 buttons close the originating dialog before opening the manual one
- [x] Manual form opens with all fields empty (resetManualForm called)
- [x] Buttons do NOT auto-save the current picked candidate
- [x] Verified all 3 new data-testids are present in the Vite-served bundle

### Fix 2: View toggle on Inventory
- [x] View toggle is visible on the inventory page (between category filter and Add Component button)
- [x] "Cards" button (data-testid="inventory-view-cards") switches to grid view
- [x] "List" button (data-testid="inventory-view-list") switches to list view
- [x] View is persisted in localStorage (key: "diy-hub-v1-inventory-view")
- [x] Default is "cards" if no preference is set
- [x] Both views show all 24 components from the DB
- [x] List view: 48x48 image area, name (bold), model, mfr, category chip, qty+location, source+confidence badges
- [x] Cards view: 200px+ image area, full details (unchanged from Stage 7)

## SUMMARY
**Argus: 12/12 PASS — STAGE 8 SHIPPED**
