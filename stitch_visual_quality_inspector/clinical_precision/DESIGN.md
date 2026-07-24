---
name: Clinical Precision
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#41493c'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#717a6b'
  outline-variant: '#c1c9b8'
  surface-tint: '#2d6c1a'
  primary: '#2a6918'
  on-primary: '#ffffff'
  primary-container: '#43832f'
  on-primary-container: '#f8ffef'
  inverse-primary: '#93d879'
  secondary: '#5d5e61'
  on-secondary: '#ffffff'
  secondary-container: '#e2e2e5'
  on-secondary-container: '#636467'
  tertiary: '#535f56'
  on-tertiary: '#ffffff'
  tertiary-container: '#6b786e'
  on-tertiary-container: '#f6fff5'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#aef592'
  primary-fixed-dim: '#93d879'
  on-primary-fixed: '#042100'
  on-primary-fixed-variant: '#125300'
  secondary-fixed: '#e2e2e5'
  secondary-fixed-dim: '#c6c6c9'
  on-secondary-fixed: '#1a1c1e'
  on-secondary-fixed-variant: '#454749'
  tertiary-fixed: '#d9e6da'
  tertiary-fixed-dim: '#bdcabe'
  on-tertiary-fixed: '#131e17'
  on-tertiary-fixed-variant: '#3e4a41'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Hanken Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 40px
  gutter: 24px
  margin: 32px
---

## Brand & Style
The design system is engineered for medical and laboratory environments where clarity, speed of cognition, and trust are paramount. The personality is clinical yet approachable—prioritizing function without sacrificing a modern aesthetic. 

The style utilizes **Modern Corporate** principles with a leaning toward **Minimalism**. It emphasizes a sterile (but not cold) environment through high-key lighting, generous whitespace, and a focused green-and-white palette. The visual mood should evoke feelings of hygiene, professional accuracy, and technological advancement.

## Colors
The palette is rooted in a "Laboratory Green" (#5A9B44), derived from the Optylab visual identity, signifying growth and health.

- **Primary:** Used for key actions, progress indicators, and active states. 
- **Secondary:** A deep charcoal used for high-contrast typography and iconography to ensure legibility.
- **Tertiary:** A soft mint tint used for large surface areas, background fills for data rows, or success notifications.
- **Neutral:** A range of cool grays and whites that form the foundation of the UI, reducing eye strain during long periods of data entry.

Backgrounds should primarily be pure white (#FFFFFF) to maintain a sterile, high-light environment.

## Typography
The system uses **Hanken Grotesk** for headlines to provide a sharp, contemporary character that feels engineered and precise. For all functional text, data, and body copy, **Inter** is utilized for its exceptional legibility at small sizes and high x-height, which is critical for laboratory results and technical documentation.

Strict vertical rhythm is maintained by adhering to the defined line heights. For data-heavy tables, use `body-sm` to maximize information density without compromising readability.

## Layout & Spacing
This design system employs a **Fluid Grid** model with a 12-column structure for desktop and a 4-column structure for mobile. 

- **Density:** The spacing rhythm is based on an 8px baseline grid. 
- **Data Views:** In administrative or laboratory result views, internal padding is reduced (using `sm` units) to ensure more data is visible above the fold. 
- **Content Flow:** Marketing or landing pages use `xl` units to provide the "generous whitespace" requested, while functional dashboards use `md` units to maintain a professional, utility-first feel.

## Elevation & Depth
Depth is communicated through **Tonal Layers** and **Ambient Shadows**. 

1.  **Surfaces:** The primary background is white. Secondary containers (like sidebars or card backgrounds) use the Neutral color hex to create subtle separation.
2.  **Shadows:** Shadows are highly diffused and low-opacity (5–10% Alpha), using a slight tint of the Primary Green to keep them "fresh" rather than "muddy." 
3.  **Borders:** Use 1px borders in a light gray (#E2E8F0) for structural definition in tables and input fields. Shadows are reserved for floating elements like modals, dropdowns, and elevated action cards.

## Shapes
The shape language follows the **Rounded** (0.5rem) standard. This provides a soft, human-centric feel that balances the "clinical" nature of the typography. 

- **Buttons & Inputs:** Use the 0.5rem base radius.
- **Large Cards:** Use `rounded-lg` (1rem) to frame data sets.
- **Status Indicators/Chips:** Use `rounded-xl` (1.5rem) or full pill-shape to distinguish them from interactive buttons.

## Components
- **Buttons:** Primary buttons use a solid green fill with white text. Ghost buttons use a 1px green border for secondary actions.
- **Input Fields:** Use a light neutral background with a subtle border. On focus, the border transitions to Primary Green with a soft outer glow.
- **Chips:** Used for lab status (e.g., "Pending", "Completed"). Completed states use the Tertiary green fill with Primary green text.
- **Data Tables:** These are the core of the system. Use alternate row striping (using the Tertiary color at 30% opacity) and sticky headers. 
- **Cards:** Cards should have a 1px border and an extremely subtle shadow to appear "lifted" from the white background.
- **Progress Steps:** A linear indicator at the top of multi-stage lab entries, using the Primary Green to denote current and completed steps.