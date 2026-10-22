# devctx · Visual identity

**Context first. Better decisions.** A field-instrument identity for a CLI and
MCP tool that gathers development signals into structured context for AI agents.
This work changes documentation and presentation, not collector behavior.

## Visual system

| Token | Value | Role |
|---|---|---|
| Mint | `#EDF3EB` | Canvas |
| Forest | `#153C35` | Primary text, rules, mark |
| Lime | `#D4EF76` | Emphasis and convergence points |
| Sage | `#526B5D` | Supporting text |
| Line | `#BDCDBF` | Light dividers |

The wordmark and technical labels use Menlo or a local monospace fallback.
Supporting type uses Avenir Next or a system sans-serif fallback. Fine rules,
inspection marks, and ordered packets suggest collection and clarity without
inventing a monitoring dashboard.

## Assets

| File | Purpose | Source |
|---|---|---|
| `devctx-banner.png` | README header, 1600 × 800 | Browser render of `banner.html` |
| `banner.html`, `brand.css` | Editable banner and shared design tokens | HTML/CSS |
| `images/mark.svg` | Converging-signal packet mark | Editable SVG |
| `images/context-hero.webp` | Four-source context field kit | AI-generated, locally optimized |
| `devctx-compare.png` | Separate checks vs one snapshot | AI-generated infographic |
| `devctx-arch.png` | Collectors, hints, JSON, CLI, and MCP | AI-generated infographic |
| `brand.html` | Responsive visual guide with text equivalents | HTML/CSS |

The generated artwork is conceptual. It is not a live snapshot, a measured
benchmark, or evidence of a guaranteed performance improvement. All example
project data in the documentation is fictitious. No captured private machine
state is needed for these assets.

## Preview and edit

Open `docs/brand.html` directly in a browser. Assets and styles are local; no
server, JavaScript build, or remote font request is required. Infographic content
also appears as README and preview-page text.

To regenerate the banner from the repository root, with `agent-browser` installed:

```bash
root="$(pwd)"
export AGENT_BROWSER_SESSION="${AGENT_BROWSER_SESSION:-$(agent-browser session id --scope worktree --prefix devctx-brand)}"
agent-browser set viewport 1600 800
agent-browser open "file://$root/docs/banner.html"
agent-browser wait --fn 'Array.from(document.images).every(img => img.complete && img.naturalWidth > 0)'
agent-browser screenshot "$root/docs/devctx-banner.png"
agent-browser close
```

The committed PNG fixes the rendered banner layout across GitHub clients; local
font fallback may change regeneration on a different operating system. Diagram
text is baked into the infographic images. Check updated diagrams against
`devctx/cli.py` and the collectors rather than editing only their text captions.
