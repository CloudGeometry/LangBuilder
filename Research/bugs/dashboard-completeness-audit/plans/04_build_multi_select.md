---
skill: serious-plan
slug: build-multi-select
status: active
parent: Research/bugs/dashboard-completeness-audit
created: 2026-03-17
---

# Implementation Plan: Build Multi-Flow Selection with Summed Totals

---

## Executive Summary

The Usage dashboard is missing the multi-flow selection feature required by FR-012. Users need to select multiple flows via checkboxes and see summed totals across their selection. FlowBreakdownList exists and renders flow rows, but has no checkbox/selection logic. This plan adds selection state management, checkbox UI, a selection summary bar, and auto-clear on filter changes.

**Key Outcomes:**
- Users can select multiple flows via checkboxes in the flow breakdown list
- A selection summary shows summed totals: "{N} flows selected: ${total} total, {count} invocations, ${avg} avg"
- Deselecting all flows returns to the normal list view
- Selection clears automatically on date range or user filter changes

**Depends on:** Plan 01 (FlowBreakdownList must be wired into UsagePage first — `data.flows` must be rendered)

---

## Project Configuration

| Variable | Value | Description |
|----------|-------|-------------|
| `{EVIDENCE_ROOT}` | `Research/bugs/dashboard-completeness-audit/plans/evidence/04` | Evidence artifacts |
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

Adding checkbox multi-selection to the flow breakdown list with a summed totals summary bar.

### Features

#### Feature 1: Multi-Flow Selection with Summed Totals (FR-012)

**What it is:** Checkbox selection on flow rows that displays combined cost and invocation totals across the selected flows.

**Why it matters:** Users analyzing costs for a group of related flows (e.g., all customer-facing bots) currently have no way to sum their metrics. This forces mental math or spreadsheet exports. Multi-select with live summing provides instant group analysis.

**User perspective:** User sees checkboxes next to each flow in the breakdown list. They check 2-3 flows and immediately see a summary bar: "3 flows selected: $450 total, 280 invocations, $1.61 avg". They can check/uncheck "Select All" in the header. Changing the date range clears the selection (the underlying data changed).

---

## Pre-Flight Readiness

- [ ] **Dependencies installed** — `npm run build` succeeds
- [ ] **Environment configured** — `.env` has required variables
- [ ] **Dev server starts** — `make frontend` launches without errors
- [ ] **Static analysis baseline** — `tsc --noEmit` and `eslint` pass
- [ ] **Test suite baseline** — `npx vitest run` passes
- [ ] **Evidence directory exists** — `{EVIDENCE_ROOT}/assets/` created
- [ ] **Mock/seed data ready** — LangWatch API key configured, usage data with multiple flows available
- [ ] **Git branch created** — Working on correct feature branch
- [ ] **Plan 01 completed** — FlowBreakdownList is wired into UsagePage rendering `data.flows`

---

## Test-Driven Development Protocol

Every task follows RED-GREEN-REFACTOR-VERIFY. Tests written before or alongside code. See master template for full TDD protocol.

---

## Master Checklist

### Progress Dashboard

| Done | # | Task Name | Risk | Start | End | Total (min) | Human Est. (min) | Multiplier | Status | Attempts | Evidence | Blocker |
|:----:|:-:|-----------|:----:|:-----:|:---:|:-----------:|:----------------:|:----------:|:------:|:--------:|:--------:|:-------:|
| ⬜ | 0 | Smoke test: confirm no checkboxes exist in flow list | L | | | | 5 | | pending | — | — | |
| ⬜ | 1 | Implement: Add selection state to UsagePage | L | | | | 10 | | pending | — | — | |
| ⬜ | 1v | Verify: Add selection state to UsagePage | | | | | | | pending | 0 | | |
| ⬜ | 2 | Implement: Add checkboxes to FlowBreakdownList + FlowBreakdownRow | M | | | | 20 | | pending | — | — | |
| ⬜ | 2v | Verify: Add checkboxes to FlowBreakdownList + FlowBreakdownRow | | | | | | | pending | 0 | | |
| ⬜ | 3 | Implement: Build SelectionSummary component | M | | | | 15 | | pending | — | — | |
| ⬜ | 3v | Verify: Build SelectionSummary component | | | | | | | pending | 0 | | |
| ⬜ | 4 | Implement: Wire everything into UsagePage | L | | | | 10 | | pending | — | — | |
| ⬜ | 4v | Verify: Wire everything into UsagePage | | | | | | | pending | 0 | | |
| ⬜ | 5 | Smoke test: verify checkboxes, selection, and summed totals | L | | | | 5 | | pending | — | — | |

