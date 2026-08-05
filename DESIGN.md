---
name: Aegis-KeePass OTP Sync
description: Localhost operate-mode UI for reviewing Aegis→KeePass OTP merges with cool paper/dark desk surfaces and a restrained blue trust accent.
colors:
  primary: "#2563eb"
  primary-hover: "#1d4ed8"
  primary-fg: "#2563eb"
  primary-fg-hover: "#1d4ed8"
  primary-soft: "#eff6ff"
  brand-indigo: "#6366f1"
  success: "#047857"
  success-fill: "#047857"
  success-bg: "#ecfdf5"
  danger: "#dc2626"
  danger-hover: "#b91c1c"
  danger-fg: "#dc2626"
  danger-bg: "#fef2f2"
  warning: "#d97706"
  warning-bg: "#fffbeb"
  on-warning: "#1a1f2e"
  bg: "#f4f6f9"
  surface: "#ffffff"
  slate-panel: "#f8fafc"
  text: "#1a1f2e"
  muted: "#5c6578"
  border: "#dde3ed"
  secondary-btn: "#eef2f7"
  secondary-btn-hover: "#e2e8f0"
  toast-ink: "#1e293b"
  on-accent: "#ffffff"
  on-success: "#ffffff"
  toast-success-bg: "#047857"
  toast-success-fg: "#ffffff"
  toast-danger-bg: "#b91c1c"
  toast-danger-fg: "#ffffff"
  empty-field: "#5c6578"
  table-stripe: "#fafbfd"
  conflict-border: "#fcd34d"
  badge-matched-bg: "#bbf7d0"
  badge-matched-fg: "#14532d"
  badge-unmatched-bg: "#fecaca"
  badge-unmatched-fg: "#7f1d1d"
  badge-modified-bg: "#fde68a"
  badge-modified-fg: "#78350f"
  dark-bg: "#0f1419"
  dark-surface: "#1a2332"
  dark-text: "#e8edf5"
  dark-muted: "#9aa6b8"
  dark-border: "#2d3a4d"
  dark-primary: "#2563eb"
  dark-primary-hover: "#1d4ed8"
  dark-primary-fg: "#60a5fa"
  dark-primary-fg-hover: "#93c5fd"
  dark-primary-soft: "#1e3a5f"
  dark-success: "#34d399"
  dark-success-fill: "#047857"
  dark-danger: "#dc2626"
  dark-danger-fg: "#f87171"
  dark-warning: "#fbbf24"
  dark-on-warning: "#1a1f2e"
  dark-toast-success-bg: "#34d399"
  dark-toast-success-fg: "#052e1c"
  dark-toast-danger-bg: "#f87171"
  dark-toast-danger-fg: "#1a0505"
  dark-empty-field: "#9aa6b8"
  dark-slate-panel: "#151d2a"
  dark-brand-indigo: "#818cf8"
  dark-table-stripe: "#161e2c"
  dark-conflict-border: "#a16207"
  dark-toast-ink: "#0b1220"
  dark-secondary-btn: "#243044"
  dark-secondary-btn-hover: "#2e3d55"
  dark-badge-matched-bg: "#14532d"
  dark-badge-matched-fg: "#bbf7d0"
  dark-badge-unmatched-bg: "#7f1d1d"
  dark-badge-unmatched-fg: "#fecaca"
  dark-badge-modified-bg: "#78350f"
  dark-badge-modified-fg: "#fde68a"
typography:
  brand:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "normal"
  complete:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "1.45rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "normal"
  modal-title:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "1.1rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "normal"
  title:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "1.35rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "normal"
  body:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  control:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  input:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "normal"
  label:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  hint:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 400
    lineHeight: 1.35
    letterSpacing: "normal"
  compact:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "0.82rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "normal"
  micro:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "0.78rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "0.04em"
  badge:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "normal"
  tiny:
    fontFamily: "\"Segoe UI\", system-ui, -apple-system, sans-serif"
    fontSize: "0.72rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.04em"
