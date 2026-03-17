# Thread 2: Missing UI Components

## Summary

UsagePage.tsx renders only 3 of 9 available components and uses only 1 of 3 available hooks. The API response contains a `flows` array that is completely ignored. Four fully-built components (FlowBreakdownList, FlowBreakdownRow, FlowRunsTable, EmptyStatePrompt) and two hooks (useGetFlowRuns, useGetKeyStatus) are never wired in, plus ErrorState is replaced by inline JSX that duplicates its purpose with less functionality.

---

## 1. UsagePage.tsx Current State

**File:** `src/frontend/src/pages/UsagePage/UsagePage.tsx` (113 lines)

### What it imports:
| Import | Source | Used in render? |
|--------|--------|-----------------|
| `useState` | react | YES |
| `To` (type) | react-router-dom | YES |
| `useGetUsageSummary` | ./hooks/useGetUsageSummary | YES |
| `UsageLoadingSkeleton` | ./components/LoadingSkeleton | YES |
| `UsageSummaryCards` | ./components/UsageSummaryCards | YES |
| `DateRangePicker` | ./components/DateRangePicker | YES |
| `UserFilterDropdown` | ./components/UserFilterDropdown | YES |
| `useDebounce` | @/hooks/useDebounce | YES |
| `PageLayout` | @/components/common/pageLayout | YES |

### What it does NOT import:
| Component/Hook | File | Status |
|----------------|------|--------|
| `FlowBreakdownList` | ./components/FlowBreakdownList | NOT IMPORTED |
| `FlowBreakdownRow` | ./components/FlowBreakdownRow | NOT IMPORTED (used by FlowBreakdownList internally) |
| `FlowRunsTable` | ./components/FlowRunsTable | NOT IMPORTED (used by FlowBreakdownRow internally) |
| `EmptyStatePrompt` | ./components/EmptyStatePrompt | NOT IMPORTED |
| `ErrorState` | ./components/ErrorState | NOT IMPORTED |
| `useGetFlowRuns` | ./hooks/useGetFlowRuns | NOT IMPORTED (used by FlowRunsTable internally) |
| `useGetKeyStatus` | ./hooks/useGetKeyStatus | NOT IMPORTED |

### What data UsagePage uses from the API response:
The `useGetUsageSummary` hook returns `UsageResponse`:
```typescript
interface UsageResponse {
  summary: UsageSummary;  // <-- USED (passed to UsageSummaryCards on line 109)
  flows: FlowUsage[];     // <-- COMPLETELY IGNORED
}
```

**Line 109:** `<UsageSummaryCards summary={data.summary} />` -- only `data.summary` is consumed. `data.flows` is never referenced anywhere in UsagePage.tsx.

---

## 2. Component-by-Component Analysis

### 2.1 FlowBreakdownList -- NOT WIRED IN

**File:** `src/frontend/src/pages/UsagePage/components/FlowBreakdownList.tsx` (95 lines)

**Imported in UsagePage?** NO
**Rendered in UsagePage?** NO

**Props interface (lines 12-16):**
```typescript
interface FlowBreakdownListProps {
  flows: FlowUsage[];                          // from data.flows
  onFlowExpand: (flowId: string) => void;      // callback when row expanded
  dateRange?: DateRange;                       // { from: string|null, to: string|null }
}
```

**What it does:** Renders a paginated table (PAGE_SIZE=50) of FlowBreakdownRow components. Has pagination controls (Previous/Next). Shows empty state if `flows.length === 0`.

**Is the data available?** YES. `data.flows` from `useGetUsageSummary` returns `FlowUsage[]` which matches the `flows` prop exactly.

**What's needed to wire it in:**
1. Add import: `import { FlowBreakdownList } from "./components/FlowBreakdownList";`
2. Add state for expanded flow: `const [expandedFlowId, setExpandedFlowId] = useState<string | null>(null);`
3. Add after `<UsageSummaryCards>` on line 109:
   ```tsx
   <FlowBreakdownList
     flows={data.flows}
     onFlowExpand={(flowId) => setExpandedFlowId(flowId)}
     dateRange={dateRange}
   />
   ```

### 2.2 FlowBreakdownRow -- NOT WIRED IN (indirect)

**File:** `src/frontend/src/pages/UsagePage/components/FlowBreakdownRow.tsx` (64 lines)

**Imported in UsagePage?** NO (only imported by FlowBreakdownList)
**Rendered in UsagePage?** NO (only rendered by FlowBreakdownList)

**Props interface (lines 10-14):**
```typescript
interface FlowBreakdownRowProps {
  flow: FlowUsage;
  onExpand: (flowId: string) => void;
  dateRange?: DateRange;
}
```

