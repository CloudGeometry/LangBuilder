# Code Implementation Audit: Phase 2, Task 2.2 - Enforce Read Permission on List Flows Endpoint

## Executive Summary

This audit evaluates the implementation of **Phase 2, Task 2.2: "Enforce Read Permission on List Flows Endpoint"**. The implementation adds RBAC permission checking to the `GET /api/v1/flows/` endpoint to enforce Flow:Read permission at Global scope.

**Overall Assessment**: **CRITICAL ISSUES FOUND - IMPLEMENTATION DOES NOT MATCH PLAN**

The implementation has **CRITICAL MISALIGNMENT** with the implementation plan specifications:
1. **Wrong permission format**: Uses "Flow:Read" instead of "Read"
2. **Wrong scope**: Checks Global scope instead of per-flow scope filtering
3. **Missing flow filtering logic**: Does not filter flows based on user's role assignments
4. **Incorrect enforcement approach**: Blocks all access instead of filtering accessible flows

The implementation applies a coarse-grained "all or nothing" permission check at Global scope, which is fundamentally different from the fine-grained per-resource filtering specified in the implementation plan. This creates a security architecture mismatch that will prevent proper multi-user flow access control.

### Critical Findings
- **Permission Format Error**: Implementation uses `permission_name="Flow:Read"` but `RBACService.can_access()` expects just `"Read"` with separate `scope_type="Flow"`
- **Scope Mismatch**: Checks Global scope (`scope_id=None`) instead of per-flow scope
- **Missing Flow Filtering**: Does not implement the required SQL joins to filter flows by user role assignments
- **Architecture Deviation**: Uses imperative check instead of recommended declarative dependency pattern

### Impact Assessment
- **Functionality**: The endpoint will **FAIL** to work correctly - will either block all users or allow all users
- **Security**: Does not provide the intended per-flow access control
- **Maintainability**: Deviates from RBAC infrastructure patterns established in decorator utilities
- **Production Readiness**: **NOT PRODUCTION READY** - requires significant rework

---

## Audit Scope

- **Task ID**: Phase 2, Task 2.2
- **Task Name**: Enforce Read Permission on List Flows Endpoint
- **Implementation Documentation**: `docs/code-generations/phase2-task2.2-rbac-decorators-implementation-report.md` (decorator infrastructure)
- **Implementation Plan**: `.alucify/implementation-plans/rbac-implementation-plan-v1.1.md`
- **AppGraph**: `.alucify/appgraph.json`
- **Architecture Spec**: `.alucify/architecture.md`
- **Audit Date**: 2025-11-09

**Scope Clarification**: The implementation report documents RBAC decorator infrastructure (prerequisite utilities), while Task 2.2 specifically requires applying RBAC enforcement to the List Flows endpoint. This audit focuses on the actual endpoint implementation in `flows.py`, not the decorator infrastructure.

---

## Overall Assessment

**Status**: **FAIL** - Critical implementation issues prevent proper functionality

**Rationale**: The implementation fundamentally deviates from the implementation plan's specifications for per-flow access control. The current implementation will not work as intended due to incorrect permission format, wrong scope checking, and missing flow filtering logic.

**Production Readiness**: **NOT READY** - Requires complete reimplementation following the plan's specifications

**Next Steps**:
1. **IMMEDIATE**: Revert the current implementation
2. **CRITICAL**: Reimplement following the implementation plan's approach:
   - Use correct permission format: `permission_name="Read"`, `scope_type="Flow"`
   - Implement SQL joins to filter flows by user role assignments
   - Handle permission inheritance from Project scope
   - Use helper functions or dependencies from decorator infrastructure
3. **REQUIRED**: Create comprehensive tests for endpoint RBAC behavior
4. **RECOMMENDED**: Conduct code review before merge

**Re-audit Required**: **YES** - Full re-audit required after reimplementation

---

## Detailed Findings

### 1. Implementation Plan Compliance

#### 1.1 Scope and Goals Alignment

**Status**: **CRITICAL ISSUES FOUND**

**Task Scope from Plan**:
> "Integrate RBAC checks into the `GET /api/v1/flows` endpoint to filter flows based on user's Read permission."

**Task Goals from Plan**:
- Filter flows based on user's Read permission at Flow scope
- Return only flows where user has explicit or inherited Read permission
- Support permission inheritance from Project to Flow
- Maintain backward compatibility for superusers

**Implementation Review**:

| Aspect | Status | Details |
|--------|--------|---------|
| Scope correctness | ❌ **CRITICAL ISSUE** | Implementation checks Global scope, not per-flow filtering |
| Goals achievement | ❌ **NOT ACHIEVED** | Does not filter flows; blocks or allows all |
| Complete implementation | ❌ **INCOMPLETE** | Missing SQL joins for flow filtering |

**Critical Gaps Identified**:

1. **Wrong Permission Check Scope** (flows.py:226-238):
   ```python
   # CURRENT IMPLEMENTATION (INCORRECT)
   has_permission = await rbac_service.can_access(
       user_id=current_user.id,
       permission_name="Flow:Read",  # ❌ WRONG FORMAT
       scope_type="Global",          # ❌ WRONG SCOPE
       scope_id=None,                # ❌ SHOULD BE PER-FLOW
       db=session,
   )
   if not has_permission:
       raise HTTPException(status_code=403, ...)  # ❌ BLOCKS ALL ACCESS
   ```

   **Issues**:
   - **Permission name format**: Uses `"Flow:Read"` but `RBACService.can_access()` expects `permission_name="Read"` with separate `scope_type="Flow"`
   - **Scope type**: Uses `"Global"` when it should filter per-flow scope
   - **Error handling**: Raises 403 blocking all access instead of filtering flows
   - **No flow filtering**: Does not implement the required SQL joins

2. **Missing Flow Filtering Logic**:
   The implementation plan specifies (lines 928-976):
   ```python
   # REQUIRED IMPLEMENTATION (FROM PLAN)
   # Get flows where user has explicit role assignment OR inherited via Project
   stmt = (
       select(Flow)
       .outerjoin(UserRoleAssignment, ...)  # Join for explicit Flow assignments
       .outerjoin(Folder, ...)              # Join for Project inheritance
       .outerjoin(UserRoleAssignment, ...)  # Join for Project assignments
       .where(or_(...))                     # Filter by assignments
       .offset(skip).limit(limit)
   )

   flows = result.scalars().all()

   # Filter flows by Read permission
   accessible_flows = []
   for flow in flows:
       if await rbac.can_access(user_id, "Read", "Flow", flow.id, db):
           accessible_flows.append(flow)
   ```

   **Current implementation**: This entire flow filtering logic is **MISSING**.