rounded:
  xs: "4px"
  sm: "8px"
  md: "12px"
  brand: "10px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "28px"
  "2xl": "48px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  button-secondary:
    backgroundColor: "{colors.secondary-btn}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  button-secondary-hover:
    backgroundColor: "{colors.secondary-btn-hover}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  button-danger-hover:
    backgroundColor: "{colors.danger-hover}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  button-sm:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.sm}"
    padding: "6px 12px"
  theme-toggle:
    backgroundColor: "{colors.slate-panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
    height: "40px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "24px 28px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "10px 14px"
  filter-btn:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "7px 14px"
  filter-btn-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.sm}"
    padding: "7px 14px"
  brand-mark:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.brand}"
    size: "44px"
  drop-zone:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "28px 16px"
  drop-zone-active:
    backgroundColor: "{colors.primary-soft}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "28px 16px"
  drop-zone-filled:
    backgroundColor: "{colors.success-bg}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "28px 16px"
  stat-chip:
    backgroundColor: "{colors.slate-panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "8px 14px"
  badge-matched:
    backgroundColor: "{colors.badge-matched-bg}"
    textColor: "{colors.badge-matched-fg}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  badge-unmatched:
    backgroundColor: "{colors.badge-unmatched-bg}"
    textColor: "{colors.badge-unmatched-fg}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  badge-modified:
    backgroundColor: "{colors.badge-modified-bg}"
    textColor: "{colors.badge-modified-fg}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  modal:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    width: "620px"
---

# Design System: Aegis-KeePass OTP Sync

## Overview

**Creative North Star: "The Local Vault Desk"**

A cool operate console for a single trusted localhost session. Surfaces stay quiet—paper-bright by day, deep slate desk by night—with one blue accent so the job (upload → review → download) stays legible and the security story never competes with chrome. The AK mark is the only ornamental signal; everything else reads as a careful toolshed UI for encrypted backups.

Density favors task clarity over marketing: short headers, muted supporting copy, compact toolbars, and a data table as the review workspace. Status color (green / red / amber) carries match state; the primary blue is reserved for progress, focus, and the decisive actions that move the session forward. Visual restraint is the trust model: no spectacle, no decorative depth theater, no brand voice louder than the product name.

Theme preference defaults to the OS (`prefers-color-scheme`). When the OS does not define a preference, the desk opens in dark. Users can cycle System → Light → Dark from the header. Confirmed visual rejections: no purple-washed marketing gradients across the page, no heavy multi-layer glow, no emoji as system iconography, and no composition that treats the first viewport as a landing hero. This is an app shell with a three-step flow, not a promotional surface.

**Key Characteristics:**
- Dual theme: cool paper (`bg` / `surface`) or dark desk (`dark-bg` / `dark-surface`) with one soft ambient shadow
- One primary blue accent plus semantic green / red / amber for match and risk states
- Single system UI type stack for all roles; hierarchy comes from size and weight, not family contrast
- Operate-mode density: header + step rail + theme control, focused upload card, full-width review table
- AK vault-shield logo mark (Trust Blue → indigo, white **AK**) as the only identity ornament in chrome; local PNG under `app/static/img/`

## Colors

A cool neutral field with a trustworthy blue accent and clear semantic status tints for match outcomes.

### Primary
- **Trust Blue** (`primary`): Solid fills for primary actions, active step numerals, filter selection, and confidence pills. Paired with `on-accent` at WCAG AA (≥4.5:1). Keep it scarce relative to neutrals so CTAs stay obvious.
- **Trust Blue Deep** (`primary-hover`): Hover/pressed deepen of primary filled controls.
- **Trust Blue Foreground** (`primary-fg` / `primary-fg-hover`): Links, drop-file names, step labels, and icon accents on canvas/surface. In dark theme this is a lighter blue than the fill so body-size text stays AA on slate.
- **Ice Blue Soft** (`primary-soft`): Hover/drag affordance on drop zones and suggested picker rows—tint, not fill dominance.
- **Brand Indigo** (`brand-indigo`): Trailing stop of the AK mark gradient only; not a page-wide secondary palette.