**Summary:**
- Total tasks: 4 (implementation) + 4 (verification) + 2 (smoke) = 10 total
- Completed: 0
- Passed verification: 0 / 4
- Total human estimate: 65 minutes

---

## Task Descriptions

### Task 0: Smoke Test — Confirm No Checkboxes Exist

**Goal:** Establish baseline. Open `/usage`, confirm FlowBreakdownList renders (Plan 01 prerequisite) but has no checkboxes.

**Steps:**
1. Navigate to `/usage` via Playwright MCP
2. Take a screenshot
3. Confirm: flow breakdown list is visible (rows with flow names, costs, invocations)
4. Confirm: no checkbox elements exist in the flow list
5. Save screenshot to `{EVIDENCE_ROOT}/assets/task_00_baseline.png`

**Acceptance Criteria:**
- [ ] FlowBreakdownList is rendered with flow rows (Plan 01 must be done)
- [ ] No checkbox inputs exist within `[data-testid="flow-breakdown-list"]`
- [ ] No `data-testid="selection-summary"` element exists

---

### Task 1: Add Selection State to UsagePage

**Goal:** Add selection state management to UsagePage with auto-clear on filter changes.

**Codebase root:** `/Users/cg-adubuc/cg-ai-msl-workspaces/orgs/4c1a52a5-c94b-4f56-a14b-704b5c2f4725/projects/83b7021c-55d2-4e01-bab2-3d59c760c2e6/main/langbuilder/`

**File:** `src/frontend/src/pages/UsagePage/UsagePage.tsx`

**What to do:**

1. Add state: `const [selectedFlowIds, setSelectedFlowIds] = useState<Set<string>>(new Set());`
2. Add auto-clear effect: `useEffect(() => setSelectedFlowIds(new Set()), [debouncedDateRange, userId]);`
3. Add import for `useEffect` (already imported: `useState` is on line 1 — check if `useEffect` is there too)

**BEFORE (UsagePage.tsx line 1):**
```tsx
import { useState } from "react";
```

**AFTER:**
```tsx
import { useEffect, useState } from "react";
```

**Add after the existing state declarations (after line 18-19 area, wherever `userId` state is):**
```tsx
const [selectedFlowIds, setSelectedFlowIds] = useState<Set<string>>(new Set());

useEffect(() => {
  setSelectedFlowIds(new Set());
}, [debouncedDateRange, userId]);
```

**Note:** The exact line numbers depend on whether Plan 03 (sub-view toggle) has already been applied. The `subView` state may be between `userId` and `debouncedDateRange`. The selection state and effect should go after all other state declarations.

**Acceptance Criteria:**
- [ ] AC-1A: `selectedFlowIds` state is a `Set<string>`, initialized empty
- [ ] AC-1B: Selection clears when `debouncedDateRange` changes
- [ ] AC-1C: Selection clears when `userId` changes
- [ ] AC-1D: TypeScript compiles without errors

---

### Task 2: Add Checkboxes to FlowBreakdownList + FlowBreakdownRow

**Goal:** Add checkbox column to the flow breakdown table with individual row checkboxes and a "select all" header checkbox.

**Files:**
- `src/frontend/src/pages/UsagePage/components/FlowBreakdownList.tsx`
- `src/frontend/src/pages/UsagePage/components/FlowBreakdownRow.tsx`

#### FlowBreakdownList changes

**Current props (lines 12-16):**
```tsx
interface FlowBreakdownListProps {
  flows: FlowUsage[];
  onFlowExpand: (flowId: string) => void;
  dateRange?: DateRange;
}
```

**New props:**
```tsx
interface FlowBreakdownListProps {
  flows: FlowUsage[];
  onFlowExpand: (flowId: string) => void;
  dateRange?: DateRange;
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
}
```

**Add to table header (before existing "Flow" th, line 48):**
```tsx
<th className="px-4 py-3 w-10">
  <input
    type="checkbox"
    data-testid="select-all-checkbox"
    checked={selectedIds !== undefined && flows.length > 0 && flows.every(f => selectedIds.has(f.flow_id))}
    onChange={(e) => {
      if (!onSelectionChange) return;
      if (e.target.checked) {
        onSelectionChange(new Set(flows.map(f => f.flow_id)));
      } else {
        onSelectionChange(new Set());
      }
    }}
    className="h-4 w-4 rounded border-border"
  />
</th>
```