3. **Incorrect Architecture Pattern**:
   - Implementation uses imperative `rbac_service.can_access()` call
   - Implementation plan and decorator infrastructure recommend declarative dependency pattern
   - Deviates from established RBAC patterns without justification

**Drifts Identified**:

1. **Architecture Drift** (flows.py:203):
   ```python
   # Uses dependency injection for rbac_service (good)
   rbac_service: Annotated[object, Depends(get_rbac_service)] = None,
   ```
   But then calls it imperatively instead of using declarative dependencies like `RequireFlowRead` or helper functions like `check_flow_permission()` established in decorator infrastructure.

2. **Permission Format Drift** (flows.py:229):
   Uses `"Flow:Read"` format inconsistent with `RBACService.can_access()` signature which expects separate `permission_name` and `scope_type` parameters.

#### 1.2 Impact Subgraph Fidelity

**Status**: **PARTIALLY CORRECT**

**Impact Subgraph from Plan**:
- **Modified Nodes**:
  - `nl0005`: List Flows Endpoint Handler (`src/backend/base/langbuilder/api/v1/flows.py`)

**Implementation Review**:

| AppGraph Node | Type | Implementation Status | Location | Issues |
|---------------|------|----------------------|----------|--------|
| nl0005: List Flows Endpoint | Modified | ⚠️ **PARTIALLY IMPLEMENTED** | flows.py:192-298 | Endpoint modified but implementation incorrect |

**Implementation Status**:
- ✅ Correct file modified: `flows.py`
- ✅ Correct endpoint: `read_flows` function
- ❌ Implementation logic does not match plan specifications
- ❌ Missing SQL joins for flow filtering
- ❌ Wrong permission checking approach

**Gaps Identified**:
- Implementation modifies the correct endpoint but does not implement the required flow filtering logic specified in the implementation plan

**Drifts Identified**:
- None related to AppGraph structure (correct node modified)

#### 1.3 Architecture & Tech Stack Alignment

**Status**: **PARTIALLY ALIGNED**

**Tech Stack from Plan**:
- Framework: FastAPI ✅
- ORM: SQLModel/SQLAlchemy ✅
- Async: Full async/await ✅
- Dependency Injection: FastAPI Depends() ✅
- RBAC Service: RBACService.can_access() ⚠️ (used incorrectly)

**Implementation Review**:

| Aspect | Expected | Actual | Aligned | Issues |
|--------|----------|--------|---------|--------|
| Framework | FastAPI | FastAPI | ✅ | None |
| Async patterns | async/await | async/await | ✅ | None |
| Dependency injection | Depends() | Depends(get_rbac_service) | ✅ | None |
| RBAC integration | RBACService.can_access() | RBACService.can_access() | ⚠️ | Incorrect parameter usage |
| SQL filtering | SQLModel select() with joins | **MISSING** | ❌ | Flow filtering not implemented |
| Error handling | 403 for no permission | 403 HTTPException | ✅ | Correct status code |

**Issues Identified**:

1. **Incorrect RBACService Usage** (flows.py:227-233):
   ```python
   # CURRENT (INCORRECT)
   has_permission = await rbac_service.can_access(
       user_id=current_user.id,
       permission_name="Flow:Read",  # ❌ Should be "Read"
       scope_type="Global",          # ❌ Should be "Flow"
       scope_id=None,                # ❌ Should be flow.id in loop
       db=session,
   )
   ```

   **RBACService.can_access() Signature** (from service.py:40-47):
   ```python
   async def can_access(
       self,
       user_id: UUID,
       permission_name: str,      # e.g., "Read", "Update", "Delete"
       scope_type: str,           # e.g., "Flow", "Project", "Global"
       scope_id: UUID | None,     # Specific resource ID (None for Global)
       db: AsyncSession,
   ) -> bool:
   ```

   The implementation passes `permission_name="Flow:Read"` which is incorrect. The service expects just `"Read"` with `scope_type="Flow"`.

2. **Missing SQL Joins** (flows.py:258-294):
   Current implementation uses simple user_id filter:
   ```python
   # CURRENT (INCORRECT)
   if auth_settings.AUTO_LOGIN:
       stmt = select(Flow).where(
           (Flow.user_id == None) | (Flow.user_id == current_user.id)
       )
   else:
       stmt = select(Flow).where(Flow.user_id == current_user.id)
   ```

   Implementation plan requires joins with UserRoleAssignment:
   ```python
   # REQUIRED (FROM PLAN)
   stmt = (
       select(Flow)
       .outerjoin(UserRoleAssignment, ...)
       .outerjoin(Folder, ...)
       .outerjoin(UserRoleAssignment, ...)  # For Project inheritance
       .where(or_(...))
   )
   ```

3. **Pattern Deviation**:
   - Does not use decorator utilities (RequireFlowRead, check_flow_permission)
   - Implements imperative check instead of declarative dependency
   - Inconsistent with RBAC infrastructure patterns

#### 1.4 Success Criteria Validation

**Status**: **NOT MET**

**Success Criteria from Plan**:
The implementation plan doesn't explicitly list success criteria for Task 2.2, but based on the task description and implementation details, the implied success criteria are:

| Criterion | Implementation Status | Test Validation | Evidence | Issues |
|-----------|----------------------|----------------|----------|--------|
| Filter flows by Read permission | ❌ **NOT MET** | ❌ No tests | N/A | No filtering implemented |
| Check per-flow permissions | ❌ **NOT MET** | ❌ No tests | N/A | Checks Global scope instead |
| Support permission inheritance | ❌ **NOT MET** | ❌ No tests | N/A | No inheritance logic |
| Maintain superuser bypass | ⚠️ **PARTIAL** | ❌ No tests | service.py:70-73 | Handled by RBACService but not tested |
| Return only accessible flows | ❌ **NOT MET** | ❌ No tests | N/A | Returns all or blocks all |
| Maintain backward compatibility | ⚠️ **UNKNOWN** | ❌ No tests | N/A | Impact on existing users unknown |

**Gaps Identified**:
- **No endpoint-specific tests**: No tests verify RBAC behavior on the actual `read_flows` endpoint
- **All success criteria unmet**: The core functionality (flow filtering) is not implemented
- **No validation evidence**: Cannot verify any success criteria without tests

### 2. Code Quality Assessment

#### 2.1 Code Correctness

**Status**: **CRITICAL ERRORS FOUND**

