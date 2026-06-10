# Pagination — Visual QA Checklist

> **Why this doc exists.** The pagination styling is enforced by
> `tests/test_pagination_css.py`, which parses the source of
> `core/static/core/css/app.css` and asserts the presence of the
> BEM blocks, design-token usage, focus-visible ring, disabled state,
> and responsive hiding of numeric links. Visual outcomes that
> cannot be asserted from a regex — pill shape, hover lift, focus
> glow, alignment, truncation behaviour — must be checked by a
> human in a browser. This checklist is the contract for that
> manual pass.

## Where the partial lives

- Template: `core/templates/core/_pagination.html`
- Stylesheet: `core/static/core/css/app.css` — search for the
  `PAGINATION — pill bar` comment block
- Templatetag: `core/templatetags/pagination_tags.py`
  (`page_range_window`, `page_query`)
- Tests: `tests/test_pagination_tags.py`, `tests/test_pagination_partial.py`,
  `tests/test_pagination_css.py`

## What the assertions already cover (no need to re-check)

| Concern | Asserted by |
|---|---|
| `.pagination` flex container, centered | `TestPaginationLayout` |
| `.pagination__link` is pill-shaped (`border-radius: 999px`) | `TestPaginationPillDesign` |
| `.pagination__link--current` uses `var(--accent)` | `TestPaginationDesignTokens` |
| `.pagination` references a design token | `TestPaginationDesignTokens` |
| Hover, focus-visible, disabled blocks exist | `TestPaginationInteractions` |
| No `lift-in`, no `animation` on `.pagination` | `TestPaginationNoEntranceAnimation` |
| Numeric links hide, ellipsis hides, meta shows at ≤640px | `TestPaginationResponsive` |
| Pagination partial renders BEM classes, ARIA, hx-get/target | `tests/test_pagination_partial.py` |
| `page_range_window` returns expected windows | `tests/test_pagination_tags.py` |

## Manual checks — Desktop (≥641px)

Run the dev server and open any paginated list view (e.g. the
access-grants or audit-log list).

### Pills
- [ ] Each page number renders as a pill with `border-radius: 999px`
- [ ] All pills are vertically aligned in a single row, centered
- [ ] The gap between pills is consistent (6px)
- [ ] Prev/Next links have the same height as numeric pills

### Current page
- [ ] The current page pill uses the cyan accent gradient
- [ ] The current pill text is dark (high contrast)
- [ ] Hovering the current pill does **not** lift it (cursor: default)

### Hover
- [ ] Hovering a numeric pill: text becomes bright, border brightens,
  pill translates up by 1px
- [ ] Hovering Prev/Next: same behaviour
- [ ] Hovering the disabled Prev (page 1) or disabled Next (last page):
  no effect, cursor stays default

### Focus (keyboard)
- [ ] Tab into the pagination: the first focusable link shows a
  glow ring (`box-shadow: 0 0 0 4px rgba(110,231,255,.15)`)
- [ ] Tab cycles through all focusable links in order
- [ ] The current page (rendered as `<span>`) is **not** focusable
- [ ] The disabled Prev/Next (rendered as `<span>`) are **not**
  focusable — Tab skips them

### Ellipsis
- [ ] On a long paginator (e.g. page 5 of 20) an ellipsis (`…`)
  appears between the first pill and the window
- [ ] The ellipsis is not focusable
- [ ] The ellipsis colour matches the muted token

### No entrance flicker
- [ ] Trigger a page change (click a number pill or Prev/Next)
- [ ] The pagination bar must **not** fade in or lift in on the
  swap — only the list content above should change
- [ ] Refresh the page; the pagination bar should appear in place
  without a lift-in animation (the surrounding card may still
  animate, the pagination `<nav>` itself must not)

## Manual checks — Mobile (≤640px)

Resize the viewport to 640px (or use dev-tools device emulation
at iPhone SE 375px).

### Layout
- [ ] Numeric page pills are hidden
- [ ] The ellipsis is hidden
- [ ] The "Página X de Y" meta line is visible
- [ ] Prev and Next pills remain visible, at the outer edges
- [ ] Prev + Next + meta line are centered, with a sensible gap

### Interaction on mobile
- [ ] Tap Prev: navigates to previous page (HTMX swap or full reload,
  depending on view wiring)
- [ ] Tap Next: navigates to next page
- [ ] The meta text updates to reflect the new page number after
  the swap

## Manual checks — Accessibility

### Keyboard
- [ ] From the search input, press Tab. The first interactive
  pagination control (Prev) receives focus
- [ ] Shift+Tab returns focus to the previous control
- [ ] Pressing Enter on a focused pill triggers the same navigation
  as a click

### Screen reader (VoiceOver / NVDA)
- [ ] Land on the pagination region: it is announced as
  "Paginación" (the `aria-label` of the `<nav>`)
- [ ] Each link is announced with "Página N"
- [ ] The current page is announced as "Página N, current page"
  (`aria-current="page"`)
- [ ] The disabled prev/next is announced as "Página anterior,
  dimmed" or similar (`aria-disabled="true"`)
- [ ] The ellipsis is **not** announced (`aria-hidden="true"`)
- [ ] The meta line "Página X de Y" is announced as a polite live
  region update after a swap (it carries `role="status"` and
  `aria-live="polite"`)

### Reduced motion
- [ ] Enable OS-level "Reduce motion"
- [ ] Hover a pill — it should still change colour but must **not**
  translate up
- [ ] Navigate — no flicker, no entrance animation

### Colour contrast (eyeball — formal audit optional)
- [ ] Default pill text on background: readable (≥4.5:1)
- [ ] Current page dark text on cyan gradient: high contrast
- [ ] Disabled pill: visibly dimmer, not invisible

## Recording results

Tick the boxes in the **commit message** for the visual-QA commit
(Commit 3 in `style/pagination-redesign`). If any item fails, do
**not** open the PR — open a follow-up issue and link it from the
PR description instead.
