# ADR-007: React 18 + TypeScript for Frontend

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder requires a rich, interactive frontend application that provides a visual drag-and-drop workflow canvas, a chat interface for interacting with deployed flows, administrative pages for user and flow management, and real-time updates during workflow execution. The frontend is a complex single-page application with approximately 634 TSX component files, 512 TypeScript files, 20 routes, and 16 state stores. The framework must support sophisticated UI interactions (drag-and-drop, canvas manipulation, real-time streaming) while maintaining code quality and developer productivity at this scale.

### Constraints

- Must support complex interactive components including a node-based graph editor with custom rendering
- Must have a mature ecosystem of libraries for the specific needs: graph canvas, form handling, data tables, animations
- Must support TypeScript for type safety at the codebase scale (1,100+ TypeScript/TSX files)
- Must support server state management (API data caching) and client state management (canvas state) as separate concerns
- Must have strong developer tooling (linting, formatting, testing, debugging)
- Team has existing React expertise

### Requirements

- Component-based architecture for reusable UI elements
- TypeScript support with strict mode for type safety
- Concurrent rendering features for responsive canvas interactions during heavy updates
- Rich ecosystem of compatible UI component libraries (Radix UI, React Flow, AG Grid, Framer Motion)
- Mature testing story (unit, component, integration, E2E)
- Active community and long-term maintenance

## Decision

Use React 18.3.1 with TypeScript 5.4.5 as the frontend framework. React was chosen for its mature ecosystem, component model, and concurrent features. TypeScript was chosen as a non-negotiable requirement for maintaining code quality across 1,100+ frontend source files. The frontend uses functional components with hooks exclusively -- no class components.

React 18's concurrent features (Suspense, transitions, automatic batching) are leveraged to keep the canvas interface responsive when updating large workflow graphs. TypeScript's strict mode catches type errors at compile time, preventing a broad class of runtime bugs in the complex state management and API interaction layers.

## Consequences

### Positive

- React's component model provides excellent code reuse across the application's many UI patterns (modals, forms, panels, node types)
- TypeScript strict mode catches type errors at compile time across 1,100+ files, dramatically reducing runtime type-related bugs
- React 18's concurrent features (automatic batching, transitions, Suspense) keep the canvas responsive during complex state updates
- The React ecosystem provides purpose-built libraries for every UI need: React Flow for the canvas, AG Grid for data tables, Framer Motion for animations, Radix UI for accessible primitives, React Hook Form for forms
- Large community means extensive learning resources, Stack Overflow answers, and third-party library support
- React's hooks model provides clean separation of concerns (data fetching via TanStack Query hooks, state via Zustand hooks, side effects via useEffect)

### Negative

- React's virtual DOM introduces overhead compared to fine-grained reactivity frameworks, though this is mitigated by React 18's concurrent features and memoization
- The JSX paradigm mixes markup with logic, which can reduce readability in complex components if not carefully structured
- React does not include built-in solutions for routing, state management, or data fetching, requiring additional library choices (each with its own learning curve)
- TypeScript compilation adds build time, though this is largely mitigated by SWC's fast transpilation (see ADR-010)
- React's frequent release cycle and ecosystem churn requires ongoing dependency maintenance

### Neutral

- React is the dominant frontend framework by market share, making hiring and onboarding straightforward
- The choice of functional components with hooks over class components is now the community standard and aligns with modern React patterns
- React 18 is a mature, stable release rather than a bleeding-edge version, providing reliability without sacrificing features

## Alternatives Considered

### Vue.js 3 + TypeScript

**Pros**: Simpler learning curve, better built-in state management (Pinia), single-file components with clean separation of template/script/style, excellent performance with fine-grained reactivity, good TypeScript support in Vue 3
**Cons**: Smaller ecosystem of specialized libraries (no equivalent to React Flow's maturity for graph editing), fewer enterprise-scale applications to reference, smaller community for niche UI patterns; would require building or adapting a graph canvas library
**Why not chosen**: The React ecosystem has purpose-built, mature libraries for LangBuilder's specific needs (React Flow for graph editing, AG Grid for data tables, Radix UI for accessible components). Vue's ecosystem, while growing, does not have equivalents at the same maturity level, particularly for the node-based graph canvas which is LangBuilder's core UI.

### Angular

**Pros**: Full framework with built-in solutions for routing, forms, HTTP client, and dependency injection; strong TypeScript integration (TypeScript is mandatory); good for large enterprise applications
**Cons**: Heavier framework with steeper learning curve; more opinionated architecture that can feel restrictive; smaller ecosystem of specialized UI libraries compared to React; React Flow (the critical graph canvas library) is React-specific with no Angular equivalent of comparable maturity
**Why not chosen**: Angular's full-framework approach includes many features LangBuilder does not need (built-in forms, HTTP client) while lacking the specialized graph canvas library (React Flow) that is essential. The ecosystem of React-specific libraries (Zustand, TanStack Query, Radix UI) provides better fit-for-purpose tooling.

### Svelte / SvelteKit

**Pros**: Excellent performance due to compile-time reactivity (no virtual DOM), minimal boilerplate, simpler mental model, smaller bundle sizes
**Cons**: Significantly smaller ecosystem; no mature equivalent to React Flow for graph editing; fewer UI component libraries; smaller community means less help for complex UI patterns; less proven at the scale of 1,100+ component files
**Why not chosen**: Svelte's smaller ecosystem was the deciding factor. The absence of a React Flow equivalent would require building the graph canvas editor from scratch, which represents months of engineering effort for a component that is central to LangBuilder's value proposition.

## Implementation Notes

- Frontend source is organized under `langbuilder/src/frontend/src/` with approximately 634 TSX and 512 TS files
- React Router 6.23.1 handles client-side routing with approximately 20 routes
- Radix UI provides accessible, unstyled component primitives; Tailwind CSS 3.4 provides utility-first styling
- Biome 2.1.1 is used for linting and formatting (replacing ESLint + Prettier)
- Testing stack: Jest 30.0.3 for unit tests, React Testing Library 16.0.0 for component tests, Playwright 1.52.0 for E2E tests
- TypeScript is configured with strict mode, ES5 target for broad compatibility, ESNext module system, and React JSX transform

## Related Decisions

- [ADR-008](008-react-flow-visual-canvas.md) - React Flow is the primary visual canvas library, requiring React
- [ADR-009](009-zustand-state-management.md) - Zustand provides state management for React components
- [ADR-010](010-vite-swc-build-tooling.md) - Vite + SWC provides the build tooling for the React + TypeScript codebase

## References

- https://react.dev/
- https://www.typescriptlang.org/
- https://react.dev/blog/2022/03/29/react-v18
- https://www.radix-ui.com/
- https://tailwindcss.com/
