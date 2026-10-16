# Platform-X — Pitch Deck

> **Purpose:** A 15-slide pitch deck for strategic buyers in the MENA
> hospitality sector.
>
> **Format:** This document contains the slide-by-slide content. To
> convert to PowerPoint, Google Slides, or Canva, use the "Slide N"
> headers as slide titles and the body text as bullet points.
>
> **Design guidance:** Dark navy background (#0A0E1A), cyan accent
> (#00D4FF), violet secondary (#7B3FE4), modern geometric sans-serif
> (Inter or Montserrat).

---

## Slide 1 — Cover

**Title:** Platform-X
**Subtitle:** AI-First Hospitality Platform

**Footer:** Acquisition Opportunity — 2026
**Contact:** platformx2026@gmail.com

**Visual:** Dark navy background with a glowing abstract 'X' logo in
cyan-to-violet gradient. Subtle circuit-board lines in the background.

---

## Slide 2 — The Problem

**Title:** Hospitality technology is 20 years behind

**Bullets:**
- Booking.com and Agoda run on 15–20-year-old data architectures.
- Retrofitting AI into them requires rebuilding the transactional core.
- Independent operators — 60–70% of MENA supply — have no AI-first option.
- Arabic-native, multi-category platforms are effectively absent.
- Large chains build in-house: 24–36 months, USD 1.5M–3.4M, high failure rate.

**Visual:** Split image. Left: dated server rack. Right: modern AI
interface. A red "20-year gap" arrow between them.

---

## Slide 3 — The Solution

**Title:** Built AI-first from day one

**Bullets:**
- Multi-tenant platform for hotels, restaurants, tours, experiences.
- AI is the operating layer, not a bolt-on.
- Four languages: EN, AR, FIL, HI.
- 79 features shipped, 15+ AI capabilities.
- Self-hosted on the buyer's own infrastructure.

**Visual:** Clean architecture diagram showing "AI Layer" as the
foundation, with "Clients / Services / Data" stacked above.

---

## Slide 4 — The Product

**Title:** 79 features. 15+ AI capabilities. 10 blue-ocean.

**Columns:**

**Core Platform**
- Multi-tenant bookings
- Rewards & referral engine
- Public API + webhooks
- 4 languages

**AI Capabilities**
- Pricing Coach
- Voice Booking
- Content Writer
- Trip Memory
- Receptionist
- 10+ more

**Blue-Ocean**
- Predictive Price Locks
- Trust Score
- Multi-Business Bundles
- Instant Refund AI
- Family Mode

**Visual:** Three columns with icons. Cyan/violet gradient headers.

---

## Slide 5 — Live Demo

**Title:** See it working

**Content:**
- [Insert 3–4 screenshots: booking flow, AI assistant, rewards ledger,
  business dashboard]
- [Optional: link to a live demo environment or recorded walkthrough]

**Footer:** Full walkthrough available under NDA.

**Visual:** Clean app screenshots arranged in a grid on a dark
background.

---

## Slide 6 — Technology

**Title:** Production-grade stack

**Table:**
| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL 18.2 (verified) |
| Migrations | Alembic (33 revisions) |
| Templates | Jinja2 (82 files) |
| Auth | JWT + TOTP 2FA |
| Webhooks | HMAC-SHA256 (generic + Stripe) |
| AI providers | Gemini / OpenAI (switchable) |
| Payments | Telr / Stripe (abstraction ready) |

**Visual:** Tech stack grid with monochrome icons and cyan accents.

---

## Slide 7 — Verification

**Title:** Verified, not claimed

**Big numbers:**
- **1,509** automated tests — all passing
- **33** migrations verified on real PostgreSQL 18.2
- **12/17** security checklist items verified in code
- **7** Stripe signature integration tests
- **0** XSS issues, **0** SQL injection issues

**Footer:** Full reports in `docs/21-PG-VERIFICATION.md` and
`docs/20-PAYMENT-TEST-MODE.md`.

**Visual:** Bold numbers in cyan gradient. Checkmark icons.

---

## Slide 8 — Market

**Title:** MENA hospitality is the opportunity

**Bullets:**
- Saudi Vision 2030: 150M annual visits by 2030.
- UAE: 40M hotel guests target.
- Independent operators dominate supply but lag in tech adoption.
- Arabic-language + data residency becoming regulatory requirements.
- Global OTAs cannot pivot fast enough.

**Numbers:**
- SAM: several thousand businesses across UAE, KSA, Qatar, Kuwait, Bahrain, Oman.
- SOM (3 years): 300–500 tenants.
- ARR at maturity (illustrative): AED 5.4M–15M.

**Visual:** MENA map with highlighted target countries and market
sizes.

---

## Slide 9 — Business Model

**Title:** Four revenue streams

**Streams:**
1. Subscription — monthly/yearly per tenant
2. Transaction commission — 3% of booking value
3. Premium features — add-ons
4. Setup / onboarding fees — one-time

**Tiers (illustrative):**
- Starter: AED 499/month
- Growth: AED 1,499/month
- Enterprise: AED 3,999/month

**Footer:** Buyer defines final pricing.

**Visual:** Three pricing tiers displayed as cards.

---

## Slide 10 — Unit Economics

**Title:** Attractive B2B SaaS metrics

**Numbers (illustrative):**
- ARPU: AED 1,800/tenant/month
- CAC: AED 3,000–6,000
- LTV (3 years, 4% churn): AED 60,000–64,000
- LTV/CAC: 10–20x
- Payback: 2–4 months
- Gross margin: 90%+

**Footer:** Numbers are illustrative. Buyer validates with their own
sales motion.

**Visual:** Simple table with highlighted LTV/CAC ratio.

---

## Slide 11 — Build vs Buy

**Title:** Buying is unambiguously better

**Comparison:**

| | Build in-house | Buy Platform-X |
|---|---|---|
| Upfront cost | USD 1.5M–3.4M | USD 1.36M |
| Time to market | 24–36 months | 2–4 weeks |
| Delivery risk | 40–60% delay probability | Low |
| Year-1 team cost | USD 700k–900k | ~USD 200/month + usage |
| Source code | Yes | Yes (transferred) |

**Footer:** See `docs/22-VALUATION-DEFENSE.md` for full analysis.

**Visual:** Two columns with check/cross icons.

---

## Slide 12 — Target Buyers

**Title:** Built for a strategic operator

**Content:**
- 25 prioritized companies in MENA hospitality and tech.
- Tier 1: Jumeirah, Emaar, Atlantis, Rotana, PIF, Red Sea Global.
- Tier 2: Katara, Minor International, regional operators.
- Tier 3: Careem, Kitopi, investment vehicles.

**Footer:** Full list in `docs/23-TARGET-BUYERS.md`.

**Visual:** Map with logos of target companies (placeholders).

---

## Slide 13 — The Ask

**Title:** AED 5,000,000

**Terms:**
- Asking: AED 5,000,000
- Range: AED 5,000,000 – AED 7,000,000
- Structure: 50% on signing, 50% on transfer completion
- Escrow: required above USD 500k
- Handover: support until platform declared live + 12 months
  emergency support
- Non-compete: 24 months

**Visual:** Bold number in the center. Terms in a card layout.

---

## Slide 14 — What the Buyer Gets

**Title:** Complete asset transfer

**Included:**
- Full source code (252 Python files, 34,342 lines)
- 1,509 automated tests
- Complete documentation (HANDOFF + docs/ + docs/buyer/)
- Deploy scripts (Nginx, systemd, install/update/backup)
- 33 Alembic migrations
- AI-driven development methodology (documented)
- 30-day handover support

**Not included (buyer's responsibility):**
- Brand name, domain, VPS
- Payment provider account, AI provider key
- Hospitality operating license
- SSL certificate

**Visual:** Two-column: "You get" (checkmarks) vs "You provide"
(arrow icons).

---

## Slide 15 — Contact

**Title:** Next steps

**Process:**
1. Sign NDA (`docs/19-NDA-TEMPLATE.md`)
2. Receive full Investment Memorandum
3. Due diligence (read-only repository access)
4. Term Sheet negotiation
5. Sale Agreement (DIFC lawyer)
6. Escrow + transfer

**Contact:**
- Email: platformx2026@gmail.com
- Subject: "Platform-X — Acquisition Inquiry"

**Visual:** Clean closing slide with contact info centered.

---

## Presenter notes

**Tone:** Confident, not aggressive. The asset is complete and
verified; there is no need to oversell.

**What NOT to say:**
- Do not claim revenue that does not exist.
- Do not claim Stripe is tested with a real account.
- Do not claim the platform is "fully live" anywhere.
- Do not claim AI Voice Booking processes raw voice input.

**What TO emphasize:**
- Time-to-market advantage (2–4 weeks vs 24–36 months).
- Cost advantage (below the low end of build cost).
- Ownership (full source code, self-hosted).
- Verification (1,509 tests, 33 migrations, security audit).

**Handling objections:** Reference `docs/22-VALUATION-DEFENSE.md` §2.5.

---

## Document control

- **Version:** 1.0
- **Date:** 2026-10-16
- **Author:** Benjamin Bahoush (with AI assistance)
- **Status:** Ready for slide conversion
