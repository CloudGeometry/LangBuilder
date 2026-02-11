# ADR-008: React Flow (xyflow) for Visual Canvas

## Status

Accepted

## Date

2026-02-09

## Decision Makers

- LangBuilder Development Team

## Context

### Problem Statement

LangBuilder's core user experience is a visual canvas where users build AI workflows by dragging components from a sidebar, placing them on the canvas, and connecting them with edges to define data flow. This canvas must render custom node types (each representing a different component with unique input/output ports), support custom edge rendering, provide smooth pan/zoom/selection interactions, handle large graphs with hundreds of nodes performantly, and produce a graph data structure that maps directly to the backend's DAG execution model. Building a graph editor from scratch would require months of engineering effort for interactions, rendering, hit testing, and accessibility.

### Constraints

- Must be a React-compatible library (the frontend uses React 18 -- see ADR-007)
- Must support custom node rendering (each component type has a unique visual representation with typed input/output ports)
- Must support custom edge rendering (edges represent data flow and need visual indicators for data type compatibility)
- Must provide built-in pan, zoom, minimap, and selection interactions
- Must handle graphs with 100+ nodes without performance degradation
- Must produce a serializable graph data structure (nodes + edges) that can be persisted and sent to the backend

### Requirements

- Custom node components with input/output handles (ports)
- Custom edge components with labels and interaction
- Built-in pan, zoom, and fit-to-view controls
- Node selection (single, multi-select, lasso)
- Drag-and-drop node creation from an external sidebar
- Serializable graph state (nodes array + edges array as JSON)
- Performance with large graphs (100+ nodes)
- Active maintenance and community support
- Accessibility considerations

## Decision

Use React Flow 12.x (`@xyflow/react`) as the visual canvas library. React Flow is a purpose-built library for creating node-based graph editors in React. It provides custom node and edge rendering, built-in interaction handling (pan, zoom, select, drag), a minimap component, and a graph data model that serializes to JSON arrays of nodes and edges.

React Flow was chosen because it is the most mature and feature-complete React library specifically designed for node-based graph editing. Its data model (arrays of typed nodes and edges with source/target references) maps directly to LangBuilder's DAG representation, and its custom node system allows each of LangBuilder's 96 component types to have a unique visual representation.

## Consequences

### Positive

- Purpose-built for the exact use case (node-based graph editing), providing polished interactions out of the box that would take months to build from scratch
- Custom node components allow each of LangBuilder's component types to have unique visual representations with typed input/output handles
- The graph data model (nodes + edges as JSON arrays) serializes directly to the Flow model's `data` field, creating a 1:1 mapping between visual representation and execution graph
- Built-in features (minimap, controls, background grid, snap-to-grid) enhance the user experience without additional development
- Performance optimizations (viewport culling, only rendering visible nodes) enable handling of large graphs
- Active maintenance with regular releases, responsive issue handling, and good documentation
- React Flow 12.x uses a modern API with hooks (`useReactFlow`, `useNodes`, `useEdges`) that integrates cleanly with Zustand state management

### Negative

- React Flow is a relatively specialized library; if the project needs to move away from React, the canvas would need to be rebuilt entirely
- Customization beyond the provided extension points (custom nodes, edges, handles) may require forking or working around library internals
- React Flow's paid "Pro" tier includes some advanced features (sub-flows, node resizer); the open-source version covers LangBuilder's current needs but may require the Pro tier for future features
- The library's update cycle requires testing LangBuilder's custom nodes and interactions after each upgrade

### Neutral

- React Flow is maintained by xyflow, a small but focused team; the project is sustainable via the Pro subscription model
- The library has been adopted by several similar tools (including LangFlow, the project LangBuilder forked from), validating its suitability for AI workflow builders
- React Flow's internal use of D3 for pan/zoom calculations is an implementation detail that does not affect LangBuilder's code

## Alternatives Considered

### D3.js (Custom Implementation)

**Pros**: Maximum flexibility; D3 provides low-level primitives for SVG manipulation, force-directed layouts, zoom/pan, and data binding; no constraints from a library's opinionated design
**Cons**: Building a full graph editor (custom nodes, edge routing, selection, drag-and-drop, keyboard shortcuts, accessibility) from D3 primitives would require 3-6 months of dedicated engineering; ongoing maintenance of the custom editor; no community of users reporting bugs and contributing fixes
**Why not chosen**: The engineering investment required to build a production-quality graph editor from D3 primitives was unjustifiable when React Flow provides exactly this functionality as a maintained open-source library.

### JointJS / Rappid

**Pros**: Mature diagramming library with support for custom shapes, link routing, and complex layouts; Rappid (commercial version) includes many advanced features; framework-agnostic
**Cons**: Not React-native; integration with React requires wrappers that add complexity; commercial license required for Rappid features; heavier bundle size; the API is designed for general-purpose diagramming rather than specifically node-based graph editing
**Why not chosen**: JointJS's lack of native React integration would add complexity and reduce developer productivity. React Flow's React-native design provides a more idiomatic development experience and better integration with the Zustand-based state management.

### Cytoscape.js

**Pros**: Powerful graph visualization library with extensive layout algorithms, analysis capabilities, and a plugin ecosystem; good for large-scale graph visualization
**Cons**: Optimized for graph visualization and analysis rather than interactive graph editing; limited support for custom HTML/React node rendering (primarily canvas-based); adding interactive editing (drag-to-connect, port-based connections) requires significant custom code
**Why not chosen**: Cytoscape.js excels at graph visualization and analysis but is not designed for the interactive editing experience LangBuilder requires. Its canvas-based rendering makes custom React node components difficult, and the interactive editing features would need to be built from scratch.

### Dagre + Custom React Components

**Pros**: Dagre provides automatic DAG layout algorithms; combined with custom React SVG/HTML components, could provide the visual representation; lightweight
**Cons**: Dagre is a layout algorithm, not an interaction library; all interaction handling (drag, pan, zoom, selection, edge creation) would need to be built from scratch; no custom node rendering framework
**Why not chosen**: Dagre solves only the layout problem, leaving the entire interaction and rendering layer to be built custom. This is the same fundamental problem as the D3 approach with even less out-of-the-box functionality.

## Implementation Notes

- Custom node types are registered for each component category, rendering the component name, icon, and typed input/output handles
- The flow store (Zustand) manages the nodes and edges arrays, with React Flow's `onNodesChange` and `onEdgesChange` callbacks updating the store
- Drag-and-drop from the sidebar uses React DnD to create new nodes at the drop position
- The graph is serialized to JSON for persistence by extracting the nodes and edges arrays from the React Flow state
- React Flow's `useReactFlow` hook provides programmatic control for fit-to-view, zoom-to-node, and viewport manipulation
- Custom edge components show data type compatibility indicators and can be clicked for edge configuration

## Related Decisions

- [ADR-007](007-react-typescript-frontend.md) - React 18 is required for React Flow to function
- [ADR-009](009-zustand-state-management.md) - Zustand manages the graph state (nodes, edges) that React Flow renders
- [ADR-004](004-custom-dag-graph-engine.md) - The React Flow graph data model maps directly to the backend DAG engine's input format

## References

- https://reactflow.dev/
- https://github.com/xyflow/xyflow
- https://reactflow.dev/learn/customization/custom-nodes
- https://reactflow.dev/learn/customization/custom-edges
