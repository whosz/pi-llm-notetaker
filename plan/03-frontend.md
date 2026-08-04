# Stage 3 — Frontend (web page)

## Goal

A complete, lightweight web interface served from the Pi: adding notes, browsing by
type, checkbox-driven lists. Comfortable on a phone (that's the main way it'll be used!).

## Stack (reminder from CLAUDE.md)

Jinja2 + HTMX + [Basecoat](https://basecoatui.com) — a vanilla HTML/CSS/JS port of the
shadcn/ui design system (Tailwind-based), used purely as vendored static assets.
**No node, no bundler, no CDN at runtime, no React anywhere:**

1. During development, pull the pre-built files from the `basecoat-css` npm package (or its
   CDN build, downloaded once) — `basecoat.css` (or one of its style packs) and the small
   `all.min.js` behavior script.
2. Commit them into `app/static/` next to `htmx.min.js`, exactly like every other vendored asset.
3. Copy the handful of Jinja component macros Basecoat ships (`dialog`, `dropdown-menu`,
   `popover`, `select`, `tabs`, `toast`, …) into `app/templates/basecoat/` and `{% import %}`
   them from the real templates. Simpler components (button, card, badge, input) are just
   HTML tags with Basecoat's CSS classes — no macro needed.

The result looks like a shadcn/ui app but is still 100% server-rendered Jinja2 + HTMX;
nothing changes about the "no build step on the Pi" constraint.

## Tasks

1. Base layout (`templates/base.html`):
   - mobile-first, a big "➕ New note" field (Basecoat `input`/`textarea` styles) always on top
   - navigation using Basecoat's `tabs` or `sidebar` component: All · Shopping · Tasks · Meetings · Quotes · Ideas
   - dark/light theme following `prefers-color-scheme` (Basecoat ships both out of the box)
2. Home page `/`:
   - add-note form (textarea + submit via HTMX, no reload)
   - a freshly added note appears as a "⏳ processing…" card (Basecoat `card` + `badge`) and
     **polls** `GET /api/notes/{id}` every 2 s (htmx trigger `every 2s`) until it's `processed` —
     then the card swaps to its final form
   - list of recent notes ("load more" pagination, Basecoat `button` variant `outline`)
3. Note cards by type (partial templates, all built on the Basecoat `card` component):
   - `shopping`: items with checkboxes (Basecoat `checkbox`, PATCH via HTMX), strikethrough when checked
   - `meeting`: date/time + sync status `badge` (after stage 4)
   - `quote`: highlighted typography
   - `task`: due date + completion checkbox
4. Views `/lists`, `/quotes`, `/ideas` — filtered by type
5. Search (Basecoat `input`, `hx-trigger="keyup changed delay:300ms"` → `q` filter)
6. Edit and delete a note (inline; delete confirmation uses the Basecoat `dialog` macro)
7. Error handling: `status=error` card with a "🔁 Retry" `button`
   (re-queues it for LLM processing); transient errors surface via the Basecoat `toast` macro

## Tips

- HTMX: `hx-post`, `hx-target`, `hx-swap="outerHTML"` patterns, polling —
  📚 <https://htmx.org/docs/> and examples at <https://htmx.org/examples/>
- Basecoat: 📚 <https://basecoatui.com> — component gallery + the Jinja template snippets
  for the macro-based components (dialog, dropdown-menu, popover, select, tabs, toast)
- UI endpoints return **HTML fragments** (partials), not JSON
- Zero JS beyond htmx + Basecoat's own `all.min.js` (call `window.basecoat.initAll()` after
  an HTMX swap injects new component markup, per Basecoat's JS lifecycle docs)

## Acceptance criteria

- [ ] Full flow from a phone: typing "buy milk" → ⏳ card → shortly after, a shopping
      list with a checkbox, with no page reload
- [ ] Checking off an item survives a page refresh (state stored in the DB)
- [ ] All note types have readable cards; search and filters work
- [ ] The site works with the internet disabled (all assets, including Basecoat, are local)
- [ ] Lighthouse mobile: reasonable usability (no need to be fanatical — it's a home site)
