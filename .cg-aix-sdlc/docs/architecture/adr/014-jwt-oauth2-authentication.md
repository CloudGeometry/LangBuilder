# ADR-014: JWT + OAuth2 for Authentication

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder requires an authentication system that supports multiple access patterns: interactive browser sessions (login form), programmatic API access (automation, CI/CD), and federated identity via external providers (Google, Microsoft, GitHub). The system must verify user identity, issue time-limited credentials, support API key-based access for machine-to-machine communication, and integrate with enterprise identity providers. The authentication mechanism must work across the FastAPI backend, WebSocket connections for real-time streaming, and the React frontend.

### Constraints

- Must support stateless authentication for horizontal scaling (multiple backend replicas behind a load balancer must validate tokens independently)
- Must support both interactive (browser) and programmatic (API key) access patterns
- Must integrate with external identity providers (Google, Microsoft, GitHub) for federated authentication
- Must secure WebSocket connections for real-time LLM token streaming
- Must not store sensitive tokens in browser local storage (XSS vulnerability consideration)
- Must support token expiration and rotation
- Passwords must be stored securely (hashed, salted)

### Requirements

- Stateless token-based authentication (no server-side session lookup required for every request)
- JWT token issuance with configurable expiration
- Password-based authentication with bcrypt hashing
- OAuth2 / OIDC support for external identity providers
- API key authentication for programmatic access
- Role-based authorization (regular users, superusers)
- Token transport via Authorization Bearer header
- Integration with FastAPI's dependency injection for route-level authorization

## Decision

Use JWT (JSON Web Tokens) with HS256 signing as the primary authentication mechanism, supplemented by OAuth2/OIDC for federated identity and API keys for programmatic access. Passwords are hashed with bcrypt. JWT tokens are signed using HMAC-SHA256 (HS256) with a server-side secret key and include a user ID and expiration claim. OAuth2 integration (via `authlib`) supports Google, Microsoft, and GitHub as external identity providers using the authorization code grant flow. API keys use the `sk-{uuid}` format and are stored as hashed values.

This multi-mechanism approach was chosen because LangBuilder serves diverse access patterns: developers using the browser UI need seamless login (JWT), automation scripts need long-lived credentials (API keys), and enterprise users need federated identity (OAuth2/OIDC). JWT's stateless nature is critical for horizontal scaling across multiple backend replicas.

## Consequences

### Positive

- Stateless JWT validation means any backend replica can verify a token without consulting a central session store, enabling horizontal scaling without session affinity
- HS256 JWT signing is simple and efficient: a single secret key is shared across all backend replicas, and validation is a fast HMAC computation
- OAuth2/OIDC integration (Google, Microsoft, GitHub) allows users to authenticate with existing enterprise or personal accounts, reducing friction and eliminating password management for those users
- API keys (`sk-{uuid}`) provide a clean, secure mechanism for programmatic access that does not require interactive login flows
- bcrypt password hashing provides strong protection against brute-force and rainbow table attacks with its adaptive cost factor
- FastAPI's `Depends()` system integrates naturally with JWT validation, providing clean route-level authorization decorators
- The `sk-{uuid}` API key format is designed for detection by secret scanning tools, preventing accidental exposure in source code or logs

### Negative

- HS256 (symmetric signing) means all backend replicas share the same secret key; compromise of this key allows forging tokens for any user. RS256 (asymmetric) would limit the blast radius but adds key management complexity
- JWT tokens cannot be individually revoked before expiration without maintaining a server-side revocation list, which partially negates the stateless benefit
- Token expiration requires the frontend to handle token refresh flows, adding complexity to the API client layer
- OAuth2/OIDC integration with external providers introduces dependencies on external services; if the identity provider is down, new logins via that provider fail
- Multiple authentication mechanisms (JWT, API key, OAuth2, LDAP, trusted header) increase the attack surface and require thorough security testing of each path

### Neutral

- The authorization model is binary (regular user vs. superuser), which is simple but may need to evolve toward more granular role-based access control (RBAC) as the platform matures
- API keys inherit the permissions of the user they are bound to, meaning API key authorization is equivalent to the user logging in directly
- LDAP and trusted header authentication are supported by the OpenWebUI backend component, extending the authentication options for enterprise deployments

## Alternatives Considered

### Session-Based Authentication (Server-Side Sessions)

