# Design Doc: Modernization of PrenoPinzo2 via Native Web APIs

**Date:** 2026-09-01  
**Status:** Draft (Awaiting User Review)  
**Topic:** UX/UI Modernization (Approccio 1: Native-First)

## 1. Overview
The goal is to modernize the user experience of PrenoPinzo2 by leveraging modern Web APIs. This will reduce reliance on heavy JavaScript libraries for common UI patterns and provide a smoother, "app-like" feel.

## 2. Key Objectives
* **Reduce JS Overhead:** Replace Bootstrap's modal/tooltip logic with native HTML5 elements.
* **Improve Fluidity:** Use the View Transitions API to animate page changes during HTMX swaps.
* **Enhanced Responsiveness:** Implement Container Queries for dashboard components.

## 3. Proposed Changes

### 3.1 Modals $\rightarrow$ `<dialog>` Element
- **Current State:** Using Bootstrap's `.modal` which relies on heavy JS and complex DOM manipulation.
- **Proposed Change:** Replace with the native HTML5 `<dialog>` element.
- **Benefits:** Native focus management, better accessibility (Aria), and significantly less code.

### 3.2 Tooltips/Popovers $\rightarrow$ Popover API
- **Current State:** Using Bootstrap's `popover` or custom JS for small UI overlays.
- **Proposed Change:** Use the native `popover` attribute.
- **Benefits:** Native handling of "top layer" rendering (no z-index hell) and simplified event management.

### 3.3 Page Transitions $\rightarrow$ View Transitions API
- **Current State:** HTMX swaps content instantly, which can feel jarring to users.
- **Proposed Change:** Wrap HTMX `endRequest` events with the View Transitions API (`document.startViewTransition`).
- **Benefits:** Smooth cross-fade or slide animations between views without a full page reload.

### 3.4 Layout $\rightarrow$ Container Queries
- **Current State:** CSS relies on `@media` (viewport width).
- **Proposed Change:** Use `@container` for dashboard cards and complex widgets.
- **Benefits:** Components adapt based on their parent container size, making the layout more robust in split-screen or dynamic grid environments.

## 4. Implementation Plan (High Level)
1.  **Phase 1: Foundation & Transitions.** Set up View Transitions API with HTMX to make all navigations smooth.
2.  **Phase 2: Modal Migration.** Replace the main modal implementation in `base.html` and its derivatives with `<dialog>`.
3.  **Phase 3: Popovers & Tooltips.** Migrate small UI elements to the Popover API.
4.  **Phase 4: Adaptive Layouts.** Refactor dashboard CSS to use Container Queries.

## 5. Risks & Mitigations
* **Browser Compatibility:** While most modern browsers support these, we will ensure graceful degradation (or check compatibility for older versions if required).
* **Complexity of Transitions:** View transitions can be tricky with complex DOM trees; we will start with simple cross-fades.
