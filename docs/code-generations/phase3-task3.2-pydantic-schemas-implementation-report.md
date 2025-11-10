# Task Implementation: Phase 3, Task 3.2 - Create Pydantic Schemas for RBAC API

## Task Information

**Phase:** Phase 3 - API Layer Implementation
**Task ID:** Task 3.2
**Task Name:** Create Pydantic Schemas for RBAC API
**Task Scope:** Define request and response schemas for RBAC API endpoints with denormalized fields

## Implementation Summary

### Files Created

1. `/home/nick/LangBuilder/src/backend/base/langbuilder/services/database/models/user_role_assignment/schema.py`
   - Comprehensive Pydantic schemas for RBAC API endpoints
   - Includes denormalized fields (role_name, scope_name) for frontend convenience
   - Field validation for scope_id requirements based on scope_type
   - Schemas for batch permission checking

2. `/home/nick/LangBuilder/src/backend/tests/unit/services/database/models/user_role_assignment/test_schema.py`
   - Comprehensive unit tests for all schema classes
   - 37 test cases covering validation rules, edge cases, and error conditions
   - Tests for all CRUD schemas and permission check schemas

3. `/home/nick/LangBuilder/src/backend/tests/unit/services/database/models/user_role_assignment/__init__.py`
   - Package initialization file for test directory

### Files Modified

1. `/home/nick/LangBuilder/src/backend/base/langbuilder/services/database/models/user_role_assignment/__init__.py`
   - Added exports for new schema classes
   - Maintains backward compatibility with existing model classes
   - Alphabetically sorted exports per project conventions

### Key Components Implemented

#### 1. UserRoleAssignmentCreate Schema
- **Purpose:** Request schema for creating role assignments
- **Key Features:**
  - Uses `role_name` instead of `role_id` for API convenience
  - Field validation ensures `scope_id` is required for Flow/Project scopes
  - Field validation ensures `scope_id` is null for Global scope
  - Validates `scope_type` is one of: Flow, Project, Global
  - Trims whitespace from `role_name`
  - Rejects empty or whitespace-only `role_name`

#### 2. UserRoleAssignmentUpdate Schema
- **Purpose:** Request schema for updating role assignments
- **Key Features:**
  - Only `role_name` can be updated (immutable user_id, scope)
  - Same validation as Create schema for role_name

#### 3. UserRoleAssignmentRead Schema
- **Purpose:** Response schema with denormalized fields
- **Key Features:**
  - Includes `role_name` (denormalized from role relationship)
  - Includes `scope_name` (denormalized from Flow/Project name)
  - Eliminates need for additional API calls to resolve names
  - `from_attributes=True` for ORM model conversion

#### 4. RoleRead Schema
- **Purpose:** Response schema for role information
- **Key Features:**
  - Simple role representation
  - Includes `is_system_role` flag
  - `from_attributes=True` for ORM model conversion

#### 5. Permission Check Schemas
- **Purpose:** Batch permission checking for frontend
- **Key Features:**
  - `PermissionCheck`: Single permission check request
  - `PermissionCheckRequest`: Batch request (max 100 checks)
  - `PermissionCheckResult`: Single permission check result
  - `PermissionCheckResponse`: Batch response
  - Validation ensures checks list is not empty
  - Constant `MAX_PERMISSION_CHECKS = 100` for maintainability

### Tech Stack Used

- **Pydantic v2:** BaseModel with modern syntax
- **Python 3.10+:** Union type syntax (X | None)
- **Field Validators:** @field_validator decorator with mode="after"
- **Type Hints:** Full type annotations throughout
- **UUID:** Standard library uuid4 for identifiers
- **datetime:** Standard library for timestamp fields

### Validation Rules Implemented

1. **scope_id Validation:**
   - Required when scope_type is "Flow" or "Project"
   - Must be None when scope_type is "Global"
   - Custom validator with cross-field validation

2. **scope_type Validation:**
   - Must be one of: Flow, Project, Global
   - Raises ValueError with clear message for invalid values

3. **role_name Validation:**
   - Cannot be empty or whitespace-only
   - Automatically trimmed of leading/trailing whitespace
   - Applied to both Create and Update schemas

4. **checks Validation (Permission Requests):**
   - List cannot be empty
   - Maximum 100 checks per batch request
   - Enforced via MAX_PERMISSION_CHECKS constant

## Test Coverage Summary

### Test Files Created
- `/home/nick/LangBuilder/src/backend/tests/unit/services/database/models/user_role_assignment/test_schema.py`

### Test Statistics
- **Total Test Cases:** 37
- **Test Classes:** 8
- **All Tests Passing:** Yes (37/37)
- **Test Execution Time:** 0.30 seconds

### Test Coverage by Schema

#### TestUserRoleAssignmentCreate (12 tests)
- Valid Flow/Project/Global scope creation
- scope_id validation (required for Flow/Project, null for Global)
- scope_type validation (allowed values)
- role_name validation (empty, whitespace, trimming)
- Missing required fields

#### TestUserRoleAssignmentUpdate (5 tests)
- Valid role_name update
- Empty/whitespace role_name rejection
- role_name trimming
- Missing required field

#### TestUserRoleAssignmentRead (3 tests)
- Complete assignment with all fields
- Global scope assignment (null scope_id/scope_name)
- ORM model conversion (from_attributes=True)