**What it does:** Renders a single flow as a table row with: flow_name, total_cost_usd, invocation_count, avg_cost_per_invocation_usd. Has an expand/collapse button that reveals FlowRunsTable inline.

**Data match:** Uses `FlowUsage` type fields: `flow_id`, `flow_name`, `total_cost_usd`, `invocation_count`, `avg_cost_per_invocation_usd` -- all present in the API response type.

**Wiring:** Automatically wired when FlowBreakdownList is wired in. No direct action needed.

### 2.3 FlowRunsTable -- NOT WIRED IN (indirect)

**File:** `src/frontend/src/pages/UsagePage/components/FlowRunsTable.tsx` (88 lines)

**Imported in UsagePage?** NO (only imported by FlowBreakdownRow)
**Rendered in UsagePage?** NO (only rendered by FlowBreakdownRow)

**Props interface (lines 8-11):**
```typescript
interface FlowRunsTableProps {
  flowId: string;
  dateRange: DateRange;
}
```

**What it does:** Uses `useGetFlowRuns(flowId, { from_date, to_date })` to fetch individual run details for a flow. Renders a sub-table with columns: Run ID (truncated), Started At, Cost, Tokens, Model, Status. Has its own loading/error/empty states.

**Data match:** Calls the `getFlowRuns` API endpoint which returns `FlowRunsResponse` with `RunDetail[]` -- fully implemented on the service layer.

**Wiring:** Automatically wired when FlowBreakdownList is wired in. No direct action needed.

### 2.4 EmptyStatePrompt -- NOT WIRED IN

**File:** `src/frontend/src/pages/UsagePage/components/EmptyStatePrompt.tsx` (92 lines)

**Imported in UsagePage?** NO
**Rendered in UsagePage?** NO

**Props interface (lines 1-4):**
```typescript
interface EmptyStatePromptProps {
  variant: "no_key" | "no_data";
  isAdmin: boolean;
}
```

**What it does:** Two variants:
- `no_key`: Shows a key icon SVG, "LangWatch API key not configured" heading. If `isAdmin=true`, shows a link to `/settings/langwatch`. If `isAdmin=false`, shows "contact your administrator".
- `no_data`: Shows a bar chart icon SVG, "No usage data found for this period", suggests adjusting date range.

**Current situation in UsagePage:** Lines 39-52 and 79-93 have **inline JSX** that does the same thing but **worse**:
- The inline `KEY_NOT_CONFIGURED` handler (lines 39-52) has no icon, no admin/non-admin distinction, and no link to settings.
- The inline `!data` handler (lines 79-93) has no icon and a less helpful message ("Configure your LangWatch API key" vs "adjust the date range").

**What's needed to wire it in:**
1. Add import: `import { EmptyStatePrompt } from "./components/EmptyStatePrompt";`
2. Need an `isAdmin` boolean -- either from auth context or passed as prop.
3. Replace lines 42-50 with: `<EmptyStatePrompt variant="no_key" isAdmin={isAdmin} />`
4. Replace lines 84-90 with: `<EmptyStatePrompt variant="no_data" isAdmin={isAdmin} />`

### 2.5 ErrorState -- NOT WIRED IN

**File:** `src/frontend/src/pages/UsagePage/components/ErrorState.tsx` (73 lines)

**Imported in UsagePage?** NO
**Rendered in UsagePage?** NO

**Props interface (lines 40-44):**
```typescript
interface ErrorStateProps {
  error: unknown;
  onRetry: () => void;
  retryable?: boolean;  // defaults to true
}
```

**What it does:** Extracts error code from the error object, maps it to a friendly message via `ERROR_MESSAGES` lookup, renders an `Alert` component (destructive variant) with the message, and conditionally shows a "Try Again" button.

**Error code mapping (lines 7-11):**
```typescript
const ERROR_MESSAGES: Record<string, string> = {
  LANGWATCH_TIMEOUT: "LangWatch took too long to respond. Try again.",
  LANGWATCH_UNAVAILABLE: "LangWatch is temporarily unavailable.",
  KEY_NOT_CONFIGURED: "LangWatch API key not configured.",
};
```

**Current situation in UsagePage:** Lines 57-76 have **inline JSX** that duplicates this purpose but:
- Does NOT use the Alert UI component (just plain divs)
- Does NOT have a "Try Again" button (just says "Try refreshing" in text)
- Does NOT use the `ERROR_MESSAGES` lookup for friendly messages
- Does NOT provide `onRetry` functionality (no programmatic retry)

**What's needed to wire it in:**
1. Add import: `import { ErrorState } from "./components/ErrorState";`
2. Need a `refetch` function from the query hook (already available: `useGetUsageSummary` returns a `refetch` from `useQuery`)
3. Replace lines 58-75 with:
   ```tsx
   <ErrorState
     error={error}
     onRetry={refetch}
     retryable={(error as any)?.retryable}
   />
   ```