### Neutral
- **Cool Paper** (`bg`): Page canvas behind all chrome.
- **Pure Surface** (`surface`): Cards, header bar, modals, inputs, inactive filter chips.
- **Slate Panel** (`slate-panel`): Recessed chips, table header band, security note / progress wells.
- **Ink Navy** (`text`): Primary readable ink on surfaces.
- **Slate Mute** (`muted`): Supporting copy, step idle labels, table header labels, meta lines, placeholders.
- **Empty Field** (`empty-field`): Italic “(empty)” detail values; AA against `surface`.
- **Hairline Border** (`border`): Card edges, table rules, idle step rings, dashed drop outlines.
- **Secondary Chip** (`secondary-btn` / `secondary-btn-hover`): Quiet secondary button fills.
- **Toast Ink** (`toast-ink`): Default toast ground when not success/error tinted.
- **On Accent** (`on-accent`): Text/icons on filled primary and danger controls.

### Semantic (status, not decorative secondary brand)
- **Match Green** / **Match Green Fill** / **Match Green Soft** (`success` / `success-fill` / `success-bg`): Surface-readable status text, solid completed-step / progress check fills (`on-success` ink), and soft matched-row wells.
- **Risk Red** / **Risk Red Soft** (`danger` / `danger-bg`): Destructive actions and error chrome; `danger-fg` is the brighter dark-theme accent when red is used as foreground rather than a fill.
- **Caution Amber** / **On Warning** / **Caution Amber Soft** (`warning` / `on-warning` / `warning-bg`): Modified-row inset mark, low-confidence pills, OTP/linked micro-badges, conflict callouts—amber always carries dark ink (`on-warning`).
- **Toast Success / Danger** (`toast-success-*` / `toast-danger-*`): Dedicated toast pairs so light and dark each meet AA without forcing body semantic fills to the same luminance.

### Named Rules
**The One Accent Rule.** Trust Blue is the only brand accent on a screen; green, red, and amber speak status only. Do not invent a second brand hue for decoration.

**The Status-Means-State Rule.** Semantic fills appear when match, conflict, or progress state changes—not as ambient section coloring.

**The Fill vs Foreground Rule.** Solid CTA fills use `primary` / `danger` / `success-fill` with `on-accent` or `on-success`. Text and icons on paper/desk surfaces use `*-fg` (or surface-tuned `success`) so dark theme never puts mid-luminance fills behind white labels or pastel labels on slate.

## Typography

**Display Font:** none distinct — product naming uses the same UI stack as body (system UI face).
**Body Font:** "Segoe UI", system-ui, -apple-system, sans-serif
**Label/Mono Font:** same stack (no mono face in the build)

**Character:** A single pragmatic system UI face. Authority comes from weight and uppercase micro-labels, not from a display pairing. Suitable for dense review tables and credential forms.

### Hierarchy
- **Title** (700, ~1.25–1.45rem, tight): Brand product name in the header (`1.25rem`); section heads in cards (`1.35rem`); completion head slightly larger (`1.45rem`). No separate marketing display size.
- **Body** (400, `1rem`; line-height `1.5` light / `1.55` dark with slight tracking): Form copy, modal body, supporting paragraphs capped near `65ch`.
- **Label** (600, `0.875rem`): Field labels, step text, table cells, theme control, filter chips. Button / drop titles use control size (`0.9rem` / 600).
- **Micro** (700, `0.72–0.78rem`, uppercase, `0.04em` tracking): Table column headers and stat-chip labels. Stats and confidence use `tabular-nums`. Supporting muted lines sit at `0.8–0.875rem` / 400 without uppercase.

### Named Rules
**The One Face Rule.** All roles share the system UI stack. Do not introduce a decorative display family for “brand presence”; the AK mark carries identity.

