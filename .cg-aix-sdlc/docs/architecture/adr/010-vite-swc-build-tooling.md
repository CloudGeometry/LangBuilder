# ADR-010: Vite + SWC for Build Tooling

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder's frontend is a large TypeScript + React application with 1,100+ source files (634 TSX + 512 TS + 172 JS) that requires a build tool for development (hot module replacement, TypeScript transpilation) and production (bundling, code splitting, minification, tree shaking). The build tool must provide fast feedback during development -- every second of HMR delay directly impacts developer productivity when iterating on canvas interactions and component UIs. Production builds must produce optimized bundles with code splitting for fast initial page loads.

### Constraints

- Must support TypeScript 5.4.5 transpilation (with strict mode)
- Must support React 18 JSX transform
- Must provide sub-second hot module replacement (HMR) for a pleasant development experience
- Must produce optimized production builds with code splitting, tree shaking, and minification
- Must handle 1,100+ source files without excessive build times
- Must support Tailwind CSS processing
- Must support environment variables for configuration (e.g., `VITE_BACKEND_URL`)

### Requirements

- Fast development server with hot module replacement (HMR)
- TypeScript transpilation (not type checking -- that is a separate step)
- Production bundling with code splitting and tree shaking
- CSS processing (Tailwind CSS, PostCSS)
- Asset handling (images, fonts, SVGs)
- Environment variable injection
- Plugin ecosystem for customization

## Decision

Use Vite 5.4.19 as the build tool with SWC (Speedy Web Compiler) as the TypeScript/JSX transpiler. Vite provides an unbundled development server using native ES modules for instant startup and fast HMR, and uses Rollup for optimized production builds. SWC replaces Babel as the transpiler, providing 20-70x faster TypeScript and JSX transpilation. Biome 2.1.1 handles linting and formatting (replacing ESLint + Prettier).

Vite + SWC was chosen because the combination provides the fastest possible development feedback loop (sub-100ms HMR) and production build times (seconds rather than minutes) for a codebase of LangBuilder's size, while maintaining full support for TypeScript, React, Tailwind CSS, and the modern JavaScript ecosystem.

## Consequences

### Positive

- Development server starts in milliseconds (unbundled ES modules) rather than seconds (Webpack's full bundle approach), even with 1,100+ files
- HMR updates are sub-100ms because Vite only transforms the changed module, not the entire dependency graph
- SWC transpiles TypeScript/JSX 20-70x faster than Babel, reducing both HMR latency and production build time
- Production builds use Rollup with automatic code splitting, producing optimal chunk sizes for browser caching and loading
- Native ES module support means no bundling during development, resulting in consistent performance regardless of codebase size
- Vite's plugin ecosystem (`@vitejs/plugin-react-swc`, `vite-plugin-svgr`, etc.) covers all required integrations
- Environment variable handling (`VITE_` prefix) provides a clean, secure pattern for injecting configuration

### Negative

- Vite's development server serves unbundled ES modules, which means the behavior during development can differ from the Rollup-bundled production build in edge cases (e.g., module resolution differences, CSS import order)
- SWC does not perform TypeScript type checking -- it only transpiles. Type checking must be done separately via `tsc --noEmit`, adding a separate CI step
- Vite's plugin ecosystem, while growing, is smaller than Webpack's, meaning some niche requirements may need custom plugin development
- Moving away from Webpack means existing Webpack-specific knowledge and configuration patterns do not transfer directly

### Neutral

- Vite uses Rollup for production builds, which has a mature plugin ecosystem and well-understood behavior
- The configuration file (`vite.config.mts`) uses TypeScript, providing type-safe build configuration
- Biome replaces ESLint + Prettier as the linter/formatter, consolidating two tools into one with significantly faster execution

## Alternatives Considered

### Webpack 5

**Pros**: Industry standard with the largest ecosystem of loaders and plugins; mature, well-understood configuration model; supports every conceivable build scenario; large community and extensive documentation
**Cons**: Significantly slower development server startup and HMR compared to Vite, especially for large codebases (30-60 seconds startup vs. milliseconds); complex configuration that grows unwieldy; Babel-based transpilation is slower than SWC; module federation adds complexity that LangBuilder does not need
**Why not chosen**: Webpack's development performance was the primary concern. For a codebase with 1,100+ files, Webpack's full-bundle development approach results in slow startup (30-60 seconds) and sluggish HMR (1-5 seconds per update). Vite's unbundled ES module approach eliminates this bottleneck entirely.

### Turbopack (Next.js)

**Pros**: Rust-based bundler designed for speed; built by the Webpack creator (Tobias Koppers) with lessons learned; integrated with the Next.js ecosystem
**Cons**: Tightly coupled to Next.js; LangBuilder is a single-page application that does not need server-side rendering (SSR) or server components; using Turbopack outside Next.js is not well-supported; still in beta/early release for production use
**Why not chosen**: Turbopack is designed for the Next.js ecosystem, and LangBuilder does not use Next.js. The SPA architecture does not benefit from SSR or server components, and Turbopack's standalone use outside Next.js is not mature.

### esbuild (Standalone)

**Pros**: Extremely fast (written in Go); handles both bundling and transpilation; simple configuration; used internally by Vite for dependency pre-bundling
**Cons**: Limited plugin API compared to Rollup/Webpack; no built-in HMR; code splitting support is less mature than Rollup; CSS handling requires additional tooling; lacks some production optimization features (e.g., CSS code splitting, advanced tree shaking)
**Why not chosen**: While esbuild is faster than Vite for raw transpilation, Vite provides a complete development experience (dev server, HMR, plugin ecosystem) that esbuild alone does not. Vite already uses esbuild internally for dependency pre-bundling, capturing esbuild's speed benefits within a more complete tool.

### Parcel 2

**Pros**: Zero-configuration bundler that "just works"; built-in support for TypeScript, JSX, CSS, and assets without configuration; good performance with caching
**Cons**: Less control over build output compared to Vite/Rollup; smaller plugin ecosystem; community and adoption are smaller than Vite or Webpack; some advanced code splitting scenarios are less configurable
**Why not chosen**: Parcel's zero-configuration approach, while appealing, provides less control over production build output (chunk splitting, manual chunk configuration) than Vite's Rollup-based build. For a complex SPA with specific optimization requirements, Vite's configurability is more appropriate.

## Implementation Notes

- Vite configuration is in `vite.config.mts` with the `@vitejs/plugin-react-swc` plugin
- TypeScript configuration in `tsconfig.json` with strict mode, ES5 target, ESNext modules, and React JSX transform
- Environment variables prefixed with `VITE_` are exposed to client code; `VITE_BACKEND_URL` configures the API endpoint
- Production builds output to `dist/` with automatic code splitting by route (lazy-loaded routes produce separate chunks)
- Biome 2.1.1 replaces ESLint + Prettier for linting and formatting, configured in the root `package.json`
- Development server runs on port 5175 with proxy configuration to forward API requests to the backend at port 8002

## Related Decisions

- [ADR-007](007-react-typescript-frontend.md) - The React + TypeScript codebase that Vite builds
- [ADR-008](008-react-flow-visual-canvas.md) - React Flow components benefit from fast HMR during canvas interaction development
- [ADR-015](015-docker-multi-stage-builds.md) - Production Docker builds use `npm run build` (Vite) in the build stage

## References

- https://vitejs.dev/
- https://swc.rs/
- https://rollupjs.org/
- https://biomejs.dev/