4. Update the destructured return on line 22 to include `refetch`:
   ```typescript
   const { data, isLoading, isError, error, refetch } = useGetUsageSummary({...});
   ```

### 2.6 LoadingSkeleton -- WIRED IN

**File:** `src/frontend/src/pages/UsagePage/components/LoadingSkeleton.tsx` (38 lines)

**Imported in UsagePage?** YES (line 4)
**Rendered in UsagePage?** YES (line 31)

**Status:** Fully wired. No issues.

### 2.7 UsageSummaryCards -- WIRED IN

**File:** `src/frontend/src/pages/UsagePage/components/UsageSummaryCards.tsx` (46 lines)

**Imported in UsagePage?** YES (line 5)
**Rendered in UsagePage?** YES (line 109)

**Props:** `{ summary: UsageSummary }` -- receives `data.summary` correctly.

**Status:** Fully wired. No issues.

### 2.8 DateRangePicker -- WIRED IN

**File:** `src/frontend/src/pages/UsagePage/components/DateRangePicker.tsx` (174 lines)

**Imported in UsagePage?** YES (line 6)
**Rendered in UsagePage?** YES (line 101)

**Props:** `{ value: DateRange, onChange: (range: DateRange) => void }` -- wired correctly.

**Status:** Fully wired. No issues.

### 2.9 UserFilterDropdown -- WIRED IN (but broken)

**File:** `src/frontend/src/pages/UsagePage/components/UserFilterDropdown.tsx` (37 lines)

**Imported in UsagePage?** YES (line 7)
**Rendered in UsagePage?** YES (line 102-106)

**Props interface (lines 6-10):**
```typescript
interface UserFilterDropdownProps {
  value: string | null;
  onChange: (userId: string | null) => void;
  users: User[];  // { id: string; username: string }[]
}
```

**Problem at line 105:** `users={[]}` -- hardcoded empty array. The dropdown is rendered but will always show "All users" with no options. There is no hook or API endpoint to fetch users. The `UsageResponse` type does not include a users list.

**Note:** Individual `FlowUsage` items have `owner_user_id` and `owner_username` fields -- these could be used to build a unique users list from the flows data, but this is not currently done.

---

## 3. Hooks Analysis

### 3.1 useGetUsageSummary -- USED

**File:** `src/frontend/src/pages/UsagePage/hooks/useGetUsageSummary.ts`
**Used in UsagePage?** YES (line 3, line 22)
**Status:** Fully wired.

### 3.2 useGetFlowRuns -- NOT USED IN USAGEPAGE (used by FlowRunsTable)

**File:** `src/frontend/src/pages/UsagePage/hooks/useGetFlowRuns.ts`
**Used in UsagePage?** NO
**Used anywhere?** YES -- by FlowRunsTable.tsx (line 1)
**Status:** Will be active once FlowBreakdownList is wired in.

### 3.3 useGetKeyStatus -- NOT USED ANYWHERE

**File:** `src/frontend/src/pages/UsagePage/hooks/useGetKeyStatus.ts`
**Used in UsagePage?** NO
**Used anywhere?** NO -- not imported by any component.

**What it does:** Calls `GET /usage/settings/langwatch-key/status` and returns `KeyStatusResponse`:
```typescript
interface KeyStatusResponse {
  has_key: boolean;
  key_preview: string | null;
  configured_at: string | null;
}
```

**What it should be used for:** Pre-checking if a key is configured before making the usage API call. Currently, UsagePage relies on the usage API returning a `KEY_NOT_CONFIGURED` error code, which is less efficient (makes the full call, waits for it to fail, then shows the error).

**Potential wiring:**
```typescript
const { data: keyStatus, isLoading: keyLoading } = useGetKeyStatus();
if (keyStatus && !keyStatus.has_key) {
  return <EmptyStatePrompt variant="no_key" isAdmin={isAdmin} />;
}
```

---

## 4. API Response vs. UI Data Consumption

### UsageResponse shape (from types/usage.ts):
```typescript
interface UsageResponse {
  summary: UsageSummary;   // CONSUMED by UsageSummaryCards
  flows: FlowUsage[];      // IGNORED -- never referenced in UsagePage
}
```

### FlowUsage fields (from types/usage.ts):
```typescript
interface FlowUsage {
  flow_id: string;                    // used by FlowBreakdownRow, FlowBreakdownList
  flow_name: string;                  // used by FlowBreakdownRow
  total_cost_usd: number;             // used by FlowBreakdownRow
  invocation_count: number;           // used by FlowBreakdownRow
  avg_cost_per_invocation_usd: number;// used by FlowBreakdownRow
  owner_user_id: string;              // NOT used by any component
  owner_username: string;             // NOT used by any component
}
```