**The Micro-Label Rule.** Uppercase + tracked micro type is reserved for tabular/stat metadata—not for section kickers or marketing eyebrows.

## Layout

Operate-mode app shell: full-width header on the paper field, content in a centered `1200px` container with horizontal padding `24px` (`--space-lg`) and bottom padding `48px` (`--space-2xl`), each side expanded with `env(safe-area-inset-*)` when present. Header is a three-column grid: brand | centered step rail | right-justified theme control. Below `900px`, steps wrap full-width under brand + theme; the review toolbar stacks and search/actions go full-width. Viewport meta uses `viewport-fit=cover` for notched devices.

Upload is a single centered work card (`max-width: 760px`) with a two-column drop grid (`16px` gap) that collapses to one column at `640px`. Supporting copy and security notes stay within a `65ch` measure. Review is denser: a toolbar grid of stats | (find cluster + action cluster), then a full-width table card with slightly tighter cell padding—keep the table horizontally scrollable on narrow screens rather than cardifying rows. Vertical rhythm uses the documented space scale (`4 / 8 / 16 / 24 / 28 / 48`). Footer is a quiet centered meta row under a hairline.

On coarse pointers (`pointer: coarse`), interactive controls use a `44px` minimum hit size (buttons, filters, theme toggle, info icons, password/search fields at `1rem` to avoid iOS focus zoom). Fine-pointer desktop density stays compact.

**The Task-First Density Rule.** Prefer compact toolbars and table density over spacious marketing sections. One job per view: upload form, or match review, or download confirmation.

## Elevation & Depth

Hybrid of hairline borders and one soft ambient lift. Cards, modals, and toasts share a single dual-stop shadow; the header uses a subtler 1px under-edge. Depth is structural (separating work surfaces from the paper field), not theatrical.

### Shadow Vocabulary
- **Surface Lift** (`box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 8px 24px rgba(15, 23, 42, 0.06)`): Cards, modals, toasts.
- **Header Hair** (`box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04)`): Site header only.
- **Focus Ring Soft** (`outline: 2px solid rgba(37, 99, 235, 0.25)` on inputs; `box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12)` on active progress steps): State, not rest elevation.
- **Modal Scrim** (`background: rgba(15, 23, 42, 0.45)`): Overlay behind dialogs.

### Named Rules
**The One Shadow Rule.** Reuse the shared surface-lift token for elevated panels. Do not stack unique dramatic shadows per component.

**The Flat-Rest Controls Rule.** Buttons and chips are flat fills; elevation belongs to containing surfaces, not to every control.

## Shapes

Gently curved tool UI: work surfaces at `12px`, controls and inputs at `8px`, the AK mark at a slightly tighter `10px` square. Status badges and confidence pills are fully rounded (`999px`). Step numbers and progress icons are circles. Drop zones use a `2px` dashed border that solidifies into semantic color when hovered or filled. Conflict and security callouts keep the soft `8px` radius with a left or full border accent—not clipped illustration shapes.

**The Soft-Tool Radius Rule.** Prefer `8px` controls and `12px` panels. Reserve pills for status chips; do not pill primary buttons.

## Components

### Buttons
Quiet, filled, no border. Medium weight labels, `8px` corners, `10px 18px` padding (`6px 12px` for small; `44px` min-height on `pointer: coarse`).
- **Shape:** Gently curved (`8px`)
- **Primary:** Trust Blue fill, white label; hover deepens to Trust Blue Deep (`0.15s`)
- **Secondary:** Cool gray fill (`secondary-btn`), ink label; hover `secondary-btn-hover`
- **Danger:** Risk Red fill for irreversible confirmations; hover Risk Red Deep (`danger-hover`)
- **Disabled:** `opacity: 0.55`, not-allowed cursor

