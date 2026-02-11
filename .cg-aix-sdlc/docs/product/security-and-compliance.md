# Security and Compliance - LangBuilder v1.6.5

> Generated: 2026-02-09 | LangBuilder v1.6.5

## Overview

LangBuilder implements a defense-in-depth security architecture spanning authentication, authorization, data protection, and network-level controls. The platform supports multiple authentication methods to accommodate deployments ranging from single-developer workstations to enterprise environments with corporate identity providers.

This document describes the security features from a product perspective: what protections exist, how they benefit users, and where LangBuilder stands relative to common compliance frameworks.

---

## Table of Contents

- [Authentication Methods](#authentication-methods)
- [Authorization Model](#authorization-model)
- [Data Protection](#data-protection)
- [Security Controls](#security-controls)
- [Compliance Readiness](#compliance-readiness)
- [Customer-Facing Security Features](#customer-facing-security-features)

---

## Authentication Methods

LangBuilder supports five authentication mechanisms, each serving a different deployment scenario. All methods ultimately produce a JWT access token that the platform uses for subsequent request authorization.

### 1. JWT Token Authentication (Primary)

The default authentication method for interactive browser sessions `[CODE]`.

| Property | Value |
|----------|-------|
| **Signing Algorithm** | HS256 (HMAC-SHA256) `[CODE]` |
| **Access Token Lifetime** | 1 hour `[CODE]` |
| **Refresh Token Lifetime** | 7 days `[CODE]` |
| **Password Hashing** | bcrypt with adaptive cost factor `[CODE]` |
| **Token Transport** | `Authorization: Bearer <token>` header `[CODE]` |

**Flow:**

1. User submits email and password to `POST /api/v1/login` `[CODE]`.
2. Server verifies password against bcrypt hash stored in the database `[CODE]`.
3. On success, server returns a JWT access token (1 hour) and a refresh token (7 days) `[CODE]`.
4. Client includes the access token in the `Authorization` header for all subsequent requests `[CODE]`.
5. When the access token expires, the client calls `POST /api/v1/refresh` with the refresh token to obtain a new access token `[CODE]`.

**User benefit:** Standard, stateless authentication that works with any HTTP client. Token expiration limits the blast radius of a leaked token.

### 2. OAuth2 / OIDC (Enterprise SSO)

External identity provider authentication for enterprise environments `[CODE]`.

| Provider | Protocol | Library | Use Case |
|----------|----------|---------|----------|
| **Google** | OAuth2 / OIDC | authlib `[CODE]` | Google Workspace organizations |
| **Microsoft** | OAuth2 / OIDC | authlib `[CODE]` | Microsoft 365 / Azure AD tenants |
| **GitHub** | OAuth2 | authlib `[CODE]` | Developer teams using GitHub identity |

**Flow (Authorization Code Grant):**

1. User selects an OAuth provider on the login page `[CODE]`.
2. Backend redirects to the provider's authorization endpoint `[CODE]`.
3. User authenticates with the external provider `[CODE]`.
4. Provider redirects back with an authorization code `[CODE]`.
5. Backend exchanges the code for an access token and ID token `[CODE]`.
6. User identity is extracted from the ID token (OIDC) or userinfo endpoint `[CODE]`.
7. A local user record is created or matched, and a LangBuilder JWT is issued `[CODE]`.

**User benefit:** Users authenticate with their existing corporate credentials. No separate LangBuilder password required. Centralized identity management through the organization's IdP.

### 3. API Key Authentication (Programmatic Access)

For automation, CI/CD pipelines, and external system integrations `[CODE]`.

| Property | Value |
|----------|-------|
| **Format** | `sk-{uuid}` (e.g., `sk-550e8400-e29b-41d4-a716-446655440000`) `[CODE]` |
| **Transport** | `Authorization: Bearer sk-{uuid}` or `x-api-key` header `[CODE]` |
| **Storage** | Hashed in database (not stored in plaintext) `[CODE]` |
| **Scope** | Bound to a specific user account; inherits that user's permissions `[CODE]` |
| **Management** | Create, list, and revoke via `/api/v1/api_key/` endpoints `[CODE]` |

**User benefit:** Long-lived credentials for non-interactive use cases. The `sk-` prefix enables detection by secret scanning tools in CI/CD pipelines and code repositories. `[INFERRED]`

### 4. LDAP / Corporate Directory Authentication

For enterprise environments with existing LDAP directory servers `[CODE]`.

| Property | Value |
|----------|-------|
| **Protocol** | LDAP bind authentication `[CODE]` |
| **User Provisioning** | Automatic -- local user record created on first successful bind `[CODE]` |
| **Group Mapping** | LDAP groups mapped to LangBuilder roles `[CODE]` |
| **Configuration** | LDAP server URL, bind DN, search base via environment variables `[CODE]` |

**User benefit:** Organizations use their existing Active Directory or LDAP infrastructure without duplicating user accounts. Group-to-role mappings ensure consistent access control aligned with the corporate directory.

### 5. Auto-Login (Development / Single-User)

Passwordless mode for single-user or development deployments `[CODE]`.

| Property | Value |
|----------|-------|
| **Endpoint** | `GET /api/v1/auto_login` `[CODE]` |
| **Use Case** | Local development, personal workstations `[CODE]` |
| **Security** | No authentication required -- must only be used in trusted environments `[CODE]` |

**User benefit:** Zero-friction access for developers running LangBuilder locally. No credentials to manage for personal use.

---

## Authorization Model

LangBuilder implements a flag-based authorization system with two levels of privilege `[CODE]`.

### User Roles and Flags

| Flag | Type | Effect |
|------|------|--------|
| `is_active` | Boolean | Controls whether the user can authenticate. Inactive users are denied all access regardless of other flags. `[CODE]` |
| `is_superuser` | Boolean | Grants full administrative privileges. Superusers bypass all access control checks. `[CODE]` |

**Effective permission logic** `[CODE]`:

```
if not user.is_active:
    DENY all access

if user.is_superuser:
    ALLOW all access

otherwise:
    apply resource-level access control
```

### Flow Access Control

Individual flows have an access type that controls visibility and executability `[CODE]`:

| Access Type | Who Can Access |
|-------------|----------------|
| `PRIVATE` | Only the flow owner and superusers can view, edit, or execute the flow `[CODE]` |
| `PUBLIC` | Any active, authenticated user can view and execute the flow `[CODE]` |

Access checks are enforced at the service layer before any operation (read, write, execute) is performed on a flow `[CODE]`.

### Superuser-Only Operations

The following operations require the `is_superuser` flag `[CODE]`:

| Operation | Endpoint |
|-----------|----------|
| List all users | `GET /api/v1/users/` |
| Update any user | `PATCH /api/v1/users/{user_id}` |
| Reset any user's password | `PATCH /api/v1/users/{user_id}/reset-password` |
| Delete any user | `DELETE /api/v1/users/{user_id}` |

---

## Data Protection

### Encryption at Rest

Sensitive data stored in the database is encrypted using AES-GCM (Galois/Counter Mode) `[CODE]`.

| Primitive | Algorithm | Purpose |
|-----------|-----------|---------|
| **Encryption** | AES-GCM | Encrypt stored secrets and sensitive variable values `[CODE]` |
| **Signing** | Ed25519 | Digital signatures for integrity verification `[CODE]` |
| **Verification** | HMAC-SHA256 | Message authentication and tamper detection `[CODE]` |

### Variable Encryption (KMS)

LangBuilder provides a built-in encrypted variable system for storing credentials used by flow components `[CODE]`.

**How it works:**

1. User creates a variable via `POST /api/v1/variables/` with a name and value `[CODE]`.
2. The value is encrypted with AES-GCM using a master key before being persisted to the database `[CODE]`.
3. The master key is configured via the `LANGBUILDER_SECRET_KEY` environment variable (or equivalent KMS configuration) `[CODE]`.
4. Variable values are never returned through the API -- only variable names and metadata are visible `[CODE]`.
5. At runtime, the graph execution engine decrypts values in memory for the duration of the flow execution, then discards them `[CODE]`.

**User benefit:** Third-party API keys and credentials (e.g., OpenAI key, Pinecone key) are stored securely. Even database compromise does not expose plaintext credentials without the master key.

### Password Security

| Control | Implementation |
|---------|----------------|
| **Hashing** | bcrypt with adaptive cost factor `[CODE]` |
| **Salt** | Unique random salt per password (built into bcrypt) `[CODE]` |
| **Plaintext handling** | Passwords are never stored, logged, or transmitted after initial receipt `[CODE]` |
| **Brute-force resistance** | bcrypt's computational cost makes offline brute-force attacks impractical `[CODE]` |

### Environment Variable Security

Runtime secrets (JWT signing key, database connection strings, OAuth secrets, encryption keys) are provided via environment variables `[CODE]`.

- Environment variables are loaded once at application startup `[CODE]`.
- They are never logged, serialized, or included in API responses `[CODE]`.
- Docker deployments use `.env` files or container orchestrator secret managers `[INFERRED]`.

---

## Security Controls

### Controls Summary Table

| Control | Implementation | Layer | Description |
|---------|----------------|-------|-------------|
| **CORS** | `CORSMiddleware` | Middleware | Configurable allowed origins. Origins set via environment config. Rejects disallowed cross-origin requests before any processing. `[CODE]` |
| **Session Management** | `SessionMiddleware` + `StarSessionsMiddleware` | Middleware | Server-side sessions backed by Redis. Session data is not stored in client cookies. `[CODE]` |
| **Cookie Security** | SameSite, Secure, HttpOnly flags | Middleware | Cookies marked `HttpOnly` (no JavaScript access), `Secure` (HTTPS only), and `SameSite` (CSRF protection). `[CODE]` |
| **Audit Logging** | `AuditLoggingMiddleware` | Middleware | Logs authentication events, access control decisions, and significant state changes. `[CODE]` |
| **Response Compression** | `CompressMiddleware` | Middleware | Applied after security middleware to avoid compressing before encryption. `[CODE]` |
| **TLS / HTTPS** | Reverse proxy (Traefik) | Infrastructure | All external traffic encrypted in transit. TLS terminated at the reverse proxy. `[CODE]` |
| **Input Validation** | Pydantic models | API Layer | All request bodies validated against typed schemas before reaching business logic. `[CODE]` |
| **API Key Format** | `sk-{uuid}` prefix | Application | Predictable format enables detection by secret scanning tools in source code and logs. `[CODE]` |
| **Token Expiry** | JWT `exp` claim | Application | Access tokens expire after 1 hour. Refresh tokens expire after 7 days. Expired tokens are rejected. `[CODE]` |
| **Secret Encryption** | AES-GCM | Data Layer | Sensitive values encrypted at rest. Decrypted only in memory during execution. `[CODE]` |
| **Integrity Checks** | Ed25519 + HMAC-SHA256 | Data Layer | Signatures and MACs verify that stored data has not been tampered with. `[CODE]` |

### Middleware Execution Order

Requests pass through the security middleware stack in this order `[CODE]`:

```
Request
  |
  v
1. CORS Middleware         -- Reject disallowed cross-origin requests
  |
  v
2. Session Middleware      -- Establish/resume server-side session (Redis)
  |
  v
3. Audit Logging           -- Record request for audit trail
  |
  v
4. Compress Middleware     -- Handle response compression
  |
  v
5. Authentication          -- JWT or API key validation
  |
  v
6. Route Handler           -- FastAPI endpoint + service layer
```

### Security Boundaries

The deployment architecture establishes three trust zones `[CODE]`:

| Zone | Components | Trust Level |
|------|-----------|-------------|
| **External (Untrusted)** | Browser clients, external API consumers, OAuth providers, LDAP servers | None -- all input validated |
| **DMZ / Reverse Proxy** | Traefik reverse proxy -- TLS termination, rate limiting | Partially trusted |
| **Application Zone** | LangBuilder backend, OpenWebUI backend, service layer, graph engine | Trusted |
| **Data Zone (Restricted)** | PostgreSQL, Redis, encrypted secret store | Highest trust -- no direct external access |

**Key boundary rule:** No direct database access from API handlers or components. All data access is mediated through the service layer. `[CODE]`

---

## Compliance Readiness

The following assessment maps LangBuilder's security features to common compliance framework requirements. `[INFERRED]`

### SOC 2 Type II Alignment

| Trust Service Criteria | LangBuilder Coverage | Status |
|----------------------|---------------------|--------|
| **CC6.1 -- Logical Access** | JWT + OAuth2 + API Key authentication; role-based superuser flag; flow-level access control | Partial -- formal RBAC not yet implemented `[INFERRED]` |
| **CC6.2 -- Authentication** | bcrypt password hashing; HS256 JWT signing; OAuth2/OIDC with multiple providers | Covered `[INFERRED]` |
| **CC6.3 -- Access Removal** | User deactivation (`is_active` flag); API key revocation | Covered `[INFERRED]` |
| **CC6.6 -- Encryption** | AES-GCM at rest; TLS in transit; bcrypt for passwords | Covered `[INFERRED]` |
| **CC6.7 -- Data Transmission** | HTTPS enforced via reverse proxy; cookie security flags | Covered `[INFERRED]` |
| **CC7.1 -- Monitoring** | Audit logging middleware; build monitoring; transaction logs | Partial -- centralized SIEM integration not built-in `[INFERRED]` |
| **CC7.2 -- Incident Response** | Error tracking (Sentry integration); log streaming | Partial -- no formal IR playbook `[INFERRED]` |

### GDPR Alignment

| Requirement | LangBuilder Coverage | Status |
|-------------|---------------------|--------|
| **Data Minimization** | Self-hosted deployment ensures no data leaves the organization's infrastructure | Covered by architecture `[INFERRED]` |
| **Right to Erasure** | User deletion endpoint (`DELETE /api/v1/users/{user_id}`) | Partial -- cascade deletion scope needs verification `[INFERRED]` |
| **Data Protection by Design** | AES-GCM encryption at rest; TLS in transit; encrypted variables | Covered `[INFERRED]` |
| **Consent** | No user analytics or tracking in self-hosted mode | Covered by architecture `[INFERRED]` |
| **Data Portability** | Flow export (`POST /api/v1/flows/download/`); project export | Covered `[CODE]` |
| **Breach Notification** | Audit logging captures security events | Partial -- no automated breach detection `[INFERRED]` |

### HIPAA Technical Safeguards

| Safeguard | LangBuilder Coverage | Status |
|-----------|---------------------|--------|
| **Access Control** | Authentication + authorization + flow access types | Covered `[INFERRED]` |
| **Audit Controls** | Audit logging middleware; transaction monitoring | Partial `[INFERRED]` |
| **Integrity** | Ed25519 + HMAC-SHA256 integrity checks on stored data | Covered `[CODE]` |
| **Transmission Security** | TLS via reverse proxy | Covered `[CODE]` |
| **Encryption** | AES-GCM at rest | Covered `[CODE]` |

### Compliance Gaps and Recommendations

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| No formal RBAC beyond superuser/user | Limits granular access control for multi-team environments | Implement role definitions (Admin, Developer, Viewer, End User) as described in the capabilities matrix `[INFERRED]` |
| No MFA support | Single-factor authentication may not satisfy compliance frameworks | Add TOTP or WebAuthn as a second factor `[INFERRED]` |
| No centralized audit log export | Difficult to integrate with SIEM tools | Add syslog/SIEM export for audit events `[INFERRED]` |
| No automated session timeout beyond token expiry | Extended sessions possible via refresh tokens | Add configurable idle session timeout `[INFERRED]` |
| No IP allowlisting | Cannot restrict access by network location | Add IP-based access rules at the application level `[INFERRED]` |

---

## Customer-Facing Security Features

These are the security capabilities that users directly interact with or benefit from when using LangBuilder.

### For Developers

| Feature | What It Does | How to Use |
|---------|-------------|------------|
| **Encrypted Variables** | Store API keys and credentials securely with AES-GCM encryption `[CODE]` | Create via Settings > Variables or `POST /api/v1/variables/` |
| **API Key Management** | Generate, list, and revoke API keys for programmatic access `[CODE]` | Create via Settings > API Keys or `POST /api/v1/api_key/` |
| **Flow Access Control** | Set flows to PRIVATE (owner-only) or PUBLIC (all authenticated users) `[CODE]` | Configure in flow settings |
| **Secure Execution** | Flow credentials are decrypted only in memory during execution and immediately discarded `[CODE]` | Automatic -- no user action needed |

### For Administrators

| Feature | What It Does | How to Use |
|---------|-------------|------------|
| **User Management** | Create, deactivate, and delete user accounts `[CODE]` | Admin panel or `/api/v1/users/` endpoints (superuser only) |
| **Password Reset** | Reset any user's password `[CODE]` | `PATCH /api/v1/users/{user_id}/reset-password` (superuser only) |
| **OAuth Configuration** | Configure corporate SSO via Google, Microsoft, or GitHub `[CODE]` | Environment variables for OAuth client credentials |
| **LDAP Integration** | Connect to corporate directory for centralized authentication `[CODE]` | Environment variables for LDAP server configuration |
| **Audit Logs** | Review authentication events and access control decisions `[CODE]` | Monitor via `/api/v1/monitor/transactions` or log stream |
| **CORS Configuration** | Control which domains can access the API `[CODE]` | `LANGBUILDER_BACKEND_URL` and related environment variables |

### For End Users (API Consumers)

| Feature | What It Does | How to Use |
|---------|-------------|------------|
| **API Key Authentication** | Access flows programmatically without interactive login `[CODE]` | Include `Authorization: Bearer sk-{uuid}` header |
| **HTTPS Encryption** | All data in transit is encrypted `[CODE]` | Automatic -- always use HTTPS endpoint |
| **Token Refresh** | Seamless session continuity without re-entering credentials `[CODE]` | Call `POST /api/v1/refresh` before access token expires |

---

*Generated by CloudGeometry AIx SDLC - Product Analysis*
