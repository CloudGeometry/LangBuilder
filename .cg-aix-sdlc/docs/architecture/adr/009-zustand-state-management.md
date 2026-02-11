# ADR-009: Zustand for State Management

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder's frontend requires sophisticated state management across multiple domains: the visual canvas graph state (nodes, edges, selection, viewport), authentication state, application settings, component registry data, chat session state, and more. The application has 16 distinct state stores managing different concerns. The state management solution must handle high-frequency updates from canvas interactions (node dragging, edge creation, viewport panning) without causing unnecessary re-renders, while remaining simple enough for developers to work with across 1,100+ frontend source files.

### Constraints

- Must handle high-frequency state updates from canvas interactions (60fps drag operations) without performance degradation
- Must support 16+ independent stores managing different state domains
- Must work well with React 18's concurrent features
- Must provide a simple API that minimizes boilerplate across a large codebase (1,100+ files)
- Must support selective state subscription (components subscribe only to the state they need, avoiding unnecessary re-renders)
- Must be compatible with React Flow's state model
- Must support devtools for debugging state changes during development

### Requirements

- Minimal boilerplate for store creation and usage
- Direct state access without action dispatchers or reducers
- Selective subscription to avoid unnecessary re-renders
- Middleware support (persistence, devtools, logging)
- TypeScript support with full type inference
- Small bundle size (the frontend serves a complex SPA that should minimize library overhead)
- Easy testing without complex mock setups

## Decision

Use Zustand 4.5.2 for client-side state management. Zustand provides a minimal, hook-based state management API where stores are created with a simple `create()` function and consumed via React hooks. State updates are performed by calling `set()` with the new state, and components subscribe to specific slices of state via selectors, ensuring only affected components re-render.

Zustand was chosen because it provides the performance characteristics needed for high-frequency canvas interactions with an API that is dramatically simpler than Redux. With 16 stores across 1,100+ files, the reduction in boilerplate compared to Redux (no action types, action creators, reducers, or dispatch) translates to thousands of lines of saved code.

## Consequences

### Positive

- Minimal boilerplate: a store is created with a single `create()` call and consumed via a hook; no action types, reducers, or dispatch functions needed
- Direct state mutation via `set()` is intuitive and requires fewer abstractions than Redux's reducer pattern
- Selective subscriptions via selectors (`useStore(state => state.nodes)`) prevent re-renders in components that do not depend on the changed state, critical for canvas performance
- Small bundle size (approximately 1KB gzipped) adds negligible overhead to the application
- 16 independent stores provide clean separation of concerns (flow store, auth store, settings store, etc.) without the complexity of Redux slices or module federation
- Works seamlessly with React Flow, which can read from and write to Zustand stores directly
- Easy to test: stores can be instantiated independently without a Provider wrapper or mock configuration
- Middleware support enables devtools integration, state persistence, and logging

### Negative

- Zustand's simplicity means there are fewer guardrails: developers can mutate state in non-standard ways without the structured pattern enforcement that Redux provides
- No built-in support for normalized state or entity adapters; managing relational data (e.g., node-to-edge relationships) requires manual implementation
- With 16 stores, there is no centralized view of all application state (unlike Redux's single store), which can make cross-cutting state debugging more complex
- Zustand's devtools middleware provides basic state inspection but is less feature-rich than Redux DevTools for time-travel debugging and action replay

### Neutral

- Zustand stores are created outside React's component tree, meaning store instances are singletons by default; this is appropriate for LangBuilder's single-application architecture
- Server state (API data) is managed separately by TanStack Query, following the recommended pattern of separating client state (Zustand) from server state (TanStack Query)
- The Zustand community is smaller than Redux's, but the API is simple enough that community support is rarely needed

## Alternatives Considered

### Redux Toolkit

**Pros**: Industry-standard state management with a massive ecosystem; Redux DevTools provides time-travel debugging, action replay, and state inspection; normalized state patterns via `createEntityAdapter`; well-established patterns for large-scale applications; extensive documentation and community support
**Cons**: Significantly more boilerplate than Zustand, even with Redux Toolkit's simplified API; requires action types, reducers, and dispatch for every state change; `createSlice` reduces boilerplate but still requires more ceremony than Zustand; the Provider wrapper adds complexity; Redux's single-store model can lead to deeply nested state trees
**Why not chosen**: The boilerplate cost of Redux across 16 stores and 1,100+ files was the primary concern. For LangBuilder's use case, the additional structure Redux provides (action types, reducers) does not add proportional value over Zustand's direct state access, and the performance benefit of Zustand's selective subscriptions is critical for canvas performance.

### MobX

**Pros**: Observable-based reactivity with minimal boilerplate; automatic dependency tracking means components re-render only when observed values change; class-based stores with decorators provide clear structure
**Cons**: Observable proxies can cause unexpected behavior with React Flow's internal state; class-based patterns are less idiomatic in modern React (hooks-first); the "magic" of automatic dependency tracking can make debugging difficult; requires understanding MobX's proxy-based reactivity model
**Why not chosen**: MobX's proxy-based reactivity, while powerful, introduces a layer of abstraction that can conflict with React Flow's internal state management and cause subtle issues with React 18's concurrent features. Zustand's explicit subscriptions provide more predictable behavior.

### React Context + useReducer

**Pros**: Built into React with no additional dependencies; familiar pattern for React developers; no library to maintain or update
**Cons**: Context does not provide fine-grained subscriptions -- all consumers of a context re-render when any part of the context value changes; this is unacceptable for high-frequency canvas updates where a node drag should not re-render every component subscribed to the flow state; requires splitting into many contexts to avoid re-render storms, leading to deeply nested Provider trees
**Why not chosen**: React Context's lack of selective subscriptions makes it fundamentally unsuitable for the high-frequency state updates generated by canvas interactions. Wrapping the application in 16+ Context Providers would create an unmanageable Provider hierarchy.

### Jotai

**Pros**: Atomic state management built for React; fine-grained subscriptions at the atom level; minimal boilerplate; excellent TypeScript support; works well with React 18 concurrent features
**Cons**: Atomic model is less intuitive for managing complex state objects (like a full graph with nodes and edges); requires defining many atoms and derived atoms for complex state; less straightforward for store-like patterns where multiple related values are updated together
**Why not chosen**: Jotai's atomic model excels at independent pieces of state but becomes awkward for LangBuilder's use case where related state (nodes, edges, selection) must be updated together atomically. Zustand's store model provides a more natural fit for managing coherent state domains.

## Implementation Notes

- 16 Zustand stores are organized by domain: flow, auth, settings, alerts, types, component, dark mode, location, folders, API, shortcuts, store, chat, messages, flow manager, playground
- The flow store manages React Flow's nodes, edges, and viewport state, with actions for addNode, updateNode, deleteNode, addEdge, and selection
- Stores use TypeScript interfaces for full type safety on state shape and actions
- Zustand's `devtools` middleware is enabled in development for browser-based state inspection
- TanStack Query 5.49.2 manages server state (API data caching, background refetching), keeping Zustand stores focused on client-side UI state
- Stores are imported directly via hooks (`useFlowStore(state => state.nodes)`) without a Provider wrapper

## Related Decisions

- [ADR-007](007-react-typescript-frontend.md) - React 18 is the framework that Zustand integrates with
- [ADR-008](008-react-flow-visual-canvas.md) - React Flow reads from and writes to Zustand stores for graph state management

## References

- https://zustand-demo.pmnd.rs/
- https://github.com/pmndrs/zustand
- https://tanstack.com/query/latest - TanStack Query for server state
