---
skill: serious-plan
slug: wire-existing-components
status: active
parent: Research/bugs/dashboard-completeness-audit
created: 2026-03-17
---

# Plan 01: Wire Existing Components into UsagePage

**FRs:** FR-003, FR-005, FR-007, FR-008, FR-010 | **Priority:** P0
**Scope:** 5 pre-built, pre-tested components need to be imported and rendered in `UsagePage.tsx`. No new components.

**Root file:** `src/frontend/src/pages/UsagePage/UsagePage.tsx` (113 lines)

---

## Task 0 -- Smoke Test (Baseline)

**Intent:** Capture current broken state so we can diff against it after wiring.

**Steps:**
1. Open `/usage` in browser
2. Confirm only summary cards visible after the header
3. Confirm no flow breakdown table rendered
4. Confirm empty-state div shows generic text with no admin/user distinction
5. Confirm error state has no retry button

**AC:**
- [ ] Screenshot captured showing current state

**Rollback:** N/A -- read-only

---

## Task 1 -- Wire FlowBreakdownList (FR-007, FR-008)

**Intent:** Render per-flow cost breakdown with expandable run details. The entire drill-down chain (`FlowBreakdownList` -> `FlowBreakdownRow` -> `FlowRunsTable`) is pre-built.

**File:** `UsagePage.tsx`

**Changes:**
1. Add import at line 5:
   ```ts
   import { FlowBreakdownList } from "./components/FlowBreakdownList";
   ```
2. Add `expandedFlowId` state tracking (for `onFlowExpand` callback):
   ```ts
   const [expandedFlowId, setExpandedFlowId] = useState<string | null>(null);
   ```
3. After `<UsageSummaryCards summary={data.summary} />` (line 109), render:
   ```tsx
   <FlowBreakdownList
     flows={data.flows}
     onFlowExpand={setExpandedFlowId}
     dateRange={dateRange}
   />
   ```

**Props contract** (from `FlowBreakdownList.tsx` lines 12-16):
- `flows: FlowUsage[]` -- matches `data.flows` from `UsageResponse`
- `onFlowExpand: (flowId: string) => void` -- callback when row expand toggled
- `dateRange?: DateRange` -- passed through to `FlowRunsTable` for run queries

**AC:**
- [ ] Flow breakdown table renders below summary cards
- [ ] Each row shows flow name, total cost, invocation count, avg cost
- [ ] Clicking "Runs" expands to show `FlowRunsTable` with per-run details
- [ ] Empty flows array shows "No flows found" empty state
- [ ] Pagination controls appear when >50 flows

**Rollback:** Remove the import and the `<FlowBreakdownList>` JSX element.

---

## Task 2 -- Wire EmptyStatePrompt (FR-003)

**Intent:** Replace inline divs with `EmptyStatePrompt` which has admin/user distinction. Admins see a settings link; regular users see "contact your administrator."

**File:** `UsagePage.tsx`

**Changes:**
1. Add imports:
   ```ts
   import { EmptyStatePrompt } from "./components/EmptyStatePrompt";
   import useAuthStore from "@/stores/authStore";
   ```
2. Inside `UsagePage()`, derive `isAdmin`:
   ```ts
   const isAdmin = useAuthStore((state) => state.isAdmin);
   ```
3. Replace the `KEY_NOT_CONFIGURED` block (lines 39-52) with:
   ```tsx
   return (
     <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
       <EmptyStatePrompt variant="no_key" isAdmin={isAdmin} />
     </PageLayout>
   );
   ```
4. Replace the no-data block (lines 79-92) with:
   ```tsx
   return (
     <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
       <EmptyStatePrompt variant="no_data" isAdmin={isAdmin} />
     </PageLayout>
   );
   ```

**Props contract** (from `EmptyStatePrompt.tsx` lines 1-4):
- `variant: "no_key" | "no_data"`
- `isAdmin: boolean`

**Auth store pattern** (confirmed from `authAdminGuard/index.tsx`):
- `useAuthStore((state) => state.isAdmin)` -- boolean, defaults `false`

**AC:**
- [ ] Admin with no key sees "Go to Admin Settings" link
- [ ] Non-admin with no key sees "Please contact your administrator"
- [ ] No-data state says "No usage data found for this period" with date range hint
- [ ] `data-testid="empty-state-no-key"` and `data-testid="empty-state-no-data"` present

