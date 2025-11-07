```
what are the new alebic script files in recent check in 
```

Prompt
```
Please do following to the alembic scripts\
1. For the 3 newly added script, its upgrade() should be idempotent when creating table, adding index, foreign keys\
2. Rollback the changes existing alembic scripts as they were working before and should not be changed 
```
Response
```
Summary

  1. Made 3 RBAC Migration Scripts Idempotent ✓

  a20a7041e437_add_rbac_tables.py:
  - Added inspector to check for existing tables before creating them
  - Added checks for existing indexes before creating them
  - Now safe to run multiple times without errors

  b30c7152f8a9_update_rbac_models_to_use_enums_and_add_is_global.py:
  - Added checks for table existence
  - Added checks for column existence before adding new columns
  - Added checks for index existence before dropping/creating indexes
  - Added checks for constraint existence before creating them
  - Data migration now skips if already migrated (checks if action/scope are NULL)
  - Now safe to run multiple times without errors

  b1c2d3e4f5a6_migrate_existing_users_to_rbac.py:
  - Already idempotent (checks for existing records before creating)

  2. Rolled Back Changes to Existing Alembic Scripts ✓

  Restored 47 existing alembic migration files to their pre-RBAC state (from commit 3c3ae2627):
  - Reverted import changes: collections.abc.Sequence → typing.Sequence, Union
  - Reverted type annotations: str | None → Union[str, None]
  - Restored removed pass statements
  - Restored any removed imports like Inspector

  Current Status

  The alembic directory now has:
  - 3 new RBAC migration files (idempotent and ready to use)
  - 47 restored existing migration files (back to their working state)
  - 2 modified files in working directory (the idempotent RBAC scripts)

  You can now stage and commit the idempotent RBAC migrations and the restored existing scripts.

  ```


Prompt

```
Please do following as we have not made any release to require a separate upgrade script on newly created tables.
1. adjust a20a7041e437_add_rbac_tables.py migration script based on the latest data models, make sure its upgrade() still idempotent
2. remove b30c7152f8a9_update_rbac_models_to_use_enums_and_add_is_global.py migration script and adjust the down_revision version chain properly
```

Prompt
```
For the new migration scripts, Sequence should be imported from the same package as old script
```

Prompt
```
Please tell me the script that runs all the new unit test files in the most recent check in
```

Shell command to run all new tests
```
uv run pytest src/backend/tests/unit/test_rbac*.py src/backend/tests/unit/test_user_role_assignment.py src/backend/tests/unit/test_migrate_rbac_data.py src/backend/tests/unit/alembic/test_rbac*.py -v
Only 3 of 100+ test fails
         - src/backend/tests/unit/test_rbac_models.py:887 TestModelRelationships.test_cascade_behavior_on_role_deletion
         - src/backend/tests/unit/test_rbac_models.py:918 TestModelRelationships.test_cascade_behavior_on_permission_deletion
         - src/backend/tests/unit/test_user_role_assignment.py:601 TestUserRoleAssignmentModel.test_user_role_assignment_created_at_timestamp
```

Prompt, Note: the cascading fix broke the server and setup again. So leave to later.
```
Please fix below failed backend unit tests. Try to fix and rerun test to confirm the fix for each test before move onto fix the next test.
         - src/backend/tests/unit/test_rbac_models.py:887 TestModelRelationships.test_cascade_behavior_on_role_deletion
         - src/backend/tests/unit/test_rbac_models.py:918 TestModelRelationships.test_cascade_behavior_on_permission_deletion
         - src/backend/tests/unit/test_user_role_assignment.py:601 TestUserRoleAssignmentModel.test_user_role_assignment_created_at_timestamp

```

Shell command to run individual failed test
```
uv run pytest src/backend/tests/unit/test_rbac_models.py::TestModelRelationships::test_cascade_behavior_on_role_deletion -xvs
uv run pytest src/backend/tests/unit/test_rbac_models.py::TestModelRelationships::test_cascade_behavior_on_permission_deletion -xvs
uv run pytest src/backend/tests/unit/test_user_role_assignment.py::TestUserRoleAssignmentModel::test_user_role_assignment_created_at_timestamp -xvs
```