| File | Issue Type | Severity | Description | Location |
|------|-----------|----------|-------------|----------|
| flows.py | Logic Error | **CRITICAL** | Incorrect permission name format "Flow:Read" | Line 229 |
| flows.py | Logic Error | **CRITICAL** | Wrong scope type "Global" for flow filtering | Line 230 |
| flows.py | Logic Error | **CRITICAL** | Blocks all access instead of filtering flows | Lines 234-238 |
| flows.py | Missing Implementation | **CRITICAL** | No SQL joins for role assignment filtering | Lines 258-294 |
| flows.py | Missing Implementation | **CRITICAL** | No per-flow permission loop | N/A |

**Critical Issues Identified**:

1. **Permission Name Format Error** (flows.py:229):
   ```python
   permission_name="Flow:Read",  # ❌ INCORRECT FORMAT
   ```

   **Issue**: `RBACService.can_access()` expects `permission_name="Read"` with separate `scope_type="Flow"` parameter.

   **Impact**: The permission check will **ALWAYS FAIL** because there is no permission named "Flow:Read" in the database. The Permission model stores permissions as:
   - `name="Read"`, `scope="Flow"`
   - `name="Update"`, `scope="Flow"`
   - etc.

   **Evidence**: From Permission model (implementation plan lines 136-149):
   ```python
   class Permission(SQLModel, table=True):
       name: str = Field(index=True)      # "Create", "Read", "Update", "Delete"
       scope: str = Field(index=True)     # "Flow", "Project"
   ```

   The `_role_has_permission` method (service.py:159-188) queries:
   ```python
   .where(
       Permission.name == permission_name,  # Expects "Read"
       Permission.scope == scope_type,      # Expects "Flow"
   )
   ```

2. **Wrong Scope Check** (flows.py:230-231):
   ```python
   scope_type="Global",  # ❌ SHOULD BE "Flow"
   scope_id=None,        # ❌ SHOULD BE flow.id per iteration
   ```

   **Issue**: Checking Global scope instead of per-flow scope.

   **Impact**:
   - Checks if user is a Global Admin (has Admin role at Global scope)
   - Does NOT check if user has Read permission on individual flows
   - Either blocks ALL users or allows ALL users (all-or-nothing)
   - Defeats the purpose of per-resource RBAC

3. **Missing Flow Filtering Logic**:
   ```python
   # CURRENT: Simple user_id filter (flows.py:258-263)
   if auth_settings.AUTO_LOGIN:
       stmt = select(Flow).where(
           (Flow.user_id == None) | (Flow.user_id == current_user.id)
       )
   else:
       stmt = select(Flow).where(Flow.user_id == current_user.id)
   ```

   **Issue**: Does not filter by role assignments.

   **Impact**: Returns flows based on ownership (user_id), ignoring role-based access control entirely.

4. **Incorrect Error Handling** (flows.py:234-238):
   ```python
   if not has_permission:
       raise HTTPException(
           status_code=403,
           detail="Missing required permission: Flow:Read on Global scope",
       )
   ```

   **Issue**: Blocks ALL access with 403 instead of filtering flows.

   **Impact**:
   - Non-admin users cannot access ANY flows
   - Breaks existing functionality
   - Not the "filter flows" behavior specified in plan

#### 2.2 Code Quality

**Status**: **ACCEPTABLE STRUCTURE, INCORRECT LOGIC**

| Aspect | Status | Issues |
|--------|--------|--------|
| Readability | ✅ Good | Code is clear and well-commented |
| Maintainability | ⚠️ Needs improvement | Logic does not match plan |
| Modularity | ✅ Good | Proper dependency injection |
| DRY Principle | ✅ Good | No duplication |
| Documentation | ⚠️ Incomplete | Docstring doesn't reflect RBAC behavior |
| Naming | ✅ Good | Variable names are clear |

**Issues Identified**:

1. **Incomplete Docstring** (flows.py:205-225):
   The docstring mentions "rbac_service: RBAC service for permission checking" but doesn't describe:
   - What permission is being checked
   - How the filtering works
   - What happens if permission is denied
   - Expected RBAC behavior

2. **Missing Comments**:
   No comments explaining the RBAC logic or why Global scope is checked (which is incorrect anyway)

#### 2.3 Pattern Consistency

**Status**: **INCONSISTENT WITH RBAC INFRASTRUCTURE**

**Expected Patterns** (from decorator infrastructure and architecture spec):

1. **Declarative Dependency Pattern** (RECOMMENDED):
   ```python
   # RECOMMENDED APPROACH
   from langbuilder.services.rbac import RequireFlowRead

   @router.get("/", dependencies=[Depends(RequireFlowRead)])
   async def read_flows(...):
       # Permission already checked by dependency
   ```

2. **Helper Function Pattern** (ALTERNATIVE):
   ```python
   # ALTERNATIVE APPROACH
   from langbuilder.services.rbac import check_flow_permission

   for flow in flows:
       if await check_flow_permission(flow.id, "Read", current_user, db, rbac):
           accessible_flows.append(flow)
   ```

3. **Correct RBACService Usage**:
   ```python
   # CORRECT IMPERATIVE APPROACH
   has_permission = await rbac.can_access(
       user_id=current_user.id,
       permission_name="Read",     # ✅ Just the permission name
       scope_type="Flow",          # ✅ The scope type
       scope_id=flow.id,           # ✅ Specific flow ID
       db=db,
   )
   ```

**Implementation Review**:

| File | Expected Pattern | Actual Pattern | Consistent | Issues |
|------|-----------------|----------------|------------|--------|
| flows.py | Declarative dependency or helper | Imperative with wrong params | ❌ | Inconsistent and incorrect |
| flows.py | Per-flow filtering loop | No filtering loop | ❌ | Missing pattern |
| flows.py | SQL joins for role assignments | Simple user_id filter | ❌ | Missing pattern |

**Issues Identified**:

1. **Does Not Use Decorator Infrastructure** (flows.py:192-298):
   - RBAC decorator utilities created in prior task (decorators.py)
   - Provides RequireFlowRead, check_flow_permission, etc.
   - Implementation does not use any of these utilities
   - Reimplements logic incorrectly

2. **Inconsistent with Implementation Plan Examples**:
   - Plan shows SQL joins with UserRoleAssignment
   - Plan shows per-flow permission checking loop
   - Plan shows use of helper functions
   - Implementation does none of these

3. **Deviates from LangBuilder Patterns**:
   - Existing endpoints use dependency injection patterns
   - RBAC infrastructure established dependency pattern
   - This implementation ignores both

#### 2.4 Integration Quality

**Status**: **POOR INTEGRATION**

**Integration Points**:

| Integration Point | Status | Issues |
|-------------------|--------|--------|
| RBACService | ❌ **INCORRECT** | Wrong parameter usage |
| CurrentActiveUser | ✅ Good | Proper dependency |
| DbSession | ✅ Good | Proper dependency |
| Decorator utilities | ❌ **NOT USED** | Ignores infrastructure |
| Permission model | ❌ **MISMATCH** | Incorrect permission format |

**Issues Identified**:

1. **RBACService Integration Incorrect** (flows.py:227-233):
   - Calls `can_access()` with wrong parameters
   - Does not match service method signature
   - Will cause runtime failures

2. **Decorator Infrastructure Not Used**:
   - RBAC decorators and helpers available
   - Implementation reinvents logic (incorrectly)
   - Missed opportunity for code reuse

3. **Permission Model Mismatch**:
   - Permission model has separate `name` and `scope` fields
   - Implementation tries to combine them as "Flow:Read"
   - Fundamental misunderstanding of data model

### 3. Test Coverage Assessment

#### 3.1 Test Completeness

**Status**: **NO TESTS FOUND**

**Test Files Reviewed**:
- No tests found for `read_flows` endpoint RBAC behavior
- Decorator infrastructure has 28 tests (decorator functionality)
- No endpoint-specific RBAC tests

**Coverage Review**:

| Implementation File | Test File | Unit Tests | Edge Cases | Error Cases | Status |
|---------------------|-----------|------------|------------|-------------|--------|
| flows.py (read_flows) | **NONE** | ❌ | ❌ | ❌ | **NO COVERAGE** |

**Critical Gaps Identified**:

1. **No Endpoint RBAC Tests**:
   - No tests verify RBAC behavior on `read_flows` endpoint
   - No tests for flow filtering by permissions
   - No tests for permission inheritance
   - No tests for superuser bypass on this endpoint
   - No tests for error cases (403 for denied access)

2. **No Integration Tests**:
   - No tests verify RBACService integration with endpoint
   - No tests verify SQL queries filter correctly
   - No tests verify role assignments affect returned flows

3. **No Edge Case Tests**:
   - No tests for users with no role assignments
   - No tests for users with multiple role assignments
   - No tests for Project-to-Flow permission inheritance
   - No tests for pagination with filtered flows

#### 3.2 Test Quality

**Status**: **NOT APPLICABLE - NO TESTS EXIST**

**No tests found for Task 2.2 endpoint implementation.**

#### 3.3 Test Coverage Metrics

**Status**: **0% COVERAGE**

| File | Line Coverage | Branch Coverage | Function Coverage | Target | Met |
|------|--------------|-----------------|-------------------|--------|-----|
| flows.py (read_flows RBAC) | 0% | 0% | 0% | 80%+ | ❌ |

**Overall Coverage**: 0%

**Gaps Identified**:
- **CRITICAL**: No tests for read_flows RBAC functionality
- **CRITICAL**: Cannot verify implementation correctness
- **CRITICAL**: No regression protection

### 4. Unrequired Functionality Detection

#### 4.1 Scope Drift

**Status**: **NO SCOPE DRIFT**

The implementation attempts to add RBAC permission checking as specified in the task scope. However, the implementation is **INCORRECT**, not out-of-scope.

**Unrequired Functionality Found**: NONE

#### 4.2 Complexity Issues

**Status**: **ACCEPTABLE**

| File:Function | Complexity | Necessary | Issues |
|---------------|------------|-----------|--------|
| flows.py:read_flows | Medium | ✅ | Logic is incorrect but not over-complex |

**No unnecessary complexity issues identified.** The problem is missing required complexity (SQL joins, filtering loops), not extra complexity.

---

## Summary of Gaps

### Critical Gaps (Must Fix)

1. **Incorrect Permission Name Format** (flows.py:229)
   - **Impact**: Permission check will always fail
   - **File:Line**: flows.py:229
   - **Fix**: Change `permission_name="Flow:Read"` to `permission_name="Read"`
   - **Severity**: CRITICAL - Breaks functionality

2. **Wrong Scope Type** (flows.py:230)
   - **Impact**: Checks Global scope instead of per-flow
   - **File:Line**: flows.py:230
   - **Fix**: Change `scope_type="Global"` to `scope_type="Flow"` and check per-flow in loop
   - **Severity**: CRITICAL - Wrong security model

3. **Missing Flow Filtering Logic** (flows.py:258-294)
   - **Impact**: Does not filter flows by role assignments
   - **File:Line**: flows.py:258-294
   - **Fix**: Implement SQL joins with UserRoleAssignment as shown in implementation plan
   - **Severity**: CRITICAL - Core functionality missing

4. **Blocks All Access Instead of Filtering** (flows.py:234-238)
   - **Impact**: Returns 403 error for non-admin users instead of filtering flows
   - **File:Line**: flows.py:234-238
   - **Fix**: Remove the 403 check; filter flows per-user instead
   - **Severity**: CRITICAL - Wrong behavior

5. **No Endpoint Tests** (N/A)
   - **Impact**: Cannot verify implementation correctness
   - **File:Line**: N/A (missing file)
   - **Fix**: Create `test_flows_rbac.py` with comprehensive tests
   - **Severity**: CRITICAL - No validation

### Major Gaps (Should Fix)

1. **Does Not Use Decorator Infrastructure** (flows.py:192-298)
   - **Impact**: Ignores reusable RBAC utilities
   - **File:Line**: flows.py:192-298
   - **Fix**: Use `check_flow_permission()` helper or create custom dependency
   - **Severity**: MAJOR - Code reuse issue

2. **Incomplete Documentation** (flows.py:205-225)
   - **Impact**: Docstring doesn't describe RBAC behavior
   - **File:Line**: flows.py:205-225
   - **Fix**: Update docstring to document RBAC filtering
   - **Severity**: MAJOR - Documentation gap

3. **No Permission Inheritance Implementation** (flows.py:258-294)
   - **Impact**: Users with Project-level roles cannot access flows
   - **File:Line**: flows.py:258-294
   - **Fix**: Implement Project-to-Flow inheritance in SQL joins
   - **Severity**: MAJOR - Missing feature

### Minor Gaps (Nice to Fix)

1. **Missing Comments** (flows.py:226-238)
   - **Impact**: RBAC logic not explained in code
   - **File:Line**: flows.py:226-238
   - **Fix**: Add comments explaining RBAC permission check
   - **Severity**: MINOR - Code clarity

---

## Summary of Drifts

### Critical Drifts (Must Fix)

1. **Wrong RBACService Usage** (flows.py:227-233)
   - **Description**: Uses "Flow:Read" combined format instead of separate name/scope
   - **File:Line**: flows.py:227-233
   - **Impact**: Permission check will fail; incompatible with service API
   - **Severity**: CRITICAL