**Rollback:** Revert to inline `<div>` elements.

---

## Task 3 -- Wire ErrorState (FR-005)

**Intent:** Replace inline error div with `ErrorState` component that has a retry button and maps error codes to user-friendly messages.

**File:** `UsagePage.tsx`

**Changes:**
1. Add import:
   ```ts
   import { ErrorState } from "./components/ErrorState";
   ```
2. Destructure `refetch` from the query hook (line 22):
   ```ts
   const { data, isLoading, isError, error, refetch } = useGetUsageSummary({...});
   ```
3. Replace the general error block (lines 57-76) with:
   ```tsx
   return (
     <PageLayout title="Usage" description="Track API usage and costs." backTo={-1 as To}>
       <ErrorState error={error} onRetry={() => refetch()} />
     </PageLayout>
   );
   ```
   Note: `ErrorState` handles error code mapping internally via `getErrorCode()` and `ERROR_MESSAGES` lookup. The `retryable` prop defaults to `true`.

**Props contract** (from `ErrorState.tsx` lines 40-44):
- `error: unknown` -- any error object, extracts `.code` or `.detail.code`
- `onRetry: () => void` -- callback for retry button
- `retryable?: boolean` -- defaults `true`

**AC:**
- [ ] Error state shows Alert with user-friendly message
- [ ] "Try Again" button visible and calls `refetch()`
- [ ] `LANGWATCH_TIMEOUT` shows "LangWatch took too long to respond. Try again."
- [ ] `data-testid="error-state"` and `data-testid="retry-button"` present

**Rollback:** Revert to inline `<div>` error display.

---

## Task 4 -- Fix UserFilterDropdown (FR-010)

**Intent:** Populate the dropdown from flow data instead of hardcoded `users={[]}`. Show only for admins. Hide when <2 users.

**File:** `UsagePage.tsx`

**Changes:**
1. Derive unique users from `data.flows` before the return statement:
   ```ts
   const uniqueUsers = useMemo(() => {
     const seen = new Map<string, string>();
     for (const flow of data.flows) {
       if (flow.owner_user_id && !seen.has(flow.owner_user_id)) {
         seen.set(flow.owner_user_id, flow.owner_username);
       }
     }
     return Array.from(seen, ([id, username]) => ({ id, username }));
   }, [data.flows]);
   ```
2. Add `useMemo` to the React import at line 1.
3. Conditionally render the dropdown (replace lines 102-106):
   ```tsx
   {isAdmin && uniqueUsers.length >= 2 && (
     <UserFilterDropdown
       value={userId}
       onChange={setUserId}
       users={uniqueUsers}
     />
   )}
   ```

**Data source** (from `FlowUsage` type, `usage.ts` lines 27-35):
- `owner_user_id: string` and `owner_username: string` on each flow

**Props contract** (from `UserFilterDropdown.tsx` lines 1-9):
- `users: { id: string; username: string }[]`

**AC:**
- [ ] Admin sees dropdown populated with usernames from flow data
- [ ] Non-admin does NOT see the dropdown
- [ ] Dropdown hidden when fewer than 2 distinct users
- [ ] Selecting a user filters the dashboard via `userId` state -> API query
- [ ] "All users" option resets filter to null

**Rollback:** Revert to `users={[]}` and remove conditional rendering.

---

## Task 5 -- Verify (End-to-End)

**Intent:** Confirm all wired components render correctly together.

**Steps:**
1. Open `/usage` as admin with valid LangWatch key and flow data
2. Confirm: summary cards + flow breakdown table visible
3. Click a flow row "Runs" button -> run detail table expands
4. Confirm: user filter dropdown populated, selecting a user filters results
5. Clear the LangWatch key, reload -> confirm admin empty state with settings link
6. Switch to non-admin user, reload -> confirm non-admin empty state
7. Force an API error -> confirm ErrorState with retry button
8. Click "Try Again" -> confirm refetch fires

**AC:**
- [ ] All 5 components render without console errors
- [ ] Flow breakdown drill-down chain works end-to-end
- [ ] Admin vs non-admin empty states show correct messaging
- [ ] Error retry works
- [ ] User filter populates and filters correctly
