# Product

## Register

product

## Users

ML researchers and AI-lab data engineers who curate billion-scale image-text datasets
for vision-language model pretraining, plus AI coding agents scaffolding a filtering
pipeline. Their context: they have noisy web-scraped image-text pairs and need to
filter them down to high-quality shards by image-text alignment — without pulling the
pool onto local disk — and want object storage to be the whole pipeline, from raw pool
to filtered output. They also evaluate B2 as the storage layer for dataset curation.

## Product Purpose

A working implementation of the DataComp filtering workflow (Next.js 16 + React 19 +
Tailwind v4 + shadcn/ui frontend, FastAPI backend) with Backblaze B2 as the sole
storage layer. It streams WebDataset `.tar` shards from B2, scores image-text alignment
with CLIP (open_clip), writes filtered shards + quality metrics back to B2, and exposes
the whole lifecycle — Filter Runs, a scoped Pool Explorer, and a full Bucket Explorer —
in a real UI. Success = a data engineer can seed a pool, run a real CLIP filter, and see
high-quality shards land back in B2 with a measured storage reduction, no second key.

## Maturity and Support Boundary

This is a maintained open-source template/sample, not a complete hosted SaaS product.
It is built with production-minded controls and can be adapted for production use with
caution, but adopters own product-specific validation, security, deployment, and
operations. Repository defects and feature requests go through the public GitHub issue
tracker; B2 account, billing, service, and API questions go through Backblaze Support.
The template/sample itself is not covered by the Backblaze service level agreement,
and no SLA is provided for the repository software.

## Brand Personality

Confident, precise, quietly professional. Voice is direct and free of hype ("filter a
noisy pool to high-quality shards without pulling it locally"). The interface should
feel like a modern developer/ML tool — considered, calm, trustworthy — not a marketing
showpiece. The design carries craft through restraint, letting the data (kept vs
dropped pairs, CLIP scores, storage reduction) be the focus.

## Anti-references

- **Generic AI/SaaS slop.** No gradient text, hero-metric templates, identical
  icon-card grids, tracked uppercase eyebrows, or decorative glassmorphism. These are
  the exact 2026 AI tells this kit exists to help builders avoid.
- **Over-branded / loud.** No heavy brand-color drenching, decorative motion, or flashy
  effects. It is scaffolding to be rebranded, not a hero page.
- **Toy / prototype feel.** No missing states, inconsistent components, or placeholder
  polish. Must read as polished, dependable scaffolding.
- **Enterprise-drab.** No Bootstrap-era gray boxes or dense-but-lifeless admin-panel
  look. Considered, like modern dev tools (Linear, GitHub Primer, Stripe).

## Design Principles

- **Practice what you preach.** The kit itself must model the engineering quality it
  asks agents to produce. Slop here propagates into every project built on it.
- **Neutral foundation, easy to rebrand.** Identity lives in tokens (`globals.css`) and
  one config file. Screens are built from the shared UI kit so a rebrand is a token
  swap, not a rewrite.
- **Earned familiarity over novelty.** Use standard, trusted affordances (top bar +
  side nav, command palette, data tables). The tool disappears into the task.
- **Every state is designed.** Default, hover, focus, active, disabled, loading (skeleton),
  empty (teaches the interface), and error (says what's wrong + offers retry) — never
  half-shipped.
- **Consistency is the feature.** One button vocabulary, one form-control set, one icon
  style across every screen. Divergence is a bug.

## Accessibility & Inclusion

Target **WCAG 2.1 AA**. Body text ≥ 4.5:1, large/bold text ≥ 3:1, visible focus
indicators on every interactive element, full keyboard navigation, correct semantic
landmarks and heading order, labelled form controls, and a `prefers-reduced-motion`
alternative for every animation. Full light and dark theme parity.
