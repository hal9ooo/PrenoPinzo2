# Modernization (Native-First) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize PrenoPinzo2 UX/UI by replacing heavy Bootstrap components with native HTML5 APIs and improving fluidity.

**Architecture:** Implementation of a "Native-First" strategy using `<dialog>` for modals, Popover API for overlays, View Transitions API for smooth HTMX swaps, and Container Queries for adaptive layouts.

**Tech Stack:** Django (Backend), HTMX (AJAX/Transitions), Native HTML5 APIs (Dialog, Popover), CSS (Container Queries).

**Spec:** `PrenoPinzo2/docs/superpowers/specs/2026-09-01-modernization-native-first-design.md`

## Global Constraints
*   Maintain existing Django functionality and logic.
*   Ensure backward compatibility for all users (graceful degradation).
*   No new heavy JS libraries unless absolutely necessary.

---

### Task 1: Implement View Transitions with HTMX

**Files:**
- Modify: `PrenoPinzo2/bookings/templates/base.html` (Add transition logic)

**Interfaces:**
- Consumes: HTMX events (`htmx:beforeSwap`, `htmx:afterSwap`)
- Produces: Smooth visual transitions between page states.

- [ ] **Step 1: Write the failing test/verification script**
    Since this is a visual transition, we verify by inspecting if the transition class is applied during an HTMX swap in the browser console (simulated).

```javascript
// Verification snippet for console
document.body.addEventListener('htmx:beforeSwap', () => {
  console.log('Transition starting...');
});
```

- [ ] **Step 2: Implement View Transitions in base.html**
    Wrap the HTMX swap logic with `document.startViewTransition`.

```javascript
// Implementation snippet for base.html
document.body.addEventListener('htmx:beforeSwap', (event) => {
    if (!document.startViewTransition) return; // Fallback if not supported

    const oldContent = document.body;
    event.preventDefault(); // Stop the actual swap to control it

    document.startViewTransition(() => {
        // Execute the original HTMX swap manually or via event
        event.detail.xhrRequest ? 
            event.detail.xhrRequest.send() : 
            fetch(event.detail.target.getAttribute('hx-post') || event.detail.target.getAttribute('hx-get'), {
                method: (event.detail.currentModifiers?.method || 'GET'),
                headers: {'X-CSRFToken': getCookie('csrftoken')}
            }).then(response => response.text()).then(html => {
                event.detail.target.innerHTML = html;
            });
    });
});
```

- [ ] **Step 3: Verify smoothness**
    Run the app and navigate between Dashboard and Calendar. Ensure no "jumps" occur.

- [ ] **Step 4: Commit**
```bash
git add PrenoPinzo2/bookings/templates/base.html
git commit -m "feat: implement view transitions with HTMX"
```

### Task 2: Migrate Modals to `<dialog>`

**Files:**
- Modify: `PrenoPinzo2/bookings/templates/base.html` (Add global dialog container)
- Modify: All templates using Bootstrap modals (e.g., `profile.html`, `chat.html`)

**Interfaces:**
- Consumes: User interactions (clicks).
- Produces: Native `<dialog>` elements in the DOM.

- [ ] **Step 1: Write minimal implementation for base.html dialog container**

```html
<!-- Add to base.html before closing body -->
<dialog id="app-modal" class="modal-style">
    <div class="modal-content">
        <button id="close-modal" aria-label="Close">×</button>
        <div id="modal-body"></div>
    </div>
</dialog>
```

- [ ] **Step 2: Implement JS controller for the dialog**

```javascript
const modal = document.getElementById('app-modal');
function openNativeModal(contentHtml) {
    document.getElementById('modal-body').innerHTML = contentHtml;
    modal.showModal();
}
// Add event listener to close button
document.getElementById('close-modal').addEventListener('click', () => modal.close());
```

- [ ] **Step 3: Migrate one specific view (e.g., Profile Edit)**
    Replace the Bootstrap Modal HTML in `profile.html` with a call to `openNativeModal`.

- [ ] **Step 4: Commit**
```bash
git add .
git commit -m "feat: migrate modals to native <dialog>"
```

### Task 3: Implement Popover API for Notifications/Chat Badges

**Files:**
- Modify: `PrenoPinzo2/bookings/templates/base.html` (Add popover elements)

**Interfaces:**
- Consumes: Chat message arrivals via WebSocket or HTMX polling.
- Produces: Native popovers appearing near the chat badge.

- [ ] **Step 1: Add popover container to base.html**

```html
<div id="chat-popover" popover class="chat-popover">
    <div id="popover-content"></div>
</div>
```

- [ ] **Step 2: Implement Popover trigger in JS**

```javascript
function showChatPopover(message) {
    const popover = document.getElementById('chat-popover');
    document.getElementById('popover-content').innerHTML = message;
    popover.showPopover();
}
```

- [ ] **Step 3: Commit**
```bash
git add PrenoPinzo2/bookings/templates/base.html
git commit -m "feat: implement chat popovers using Popover API"
```

### Task 4: Implement Container Queries for Dashboard Cards

**Files:**
- Modify: `PrenoPinzo2/bookings/static/bookings/app.css` (or relevant CSS file)

**Interfaces:**
- Consumes: Changes in parent container size.
- Produces: Adaptive card layouts.

- [ ] **Step 1: Define Container Context in CSS**

```css
.dashboard-card {
    container-type: inline-size;
    container-name: card;
}
```

- [ ] **Step 2: Implement Responsive Layout via @container**

```css
@container card (max-width: 300px) {
    .card-layout {
        flex-direction: column;
    }
    .card-image {
        display: none;
    }
}
```

- [ ] **Step 3: Commit**
```bash
git add PrenoPinzo2/bookings/static/bookings/app.css
git commit -m "feat: implement container queries for dashboard cards"
```