### Chips
- **Stat chips:** Slate panel fill, stacked uppercase micro label + strong value; success/danger variants swap soft semantic backgrounds.
- **Filter buttons:** Bordered white chips; active fills Trust Blue with white text; `aria-pressed` mirrors the active chip; active focus uses a white ring so the outline stays visible on the blue fill. Status set: All / Matched / Unmatched / No Aegis UUID (matched KeePass targets lacking an `AegisUUID` marker).
- **Status badges:** Pill capsules with solid tint fills (matched / unmatched / modified). Confidence uses primary (or warning + `on-warning` when low). OTP/linked micro-badges are compact amber pills (`4px` radius) with `on-warning` ink.

### Cards / Containers
- **Corner Style:** `12px`
- **Background:** Pure Surface on Cool Paper
- **Shadow Strategy:** Surface Lift (see Elevation)
- **Border:** `1px` Hairline Border
- **Internal Padding:** Header `24px 28px` top; form body `28px` sides/bottom; toolbar `18px 20px`

### Inputs / Fields
- **Style:** Full-width, white fill, `1px` border, `8px` radius, `10px 14px` padding, ~`0.95rem` text (`1rem` / `44px` min-height on coarse pointers)
- **Password fields:** In-control eye toggle (`Show password` / `Hide password`, `aria-pressed`); right padding reserves the hit target; focus ring wraps the whole control via `:focus-within`
- **Focus:** Border shifts to Trust Blue; soft blue outline ring (`rgba(37, 99, 235, 0.25)` light / stronger alpha in dark)
- **Invalid:** `[aria-invalid="true"]` uses Risk Red border (and danger-soft fill on drop zones); focus ring follows danger
- **Labels:** `0.875rem` / 600 above field with `6px` gap; search fields use a visually hidden `<label>` when the placeholder alone would be insufficient
- **File drop inputs:** Visually hidden (still focusable), not the HTML `hidden` attribute

### Navigation
- **Chrome:** Surface header with bottom hairline + hair shadow; brand row left, step rail center, theme control right
- **Steps:** Muted label + circled number; active = Trust Blue fill/ring; done = Match Green Fill (`success-fill`) with `on-success` ink
- **Separators:** `24×2px` border-colored bars between steps
- **Footer:** Centered muted version + `primary-fg` repo link

### Brand Mark (signature)
- **Asset:** local `app/static/img/logo.png` (approved option A vault-shield with white **AK**); favicons in the same folder
- **Shape:** `44×44` display, `10px` radius clip on the header `<img>`
- **Fill:** Trust Blue → Brand Indigo vault plate with white **AK** monogram (baked into the PNG)
- **Role:** Sole identity ornament beside the product name; do not repeat as decorative page motifs; do not load from a CDN

### Drop Zone (signature)
- **Shape:** Dashed `2px` border, `8px` radius, centered stack, `28px 16px` padding; `position: relative` for the visually hidden file input
- **Idle → Hover/Drag:** Border and Ice Blue Soft fill; `:focus-within` shows the focus ring for keyboard file selection
- **Filled:** Match Green border + soft success fill; filename in Trust Blue Foreground (`primary-fg`)
- **Motion:** `0.15s` border/background transitions

### Review Table
- **Header:** Sticky slate/surface band within a `max-height: min(70vh, 720px)` scrollport; uppercase micro labels; caption is visually hidden for assistive tech
- **Rows:** Alternating near-white stripe; matched rows success-soft; modified rows amber inset bar (`3px`); cell text uses `overflow-wrap: anywhere`
- **Actions:** Compact button/gap clusters per row (wider gaps / `44px` icons on coarse pointers)

### Modal
- **Shape:** Surface Lift card, `12px`, max-width `620px`, max-height `85vh` (safe-area aware on small screens), column flex with scrollable body
- **Chrome:** Header/footer separated by hairlines; scrim from theme (`--scrim`); Escape dismisses (blocked while save is busy); Tab cycles within the top dialog; conflict stacks above the picker; closed overlays stay `aria-hidden="true"`
- **Picker rows:** Bordered `8px` results; hover/suggested Ice Blue Soft; linked Caution Amber Soft
- **Save / End session:** In-app confirms (never `window.confirm`); save confirm transitions into the same progress step list used on upload

