# UI system

## Visual direction

TriageIQ should feel calm, dependable, warm, and operational. The interface intentionally avoids bright AI gradients, glassmorphism, neon status colours, and dashboard clutter.

## Palette

| Token | Value | Purpose |
|---|---|---|
| Cream | `#F6F1E7` | Page background |
| Ivory | `#FFFDF8` | Cards and fields |
| Sand | `#EFE5D6` | Sidebar and soft surfaces |
| Border | `#DED1C1` | Dividers and card borders |
| Espresso | `#29231F` | Primary text and buttons |
| Taupe | `#74685E` | Secondary text |
| Camel | `#B9855A` | Brand accent and progress |
| Forest | `#54705A` | Success |
| Burnt amber | `#A66C32` | Warning |
| Brick | `#9D463A` | Error and critical |
| Slate | `#526B73` | Informational state |

Camel is used for emphasis, not for small body text on cream. Espresso is used for primary buttons to preserve contrast.

## Layout principles

- 18px card radius, subtle warm border, minimal shadow.
- Wide spacing and short content sections.
- One primary action per panel.
- Status, severity, and confidence are visible without dominating the page.
- Incident details use four tabs: Overview, Analysis, Timeline, Resolution.
- The lifecycle stepper is always visible near the top.
- Charts are limited to information that changes a decision.

## Interviewer experience

- Login form is prefilled with seeded credentials.
- “Try demo incident” creates a realistic incident immediately.
- Mock AI mode avoids external quota failure.
- A pre-resolved sample demonstrates the final report without waiting.
- Every stage and human decision is visible in a single incident workspace.

## Source upload experience

- The New Incident page first asks users to choose manual entry or document upload.
- Upload accepts PDF, JSON, CSV, TXT, and LOG with a visible 4 MB limit.
- Retention is selected explicitly as 7 or 10 days.
- Extraction results appear as an editable preview, never as an automatic submission.
- Information gaps are displayed in warm amber surfaces, not destructive red, because they are actionable uncertainties rather than failures.
- Incident details show file type, size, retention, expiry, availability, re-extraction, and early deletion without exposing a public storage URL.
