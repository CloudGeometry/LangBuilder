# OpenWebUI Development - Testing Protocol

## ⚠️ MANDATORY: Read This BEFORE Coding

**CRITICAL RULE**: You MUST complete ALL sections of this testing protocol before declaring a feature "done" or asking the user to test.

---

## Phase 1: Pre-Development Analysis

### 1.1 Understand Existing Code (30 minutes minimum)

Before writing ANY new code:

- [ ] Read ALL related files completely
- [ ] Trace data flow from database → API → store → component
- [ ] Document all state management patterns used
- [ ] Identify what variables can be `null`, `undefined`, or empty
- [ ] List all existing features that could be affected
- [ ] Check for reactive statements (`$:`) that depend on your changes

**Example Questions to Answer:**
- When does `$settings` get populated? Can it be null?
- What happens if the API call fails?
- What if the user has no data in the database yet?
- How does this component communicate with others?

### 1.2 Document Defensive Programming Needs

Create a checklist of what needs protection:

- [ ] Null/undefined checks for all external data
- [ ] Error handling for all async operations
- [ ] Fallback values for missing data
- [ ] Try/catch blocks around risky operations
- [ ] Loading states for async operations
- [ ] Error states with user-friendly messages

---

## Phase 2: Code Implementation

### 2.1 Write Defensive Code

**ALWAYS include these patterns:**

```javascript
// ✅ GOOD - Defensive coding
const currentShortcuts = $settings?.flowShortcuts?.shortcuts ?? [];

if (!currentShortcuts) {
    console.error('No shortcuts found in settings');
    return;
}

try {
    const response = await fetch('/api/...');
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    const data = await response.json();
} catch (error) {
    console.error('Failed to fetch:', error);
    toast.error('Failed to load data');
    return;
}
```

```javascript
// ❌ BAD - No defensive coding
const currentShortcuts = $settings.flowShortcuts.shortcuts;
const response = await fetch('/api/...');
const data = await response.json();
```

### 2.2 Add Comprehensive Logging

Every critical operation needs logging:

```javascript
console.log('🔍 [ComponentName] Starting operation:', { input });
console.log('📊 [ComponentName] Current state:', { state });
console.error('❌ [ComponentName] Error:', { error, context });
console.log('✅ [ComponentName] Success:', { result });
```

### 2.3 Write Error Boundaries

For Svelte components, wrap risky operations:

```svelte
{#if error}
    <div class="error-message">
        <p>Something went wrong: {error.message}</p>
        <button on:click={retry}>Retry</button>
    </div>
{:else if loading}
    <div>Loading...</div>
{:else}
    <!-- Normal content -->
{/if}
```

---

## Phase 3: Local Testing (BEFORE Building)

### 3.1 Code Review Checklist

- [ ] **Null Safety**: All external data has null checks
- [ ] **Error Handling**: All async operations wrapped in try/catch
- [ ] **Logging**: Console logs for all critical paths
- [ ] **Type Safety**: TypeScript types are correct (if using TS)
- [ ] **Reactive Safety**: `$:` statements won't trigger infinite loops
- [ ] **Store Safety**: Store mutations happen correctly

### 3.2 Mental Walkthrough

For EACH code path, answer:

1. **What if the API returns 404?**
2. **What if the data is empty?**
3. **What if the user's settings are null?**
4. **What if the network fails?**
5. **What if the user clicks twice rapidly?**

### 3.3 Regression Check

- [ ] List every existing feature
- [ ] Verify your changes don't break them
- [ ] Check that you didn't remove any null checks
- [ ] Ensure you didn't change shared state incorrectly

---

## Phase 4: Build & Deploy Testing

### 4.1 Follow CLAUDE.md Deployment Process

Complete ALL steps in CLAUDE.md:
- [ ] Clean build directories
- [ ] Build frontend
- [ ] **VERIFY local build** (grep for your changes)
- [ ] Docker rebuild with `--no-cache`
- [ ] Recreate container
- [ ] **VERIFY container** (grep inside container)

**DO NOT SKIP VERIFICATION STEPS!**

### 4.2 Container Verification

Before telling user to test:

```bash
# 1. Check container is running
docker ps | grep open-webui

# 2. Check logs for errors
docker logs open-webui --tail 50

# 3. Verify your changes are in the build
docker exec open-webui sh -c 'grep -r "YOUR_CHANGE" /app/build'

# 4. Check API is responding
curl http://localhost:3000/api/health
```

---

## Phase 5: Browser Testing Protocol

### 5.1 Manual Test Cases

Create test cases for EVERY user workflow:

**Example: FlowShortcuts Feature**

| Test Case | Steps | Expected Result | Pass/Fail |
|-----------|-------|-----------------|-----------|
| Load with no shortcuts | 1. Fresh user<br>2. Load page | No shortcuts display, no errors | ⬜ |
| Load with shortcuts | 1. User has data<br>2. Load page | Shortcuts display correctly | ⬜ |
| Add shortcut | 1. Click "Edit"<br>2. Click "Add"<br>3. Fill form<br>4. Save | New shortcut appears | ⬜ |
| Edit shortcut | 1. Click "Edit"<br>2. Click pencil<br>3. Change data<br>4. Update | Changes saved, all others remain | ⬜ |
| Delete shortcut | 1. Click "Edit"<br>2. Click trash<br>3. Confirm | Shortcut removed, others remain | ⬜ |
| API failure | 1. Stop backend<br>2. Try to save | User sees error message | ⬜ |
| Empty settings | 1. Clear localStorage<br>2. Reload | No errors, graceful fallback | ⬜ |