2. **Wrong Security Model** (flows.py:230-231)
   - **Description**: Checks Global scope instead of per-flow filtering
   - **File:Line**: flows.py:230-231
   - **Impact**: All-or-nothing access instead of granular control
   - **Severity**: CRITICAL

3. **Missing Implementation Plan Logic** (flows.py:258-294)
   - **Description**: Does not implement SQL joins specified in plan
   - **File:Line**: flows.py:258-294
   - **Impact**: Flow filtering by role assignments not working
   - **Severity**: CRITICAL

### Major Drifts (Should Fix)

1. **Pattern Inconsistency** (flows.py:192-298)
   - **Description**: Does not use decorator infrastructure patterns
   - **File:Line**: flows.py:192-298
   - **Impact**: Code inconsistency; missed code reuse opportunity
   - **Severity**: MAJOR

### Minor Drifts (Nice to Fix)

NONE

---

## Test Coverage Gaps

### Critical Coverage Gaps (Must Fix)

1. **No Endpoint RBAC Tests** (N/A)
   - **Description**: No tests for read_flows endpoint RBAC behavior
   - **File:Line**: N/A (missing test file)
   - **Impact**: Cannot verify implementation works correctly
   - **Fix**: Create comprehensive test suite for endpoint
   - **Severity**: CRITICAL

2. **No Permission Filtering Tests** (N/A)
   - **Description**: No tests verify flows are filtered by permissions
   - **File:Line**: N/A (missing test file)
   - **Impact**: Cannot verify security model works
   - **Fix**: Add tests for flow filtering by role assignments
   - **Severity**: CRITICAL

3. **No Permission Inheritance Tests** (N/A)
   - **Description**: No tests verify Project-to-Flow permission inheritance
   - **File:Line**: N/A (missing test file)
   - **Impact**: Cannot verify inheritance works
   - **Fix**: Add tests for inherited permissions
   - **Severity**: CRITICAL

### Major Coverage Gaps (Should Fix)

1. **No Edge Case Tests** (N/A)
   - **Description**: No tests for users with no role assignments
   - **File:Line**: N/A (missing test file)
   - **Impact**: Edge cases not validated
   - **Fix**: Add edge case tests
   - **Severity**: MAJOR

2. **No Integration Tests** (N/A)
   - **Description**: No tests verify RBACService integration
   - **File:Line**: N/A (missing test file)
   - **Impact**: Integration not validated
   - **Fix**: Add integration tests
   - **Severity**: MAJOR

### Minor Coverage Gaps (Nice to Fix)

1. **No Superuser Bypass Tests** (N/A)
   - **Description**: No tests verify superuser can access all flows
   - **File:Line**: N/A (missing test file)
   - **Impact**: Superuser behavior not validated
   - **Fix**: Add superuser tests
   - **Severity**: MINOR

---

## Recommended Improvements

### 1. Implementation Compliance Improvements

**CRITICAL: Complete Reimplementation Required**

The current implementation must be completely rewritten to follow the implementation plan's specifications. Here is the correct implementation approach:

#### Recommended Implementation (Based on Plan):

```python
@router.get("/", response_model=list[FlowRead] | Page[FlowRead] | list[FlowHeader], status_code=200)
async def read_flows(
    *,
    current_user: CurrentActiveUser,
    session: DbSession,
    rbac: RBACServiceDep,  # Use type alias from decorators
    remove_example_flows: bool = False,
    components_only: bool = False,
    get_all: bool = True,
    folder_id: UUID | None = None,
    params: Annotated[Params, Depends()],
    header_flows: bool = False,
):
    """Retrieve a list of flows with RBAC filtering.

    Returns only flows where the user has Read permission, either through:
    - Explicit Flow-level role assignment
    - Inherited Project-level role assignment
    - Superuser bypass
    - Global Admin role bypass

    Args:
        current_user: Authenticated user
        session: Database session
        rbac: RBAC service for permission checking
        ... (other params)

    Returns:
        Filtered list of flows based on user's Read permissions
    """
    try:
        auth_settings = get_settings_service().auth_settings

        # Get folders for filtering
        default_folder = (await session.exec(
            select(Folder).where(Folder.name == DEFAULT_FOLDER_NAME)
        )).first()
        default_folder_id = default_folder.id if default_folder else None

        starter_folder = (await session.exec(
            select(Folder).where(Folder.name == STARTER_FOLDER_NAME)
        )).first()
        starter_folder_id = starter_folder.id if starter_folder else None

        # Step 1: Get candidate flows based on role assignments
        # (simplified for clarity - full implementation needs joins)
        if current_user.is_superuser or await rbac._has_global_admin_role(current_user.id, session):
            # Superuser/Admin: get all flows
            stmt = select(Flow)
        else:
            # Regular user: get flows where user has role assignments
            # (Implementation plan lines 928-964 shows full SQL joins)
            stmt = (
                select(Flow)
                .distinct()
                .outerjoin(
                    UserRoleAssignment,
                    and_(
                        UserRoleAssignment.scope_id == Flow.id,
                        UserRoleAssignment.scope_type == "Flow",
                        UserRoleAssignment.user_id == current_user.id
                    )
                )
                .outerjoin(Folder, Flow.folder_id == Folder.id)
                .outerjoin(
                    UserRoleAssignment.alias("project_assignment"),
                    and_(
                        UserRoleAssignment.scope_id == Folder.id,
                        UserRoleAssignment.scope_type == "Project",
                        UserRoleAssignment.user_id == current_user.id
                    ),
                    isouter=True
                )
                .where(
                    or_(
                        UserRoleAssignment.id.isnot(None),           # Has Flow assignment
                        UserRoleAssignment.alias("project_assignment").id.isnot(None)  # Has Project assignment
                    )
                )
            )

        # Apply additional filters
        if remove_example_flows and starter_folder_id:
            stmt = stmt.where(Flow.folder_id != starter_folder_id)
        if components_only:
            stmt = stmt.where(Flow.is_component == True)
        if folder_id:
            stmt = stmt.where(Flow.folder_id == folder_id)

        # Execute query
        if get_all:
            flows = (await session.exec(stmt)).all()
        else:
            stmt = stmt.offset(params.skip).limit(params.limit)
            flows = (await session.exec(stmt)).all()

        # Step 2: Filter flows by Read permission
        accessible_flows = []
        for flow in flows:
            # Check if user has Read permission on this flow
            # CORRECT USAGE: permission_name="Read", scope_type="Flow", scope_id=flow.id
            if await rbac.can_access(
                user_id=current_user.id,
                permission_name="Read",      # ✅ Just "Read"
                scope_type="Flow",           # ✅ Flow scope
                scope_id=flow.id,            # ✅ Specific flow ID
                db=session,
            ):
                accessible_flows.append(flow)

        # Validate and return
        accessible_flows = validate_is_component(accessible_flows)

        if header_flows:
            flow_headers = [FlowHeader.model_validate(flow, from_attributes=True)
                          for flow in accessible_flows]
            return compress_response(flow_headers)

        return compress_response(accessible_flows)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
```

