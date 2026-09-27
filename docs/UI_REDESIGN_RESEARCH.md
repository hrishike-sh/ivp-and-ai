# UI redesign research — 9 September 2026

## User feedback and timing

The current interface looks generic and the user considers it visually poor. Redesign is deferred until later. Treat Streamlit as the functional IVP prototype, not an accepted finished visual design. No frontend migration or new design-tool installation has been performed.

## Shortlist

| Resource | What it provides | Fit for this project |
|---|---|---|
| [Mantine](https://mantine.dev/getting-started/) | React controls, forms, dropzone, charts, notifications, and custom styling | Recommended component foundation for a compact image/video workspace. Its coordinated controls cover most of the application's needs. |
| [shadcn/ui](https://ui.shadcn.com/blocks) | Editable React components and responsive, accessible composable blocks | Good alternative when more custom composition is wanted. A stock dashboard block would repeat the generic look the user rejected. |
| [Impeccable](https://github.com/pbakaus/impeccable) | Design guidance, critique, audit, typography, simplification, and polish workflows for coding agents | Recommended design-review workflow to evaluate hierarchy and usability, not just whether code renders. Published capabilities are not independently benchmarked here. |
| [Anthropic frontend-design skill](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) | Guidance on intentional visual direction, typography, layout, restraint, and critique | A simpler alternative design skill. It is guidance rather than a component library or a guarantee of good results. |

Official Mantine documentation also exposes LLM documentation and agent integrations: https://mantine.dev/ and https://mantine.dev/llms.txt. These can help implement components correctly; they do not replace design judgment.

## Reddit findings

[This r/Frontend discussion](https://www.reddit.com/r/Frontend/comments/1opi3h3/is_anyone_else_tired_of_every_tailwindshadcn_app/) discusses repeated Tailwind/shadcn appearances. Participants distinguish a component library from a deliberate visual system and suggest making typography, spacing, layout, and colour decisions before coding. This is community opinion, not comparative evidence that one library produces better designs.

[This r/webdesign workflow discussion](https://www.reddit.com/r/webdesign/comments/1tab7tz/built_10_websites_for_clients_in_4_months_heres/) similarly argues for reference research before implementation. Its recommendations are anecdotal.

My conclusion: swapping libraries alone will not fix the interface. The next pass must be designed around inspecting footage, with real reference interfaces and screenshot-based critique.

## Recommended later direction

Use a custom React + Vite + Mantine frontend, with the existing IVP pipeline behind a local Python API. This is a proposal for a later change, not a modification to the current working app.

Shape the UI like a media-processing workspace: a large central original/processed viewport, compact toolbar, video timeline, a focused processing inspector, and exports/job status positioned near the work. Reduce nested tabs, oversized headings, decorative labels, and excessive explanation in the primary workspace. Keep detailed IVP explanations in contextual help or a dedicated inspection view.

Before migration, choose reference interfaces and capture the proposed layout. Preserve all existing upload, timestamp, cancellation, export, original-file, and IVP-interface behaviour. Use the design skill for planning and critique, and verify the finished interface with actual image/video content. Keep the local start command and localhost-only operation.

The next redesign should address the user's stated dissatisfaction, not invent unrelated dashboard cards, metrics, animations, or marketing sections. Do not install both component libraries or multiple overlapping design skills by default.