### 5.2 Console Check

Before declaring success:

- [ ] Open DevTools Console (F12)
- [ ] Check for ANY red errors
- [ ] Check for ANY yellow warnings
- [ ] Verify your debug logs appear
- [ ] Verify no infinite loops (repeating logs)

### 5.3 Network Tab Check

- [ ] Open DevTools Network tab
- [ ] Verify API calls succeed (status 200)
- [ ] Check API responses have expected data
- [ ] Verify no 404s or 500s
- [ ] Check no requests happen in infinite loops

---

## Phase 6: Edge Case Testing

### 6.1 Required Edge Cases

ALWAYS test these scenarios:

- [ ] **Empty State**: No data in database
- [ ] **Null State**: API returns null/undefined
- [ ] **Error State**: API returns error
- [ ] **Loading State**: Slow network (throttle to 3G)
- [ ] **Rapid Clicks**: Click buttons rapidly
- [ ] **Browser Refresh**: Hard refresh mid-operation
- [ ] **Multiple Tabs**: Open same page in 2 tabs
- [ ] **Stale Data**: Data changed by another tab

### 6.2 Stress Testing

- [ ] Add 50+ items (if applicable)
- [ ] Delete all items
- [ ] Rapid add/edit/delete cycles
- [ ] Fill forms with edge case data (special chars, emojis)

---

## Phase 7: Documentation

### 7.1 Update Documentation

- [ ] Add new feature to README
- [ ] Document any new APIs
- [ ] Update troubleshooting section if needed
- [ ] Add examples of error messages users might see

### 7.2 Create Recovery Instructions

If this feature can break, document:
- [ ] How to detect it's broken
- [ ] How to recover user data
- [ ] Browser console commands for quick fixes
- [ ] Database queries to restore state

---

## Phase 8: Final Checklist

**BEFORE telling user "it's ready":**

- [ ] All Phase 1-7 steps completed
- [ ] No console errors in browser
- [ ] All test cases pass
- [ ] Edge cases handled gracefully
- [ ] Error messages are user-friendly
- [ ] Feature works after hard refresh
- [ ] Changes verified in Docker container
- [ ] Regression tests pass (old features work)
- [ ] Documentation updated

---

## Common Anti-Patterns to Avoid

### ❌ What NOT to Do

1. **Assuming data exists**
   ```javascript
   // BAD
   const shortcuts = $settings.flowShortcuts.shortcuts;
   ```

2. **No error handling**
   ```javascript
   // BAD
   const data = await fetch('/api/data').then(r => r.json());
   ```

3. **Silent failures**
   ```javascript
   // BAD
   try { /* operation */ } catch (e) { /* nothing */ }
   ```

4. **No user feedback**
   ```javascript
   // BAD - user doesn't know what happened
   await saveData();
   ```

### ✅ What TO Do

1. **Always check for null**
   ```javascript
   // GOOD
   const shortcuts = $settings?.flowShortcuts?.shortcuts ?? [];
   if (!shortcuts) {
       console.error('No shortcuts found');
       toast.error('Failed to load shortcuts');
       return;
   }
   ```

2. **Always handle errors**
   ```javascript
   // GOOD
   try {
       const response = await fetch('/api/data');
       if (!response.ok) {
           throw new Error(`HTTP ${response.status}`);
       }
       const data = await response.json();
   } catch (error) {
       console.error('Fetch failed:', error);
       toast.error('Failed to load data');
       return;
   }
   ```

3. **Always provide feedback**
   ```javascript
   // GOOD
   try {
       await saveData();
       toast.success('Saved successfully');
   } catch (error) {
       console.error('Save failed:', error);
       toast.error('Failed to save');
   }
   ```

---

## Emergency Rollback Procedure

If you deploy broken code:

1. **Immediate Actions**
   ```bash
   # Revert to last working commit
   git log --oneline  # Find last good commit
   git checkout COMMIT_HASH -- path/to/broken/file.svelte

   # Rebuild and redeploy
   rm -rf build/ .svelte-kit/
   npm run build
   docker compose build --no-cache open-webui
   docker compose down open-webui && docker compose up -d open-webui
   ```

2. **User Recovery**
   - Provide browser console commands to restore state
   - Document in TROUBLESHOOTING.md
   - Add to user message explaining the issue

---

## Testing Time Estimates

**Budget this much time for testing:**

- Small change (CSS, text): 15 minutes
- Medium change (new button, minor feature): 30 minutes
- Large change (new component, major feature): 1 hour
- Critical change (state management, data flow): 2 hours

**Include:**
- Manual testing: 40%
- Edge case testing: 30%
- Documentation: 20%
- Regression testing: 10%

---

## Review Questions Before Deploying

Ask yourself:

1. ❓ **Did I actually test this in the browser?**
2. ❓ **Did I check the console for errors?**
3. ❓ **Did I verify it works with no data?**
4. ❓ **Did I test what happens if the API fails?**
5. ❓ **Did I verify old features still work?**
6. ❓ **Did I follow the CLAUDE.md deployment process?**
7. ❓ **Did I verify changes in the Docker container?**
8. ❓ **Can I recover if this breaks production?**

**If ANY answer is "no" - DO NOT DEPLOY!**
