# Platform-X — Design System

> Visual design language. Every UI must follow this system.

---

## 1. Design Principles

- Luxury first. Every screen should feel premium.
- Minimal. Remove everything unnecessary.
- Consistent. Same spacing, colors, typography.
- Accessible. WCAG 2.1 AA minimum.
- Mobile first. Design for mobile, scale up.
- Fast. Optimized images, no heavy assets.

---

## 2. Color Palette

### Core Colors

Background:
- --bg-deep: #050608 (deepest black)
- --bg: #08090b (main background)
- --surface: #101216 (cards, panels)
- --surface-2: #15171c (elevated)
- --surface-3: #1a1c22 (highest elevation)

Brand:
- --gold: #c9a66b (primary)
- --gold-soft: #dfc18c (lighter)
- --gold-bright: #e8d5a8 (highlight)

Text:
- --cream: #f4efe6 (primary)
- --cream-soft: #e8e2d5 (secondary)
- --muted: #96928a (tertiary)
- --muted-deep: #66645f (disabled)

Lines:
- --line: rgba(255,255,255,0.08)
- --line-gold: rgba(201,166,107,0.28)

### Status Colors

- --success: #8dc88d (green)
- --warning: #e8c878 (yellow)
- --error: #e88 (red)
- --info: #8ab4d8 (blue)

---

## 3. Typography

### Fonts

Serif (headings):
"Playfair Display", "Cormorant Garamond", Georgia, serif

Sans (body):
"Inter", "Helvetica Neue", Arial, sans-serif

Mono (code, some numbers):
"JetBrains Mono", "SF Mono", Consolas, monospace

### Type Scale

- --text-xs: 10px (labels, eyebrows)
- --text-sm: 12px (small text)
- --text-base: 14px (body)
- --text-md: 16px (large body)
- --text-lg: 20px (small headings)
- --text-xl: 28px (headings)
- --text-2xl: 40px (large headings)
- --text-3xl: 56px (hero)
- --text-4xl: 72px (mega hero)

### Weight

- Light: 300
- Regular: 400 (default)
- Medium: 500
- Semi-bold: 600
- Bold: 700

### Line Heights

- Tight: 1.05 (large headings)
- Normal: 1.1 (headings)
- Relaxed: 1.5 (subheadings)
- Body: 1.75 (paragraphs)

### Letter Spacing

- Tight: -0.03em (large headings)
- Normal: -0.02em (headings)
- Wide: 0.02em (body)
- Extra-wide: 0.24em (eyebrows, labels)

---

## 4. Spacing System

Scale (based on 4px):
- --space-1: 4px
- --space-2: 8px
- --space-3: 12px
- --space-4: 16px
- --space-5: 24px
- --space-6: 32px
- --space-7: 40px
- --space-8: 60px
- --space-9: 90px

---

## 5. Border Radius

- --radius-none: 0 (default for luxury)
- --radius-sm: 2px (subtle)
- --radius-md: 4px (some cards)
- --radius-lg: 8px (rare)
- --radius-full: 9999px (pills, avatars)

---

## 6. Shadows

Subtle luxury:
- --shadow-sm: 0 2px 8px rgba(0,0,0,0.15)
- --shadow-md: 0 8px 24px rgba(0,0,0,0.25)
- --shadow-lg: 0 20px 50px rgba(0,0,0,0.35)
- --shadow-gold: 0 8px 30px rgba(201,166,107,0.25)

---

## 7. Components

### Buttons

Primary:
- Background: --gold
- Text: --bg-deep
- Padding: 16-18px horizontal, 14px vertical
- Font: Inter, 11px, 600, letter-spacing 0.18em, uppercase
- Hover: background --gold-soft, slight translateY(-2px)
- Border-radius: 0 (sharp luxury)

Secondary:
- Border: 1px solid --line
- Text: --cream
- Same padding and font
- Hover: border --gold, text --gold

Ghost:
- No background, no border
- Text: --muted
- Hover: text --gold

### Inputs

- Background: --bg
- Border: 1px solid --line
- Padding: 13px 14px
- Text: --cream
- Font: Inter, 13px
- Focus: border --gold
- Placeholder: --muted
- Border-radius: 0

### Cards

- Background: --surface
- Border: 1px solid --line
- Padding: 24-32px
- Hover: border --line-gold, translateY(-3px), shadow-md
- Border-radius: 0

### Modals

- Overlay: rgba(0,0,0,0.82) with backdrop blur 6px
- Modal background: --surface
- Border: 1px solid --line-gold
- Padding: 44px 32px
- Max-width: 440px
- Centered

---

## 8. Icons

- Line icons only, no filled
- Stroke width: 1.5px
- Color: matches text or --gold
- Sizes: 16px (small), 20px (default), 24px (large)
- Library: Lucide Icons or custom SVG

---

## 9. Motion

Durations:
- Fast: 0.2s (hover)
- Normal: 0.3s (default)
- Slow: 0.5s (modal)
- Very slow: 1.2s (image zoom)

Easing:
- Ease-out: cubic-bezier(0.2, 0.7, 0.2, 1) — default
- Ease-smooth: cubic-bezier(0.22, 0.61, 0.36, 1) — luxury feel

Never animate:
- Text color changes on load
- Position changes without cause
- Anything that distracts

---

## 10. Responsive Breakpoints

- Mobile: < 600px (default)
- Tablet: 600-900px
- Desktop: 900-1200px
- Wide: > 1200px

Container max-width: 1180px, with 90% padding on mobile.

---

## 11. Accessibility

- Contrast ratio: minimum 4.5:1 for body, 3:1 for large text
- Focus states: visible outline on all interactive elements
- Keyboard navigation: full support
- Screen readers: proper ARIA labels
- Reduced motion: respect prefers-reduced-motion

---

## 12. Dark Mode

Platform-X is dark-mode-first.
No light mode in Phase 1.
Future: consider light mode for accessibility in Phase 3+.

---

## 13. Design Tokens Implementation

All design tokens live in CSS custom properties:
- File: frontend/styles/tokens.css
- Injected at :root
- Used everywhere via var()

Single source of truth.

---

## 14. Component Library

Every component will have:
- HTML structure
- CSS classes
- JS behavior (if any)
- Usage examples
- Accessibility notes

Living documentation in frontend/styles/components/

---

Last updated: September 2026
Status: Living document.