**The `flows` data is fully available from the API but completely dropped on the floor.** FlowBreakdownList expects exactly this data shape. The connection is trivially `<FlowBreakdownList flows={data.flows} ... />`.

### UsageSummary unused fields:
Several fields from `UsageSummary` are available but not displayed:
- `date_range` -- not shown (the UI has its own date picker)
- `currency` -- not shown (hardcoded `$` in UsageSummaryCards)
- `data_source` -- not shown
- `cached` / `cache_age_seconds` -- not shown (could show staleness indicator)
- `truncated` -- not shown (should show a warning if data is truncated)

---

## 5. Error/Empty State Handling Problems

### Current state (UsagePage.tsx lines 36-93):

| Condition | Current handling | Better component available? |
|-----------|-----------------|----------------------------|
| `isError && errCode === "KEY_NOT_CONFIGURED"` (line 39) | Inline div, no icon, no admin distinction, no settings link | YES: `EmptyStatePrompt` variant="no_key" |
| `isError` (general, line 57) | Inline div, no retry button, no Alert component | YES: `ErrorState` with onRetry |
| `!data` (line 79) | Inline div, wrong message ("Configure your API key" instead of "adjust date range") | YES: `EmptyStatePrompt` variant="no_data" |

### Specific issues:

1. **No retry button (lines 69-73):** The inline error state mentions "Try refreshing" as text but provides no clickable button. The `ErrorState` component has a proper "Try Again" button wired to `onRetry`.

2. **Wrong message for no-data state (lines 87-89):** When `!data` but no error, the message says "Configure your LangWatch API key to start tracking usage" -- but if there's no error, the key IS configured; there's just no data. Should say "adjust the date range" (as EmptyStatePrompt's `no_data` variant does).

3. **No admin/non-admin distinction:** The `KEY_NOT_CONFIGURED` inline handler (line 47) says "Configure your LangWatch API key in Settings" but doesn't link to settings and doesn't distinguish admin from non-admin users. `EmptyStatePrompt` handles both cases properly.

---

## 6. Complete Wiring Gap Summary

| # | Component/Hook | Status | Severity | Effort |
|---|---------------|--------|----------|--------|
| 1 | **FlowBreakdownList** | NOT WIRED | **CRITICAL** -- entire flows table missing from dashboard | Low -- data is available, just needs render call |
| 2 | FlowBreakdownRow | Not directly wired (used by #1) | Part of #1 | N/A |
| 3 | FlowRunsTable | Not directly wired (used by #2) | Part of #1 | N/A |
| 4 | **EmptyStatePrompt** | NOT WIRED | **HIGH** -- inline versions are inferior (no icons, no admin logic, wrong messages) | Low -- replace 3 inline divs with component |
| 5 | **ErrorState** | NOT WIRED | **HIGH** -- inline version has no retry button, no Alert component | Low -- replace 1 inline div, add refetch |
| 6 | **useGetKeyStatus** | NOT USED | **MEDIUM** -- forces unnecessary full API call to detect missing key | Low -- add hook call, conditional check |
| 7 | **UserFilterDropdown** | WIRED BUT BROKEN | **MEDIUM** -- `users={[]}` hardcoded, dropdown is useless | Medium -- need to derive user list from flows or add API endpoint |
| 8 | **`data.flows`** | IGNORED | **CRITICAL** -- API returns flow data, UI drops it entirely | Low -- connects through FlowBreakdownList |
| 9 | **`summary.truncated`** | IGNORED | **LOW** -- no truncation warning shown | Low -- add conditional warning |
| 10 | **`summary.cached`** | IGNORED | **LOW** -- no staleness indicator | Low -- add badge/indicator |

---

## 7. What a Fully-Wired UsagePage Would Look Like

The happy-path render (lines 95-112) currently renders:
1. Page header with title
2. DateRangePicker + UserFilterDropdown
3. UsageSummaryCards

**Missing from the render tree:**
4. FlowBreakdownList (the main data table)
5. Truncation warning (when `data.summary.truncated`)
6. Cache staleness indicator (when `data.summary.cached`)

**Missing from error/empty handling:**
- EmptyStatePrompt replacing inline KEY_NOT_CONFIGURED div
- EmptyStatePrompt replacing inline no-data div
- ErrorState replacing inline error div
- useGetKeyStatus for pre-flight key check

**Estimated lines of code to fix:** ~25 lines changed in UsagePage.tsx (mostly replacing inline JSX with component calls, adding FlowBreakdownList render, adding refetch destructuring).
