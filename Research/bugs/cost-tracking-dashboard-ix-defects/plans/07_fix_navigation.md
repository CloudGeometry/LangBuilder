---
skill: serious-plan
slug: fix-navigation
status: active
parent: Research/bugs/cost-tracking-dashboard-ix-defects
created: 2026-03-17
---

# Plan 07: Fix Navigation (NAV-1, NAV-2, NAV-3, NAV-4)

**Bugs:** NAV-1 (wrong placement), NAV-2 (wrong mechanism), NAV-3 (no feature flag), NAV-4 (no PageLayout)
**Priority:** 7 (UX polish)
**Depends on:** None (frontend only, independent of backend plans)
**Research:** `Research/bugs/cost-tracking-dashboard-ix-defects/thread-1-navigation-architecture.md`

---

## Task 0: Smoke test — confirm current state

Verify the Usage link currently exists as a bare `<Link>` in the AppHeader at lines 86-92 of:
`src/frontend/src/components/core/appHeaderComponent/index.tsx`

Confirm it navigates to `/usage` and that `UsagePage` renders without a back button or PageLayout wrapper.

---

## Task 1: Remove Usage link from AppHeader (NAV-1, NAV-2)

**File:** `src/frontend/src/components/core/appHeaderComponent/index.tsx`

Delete lines 86-92 (the `<Link to="/usage">...</Link>` block):

```tsx
// DELETE these lines:
        <Link
          to="/usage"
          className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors"
          data-testid="usage-tab"
        >
          Usage
        </Link>
```

Then remove the `Link` import from `react-router-dom` (line 18) — no other usage of `Link` remains in this file. The file already imports `useCustomNavigate` (line 14) which is the correct navigation mechanism used by everything else.

> **AMENDMENT (review verdict):** Update tests that reference the removed `usage-tab` link:
> - **Delete** `src/frontend/src/components/core/appHeaderComponent/__tests__/AppHeader.usage-nav.test.tsx` — it asserts `usage-tab` link in the header, which no longer exists.
> - **Update** `src/frontend/tests/extended/features/usage-dashboard.spec.ts` line 54 — change from clicking `[data-testid="usage-tab"]` to navigating via `page.goto("/usage")` or clicking through the Account Menu (e.g., click the profile avatar, then click `[data-testid="menu_usage_button"]`).

---

## Task 2: Add Usage to Account Menu (NAV-1, NAV-2)

**File:** `src/frontend/src/components/core/appHeaderComponent/components/AccountMenu/index.tsx`

Add a `HeaderMenuItemButton` after the Settings entry (after line 98, before the `isAdmin` block at line 100). Follow the exact pattern used by Settings (lines 87-98):

```tsx
            <HeaderMenuItemButton
              onClick={() => {
                navigate("/usage");
              }}
            >
              <span
                data-testid="menu_usage_button"
                id="menu_usage_button"
              >
                Usage
              </span>
            </HeaderMenuItemButton>
```

Gate it with the feature flag from Task 3:

```tsx
import { ENABLE_USAGE_TRACKING } from "@/customization/feature-flags";
// ...
            {ENABLE_USAGE_TRACKING && (
              <HeaderMenuItemButton
                onClick={() => {
                  navigate("/usage");
                }}
              >
                <span data-testid="menu_usage_button" id="menu_usage_button">
                  Usage
                </span>
              </HeaderMenuItemButton>
            )}
```

---

## Task 3: Add feature flag (NAV-3)

**File:** `src/frontend/src/customization/feature-flags.ts`

Add after `ENABLE_INSPECTION_PANEL` (line 20):

```ts
export const ENABLE_USAGE_TRACKING = true;
```

> **AMENDMENT (review verdict):** Default changed to `true`. Setting it to `false` makes verification impossible during development and testing. **Note:** Set back to `false` before merging to `main` if backend bugs (Plans 01-02) are not yet fixed.

Also gate the `/usage` route in `src/frontend/src/routes.tsx` (line 142):

```tsx
{ENABLE_USAGE_TRACKING && (
  <Route path="usage" element={<UsagePage />} />
)}
```

Import the flag at the top of `routes.tsx`.

---

## Task 4: Wrap UsagePage in PageLayout (NAV-4)

**File:** `src/frontend/src/pages/UsagePage/UsagePage.tsx`

Wrap the page content in `PageLayout` matching the Settings page pattern (`src/frontend/src/pages/SettingsPage/index.tsx` lines 101-114):

```tsx
import PageLayout from "@/components/common/pageLayout";
import type { To } from "react-router-dom";

// In the return for the success state (~line 60), wrap with:
return (
  <PageLayout backTo={-1 as To} title="Usage" description="Track API usage and costs.">
    <div className="space-y-6 p-6" data-testid="usage-dashboard">
      {/* existing content */}
    </div>
  </PageLayout>
);
```

Also wrap the error state (~line 31) and empty state (~line 47) in `PageLayout` so the back button is always available regardless of page state.

> **AMENDMENT (review verdict):** Also wrap the **loading** state. `UsagePage` line 27 returns `<UsageLoadingSkeleton />` without `PageLayout`. All four return paths (loading, error, empty, success) must be wrapped in `<PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>` for consistent layout and navigation.

---

## Task 5: Verify

1. Open the app. Confirm the Usage link is **not** in the AppHeader top bar.
2. Click the profile avatar (top-right). Confirm "Usage" appears in the Account Menu dropdown between "Settings" and "Admin Page".
3. Click "Usage" in the dropdown. Confirm it navigates to `/usage`.
4. Confirm the Usage page has a back button (top-left arrow) provided by PageLayout.
5. Click the back button. Confirm it navigates to the previous page.
6. Set `ENABLE_USAGE_TRACKING = false`. Confirm "Usage" disappears from the Account Menu and `/usage` route returns 404.
7. Inspect the DOM — confirm no `<Link>` elements to `/usage` remain anywhere in the header.