**Key Fixes in Recommended Implementation**:
1. ✅ Uses correct permission format: `permission_name="Read"`, `scope_type="Flow"`
2. ✅ Checks per-flow permissions in loop
3. ✅ Implements SQL joins for role assignment filtering
4. ✅ Handles permission inheritance from Project
5. ✅ Uses RBACServiceDep type alias from decorator infrastructure
6. ✅ Returns filtered flows instead of blocking access
7. ✅ Maintains superuser/admin bypass
8. ✅ Updated docstring documenting RBAC behavior

#### Alternative: Use Decorator Infrastructure

```python
# EVEN BETTER: Use helper function from decorator infrastructure
from langbuilder.services.rbac import check_flow_permission

# ... in filtering loop ...
for flow in flows:
    if await check_flow_permission(
        flow.id, "Read", current_user, session, rbac
    ):
        accessible_flows.append(flow)
```

### 2. Code Quality Improvements

1. **Fix Permission Name Format** (flows.py:229)
   - Change `permission_name="Flow:Read"` to `permission_name="Read"`
   - Add `scope_type="Flow"` parameter
   - **Rationale**: Match RBACService API signature

2. **Fix Scope Checking** (flows.py:230-231)
   - Change `scope_type="Global"` to `scope_type="Flow"`
   - Change `scope_id=None` to `scope_id=flow.id` in loop
   - **Rationale**: Enable per-flow permission checking

3. **Add Flow Filtering Logic** (flows.py:258-294)
   - Implement SQL joins with UserRoleAssignment
   - Add per-flow permission checking loop
   - Handle Project-to-Flow inheritance
   - **Rationale**: Implement core functionality

4. **Remove 403 Blocking** (flows.py:234-238)
   - Remove the HTTPException that blocks all access
   - Let flow filtering handle access control
   - **Rationale**: Correct behavior per plan

5. **Update Documentation** (flows.py:205-225)
   - Document RBAC filtering behavior
   - Explain permission checking logic
   - Document inheritance from Project
   - **Rationale**: Improve maintainability

### 3. Test Coverage Improvements

**CRITICAL: Create Comprehensive Test Suite**

Create `src/backend/tests/unit/api/v1/test_flows_rbac.py`:

```python
"""Tests for RBAC on List Flows endpoint."""

import pytest
from uuid import uuid4
from fastapi import status

class TestListFlowsRBAC:
    """Test suite for read_flows endpoint RBAC behavior."""

    @pytest.mark.asyncio
    async def test_list_flows_filters_by_read_permission(
        self, client, test_user, test_flow, editor_role, flow_read_permission, db
    ):
        """Test that endpoint filters flows by Read permission."""
        # Setup: Assign Editor role with Read permission to user for specific flow
        # ... setup code ...

        # Act: Call endpoint
        response = await client.get("/api/v1/flows/", headers=logged_in_headers)

        # Assert: User sees only flows they have Read permission for
        assert response.status_code == 200
        flows = response.json()
        assert len(flows) == 1
        assert flows[0]["id"] == str(test_flow.id)

    @pytest.mark.asyncio
    async def test_list_flows_inherits_permission_from_project(
        self, client, test_user, test_flow, test_folder, editor_role,
        flow_read_permission, db
    ):
        """Test that flow permissions are inherited from project."""
        # Setup: Assign role at Project level, not Flow level
        # ... setup code ...

        # Act: Call endpoint
        response = await client.get("/api/v1/flows/", headers=logged_in_headers)

        # Assert: User sees flow through Project inheritance
        assert response.status_code == 200
        flows = response.json()
        assert any(f["id"] == str(test_flow.id) for f in flows)

    @pytest.mark.asyncio
    async def test_list_flows_excludes_flows_without_permission(
        self, client, test_user, other_user_flow, db
    ):
        """Test that flows without permission are excluded."""
        # Setup: other_user_flow belongs to different user

        # Act: Call endpoint
        response = await client.get("/api/v1/flows/", headers=logged_in_headers)

        # Assert: User does not see other user's flows
        assert response.status_code == 200
        flows = response.json()
        assert not any(f["id"] == str(other_user_flow.id) for f in flows)

    @pytest.mark.asyncio
    async def test_list_flows_superuser_sees_all(
        self, client, superuser, test_flow, other_user_flow, db
    ):
        """Test that superuser sees all flows."""
        # Act: Call endpoint as superuser
        response = await client.get("/api/v1/flows/", headers=superuser_headers)

        # Assert: Superuser sees all flows
        assert response.status_code == 200
        flows = response.json()
        flow_ids = [f["id"] for f in flows]
        assert str(test_flow.id) in flow_ids
        assert str(other_user_flow.id) in flow_ids

    @pytest.mark.asyncio
    async def test_list_flows_global_admin_sees_all(
        self, client, test_user, admin_role, test_flow, other_user_flow, db
    ):
        """Test that global admin sees all flows."""
        # Setup: Assign Admin role at Global scope
        # ... setup code ...

        # Act: Call endpoint
        response = await client.get("/api/v1/flows/", headers=logged_in_headers)

        # Assert: Global admin sees all flows
        assert response.status_code == 200
        flows = response.json()
        flow_ids = [f["id"] for f in flows]
        assert str(test_flow.id) in flow_ids
        assert str(other_user_flow.id) in flow_ids

    @pytest.mark.asyncio
    async def test_list_flows_no_roles_returns_empty(
        self, client, test_user_no_roles, test_flow, db
    ):
        """Test that user with no role assignments sees no flows."""
        # Setup: User has no role assignments

        # Act: Call endpoint
        response = await client.get("/api/v1/flows/", headers=logged_in_headers)

        # Assert: Returns empty list
        assert response.status_code == 200
        flows = response.json()
        assert len(flows) == 0

    # Add more tests for:
    # - Multiple flows with different permissions
    # - Viewer role (Read only)
    # - Owner role (full access)
    # - Pagination with filtered flows
    # - Folder filtering with RBAC
    # - Component filtering with RBAC
```