**Pass selectedIds and onSelectionChange to FlowBreakdownRow (line 57-61 area):**
```tsx
<FlowBreakdownRow
  key={flow.flow_id}
  flow={flow}
  onExpand={onFlowExpand}
  dateRange={dateRange}
  selected={selectedIds?.has(flow.flow_id) ?? false}
  onSelectChange={(checked) => {
    if (!onSelectionChange || !selectedIds) return;
    const next = new Set(selectedIds);
    if (checked) next.add(flow.flow_id);
    else next.delete(flow.flow_id);
    onSelectionChange(next);
  }}
/>
```

#### FlowBreakdownRow changes

**Current props (lines 10-14):**
```tsx
interface FlowBreakdownRowProps {
  flow: FlowUsage;
  onExpand: (flowId: string) => void;
  dateRange?: DateRange;
}
```

**New props:**
```tsx
interface FlowBreakdownRowProps {
  flow: FlowUsage;
  onExpand: (flowId: string) => void;
  dateRange?: DateRange;
  selected?: boolean;
  onSelectChange?: (checked: boolean) => void;
}
```

**Add checkbox cell as first `<td>` in the row (before the flow name td, line 36):**
```tsx
<td className="px-4 py-3 w-10">
  <input
    type="checkbox"
    data-testid={`select-flow-${flow.flow_id}`}
    checked={selected ?? false}
    onChange={(e) => onSelectChange?.(e.target.checked)}
    className="h-4 w-4 rounded border-border"
  />
</td>
```

**Update colspan on expanded row from 5 to 6 (line 53):**
```tsx
<td colSpan={6} className="px-0 py-0">
```

**Acceptance Criteria:**
- [ ] AC-2A: Each flow row has a checkbox as the first column
- [ ] AC-2B: Header has a "select all" checkbox
- [ ] AC-2C: Clicking a row checkbox toggles that flow's selection
- [ ] AC-2D: "Select all" checks all visible flows
- [ ] AC-2E: Unchecking "select all" clears all selections
- [ ] AC-2F: "Select all" shows checked state when all flows are selected
- [ ] AC-2G: Checkboxes have appropriate `data-testid` attributes
- [ ] AC-2H: New props are optional (backward compatible — component works without them)
- [ ] AC-2I: Expanded row colspan updated from 5 to 6
- [ ] AC-2J: TypeScript compiles without errors

---

### Task 3: Build SelectionSummary Component

**Goal:** Create a component that displays summed totals for the selected flows.

**File to create:** `src/frontend/src/pages/UsagePage/components/SelectionSummary.tsx`

**Component spec:**

```tsx
import type { FlowUsage } from "@/types/usage";

interface SelectionSummaryProps {
  selectedFlows: FlowUsage[];
}
```

**Display format:** "{N} flows selected: ${total} total, {count} invocations, ${avg} avg"

- Example: "2 flows selected: $180.00 total, 120 invocations, $1.50 avg"
- Singular: "1 flow selected: $60.00 total, 40 invocations, $1.50 avg"
- Cost format: `$X.XX` (2 decimal places for summary, matching PRD example)
- Avg cost: total / invocations (handle zero invocations — show $0.00)

**Styling:**
- Background: `bg-muted/50` with `rounded-md border` to visually distinguish from surrounding content
- Padding: `p-3`
- Text: `text-sm font-medium`
- Wrap with `data-testid="selection-summary"`

**Acceptance Criteria:**
- [ ] AC-3A: Component renders "{N} flows selected" with correct count
- [ ] AC-3B: Total cost is summed correctly from `selectedFlows[].total_cost_usd`
- [ ] AC-3C: Invocation count is summed from `selectedFlows[].invocation_count`
- [ ] AC-3D: Average cost is computed as total / invocations
- [ ] AC-3E: Zero invocations shows $0.00 avg (no division by zero)
- [ ] AC-3F: Singular "flow" vs plural "flows" handled
- [ ] AC-3G: Cost formatted to 2 decimal places
- [ ] AC-3H: Has `data-testid="selection-summary"`
- [ ] AC-3I: TypeScript compiles without errors

---

### Task 4: Wire Everything into UsagePage

**Goal:** Connect selection state, FlowBreakdownList checkboxes, and SelectionSummary into the UsagePage render tree.

**File:** `src/frontend/src/pages/UsagePage/UsagePage.tsx`

**What to do:**

1. Add imports for SelectionSummary
2. Compute `selectedFlows` from data
3. Pass selection props to FlowBreakdownList
4. Render SelectionSummary conditionally

