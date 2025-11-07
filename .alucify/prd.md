# **Product Requirements Document (PRD)**

## **Project: MVP Feature Set: Role-Based Access Control (RBAC) for LangBuilder**

## **1\. Introduction and Goals**

### **1.1. Problem Statement**

LangBuilder currently lacks a **customizable, fine-grained access control** mechanism, which is critical for enforcing security policies and managing enterprise teams. This gap exposes customer data and prevents organizations from structuring access appropriately across their work.

### **1.2. Project Goal (The "Why")**

The primary goal is to introduce a customizable, fine-grained **Role-Based Access Control (RBAC)** system. This system must enforce secure, contextual permissions across all major elements of LangBuilder, ensuring:

* Secure, fine-grained permission enforcement.
* Customizable roles to suit different team structures (via predefined defaults).
* Management available exclusively through a Web-based administrative UI by the **Admin** role.

---

## **2\. Scope and Dependencies**

### **2.1. In-Scope for MVP (High-Level Summary)**

The MVP will establish the core RBAC data model, assignment logic, and enforcement engine using four predefined default roles and standard CRUD permissions across **Flow** and **Project** entities. All assignment management is centralized under the **Admin** role in a dedicated UI.

### **2.2. Out-of-Scope (Non-Goals)**

The following items are explicitly **out-of-scope** for the MVP:

* Custom Roles or permissions beyond CRUD (e.g., `Can_export_flow`, `Can_deploy_environment`).
* Extended Permission Scopes (Component, Environment, Workspace, API/Token).
* SSO (Single Sign-On), User Groups, Service Accounts, SCIM, API/IaC based access management.
* User-triggered sharing of flows.

### **2.3. Dependencies & Constraints**

The RBAC implementation **must** integrate with and rely on the following existing systems:

* Existing authentication system
* A persistent metadata store for role and permission configuration

---

## **3\. Detailed Requirements (Epics & Stories in Gherkin Format)**

### **Epic 1: Core RBAC Data Model and Default Assignment**

**Goal:** Establish the persistent data model for roles, permissions, scopes, and assignments, including all initial assignment rules and immutability logic.

| Story \# | Short Description | Gherkin Acceptance Criteria |
| :---- | :---- | :---- |
| **1.1** | **Define & Persist Core Permissions (CRUD) and Scopes** | **Scenario: Defining the Core RBAC Entities**  **Given** the persistence layer is available  **When** the system is initialized  **Then** the four base permissions (**Create, Read, Update, Delete**) should be defined in the metadata store  **And** the two entity scopes (**Flow, Project**) should be defined in the metadata store  **And** the data model should establish the relationship between permissions and scopes |
| **1.2** | **Define & Persist Default Roles and Mappings** | **Scenario: Mapping Default Roles and Extended Permissions**  **Given** the four base permissions are defined  **When** the default roles are persisted  **Then** the **Owner** role should have full **CRUD** access to its scope entity  **And** the **Admin** role should have full **CRUD** access across all scopes/entities  **And** the **Editor** role should have **Create, Read, Update** access (but **not Delete**)  **And** the **Viewer** role should have only **Read/View** access  **And** the **Read/View** permission should enable Flow **execution, saving, exporting, and downloading**  **And** the **Update/Edit** permission should enable Flow/Project **import** |
| **1.3** | **Implement Core Role Assignment Logic** | **Scenario: Admin Assigns or Modifies a Role Assignment** **Given** the internal assignment API (`assignRole` / `removeRole`) is exposed  **When** an **Admin** calls the API to **create a new role assignment** (User, Role, Scope)  **Then** the assignment should be successfully persisted  **When** an **Admin** calls the API to **modify or delete** an existing assignment  **Then** the Admin should be authorized to perform the action  **And** the updated assignment should be successfully persisted or removed **But** the Admin should be **prevented** from modifying the Starter Project Owner assignment (as per 1.4) |
| **1.4** | **Default Project Owner Immutability Check** | **Scenario: Preventing changes to the Starter Project Owner Role**  **Given** a user has the **Owner** role assigned to their default/Starter Project (which is pre-existing)  **When** an **Admin** attempts to modify, delete, or transfer this specific Owner role assignment  **Then** the attempt should be blocked at the application logic layer **And** the user should maintain the **Owner** role on their Starter Project |
| **1.5** | **Global Project Creation & New Entity Owner Mutability** | **Scenario: Project Creation and New Entity Owner Assignment**  **Given** any authenticated user is logged in  **When** the user attempts to create a new Project  **Then** the user should have access to the **Create Project** function **When** a user successfully creates a new Project or Flow  **Then** the creating user should be automatically assigned the **Owner** role for that new entity  **And** an **Admin** should be able to modify this new entity's Owner role assignment  |
| **1.6** | **Define Project to Flow Role Extension Rule** | **Scenario: Establishing Project Role Inheritance Logic**  **Given** a user has a specific(or default) role assigned to a Project **When** the user attempts to access a Flow contained within that Project  **Then** the user should automatically inherit the permissions of the assigned Project role for that Flow But if an explicit, different role is assigned to the user for that specific Flow scope, the Flow-specific role should override the inherited role (per 2.1 logic) |