#### TestRoleRead (3 tests)
- System role
- Custom role
- ORM model conversion

#### TestPermissionCheck (3 tests)
- With resource_id
- Without resource_id
- Missing required fields

#### TestPermissionCheckRequest (5 tests)
- Single check
- Multiple checks
- Empty checks list (rejected)
- Too many checks (>100, rejected)
- Exactly MAX_PERMISSION_CHECKS (allowed)

#### TestPermissionCheckResult (3 tests)
- Allowed permission
- Denied permission
- Without resource_id

#### TestPermissionCheckResponse (3 tests)
- Single result
- Multiple results
- Empty results

## Success Criteria Validation

### All schemas defined with correct field types
✅ **Met**
- All schemas use appropriate types (UUID, str, bool, datetime, list)
- Optional fields use Union syntax (X | None)
- Field descriptions provided for documentation

### Schemas use Pydantic v2 syntax
✅ **Met**
- Uses BaseModel from pydantic
- Uses Field() for field configuration
- Uses @field_validator decorator
- Uses model_config dict instead of nested Config class (where applicable)
- Uses from_attributes=True in Config

### from_attributes=True for ORM models
✅ **Met**
- UserRoleAssignmentRead has Config with from_attributes=True
- RoleRead has Config with from_attributes=True
- Enables automatic conversion from SQLModel ORM objects

### Schemas include validation
✅ **Met**
- scope_id validation based on scope_type (cross-field validation)
- scope_type validation (allowed values)
- role_name validation (non-empty, trimming)
- checks validation (non-empty, max 100 items)
- All validators include clear error messages

## Integration Validation

### Integrates with existing code
✅ **Yes**
- Schemas complement existing model.py classes
- Maintains backward compatibility
- Follows existing patterns from other models (e.g., role/model.py)

### Follows existing patterns
✅ **Yes**
- Similar structure to role/model.py schemas
- Follows naming conventions (Create, Read, Update suffixes)
- Uses same validation patterns as existing code
- Docstrings follow project style

### Uses correct tech stack
✅ **Yes**
- Pydantic v2 as specified in architecture
- SQLModel compatibility maintained
- Python 3.10+ type hints
- FastAPI-compatible schemas

### Placed in correct locations
✅ **Yes**
- Schema file: `services/database/models/user_role_assignment/schema.py`
- Test file: `tests/unit/services/database/models/user_role_assignment/test_schema.py`
- Follows project directory structure conventions

## Code Quality

### Style and Formatting
- All code formatted with ruff
- Passes linting checks (no errors in task files)
- Docstrings for all classes and methods
- Clear, descriptive variable names

### Documentation
- Comprehensive module-level docstring
- Class-level docstrings explaining purpose
- Field-level descriptions via Field(description=...)
- Inline comments for complex validation logic

### Error Handling
- All validators raise clear ValueError messages
- Error messages stored in variables (not inline)
- Follows TRY003 best practice

### Maintainability
- Constants for magic numbers (MAX_PERMISSION_CHECKS)
- Reusable validation patterns
- Well-organized test structure
- Easy to extend with new schemas

## Integration with Future Tasks

This implementation provides the foundation for:

### Task 3.3: Batch Permission Check Endpoint
- PermissionCheckRequest/Response schemas ready to use
- Validation already implemented
- Clear contract for frontend-backend communication

### Task 3.4: RBAC API Endpoints
- UserRoleAssignmentCreate/Update/Read schemas ready
- RoleRead schema ready
- Validation ensures data integrity

### Frontend Integration
- Denormalized fields (role_name, scope_name) eliminate extra API calls
- Clear error messages for validation failures
- Consistent response structure

## Known Issues or Follow-ups

None. Implementation is complete and all tests pass.

## Assumptions Made

1. **Denormalized Fields:** `role_name` and `scope_name` will be populated by service layer when converting from ORM models
2. **Scope Names:** `scope_name` is None for Global scope, populated from Flow.name or Folder.name for scoped assignments
3. **Permission Checks:** Maximum 100 checks per batch is sufficient for frontend needs
4. **Validation:** Field validation is sufficient; business logic validation handled in service/repository layer

## Performance Considerations

1. **Pydantic v2:** Uses fast Rust core for validation (significant performance improvement)
2. **Batch Permission Checks:** Limit of 100 prevents excessive processing time
3. **Denormalization:** Trades storage for query performance (eliminates JOIN queries from frontend)
4. **Field Validators:** Run only on relevant fields, not entire model

## Security Considerations

1. **Input Validation:** All user inputs validated before reaching database
2. **Scope_id Validation:** Prevents mismatched scope_type/scope_id combinations
3. **Role Name Trimming:** Prevents whitespace-based bypass attempts
4. **Batch Limit:** MAX_PERMISSION_CHECKS prevents DoS via excessive requests

## Conclusion

Task 3.2 has been successfully implemented with comprehensive schemas, validation, and testing. All success criteria are met, and the implementation follows LangBuilder conventions and best practices. The schemas provide a solid foundation for the RBAC API layer with frontend-friendly denormalized fields and robust validation.

**Implementation Status:** ✅ Complete
**Test Status:** ✅ All tests passing (37/37)
**Code Quality:** ✅ Formatted and linted
**Documentation:** ✅ Complete
**Ready for Next Task:** ✅ Yes
