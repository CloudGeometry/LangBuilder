---
skill: serious-plan
slug: build-subview-toggle
status: active
parent: Research/bugs/dashboard-completeness-audit
created: 2026-03-17
---

# Implementation Plan: Build Sub-View Toggle (Flows / MCP Server)

---

## Executive Summary

The Usage dashboard is missing the Flows/MCP Server sub-view toggle required by FR-002. The backend already supports filtering by `sub_view` ("flows" or "mcp") via `UsageQueryParams.sub_view`, and `LangWatchService.getUsageSummary` already passes `sub_view` to the API. The frontend simply needs a toggle UI component and state management to pass the selected sub-view through the existing data pipeline.

**Key Outcomes:**
- Users can toggle between "Flows" and "MCP Server" usage views
- Switching sub-view refetches data via TanStack Query (query key includes `sub_view`)
- Toggle follows the existing tab pattern from `MainPage/components/header/index.tsx`

---

## Project Configuration

| Variable | Value | Description |
|----------|-------|-------------|
| `{EVIDENCE_ROOT}` | `Research/bugs/dashboard-completeness-audit/plans/evidence/03` | Evidence artifacts |
| `{STATIC_ANALYSIS_CMD}` | `cd src/frontend && npx tsc --noEmit && npx eslint src/pages/UsagePage/` | Typecheck + lint |
| `{DEV_SERVER_CMD}` | `make frontend` | Start the frontend dev server |
| `{TEST_CMD}` | `cd src/frontend && npx vitest run` | Run unit tests |
| `{RUNTIME_LOGS_CMD}` | `browser console` | Browser DevTools console |
| `{BUILD_CMD}` | `cd src/frontend && npm run build` | Production build |
| `{VERIFICATION_AGENT}` | `Playwright MCP` | Runtime verification |
| `{SCREENSHOT_TOOL}` | `mcp__playwright__browser_take_screenshot` | Visual evidence |
| `{MAX_RETRIES}` | `3` | Max verification failures before escalating |
| `{STUB_PATTERNS}` | `["throw UnimplementedException", "// TODO", "placeholder", "FIXME"]` | Stub detection |
| `{RUNTIME_VERIFY_CMD}` | `Playwright MCP — navigate to /usage` | Runtime verification |

---

## Product Manager Review

### Feature Overview

Adding the missing sub-view toggle to let users switch between Flows and MCP Server usage data on the Usage dashboard.

### Features

#### Feature 1: Sub-View Toggle (FR-002)

**What it is:** A two-button toggle bar ("Flows" / "MCP Server") on the Usage dashboard that filters all displayed data by category.

**Why it matters:** Without this toggle, users see combined usage data with no way to distinguish between Flow and MCP Server costs. This is a Must Have FR and blocks the MCP Server usage view entirely.

**User perspective:** User opens the Usage tab, sees "Flows" selected by default. Clicks "MCP Server" to see MCP-specific cost data. The aggregate cards and breakdown list all update. Switching back to "Flows" returns to flow data. Sub-view persists across date range changes.

---

## Pre-Flight Readiness

- [ ] **Dependencies installed** — `npm run build` succeeds
- [ ] **Environment configured** — `.env` has required variables
- [ ] **Dev server starts** — `make frontend` launches without errors
- [ ] **Static analysis baseline** — `tsc --noEmit` and `eslint` pass
- [ ] **Test suite baseline** — `npx vitest run` passes
- [ ] **Evidence directory exists** — `{EVIDENCE_ROOT}/assets/` created
- [ ] **Mock/seed data ready** — LangWatch API key configured, usage data available
- [ ] **Git branch created** — Working on correct feature branch

---

## Test-Driven Development Protocol

Every task follows RED-GREEN-REFACTOR-VERIFY. Tests written before or alongside code. See master template for full TDD protocol.

---

## Master Checklist

### Progress Dashboard

| Done | # | Task Name | Risk | Start | End | Total (min) | Human Est. (min) | Multiplier | Status | Attempts | Evidence | Blocker |
|:----:|:-:|-----------|:----:|:-----:|:---:|:-----------:|:----------------:|:----------:|:------:|:--------:|:--------:|:-------:|
| ⬜ | 0 | Smoke test: confirm no toggle exists | L | | | | 5 | | pending | — | — | |
| ⬜ | 1 | Implement: Add sub_view state to UsagePage + wire to hook | L | | | | 10 | | pending | — | — | |
| ⬜ | 1v | Verify: Add sub_view state to UsagePage + wire to hook | | | | | | | pending | 0 | | |
| ⬜ | 2 | Implement: Build SubViewToggle component | M | | | | 15 | | pending | — | — | |
| ⬜ | 2v | Verify: Build SubViewToggle component | | | | | | | pending | 0 | | |
| ⬜ | 3 | Implement: Wire toggle into UsagePage | L | | | | 10 | | pending | — | — | |
| ⬜ | 3v | Verify: Wire toggle into UsagePage | | | | | | | pending | 0 | | |
| ⬜ | 4 | Smoke test: verify toggle visible, switching refetches data | L | | | | 5 | | pending | — | — | |