### Toast
- Shared `toast.js` helper; fixed bottom-right panel (safe-area inset); default Toast Ink, or dedicated `toast-success-*` / `toast-danger-*` pairs; `8px` radius, Surface Lift, control-size type
- **Motion:** Short opacity + `translateY(6px→0)` entrance (`--motion-fast` / `--ease-out`); replacing a visible toast clears the hide timer and restarts the entrance; instant under `prefers-reduced-motion`

### Upload Progress
- Ordered step list with pending → active → done → error; active step uses a spinning ring as the sole looping cue; error shows a white X on Risk Red
- **Reduced motion:** Solid Trust Blue ring + Ice Blue Soft fill (no infinite spin); step opacity/border transitions remain
- **Save progress:** Same step chrome inside the save modal (`cleanup` → `apply` → `build` → `download`) driven by `/api/save/process` + `/api/save/download`

### Security Note
- Slate panel well, `8px` radius, hairline border, Ice Blue Soft fill, muted compact copy—trust messaging stays quiet and inline

### Theme Toggle
- Right-justified in the header grid after brand + steps; cycles System → Light → Dark
- Flat slate-panel control with a half-filled circle (light/dark) icon plus a short mode label (`System` / `Light` / `Dark`) so the control reads as appearance, not a device glyph; `44px` min-height on coarse pointers

### Motion (operate)
Shared tokens: `--motion-fast` (`0.15s`) for control/drop-zone/toast feedback; `--motion-step` (`0.2s`) for progress-step state; `--ease-out` (`cubic-bezier(0.16, 1, 0.3, 1)`) for toast arrival. The upload spinner is the only infinite animation.

**The Feedback-Not-Spectacle Rule.** Animate cause→result (hover, active step, toast). Do not add page-load choreography or scroll reveals. Under `prefers-reduced-motion`, remove loops and entrance transforms; keep short color/opacity state changes.

## Do's and Don'ts

### Do:
- **Do** keep screens task-clear: one primary CTA path (continue / download) in Trust Blue, secondary actions in quiet gray.
- **Do** use semantic green/red/amber only for match, conflict, progress, and risk states.
- **Do** elevate work with the shared Surface Lift card on Cool Paper; keep controls flat.
- **Do** preserve the AK mark + product name as the header identity pair; keep the subtitle as one muted utility line.
- **Do** collapse the upload drop grid to a single column at `640px` and keep the review table horizontally scrollable rather than cardifying every row.
- **Do** use `primary` / `danger` / `success-fill` for solid fills with on-colors, and `*-fg` accents for text on surfaces (Fill vs Foreground Rule).
- **Do** enlarge interactive targets to `44px` when `pointer: coarse`, and honor safe-area insets on notched devices.
- **Do** respect `prefers-reduced-motion` by replacing the progress spinner with a static active indicator—never a global `0.01ms` transition kill.

### Don't:
- **Don't** introduce a second brand accent or wash the page in indigo/purple gradients (indigo stops at the AK mark).
- **Don't** treat system UI type as a decorative display brand face or pair it with an ornamental serif for “premium.”
- **Don't** add marketing kickers/eyebrows, hero compositions, stat-strip landing layouts, or emoji as system iconography for new surfaces.
- **Don't** invent per-component shadow stacks or glow focus; keep both themes on the shared Surface Lift token and flat controls.
- **Don't** use pill radii on primary buttons or turn every container into a floating card; cards wrap jobs, not every label.
- **Don't** load fonts, scripts, stylesheets, or icon kits from a CDN or any remote host; the UI must run offline from assets bundled in the container.
- **Don't** add bounce/elastic easing, scroll-driven reveals, or looping decoration outside the upload progress active step.