**Pros**: Server-side sessions allow immediate revocation; session state is fully controlled by the server; no token expiration concerns; simpler token management (opaque session ID vs. JWT)
**Cons**: Requires server-side session storage (Redis or database) that must be consulted on every request; creates a scaling bottleneck unless a distributed session store is used; session affinity may be needed with multiple replicas; does not naturally support programmatic API access
**Why not chosen**: Server-side sessions require a centralized session store that every request must consult, creating a scaling dependency. JWT's stateless validation is more appropriate for a horizontally scaled deployment where any replica must independently authenticate requests. Note: Redis-backed sessions are used for specific features (CSRF, OAuth state) but not as the primary authentication mechanism.

### Auth0 / Clerk / Third-Party Auth Service

**Pros**: Fully managed authentication with support for JWT, OAuth2, LDAP, SAML, and more; no need to implement or maintain authentication logic; built-in dashboard for user management; compliance certifications
**Cons**: External dependency for a critical path (authentication); recurring cost that scales with user count; vendor lock-in; latency for every authentication check (network call to external service); privacy concerns with sending user data to a third party; not usable in air-gapped or on-premises deployments
**Why not chosen**: LangBuilder must support on-premises and air-gapped deployments where external SaaS dependencies are not acceptable. A self-hosted authentication system ensures the platform can be deployed anywhere without external service dependencies.

### Paseto (Platform-Agnostic Security Tokens)

**Pros**: Addresses several JWT security concerns (no algorithm confusion attacks, no `none` algorithm vulnerability); stronger default security; simpler and safer API
**Cons**: Much smaller ecosystem and library support compared to JWT; fewer developers are familiar with Paseto; limited tooling for debugging and inspection; no native support in most web frameworks or identity providers; OAuth2/OIDC standards are built around JWT, not Paseto
**Why not chosen**: Paseto's smaller ecosystem and lack of integration with the OAuth2/OIDC standards that LangBuilder uses for federated identity made it impractical. JWT's security concerns are mitigated by following best practices (fixed algorithm, strong secret, short expiration).

### mTLS (Mutual TLS)

**Pros**: Strong identity verification at the transport level; no application-layer tokens to manage; client certificates provide non-repudiation; resistant to token theft
**Cons**: Complex certificate management (issuance, renewal, revocation for every client); poor developer experience for browser-based access; not suitable for end-user authentication; primarily designed for service-to-service communication
**Why not chosen**: mTLS is designed for machine-to-machine communication and is impractical for browser-based interactive access. Certificate management for potentially thousands of users would be operationally prohibitive.

## Implementation Notes

- JWT signing secret is configured via the `SECRET_KEY` environment variable; this must be the same across all backend replicas
- Token creation uses `python-jose` or `PyJWT` to encode `{"sub": user_id, "exp": expiry}` with HS256
- Password hashing uses `bcrypt` with an adaptive cost factor; passwords are hashed on registration and verified on login
- OAuth2 flow is implemented via `authlib`: redirect to provider -> authorization code callback -> exchange for ID token -> extract user identity -> create/match local user -> issue LangBuilder JWT
- API keys are formatted as `sk-{uuid}`, hashed with SHA-256 before storage, and validated by hashing the provided key and comparing against stored hashes
- Authentication is enforced via FastAPI's `Depends(get_current_user)` which extracts and validates the JWT from the Authorization header
- Superuser checks use `Depends(get_current_active_superuser)` which verifies both token validity and the `is_superuser` flag
- CORS middleware is configured to accept credentials from allowed origins
- The middleware execution order is: CORS -> Session -> Audit Logging -> Compression -> Authentication -> Route Handler

## Related Decisions

- [ADR-002](002-fastapi-backend-api.md) - FastAPI's dependency injection system is used for authentication middleware
- [ADR-006](006-sqlite-postgresql-dual-database.md) - User credentials, API keys, and encrypted secrets are stored in the database
- [ADR-012](012-traefik-reverse-proxy.md) - TLS termination at Traefik protects token transport

## References

- https://jwt.io/
- https://www.rfc-editor.org/rfc/rfc7519 - JWT RFC
- https://www.rfc-editor.org/rfc/rfc6749 - OAuth 2.0 RFC
- https://openid.net/specs/openid-connect-core-1_0.html - OpenID Connect
- https://docs.authlib.org/
- https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html - OWASP JWT best practices