###

### **Epic 2: RBAC Enforcement Engine & Runtime Checks**

**Goal:** Implement the core application logic to validate user permissions against the RBAC data model at every critical user action.

| Story \# | Short Description | Gherkin Acceptance Criteria |
| :---- | :---- | :---- |
| **2.1** | **Core `CanAccess` Authorization Service** | **Scenario: Evaluating User Access**  **Given** the `CanAccess` method is called with a user, permission, and scope  **When** the `user_id` has the **Admin** role  **Then** the method should immediately return **true**  **When** the user is non-Admin accessing a Flow  **Then** the service should first check for a direct **Flow-specific** role  **And** if no Flow-specific role exists, the service should check the inherited role from the containing **Project**  **When** the user is non-Admin accessing a Project  **Then** the service should check the **Project-specific** role |
| **2.2** | **Enforce Read/View Permission & List Visibility** | **Scenario: UI Filtering and Read Access Enforcement**  **Given** a user loads the Project or Flow list view  **When** the user lacks the **Read/View** permission for an entity **Then** that entity should **not** be displayed in the list view  **When** a user attempts to **view the editor, execute, save/export, or download** a Flow/Project  **Then** the `AuthService` should confirm **Read/View** permission **And** the action should be blocked if permission is denied |
| **2.3** | **Enforce Create Permission on Projects & Flows** | **Scenario: Blocking Unauthorized Flow Creation**  **Given** a non-Admin user is logged in  **When** the user views the Project interface  **Then** the UI elements (e.g., buttons, options) for **creating a new Flow** must be hidden or disabled if the user lacks the **Create** permission on that Project scope  **And** if the user attempts to bypass the UI (e.g., API call), the `AuthService` should block the creation |
| **2.4** | **Enforce Update/Edit Permission for Projects & Flows** | **Scenario: Preventing Edits for Unauthorized Users**  **Given** a user loads the editor for a Project or Flow  **When** the user lacks the **Update/Edit** permission  **Then** the editor should load in a **read-only state** **And** the user should be prevented from making any changes/edits  **And** the check must also occur before allowing **import** functionality |
| **2.5** | **Enforce Delete Permission for Projects & Flows** | **Scenario: Blocking Unauthorized Deletion**  **Given** a user views the interface for a Project or Flow  **When** the user does not have the **Delete** permission  **Then** the UI elements (e.g., buttons, options) for **deleting** the entity must be hidden or disabled  **And** if the user attempts to bypass the UI, the `AuthService` should block the action **And** the action should only be permitted if the user is an **Admin** or has the **Owner** role for the scope entity |

###

### **Epic 3: Web-based Admin Management Interface**

**Goal:** Deliver a **centralized, secure, web-based administrative UI** to enable the **Admin** role to efficiently manage all role assignments.

