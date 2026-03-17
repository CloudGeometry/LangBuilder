---
skill: serious-plan
slug: fix-frontend-errors
status: active
parent: Research/bugs/cost-tracking-dashboard-ix-defects
created: 2026-03-17
---

# Plan 05 — Fix Frontend Error Handling (BUG-I2, BUG-I3)

**Priority:** 5 (user experience)
**Depends on:** Plan 01 (DI crashes), Plan 02 (null date crash)

**Codebase root:** `/Users/cg-adubuc/cg-ai-msl-workspaces/orgs/4c1a52a5-c94b-4f56-a14b-704b5c2f4725/projects/83b7021c-55d2-4e01-bab2-3d59c760c2e6/main/langbuilder/`

---

## Task 0 — Smoke test: observe current broken behavior

**Goal:** Confirm the bug before fixing.

**Steps:**
1. Ensure no LangWatch API key is configured (or temporarily clear it).
2. Navigate to the Usage page.
3. Observe the network response: `503` with body `{"detail": {"code": "KEY_NOT_CONFIGURED", "message": "LangWatch API key not configured. Admin setup required.", "retryable": false}}`.
4. Observe the UI: generic "An error occurred" text in the error state.

**Root cause chain:**
- `LangWatchService.ts:25` — `throw await response.json()` throws a plain object `{detail: {...}}`, not an `Error` instance.
- `UsagePage.tsx:40` — `error instanceof Error` is `false` for plain objects, so the ternary falls through to `"An error occurred"`.

---

## Task 1 — Fix `LangWatchService.ts` error throwing (BUG-I2)

**File:** `src/frontend/src/services/LangWatchService.ts`
**Lines:** 25, 44, 55, 73 (all four `throw await response.json()` sites)

**Replace each instance** with proper Error construction:

```typescript
if (!response.ok) {
  const data = await response.json().catch(() => ({}));
  const detail = data?.detail;
  const message =
    (typeof detail === "object" ? detail?.message : detail) ||
    data?.message ||
    response.statusText ||
    "Unknown error";
  const err = new Error(message);
  (err as any).code = typeof detail === "object" ? detail?.code : undefined;
  (err as any).retryable = typeof detail === "object" ? detail?.retryable : undefined;
  throw err;
}
```

**Why this shape:** The backend `_raise_langwatch_http_error` (router.py:91-136) emits `detail` as an object `{code, message, retryable}`. But FastAPI can also emit `detail` as a string for validation errors. The code handles both.

**Error codes emitted by backend** (router.py:83-135):
| Code | HTTP | Retryable |
|------|------|-----------|
| `KEY_NOT_CONFIGURED` | 503 | `false` |
| `LANGWATCH_TIMEOUT` | 503 | `true` |
| `LANGWATCH_UNAVAILABLE` | 503 | `true` |
| `INVALID_KEY` | 422 | — |
| `INSUFFICIENT_CREDITS` | 422 | — |

---

## Task 1.5 — Update `LangWatchKeyForm.tsx` error handling

**File:** `src/frontend/src/components/LangWatchKeyForm.tsx`

**Goal:** Update the `getErrorMessage` helper to handle the new `Error` instance shape (from Task 1) in addition to the existing plain-object shape. This ensures backward compatibility.

**Replace the `getErrorMessage` function** with:

```typescript
function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "object" && error !== null && "detail" in error) {
    const detail = (error as any).detail;
    return detail?.message || detail?.code || "An unexpected error occurred";
  }
  return "An unexpected error occurred";
}
```

**Why:** Task 1 changes `throw await response.json()` to `throw new Error(...)`. Any component that catches service errors and inspects `error.detail.code` will break unless it also checks the `Error` instance path.

---

## Task 1.6 — Update `ErrorState.tsx` error code extraction

**File:** `src/frontend/src/pages/UsagePage/ErrorState.tsx` (if it exists and is imported by UsagePage)

**Goal:** Update `getErrorCode` to handle the new error shape.

**Update `getErrorCode`** to also check `(error as any).code` in addition to `(error as any).detail?.code`:

```typescript
function getErrorCode(error: unknown): string | undefined {
  return (error as any)?.code || (error as any)?.detail?.code;
}
```

**Note:** If `ErrorState.tsx` is dead code (not imported by `UsagePage.tsx` or any other component), it can be cleaned up in a later pass. Verify imports before editing.

---

## Task 2 — Fix `UsagePage.tsx` error display (BUG-I3)

**File:** `src/frontend/src/pages/UsagePage/UsagePage.tsx`
**Lines:** 30-43 (the `isError` block)

**Replace the error block** with code-aware rendering:

```tsx
if (isError) {
  const errCode = (error as any)?.code;

  if (errCode === "KEY_NOT_CONFIGURED") {
    return (
      <div
        className="flex flex-col items-center justify-center p-12 text-center"
        data-testid="usage-no-key-state"
      >
        <h2 className="text-lg font-semibold">No API Key Configured</h2>
        <p className="text-sm text-muted-foreground mt-2">
          A LangWatch API key is required to view usage data. Contact your
          administrator to configure one.
        </p>
      </div>
    );
  }

  const retryable = (error as any)?.retryable;

  return (
    <div
      className="flex flex-col items-center justify-center p-12 text-center"
      data-testid="usage-error-state"
    >
      <h2 className="text-lg font-semibold text-destructive">
        Failed to load usage data
      </h2>
      <p className="text-sm text-muted-foreground mt-2">
        {error instanceof Error ? error.message : "An error occurred"}
      </p>
      {retryable && (
        <p className="text-xs text-muted-foreground mt-1">
          This may be temporary. Try refreshing.
        </p>
      )}
    </div>
  );
}
```

**Sync pair:** The `errCode` values checked here must match the `code` strings set in Task 1, which must match the `code` fields in `router.py:83-135`.

---

## Task 3 — Verify all error states render correctly

**Test matrix:**

| Trigger | Expected code | Expected UI |
|---------|--------------|-------------|
| No API key configured | `KEY_NOT_CONFIGURED` | "No API Key Configured" with admin instructions |
| LangWatch down / network error | `LANGWATCH_UNAVAILABLE` | "Failed to load usage data" + message + retry hint |
| LangWatch timeout | `LANGWATCH_TIMEOUT` | "Failed to load usage data" + timeout message + retry hint |
| Invalid key stored | `INVALID_KEY` | "Failed to load usage data" + invalid key message |
| Generic/unexpected error | none | "Failed to load usage data" + `error.message` |

**Verify for each:**
1. Error state renders (not loading skeleton, not empty state).
2. Correct `data-testid` is present (`usage-no-key-state` or `usage-error-state`).
3. User-facing message is meaningful (not "An error occurred", not raw JSON).
4. No console errors from `instanceof Error` check.

---

## Task 4 — Update `LangWatchService.test.ts` assertions

**File:** `src/frontend/src/services/LangWatchService.test.ts`

**Goal:** Update test assertions to match the new error shape from Task 1. Errors are now `Error` instances, not plain objects.

**Change all assertions** that use `rejects.toEqual({ detail: "..." })` to `rejects.toThrow("...")`:

```typescript
// Before:
await expect(someCall()).rejects.toEqual({ detail: "..." });

// After:
await expect(someCall()).rejects.toThrow("...");
```

**Why:** Task 1 changed `throw await response.json()` to `throw new Error(message)`. Tests that assert against the old plain-object shape (`{ detail: ... }`) will fail because the thrown value is now an `Error` instance with `.message` containing the extracted message string.