**Summary:**
- Total tasks: 4 (implementation) + 2 (verification) + 2 (smoke) = 8 total
- Completed: 0
- Passed verification: 0 / 2
- Total human estimate: 45 minutes

---

## Task Descriptions

### Task 0: Smoke Test — Confirm No Toggle Exists

**Goal:** Establish baseline. Open `/usage` in browser, confirm there is no sub-view toggle.

**Steps:**
1. Navigate to `/usage` via Playwright MCP
2. Take a screenshot
3. Confirm: no element matching "Flows" / "MCP Server" toggle buttons exists on the page
4. Save screenshot to `{EVIDENCE_ROOT}/assets/task_00_baseline.png`

**Acceptance Criteria:**
- [ ] Screenshot shows Usage dashboard with no sub-view toggle
- [ ] No DOM element with `data-testid="sub-view-toggle"` exists

---

### Task 1: Add `sub_view` State to UsagePage + Wire to Hook

**Goal:** Add `sub_view` state to UsagePage and pass it through to useGetUsageSummary so the API query includes it.

**Codebase root:** `/Users/cg-adubuc/cg-ai-msl-workspaces/orgs/4c1a52a5-c94b-4f56-a14b-704b5c2f4725/projects/83b7021c-55d2-4e01-bab2-3d59c760c2e6/main/langbuilder/`

**File:** `src/frontend/src/pages/UsagePage/UsagePage.tsx`

**What to do:**

1. Add state: `const [subView, setSubView] = useState<"flows" | "mcp">("flows");`
2. Pass `sub_view: subView` to useGetUsageSummary params

**BEFORE (UsagePage.tsx lines 17-26):**
```tsx
export function UsagePage() {
  const [dateRange, setDateRange] = useState<DateRange>({ from: null, to: null });
  const [userId, setUserId] = useState<string | null>(null);

  const debouncedDateRange = useDebounce(dateRange, 500);

  const { data, isLoading, isError, error } = useGetUsageSummary({
    from_date: debouncedDateRange.from,
    to_date: debouncedDateRange.to,
    user_id: userId,
  });
```

**AFTER:**
```tsx
export function UsagePage() {
  const [dateRange, setDateRange] = useState<DateRange>({ from: null, to: null });
  const [userId, setUserId] = useState<string | null>(null);
  const [subView, setSubView] = useState<"flows" | "mcp">("flows");

  const debouncedDateRange = useDebounce(dateRange, 500);

  const { data, isLoading, isError, error } = useGetUsageSummary({
    from_date: debouncedDateRange.from,
    to_date: debouncedDateRange.to,
    user_id: userId,
    sub_view: subView,
  });
```

**Why this works:**
- `UsageQueryParams` already has `sub_view?: "flows" | "mcp"` (see `src/frontend/src/types/usage.ts` line 5)
- `useGetUsageSummary` passes params directly to `getUsageSummary` (see `src/frontend/src/pages/UsagePage/hooks/useGetUsageSummary.ts` lines 5-8)
- `getUsageSummary` already sends `sub_view` as a query param (see `src/frontend/src/services/LangWatchService.ts` line 20)
- TanStack Query key includes `params` so changing `subView` triggers automatic refetch (line 7 of hook: `queryKey: ["usage", "summary", params]`)

**Acceptance Criteria:**
- [ ] AC-1A: `subView` state defaults to `"flows"`
- [ ] AC-1B: `sub_view` is included in the useGetUsageSummary params object
- [ ] AC-1C: Changing `subView` triggers a refetch (TanStack Query key changes)
- [ ] AC-1D: TypeScript compiles without errors

---

### Task 2: Build SubViewToggle Component

**Goal:** Create a toggle component with two buttons ("Flows" and "MCP Server") matching the existing tab pattern.

**File to create:** `src/frontend/src/pages/UsagePage/components/SubViewToggle.tsx`

**Reference pattern:** `src/frontend/src/pages/MainPage/components/header/index.tsx` lines 124-148

The MainPage header uses this pattern for tabs:
```tsx
<div className={cn("flex flex-row-reverse pb-4")}>
  <div className="w-full border-b dark:border-border" />
  {tabTypes.map((type) => (
    <Button
      key={type}
      unstyled
      onClick={() => setFlowType(type)}
      className={`border-b ${
        flowType === type
          ? "border-b-2 border-foreground text-foreground"
          : "border-border text-muted-foreground hover:text-foreground"
      } text-nowrap px-2 pb-2 pt-1 text-mmd`}
    >
      <div className={flowType === type ? "-mb-px" : ""}>
        {label}
      </div>
    </Button>
  ))}
</div>
```

**Component spec:**

```tsx
interface SubViewToggleProps {
  value: "flows" | "mcp";
  onChange: (value: "flows" | "mcp") => void;
}
```