| Story \# | Short Description | Gherkin Acceptance Criteria |
| :---- | :---- | :---- |
| **3.1** | **RBAC Management Section in the Admin Page** | **Scenario: Centralized RBAC Management Section**   **Given** a Admin Page exists which contains the User Management section today, a new RBAC Management section gets added to the Admin Page, and Admin Page has two two tabs now with the User Management Section(default one to open when user accesses the Admin Page) and the RBAC Management section and a deep link exists for the RBAC management section within the Admin Page **When** an **Admin** user accesses the Admin Page **Then** she should be able to access the **RBAC Management section** **When** a non-Admin user accesses the Admin Page **Then** she should NOT be able to access the **RBAC Management section When** a Admin user tries to access the deeplink for  the RBAC management section **Then** she should be able to access the **RBAC Management section** **When** a non-Admin user tries to access the deeplink for  the RBAC management section **Then** the system should display an **Access Denied** message  |
| **3.2** | **Assignment Creation Workflow (New Roles)** | **Scenario: Assigning a New Role to a User**  **Given** an **Admin** is in the RBAC management section  **When** the Admin initiates the new assignment workflow  **Then** the workflow should guide the Admin through sequential steps: **Select User** → **Select Scope** → **Select Role** → **Confirm** **And** the only assignable role options should be the four default roles or the global Admin role  **When** the Admin confirms the assignment  **Then** the Core Role Assignment Logic (Epic 1.3) should be successfully called |
| **3.3** | **Assignment List View and Filtering** | **Scenario: Viewing and Filtering All Assignments**  **Given** an **Admin** is in the RBAC management section  **When** the master assignment list view is displayed  **Then** the list should show all active `User: Scope: Role` assignments  **And** the list should be filterable by **User**, **Role**, and **Scope Entity** **And** a clear mechanism should be available to **directly delete** any assignment from the list view |
| **3.4** | **Assignment Editing and Removal** | **Scenario: Modifying an Existing Role**  **Given** an **Admin** selects an assignment from the master list to edit  **When** the Admin changes the Role for that specific scope  **Then** the system should call the Core Role Assignment Logic (Epic 1.3) to update the assignment |
| **3.5** | **Flow Role Inheritance Display Rule** | **Scenario: Displaying Flow Role Information**  **Given** a user has an inherited role from a Project  **When** the Admin views the assignment list  **Then** the list **should not** display a specific assignment entry for the inherited Flow role  **When** the Admin views the assignment interface  **Then** a clear message should be displayed: *"Project-level assignments are inherited by contained Flows and can be overridden by explicit Flow-specific roles."* |

###

### **Epic 5: Non-Functional Requirements**

**Goal:** Define measurable criteria for performance, reliability, and responsiveness, and ensure the system supports required data access rights for compliance purposes (GDPR/CCPA).

| Story \# | Short Description | Gherkin Acceptance Criteria |
| :---- | :---- | :---- |
| **5.1** | **Role Assignment and Enforcement Latency** | **Scenario:** Latency for CanAccess Check  **Given** the authorization service (AuthService) is running at 50% average load  **When** the AuthService.CanAccess method is called for any user/permission/scope combination  **Then** the check must return a response in **less than 50 milliseconds (p95)**. **Scenario:** Latency for Assignment Creation  **Given** an **Admin** executes an assignment update/create via the API  **When** the Core Role Assignment Logic (Epic 1.3) is executed  **Then** the API response time should be **less than 200 milliseconds (p95)**. |
| **5.2** | **System Uptime and Availability** | **Scenario:** System Availability Requirement  **Given** all core services (Auth, RBAC Data Store, AuthService) are monitored  **When** measuring system availability over a calendar month  **Then** the overall platform uptime must meet **99.9% availability** (excluding scheduled maintenance). |
| **5.3** | **Readiness Time (Initial Load)** | **Scenario:** Editor Load Time with RBAC Check  **Given** a user loads the Project/Flow editor page  **When** the page requires the initial bulk permission check (e.g., hiding create/delete buttons)  **Then** the entire page load, including the RBAC checks, must be completed in **less than 2.5 seconds (p95)**. |