**Minimum Required Tests**:
1. ✅ Filter flows by Read permission (user sees only authorized flows)
2. ✅ Permission inheritance from Project to Flow
3. ✅ Exclude flows without permission
4. ✅ Superuser bypass (sees all flows)
5. ✅ Global Admin bypass (sees all flows)
6. ✅ No roles returns empty list
7. Multiple flows with mixed permissions
8. Different role types (Viewer, Editor, Owner)
9. Pagination with RBAC filtering
10. Folder filtering with RBAC

**Target Coverage**: 95%+ line coverage, 90%+ branch coverage

### 4. Scope and Complexity Improvements

**No scope or complexity improvements needed** - the issue is missing required complexity (SQL joins, filtering), not excessive complexity.

---

## Action Items

### Immediate Actions (Must Complete Before Task Approval)

1. **REVERT Current Implementation** (Priority: CRITICAL)
   - **Action**: Revert changes to flows.py:192-298 (read_flows function)
   - **Rationale**: Current implementation is fundamentally incorrect and will break functionality
   - **File**: flows.py
   - **Expected Outcome**: Endpoint reverted to pre-Task-2.2 state

2. **REIMPLEMENT Following Plan** (Priority: CRITICAL)
   - **Action**: Implement flow filtering with SQL joins as specified in implementation plan
   - **Approach**: Use recommended implementation from Section 6.1 above
   - **File**: flows.py:192-298
   - **Expected Outcome**: Endpoint filters flows by user's Read permissions

3. **FIX Permission Name Format** (Priority: CRITICAL)
   - **Action**: Use `permission_name="Read"`, `scope_type="Flow"`, `scope_id=flow.id`
   - **File**: flows.py (in new implementation)
   - **Expected Outcome**: Permission check uses correct RBACService API

4. **IMPLEMENT Per-Flow Permission Loop** (Priority: CRITICAL)
   - **Action**: Add loop to check Read permission for each flow
   - **File**: flows.py (in new implementation)
   - **Expected Outcome**: Returns only flows user can access

5. **CREATE Comprehensive Test Suite** (Priority: CRITICAL)
   - **Action**: Create `test_flows_rbac.py` with minimum 10 test cases
   - **File**: tests/unit/api/v1/test_flows_rbac.py (new file)
   - **Expected Outcome**: 95%+ coverage of RBAC filtering logic

### Follow-up Actions (Should Address in Near Term)

1. **ADD Documentation** (Priority: MAJOR)
   - **Action**: Update docstring to document RBAC filtering behavior
   - **File**: flows.py:205-225
   - **Expected Outcome**: Clear documentation of permission checking

2. **USE Decorator Infrastructure** (Priority: MAJOR)
   - **Action**: Consider using `check_flow_permission()` helper from decorator utilities
   - **File**: flows.py
   - **Expected Outcome**: Code reuse and pattern consistency

3. **ADD Permission Inheritance Tests** (Priority: MAJOR)
   - **Action**: Add tests for Project-to-Flow permission inheritance
   - **File**: tests/unit/api/v1/test_flows_rbac.py
   - **Expected Outcome**: Inheritance behavior validated

4. **VERIFY SQL Performance** (Priority: MAJOR)
   - **Action**: Test SQL query performance with role assignment joins
   - **File**: flows.py
   - **Expected Outcome**: Query performance acceptable (< 100ms for typical dataset)

### Future Improvements (Nice to Have)

1. **ADD Query Optimization** (Priority: MINOR)
   - **Action**: Use SQLAlchemy eager loading (selectinload) for role assignments
   - **File**: flows.py
   - **Expected Outcome**: Improved query performance

2. **ADD Caching** (Priority: MINOR)
   - **Action**: Consider caching role assignments for performance
   - **File**: flows.py or RBACService
   - **Expected Outcome**: Reduced database load

---

## Code Examples

### Example 1: Current Implementation (INCORRECT)

**Current Implementation** (flows.py:226-238):
```python
# ❌ INCORRECT IMPLEMENTATION
# Check RBAC permission for Flow:Read at Global scope
has_permission = await rbac_service.can_access(
    user_id=current_user.id,
    permission_name="Flow:Read",  # ❌ WRONG: Combined format
    scope_type="Global",          # ❌ WRONG: Should be "Flow"
    scope_id=None,                # ❌ WRONG: Should be per-flow
    db=session,
)
if not has_permission:
    raise HTTPException(
        status_code=403,
        detail="Missing required permission: Flow:Read on Global scope",
    )  # ❌ WRONG: Blocks all access instead of filtering
```

**Issues**:
1. Permission name format is wrong ("Flow:Read" instead of "Read")
2. Scope type is wrong (Global instead of Flow)
3. Blocks all access with 403 instead of filtering flows
4. Does not check permissions per-flow

### Example 2: Recommended Fix - Correct Per-Flow Filtering

**Recommended Fix** (flows.py - new implementation):
```python
# ✅ CORRECT IMPLEMENTATION
# Step 1: Get candidate flows with SQL joins
if current_user.is_superuser or await rbac._has_global_admin_role(current_user.id, session):
    # Admin bypass: get all flows
    stmt = select(Flow)
else:
    # Regular user: get flows with role assignments
    stmt = (
        select(Flow)
        .distinct()
        .outerjoin(
            UserRoleAssignment,
            and_(
                UserRoleAssignment.scope_id == Flow.id,
                UserRoleAssignment.scope_type == "Flow",
                UserRoleAssignment.user_id == current_user.id
            )
        )
        .outerjoin(Folder, Flow.folder_id == Folder.id)
        .outerjoin(
            UserRoleAssignment.alias("project_assignment"),
            and_(
                UserRoleAssignment.scope_id == Folder.id,
                UserRoleAssignment.scope_type == "Project",
                UserRoleAssignment.user_id == current_user.id
            ),
            isouter=True
        )
        .where(
            or_(
                UserRoleAssignment.id.isnot(None),
                UserRoleAssignment.alias("project_assignment").id.isnot(None)
            )
        )
    )

# Execute query
flows = (await session.exec(stmt)).all()

# Step 2: Filter by Read permission
accessible_flows = []
for flow in flows:
    # ✅ CORRECT: permission_name="Read", scope_type="Flow", scope_id=flow.id
    if await rbac.can_access(
        user_id=current_user.id,
        permission_name="Read",      # ✅ Just "Read"
        scope_type="Flow",           # ✅ Flow scope
        scope_id=flow.id,            # ✅ Specific flow ID
        db=session,
    ):
        accessible_flows.append(flow)

return compress_response(accessible_flows)
```

**Key Improvements**:
1. ✅ Correct permission format: separate `name` and `scope`
2. ✅ Checks per-flow permissions in loop
3. ✅ Implements SQL joins for role assignments
4. ✅ Handles permission inheritance
5. ✅ Returns filtered flows instead of blocking access