- Two buttons: "Flows" and "MCP Server"
- Active button: `border-b-2 border-foreground text-foreground`
- Inactive button: `border-border text-muted-foreground hover:text-foreground`
- Wrap in `data-testid="sub-view-toggle"`
- Each button: `data-testid="sub-view-flows"` and `data-testid="sub-view-mcp"`
- Use the `Button` component from `@/components/ui/button` with `unstyled` prop (matching existing pattern)

**Acceptance Criteria:**
- [ ] AC-2A: Component renders two buttons labeled "Flows" and "MCP Server"
- [ ] AC-2B: Active button has `border-b-2 border-foreground` visual treatment
- [ ] AC-2C: Clicking inactive button calls `onChange` with the correct value
- [ ] AC-2D: Clicking active button does not trigger unnecessary onChange
- [ ] AC-2E: Component has `data-testid="sub-view-toggle"` wrapper
- [ ] AC-2F: Follows existing `Button unstyled` pattern from MainPage header
- [ ] AC-2G: TypeScript compiles without errors

---

### Task 3: Wire Toggle into UsagePage

**Goal:** Render SubViewToggle in UsagePage, positioned below the page title and before the DateRangePicker.

**File:** `src/frontend/src/pages/UsagePage/UsagePage.tsx`

**BEFORE (lines 96-110):**
```tsx
  return (
    <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
      <div className="space-y-6 p-6" data-testid="usage-dashboard">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Usage</h1>
          <div className="flex gap-4 items-center">
            <DateRangePicker value={dateRange} onChange={setDateRange} />
            <UserFilterDropdown
              value={userId}
              onChange={setUserId}
              users={[]}
            />
          </div>
        </div>
        <UsageSummaryCards summary={data.summary} />
      </div>
    </PageLayout>
  );
```

**AFTER:**
```tsx
  return (
    <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
      <div className="space-y-6 p-6" data-testid="usage-dashboard">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Usage</h1>
          <div className="flex gap-4 items-center">
            <DateRangePicker value={dateRange} onChange={setDateRange} />
            <UserFilterDropdown
              value={userId}
              onChange={setUserId}
              users={[]}
            />
          </div>
        </div>
        <SubViewToggle value={subView} onChange={setSubView} />
        <UsageSummaryCards summary={data.summary} />
      </div>
    </PageLayout>
  );
```

**Also add import at top of file:**
```tsx
import { SubViewToggle } from "./components/SubViewToggle";
```

**Acceptance Criteria:**
- [ ] AC-3A: SubViewToggle renders between the title row and UsageSummaryCards
- [ ] AC-3B: Toggle defaults to "Flows" on page load
- [ ] AC-3C: Clicking "MCP Server" triggers data refetch with `sub_view=mcp`
- [ ] AC-3D: Sub-view persists when date range changes (FR-002 AC-FR002-04)
- [ ] AC-3E: Import path resolves correctly
- [ ] AC-3F: No console errors on toggle interaction

---

### Task 4: Smoke Test — Verify Toggle Works End-to-End

**Goal:** Open `/usage`, confirm toggle is visible, and switching refetches data.

**Steps:**
1. Navigate to `/usage` via Playwright MCP
2. Take screenshot showing toggle with "Flows" active — save to `{EVIDENCE_ROOT}/assets/task_04_flows.png`
3. Click "MCP Server" button
4. Take screenshot showing toggle with "MCP Server" active — save to `{EVIDENCE_ROOT}/assets/task_04_mcp.png`
5. Open browser Network tab or check console — confirm API call includes `sub_view=mcp` query param
6. Click "Flows" again — confirm data reloads with `sub_view=flows`

**Acceptance Criteria:**
- [ ] Screenshot shows SubViewToggle with "Flows" and "MCP Server" buttons
- [ ] "Flows" is visually active by default (border-b-2)
- [ ] Clicking "MCP Server" changes the active state and triggers network request
- [ ] API request URL includes `sub_view=mcp` parameter
- [ ] No console errors during interaction

---

## Sync Pairs

| Function A | Function B | Must agree on |
|-----------|-----------|---------------|
| `UsagePage` subView state | `useGetUsageSummary` params | `sub_view: "flows" \| "mcp"` |
| `SubViewToggle` onChange | `UsagePage` setSubView | Same `"flows" \| "mcp"` type |
| Frontend `sub_view` param | Backend `UsageQueryParams.sub_view` | String values `"flows"` and `"mcp"` |
| `SubViewToggle` styling | `MainPage header` tab styling | Same `border-b-2 border-foreground` pattern |

---

## Files Modified

| File | Action | Lines Changed |
|------|--------|---------------|
| `src/frontend/src/pages/UsagePage/UsagePage.tsx` | MODIFY | ~5 lines (state + param + import + render) |
| `src/frontend/src/pages/UsagePage/components/SubViewToggle.tsx` | CREATE | ~35 lines |

**No backend changes required.** The backend already supports `sub_view` filtering.
