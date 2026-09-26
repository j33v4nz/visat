# Design Guardrails

Read this before generating or editing any page. Do not use the items below unless explicitly asked. These are the default "AI slop" patterns — avoid them by default.

## Visual style — never use
- Harsh/loud gradients
- Lucide icon set (pick a different, less default-feeling icon set)
- Pure white (#FFFFFF) background — use off-white/tinted white per brand
- Rainbow coloring on text or UI elements
- Drop shadows as a default effect (use only if a specific elevation need exists)
- Colored left stripe on cards/callouts
- Radial orb/blob background decorations
- Dot grid backgrounds
- Sparkle (✨) icons
- Neon colors
- Basic/generic pastel palettes
- Purple-and-black color scheme
- Soft, uniform corner radius on everything (vary intentionally or use sharper corners)
- "Liquid glass" / glassmorphism as a default effect

## Layout — never use
- 3 feature cards in a row (as a default layout crutch)
- Bento grid layouts
- Terminal/code-window decorative elements unless the product is dev-facing; UHI may use monospace typography without decorative terminal chrome
- 3 pricing tiers as a default (structure pricing to the actual product)

## Copy — never use
- Em dashes
- "It's not X, it's Y" phrasing
- Checkmark bullet lists as a default list style
- Fake/placeholder testimonials

## Fonts — never use
- Inter, Geist, or Space Grotesk as the default typeface — choose something intentional for the brand

## Motion — avoid as defaults
- Animated arrows
- Generic hover animations applied everywhere without purpose

## Functional gaps — never ship without
- Real product demos/screenshots (not just marketing copy)
- Skeleton loaders for async content
- Terms of Service
- Privacy Policy

## Brand-specific
- Product theme: dark-only near-black surfaces, high-contrast warm-white text, orange heat highlights, and restrained mint cooling indicators. Never add a light-mode toggle.
- Any new page should look intentionally designed for this product, not templated from a generic SaaS starter kit.