### Example 3: Alternative Using Decorator Helper

**Alternative Implementation Using Helper**:
```python
from langbuilder.services.rbac import check_flow_permission

# ... SQL joins to get candidate flows ...

# Filter by Read permission using helper
accessible_flows = []
for flow in flows:
    # ✅ Use helper from decorator infrastructure
    if await check_flow_permission(
        flow_id=flow.id,
        permission_name="Read",
        current_user=current_user,
        db=session,
        rbac=rbac,
    ):
        accessible_flows.append(flow)

return compress_response(accessible_flows)
```

**Benefits**:
- ✅ Cleaner code using established helper
- ✅ Consistent with decorator infrastructure
- ✅ Same functionality as direct `can_access()` call

---

## Conclusion

**Overall Status**: **FAIL - CRITICAL IMPLEMENTATION ERRORS**

**Rationale**: The implementation of Task 2.2 contains critical errors that prevent it from functioning as specified in the implementation plan:

1. **Wrong Permission Format**: Uses "Flow:Read" instead of "Read" with separate scope
2. **Wrong Scope**: Checks Global scope instead of per-flow filtering
3. **Wrong Behavior**: Blocks all access with 403 instead of filtering flows
4. **Missing Core Logic**: Does not implement SQL joins for role assignment filtering
5. **No Tests**: Zero test coverage for endpoint RBAC behavior

These errors indicate a fundamental misunderstanding of:
- The RBAC permission model (separate name/scope fields)
- The RBACService.can_access() API signature
- The task requirements (filter flows, not block access)
- The implementation plan specifications (SQL joins, per-flow checks)

**Resolution Rate**: 0% (0/5 critical issues fixed)

**Quality Assessment**: The implementation deviates fundamentally from the implementation plan and will not work correctly. Complete reimplementation is required.

**Ready to Proceed**: **NO** - Must revert and reimplement

**Next Actions**:
1. **IMMEDIATE**: Revert current implementation
2. **CRITICAL**: Reimplement following the implementation plan and recommendations in this audit
3. **CRITICAL**: Create comprehensive test suite (minimum 10 tests)
4. **REQUIRED**: Code review before merge
5. **REQUIRED**: Re-audit after fixes

### Critical Issues Summary

| Issue | Severity | Status | Blocking |
|-------|----------|--------|----------|
| Wrong permission name format | CRITICAL | ❌ Not Fixed | YES |
| Wrong scope type (Global vs Flow) | CRITICAL | ❌ Not Fixed | YES |
| Missing flow filtering logic | CRITICAL | ❌ Not Fixed | YES |
| Blocks access instead of filtering | CRITICAL | ❌ Not Fixed | YES |
| No endpoint RBAC tests | CRITICAL | ❌ Not Fixed | YES |

**All 5 critical issues are blocking production deployment.**

### Recommended Implementation Timeline

1. **Day 1**: Revert current implementation, study implementation plan Section 2.2
2. **Day 2-3**: Implement SQL joins and per-flow filtering logic
3. **Day 3-4**: Create comprehensive test suite (10+ tests)
4. **Day 4**: Code review and testing
5. **Day 5**: Re-audit and approval

**Estimated Effort**: 5 days (complete reimplementation)

### Learning Points for Future Tasks

1. **Read Implementation Plan Carefully**: The plan provided detailed SQL join examples and permission checking logic that were not followed
2. **Understand Service APIs**: Study `RBACService.can_access()` signature before using it
3. **Use Established Patterns**: Leverage decorator infrastructure instead of reinventing
4. **Test First**: Write tests to validate understanding before implementing
5. **Incremental Implementation**: Implement and test SQL joins first, then add permission filtering

The RBAC system design is sound (Task 2.1 and decorator infrastructure are well-implemented), but this endpoint implementation misapplied the patterns and APIs. With careful attention to the implementation plan and proper testing, the endpoint can be successfully implemented in the next iteration.

---

## Appendix: Implementation Plan Reference

### Implementation Plan Task 2.2 Specifications (Lines 885-1026)

**Task Description**:
> "Integrate RBAC checks into the `GET /api/v1/flows` endpoint to filter flows based on user's Read permission."

**Required Implementation** (lines 918-976):
```python
@router.get("/")
async def read_flows(
    current_user: CurrentActiveUser,
    db: DbSession,
    rbac: RBACServiceDep,
    skip: int = 0,
    limit: int = 100
):
    # 1. Get all flows (or user's flows if not superuser/admin)
    if current_user.is_superuser or await rbac._has_global_admin_role(current_user.id, db):
        stmt = select(Flow).offset(skip).limit(limit)
    else:
        # Get flows where user has explicit role assignment OR inherited via Project
        stmt = (
            select(Flow)
            .outerjoin(
                UserRoleAssignment,
                and_(
                    UserRoleAssignment.scope_id == Flow.id,
                    UserRoleAssignment.scope_type == "Flow",
                    UserRoleAssignment.user_id == current_user.id
                )
            )
            .outerjoin(
                Folder,
                Flow.folder_id == Folder.id
            )
            .outerjoin(
                UserRoleAssignment,
                and_(
                    UserRoleAssignment.scope_id == Folder.id,
                    UserRoleAssignment.scope_type == "Project",
                    UserRoleAssignment.user_id == current_user.id
                ),
                isouter=True
            )
            .where(
                or_(
                    UserRoleAssignment.id.isnot(None),  # Has explicit Flow assignment
                    UserRoleAssignment.id.isnot(None)   # Has inherited Project assignment
                )
            )
            .offset(skip)
            .limit(limit)
        )

    result = await db.execute(stmt)
    flows = result.scalars().all()

    # 2. Filter flows by Read permission
    accessible_flows = []
    for flow in flows:
        if await rbac.can_access(current_user.id, "Read", "Flow", flow.id, db):
            accessible_flows.append(flow)

    return accessible_flows
```

**Key Specifications**:
1. Use SQL joins with UserRoleAssignment
2. Handle both explicit Flow and inherited Project assignments
3. Filter flows in per-flow loop using `rbac.can_access()`
4. Use correct permission format: `permission_name="Read"`, `scope_type="Flow"`, `scope_id=flow.id`
5. Return filtered list of accessible flows
6. Support superuser and Global Admin bypass

**Success Criteria** (Implied):
- ✅ Returns only flows where user has Read permission
- ✅ Supports permission inheritance from Project to Flow
- ✅ Maintains superuser bypass behavior
- ✅ Efficient query with appropriate joins
- ✅ No N+1 query issues