**Add import:**
```tsx
import { SelectionSummary } from "./components/SelectionSummary";
```

**Add computed value (inside the component, after data is available, before the return):**
```tsx
const selectedFlows = data?.flows.filter(f => selectedFlowIds.has(f.flow_id)) ?? [];
```

**In the JSX return, after UsageSummaryCards and before FlowBreakdownList (which should exist from Plan 01):**
```tsx
{selectedFlows.length > 0 && (
  <SelectionSummary selectedFlows={selectedFlows} />
)}
```

**Pass selection props to FlowBreakdownList (which should be rendered from Plan 01):**
```tsx
<FlowBreakdownList
  flows={data.flows}
  onFlowExpand={handleFlowExpand}
  dateRange={debouncedDateRange}
  selectedIds={selectedFlowIds}
  onSelectionChange={setSelectedFlowIds}
/>
```

**Note:** The exact placement depends on what Plan 01 added. FlowBreakdownList should already be in the render tree. This task adds `selectedIds` and `onSelectionChange` props to it and inserts SelectionSummary above it.

**Acceptance Criteria:**
- [ ] AC-4A: SelectionSummary appears when 1+ flows are selected
- [ ] AC-4B: SelectionSummary disappears when all flows are deselected
- [ ] AC-4C: SelectionSummary totals match the sum of selected rows
- [ ] AC-4D: FlowBreakdownList receives `selectedIds` and `onSelectionChange`
- [ ] AC-4E: Selecting all flows shows totals matching the aggregate summary card (within rounding)
- [ ] AC-4F: Changing date range clears selection and hides summary
- [ ] AC-4G: TypeScript compiles without errors

---

### Task 5: Smoke Test — Verify Multi-Selection End-to-End

**Goal:** Open `/usage`, verify checkboxes work, select multiple flows, confirm summed totals.

**Steps:**
1. Navigate to `/usage` via Playwright MCP
2. Take screenshot showing flow list with checkboxes — save to `{EVIDENCE_ROOT}/assets/task_05_checkboxes.png`
3. Click checkbox on first flow row
4. Take screenshot showing selection summary with 1 flow — save to `{EVIDENCE_ROOT}/assets/task_05_one_selected.png`
5. Click checkbox on second flow row
6. Take screenshot showing selection summary with 2 flows — save to `{EVIDENCE_ROOT}/assets/task_05_two_selected.png`
7. Verify summed totals are correct (total = sum of both rows' costs, invocations = sum of counts)
8. Click "select all" checkbox — verify all rows checked and summary updates
9. Uncheck "select all" — verify summary disappears
10. Select 2 flows, then change date range — verify selection clears

**Acceptance Criteria:**
- [ ] Checkboxes visible on every flow row and in the header
- [ ] Selecting 1 flow shows "1 flow selected" summary
- [ ] Selecting 2 flows shows "2 flows selected" with correct summed totals
- [ ] "Select all" selects all flows
- [ ] Deselecting all hides the summary bar
- [ ] Date range change clears selection
- [ ] No console errors during interaction

---

## Sync Pairs

| Function A | Function B | Must agree on |
|-----------|-----------|---------------|
| `UsagePage` selectedFlowIds | `FlowBreakdownList` selectedIds prop | `Set<string>` type, same reference |
| `FlowBreakdownList` onSelectionChange | `UsagePage` setSelectedFlowIds | `Set<string>` callback signature |
| `FlowBreakdownRow` selected prop | `selectedIds.has(flow.flow_id)` | Boolean derived from Set membership |
| `SelectionSummary` selectedFlows | `data.flows.filter(...)` | `FlowUsage[]` — same type as API response |
| `FlowBreakdownList` header colspan | `FlowBreakdownRow` colspan | Both must be 6 (was 5, +1 for checkbox) |

---

## Files Modified

| File | Action | Lines Changed |
|------|--------|---------------|
| `src/frontend/src/pages/UsagePage/UsagePage.tsx` | MODIFY | ~12 lines (state, effect, import, computed, render) |
| `src/frontend/src/pages/UsagePage/components/FlowBreakdownList.tsx` | MODIFY | ~20 lines (props, header checkbox, pass to row) |
| `src/frontend/src/pages/UsagePage/components/FlowBreakdownRow.tsx` | MODIFY | ~10 lines (props, checkbox cell, colspan) |
| `src/frontend/src/pages/UsagePage/components/SelectionSummary.tsx` | CREATE | ~30 lines |

**No backend changes required.** All selection logic is client-side.
