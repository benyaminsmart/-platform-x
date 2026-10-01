# Platform-X — Project Handoff

> Complete overview for any new AI/dev session. Read this + PROJECT-RULES.md + AI-CONTEXT.md.
> Version: v0.40.0-budget-optimizer (Phases 0-7, 9, 11, 14, 18-23, 25-30, 32-50 complete; 24 DEFERRED). TIER 1+2 = 100%.

Last updated: 2026-10-01

---

## 0. STRATEGIC PRIORITY — READ THIS FIRST

> **Mission:** Platform-X must be *better and more attractive than
> Booking.com and Agoda* in every dimension. This is the standing
> directive from the project owner (2026-09-29).
>
> **Detailed strategy:** `docs/14-ROADMAP-V3-COMPETITIVE.md`
>
> That file is the canonical competitive roadmap. It contains:
> - Reference competitors (Booking.com, Agoda)
> - 30 features competitors have that we must add (Tier 1-3)
> - 19 AI moats we already have (they don't)
> - 15 blue-ocean innovations no competitor has
> - 6 implementation waves (Wave 0-5)
> - Business rules + success metrics + decision log
>
> **Current reality (2026-09-29):**
> - All AI-focused phases complete (~750 tests, 90 smoke checks)
> - Public API + Webhooks complete
> - BLOCKED by two user-side items:
>   1. VPS + Domain purchase (Phase 12)
>   2. Payment account — Telr/Stripe (Phase 10)
> - **NEXT: Wave 0 — Foundation for advertising** (see Roadmap v3 §6)
>
> **This HANDOFF is the "what is."** The Roadmap v3 is the "where
> we go and why." Read both.
>
> **Anti-features** (do NOT build): social feeds, forum, video
> reviews, crypto payments, human live chat, virtual currency,
> auction booking, blockchain. (See Roadmap v3 §5.)

---


## 0.1 Standing Goals (user directive, 2026-09-29)

Permanent goals guiding EVERY decision:

**Primary mission:**
Platform-X must be *better and more attractive than Booking.com and
Agoda* in every dimension. Not an alternative — a superior product.

**Strategic stance:**
AI-First Hospitality Platform (Strategy B).
- AI for guests (booking, planning, concierge, trip memory)
- AI for businesses (pricing, marketing, insights, reviews)

**Quality bar (non-negotiable):**
- EXCELLENCE — no shortcuts, no bugs, production-ready
- Every feature must answer: "Does this make us more attractive than
  Booking/Agoda?" If no → reject.
- Every new feature must consider AI augmentation.

**Business-first direction:**
Value for business owners comes before value for guests, because
businesses pay; users use.

**Anti-features (never build):** social feeds, forum, video reviews,
crypto, human live chat, virtual currency, auction booking, blockchain.

Full details: `docs/14-ROADMAP-V3-COMPETITIVE.md`.

---

## 0.2 Working Method (fast + safe)

Fast, safe, AI-driven loop:

**Per Step (TWO commands, in order):**
1. Code + tests written together (by the AI in one message)
2. `bash scripts/step.sh --test <path> --message "<msg>" --label <lbl>`
   - git add -A
   - pytest <test>  (MUST pass, else ABORT and unstage)
   - git commit (only on green tests)
   - backup.sh <label>
   - updates `Last step:` line in HANDOFF Section 0.5
3. `bash scripts/handoff.sh "<step description>" <sha> "<msg>"`
   - flips the matching checklist item to [x] in Section 0.5
   - prepends the commit to "Commits (recent)"
   - commits HANDOFF
   - backups
4. Report in Persian

**Both commands must be run for every Step.** Without handoff.sh the
checklist goes stale.

**HANDOFF verification at Phase close (MANDATORY — AI responsibility):**
The AI MUST run this verification itself at Phase close, BEFORE tagging.
Do NOT ask the user. If anything is stale, the AI fixes it in the same
command sequence, commits, then tags.
After every Phase (milestone), before tagging, verify HANDOFF is fresh:
  - Version line matches the new tag
  - Test Count matches the real `pytest tests/` output (use `pytest tests/ -n auto` for speed — same results, ~2.5x faster)
  - Section 0.5 checklist has no stale [ ] for finished Steps
  - Phase appears in Section 5 (Phases Status)
  - "Last updated" is today
If anything is stale → fix it FIRST, commit, then tag.
Never tag with stale HANDOFF.

**Per Phase (milestone):**

1. Full test suite
2. Milestone tag
3. Full HANDOFF update
4. Full backup (backup-full.sh)

**Per Wave (multiple phases):**
1. Re-read Section 0 + Roadmap v3
2. Reassess wave success metrics
3. Update Section 0.1 if needed

**Rules unchanged:** backup, one step at a time, test before done,
no AI-initiated features, no architecture changes without approval,
Persian only.

**Speed principle:** one chat message = one complete Step
(code + tests + commit). Quality preserved because tests must pass.

---

## 0.5 Wave 0 Progress (updated after every step)

**Phase 30 — Wave 0 / Foundation for advertising (part A, free)**
Started: 2026-09-29
- [x] Phase 51 Step 2 — Bundle Deals API
- [x] Phase 51 Step 1 — Multi-Business Bundle Deals service
- [x] Phase 50 Step 3 — Budget Optimizer UI on /account/ai
- [x] Phase 50 Step 2 — Budget Optimizer API
- [x] Phase 50 Step 1 — AI Budget Optimizer service
- [x] Phase 49 Step 3 — Trust Score in search + UI badge
- [x] Phase 49 Step 2 — Trust Score API
- [x] Phase 49 Step 1 — Trust Score service
- [x] Phase 48 Step 4 — Waitlist auto-notify on cancellation
- [x] Phase 48 Step 3 — Waitlist UI page
- [x] Phase 48 Step 2 — Waitlist API
- [x] Phase 48 Step 1 — WaitlistEntry model + service
- [x] Phase 47 Step 4 — Lock price button on /search cards
- [x] Phase 47 Step 3 — Price Locks UI page
- [x] Phase 47 Step 2 — Price Locks API
- [x] Phase 47 Step 1 — PriceLock model + service
- [x] Phase 46 Step 3 — AI Trip Memory UI
- [x] Phase 46 Step 2 — AI Trip Memory API
- [x] Phase 46 Step 1 — AI Trip Memory service
- [x] Phase 45 Step 3 — AI location recommend UI
- [x] Phase 45 Step 2 — AI location recommend API
- [x] Phase 45 Step 1 — AI Location Recommender service
- [x] Phase 44 Step 2 — Redeem page UI
- [x] Phase 44 Step 1 — Redeem service + API
- [x] Phase 43 Step 2 — Price alerts UI + watch button
- [x] Phase 43 Step 1 — Price alerts model + service + API
- [x] Phase 42 Step 2 — Recent searches UI
- [x] Phase 42 Step 1 — Recent searches model + API
- [x] Phase 41 Step 3 — Nearby attractions UI
- [x] Phase 41 Step 2 — Attractions service + API
- [x] Phase 41 Step 1 — Attraction model + migration + seed
- [x] Phase 40 Step 4 — Group management UI
- [x] Phase 40 Step 3 — Group booking API
- [x] Phase 40 Step 2 — Group service
- [x] Phase 40 Step 1 — GroupMember model + is_group
- [x] Phase 39 Step 6 — Messages inbox page + sidebar
- [x] Phase 39 Step 5 — Messages service + API
- [x] Phase 39 Step 4 — Message model + migration
- [x] Phase 39 Step 3 — Write-review modal with photo upload
- [x] Phase 39 Step 2 — Review photos on tenant page
- [x] Phase 39 Step 1 — Review photos model + upload API
- [x] Phase 38 Step 5 — Promotions UI + sidebar
- [x] Phase 38 Step 4 — Booking promotion integration
- [x] Phase 38 Step 3 — Promotions API
- [x] Phase 38 Step 2 — Promotion service
- [x] Phase 38 Step 1 — Promotion model + migration
- [x] Phase 37 Step 5a — Public service rate plans endpoint
- [x] Phase 37 Step 4 — Rate plans page + sidebar
- [x] Phase 37 Step 3 — Booking rate plan integration
- [x] Phase 37 Step 2 — Rate plan service + API
- [x] Phase 37 Step 1 — RatePlan model + migration
- [x] Phase 36 Step 5 — Room number in receipt + account
- [x] Phase 36 Step 4 — Auto-assign room on payment
- [x] Phase 36 Step 3 — Rooms page + sidebar
- [x] Phase 36 Step 2 — Rooms service + API
- [x] Phase 36 Step 1 — Room model + migration
- [x] Phase 35 Step 5 — No-show UI in dashboard
- [x] Phase 35 Step 4 — No-show detection + API
- [x] Phase 35 Step 3 — Booking modification UI
- [x] Phase 35 Step 2 — Booking modification API
- [x] Phase 35 Step 1 — Booking modification service
- [x] Phase 34 Step 4 — Print report button in dashboard
- [x] Phase 34 Step 3 — Printable business report
- [x] Phase 34 Step 2 — Export buttons in dashboard
- [x] Phase 34 Step 1 — Reports service + exports API
- [x] Phase 33 Step 5b — Compare UI + button
- [x] Phase 33 Step 5a — Compare API
- [x] Phase 33 Step 4 — Wishlist page
- [x] Phase 33 Step 3 — Heart button in search results
- [x] Phase 33 Step 2 — Wishlist service + API
- [x] Phase 33 Step 1 — Wishlist model + migration
- [x] Step 4 — Map section on tenant page
- [x] Step 3 — Leaflet map in /search
- [x] Step 2 — Geographic filter in search
- [x] Step 1 — Coordinates seed for tenants
Last step: Phase 51 Step 2 — Bundle Deals API (2026-10-01 15:47)

- [x] Step 1 — Search service (cross-tenant, availability, filters)
- [x] Step 2 — /api/search endpoint
- [x] Step 3 — Search form on home + /search results page
- [x] Step 4a — /api/availability endpoint
- [x] Step 4b — Availability calendar on tenant page
- [x] Step 5 — Cancellation + refund service
- [x] Step 5b — Cancellation API
- [x] Step 5c — Cancel UI in account page
- [x] Step 6a — Multi-currency service
- [x] Step 6b — Currency in search API
- [x] Step 6c — Currency dropdown in /search UI
- [x] Step 7 — Booking receipt (print to PDF)
- [x] Step 8 — PWA (manifest + service worker + icon)
- [x] Step 9 — Extended search filters (rating, type, location)
- [x] Step 9b — Extended filters in /search UI
- [x] Step 10a — Service gallery API
- [x] Step 10b — Gallery section on tenant page
- [x] Phase close — milestone tag (v0.21.0-wave0-part-a) + full HANDOFF update

**Commits (recent):**
- 73ac6ac Phase 51 Step 2 — Bundle Deals API
- e5a76df Phase 51 Step 1 — Multi-Business Bundle Deals service
- 3d32f41 Phase 50 Step 3 — Budget Optimizer UI on /account/ai
- 9409822 Phase 50 Step 2 — Budget Optimizer API
- 16667f7 Phase 50 Step 1 — AI Budget Optimizer service
- 2a590cf Phase 49 Step 3 — Trust Score in search + UI badge
- 50b3fb4 Phase 49 Step 2 — Trust Score API
- b743a19 Phase 49 Step 1 — Trust Score service
- df87c83 Phase 48 Step 4 — Waitlist auto-notify on cancellation
- f7bd6b4 Phase 48 Step 3 — Waitlist UI page
- 6855c94 Phase 48 Step 2 — Waitlist API
- 6528999 Phase 48 Step 1 — WaitlistEntry model + service
- 2e3f037 Phase 47 Step 4 — Lock price button on /search cards
- 6e99700 Phase 47 Step 3 — Price Locks UI page
- 2652047 Phase 47 Step 2 — Price Locks API
- 5396c0c Phase 47 Step 1 — PriceLock model + service
- 80cd9ee Phase 46 Step 3 — AI Trip Memory UI
- 2ee3a85 Phase 46 Step 2 — AI Trip Memory API
- 43a1a47 Phase 46 Step 1 — AI Trip Memory service
- 52f0371 Phase 45 Step 3 — AI location recommend UI
- d5bf7d4 Phase 45 Step 2 — AI location recommend API
- 1021990 Phase 45 Step 1 — AI Location Recommender service
- 0d88e5b Phase 44 Step 2 — Redeem page UI
- 9064894 Phase 44 Step 1 — Redeem service + API
- 6416df1 Phase 43 Step 2 — Price alerts UI + watch button
- aa87779 Phase 43 Step 1 — Price alerts model + service + API
- c016471 Phase 42 Step 2 — Recent searches UI
- a91a427 Phase 42 Step 1 — Recent searches model + API
- cf6bbac Phase 41 Step 3 — Nearby attractions UI
- 6e236e1 Phase 41 Step 2 — Attractions service + API
- f544763 Phase 41 Step 1 — Attraction model + migration + seed
- 36ff651 Phase 40 Step 4 — Group management UI
- 0e3378d Phase 40 Step 3 — Group booking API
- 2918edf Phase 40 Step 2 — Group service
- e24af21 Phase 40 Step 1 — GroupMember model + is_group
- dc08826 Phase 39 Step 6 — Messages inbox page + sidebar
- 645f0ba Phase 39 Step 5 — Messages service + API
- 585334f Phase 39 Step 4 — Message model + migration
- 3900370 Phase 39 Step 3 — Write-review modal with photo upload
- b7af556 Phase 39 Step 2 — Review photos on tenant page
- 5e9e5c0 Phase 39 Step 1 — Review photos model + upload API
- 759b8dd Phase 38 Step 5 — Promotions UI + sidebar
- 40a37cd Phase 38 Step 4 — Booking promotion integration
- e70ff82 Phase 38 Step 3 — Promotions API
- e774e6d Phase 38 Step 2 — Promotion service
- daffa9a Phase 38 Step 1 — Promotion model + migration
- 348bbf9 Phase 37 Step 5a — Public service rate plans endpoint
- 914ce43 Phase 37 Step 4 — Rate plans page + sidebar
- aa23648 Phase 37 Step 3 — Booking rate plan integration
- 8f1164c Phase 37 Step 2 — Rate plan service + API
- 238c984 Phase 37 Step 1 — RatePlan model + migration
- ee6f054 Phase 36 Step 5 — Room number in receipt + account
- e8240f9 Phase 36 Step 4 — Auto-assign room on payment
- 63da3f2 Phase 36 Step 3 — Rooms page + sidebar
- 8d94420 Phase 36 Step 2 — Rooms service + API
- 857fbef Phase 36 Step 1 — Room model + migration
- cc6526c Phase 35 Step 5 — No-show UI in dashboard
- 30e0dd4 Phase 35 Step 4 — No-show detection + API
- e000ea5 Phase 35 Step 3 — Booking modification UI
- a316d41 Phase 35 Step 2 — Booking modification API
- f1332a1 Phase 35 Step 1 — Booking modification service
- 35d9dfb Phase 34 Step 4 — Print report button in dashboard
- 1535d00 Phase 34 Step 3 — Printable business report
- 2b658b7 Phase 34 Step 2 — Export buttons in dashboard
- a3db0f5 Phase 34 Step 1 — Reports service + exports API
- d3a8612 Phase 33 Step 5b — Compare UI + button
- 0b7f052 Phase 33 Step 5a — Compare API
- f57e235 Phase 33 Step 4 — Wishlist page
- 39811a7 Phase 33 Step 3 — Heart button in search results
- 338b0d8 Phase 33 Step 2 — Wishlist service + API
- a8ef6d7 Phase 33 Step 1 — Wishlist model + migration
- e97f6ee Step 4 — Map section on tenant page
- 743c3e6 Step 3 — Leaflet map in /search
- a043b85 Step 2 — Geographic filter in search
- 9f609ca Step 1 — Coordinates seed for tenants
- 3c872b7 Step 10b — Gallery section on tenant page
- f2485ae feat(phase-30/step-10a): service gallery API
- 02988b0 feat(phase-30/step-9b): extra filters in /search UI
- ceb5351 feat(phase-30/step-9): extended search filters
- 8345072 feat(phase-30/step-8): PWA
- 7ec863b feat(phase-30/step-7): booking receipt HTML

**Wave 0 part B (needs purchases):** VPS, Domain, Payment (Phase 31)

---

**Phase 32 — Wave 1 / Map + Location Search: COMPLETE**
Tag: v0.22.0-map-location
- [x] Step 1 — Coordinates seed for tenants
- [x] Step 2 — Geographic filter in search (Haversine)
- [x] Step 3 — Leaflet map in /search (markers + radius)
- [x] Step 4 — Map section on tenant page (Find nearby)
- [x] Phase close — tag v0.22.0-map-location

**Phase 33 — Wave 1 / Wishlist + Compare: COMPLETE**
Tag: v0.23.0-wishlist-compare
- [x] Step 1 — Wishlist model + migration
- [x] Step 2 — Wishlist service + API
- [x] Step 3 — Heart button in search results
- [x] Step 4 — Wishlist page (/account/wishlist)
- [x] Step 5a — Compare API
- [x] Step 5b — Compare UI + button in search
- [x] Phase close — tag v0.23.0-wishlist-compare

**Phase 34 — Wave 1 / Reports (CSV + PDF): COMPLETE**
Tag: v0.24.0-reports
- [x] Step 1 — Reports service + exports API
- [x] Step 2 — Export buttons in dashboard
- [x] Step 3 — Printable business report
- [x] Step 4 — Print report button + milestone close
- [x] Phase close — tag v0.24.0-reports

**Phase 35 — Wave 1 / Booking modification + No-show: COMPLETE**
Tag: v0.25.0-booking-mod
- [x] Step 1 — Booking modification service
- [x] Step 2 — Booking modification API
- [x] Step 3 — Booking modification UI
- [x] Step 4 — No-show detection + API
- [x] Step 5 — No-show UI in dashboard
- [x] Phase close — tag v0.25.0-booking-mod

**Phase 36 — Wave 1 / Room inventory + auto-assignment: COMPLETE**
Tag: v0.26.0-rooms
- [x] Step 1 — Room model + migration
- [x] Step 2 — Rooms service + API
- [x] Step 3 — Rooms page + sidebar link
- [x] Step 4 — Auto-assign room on payment
- [x] Step 5 — Room number in receipt + account
- [x] Phase close — tag v0.26.0-rooms

**Phase 37 — Wave 1 / Rate Plans: COMPLETE**
Tag: v0.27.0-rate-plans
- [x] Step 1 — RatePlan model + migration
- [x] Step 2 — Rate plan service + API
- [x] Step 3 — Booking rate plan integration
- [x] Step 4 — Rate plans page + sidebar
- [x] Step 5a — Public service rate plans endpoint
- [x] Phase close — tag v0.27.0-rate-plans

**Phase 38 — Wave 1 / Promotions Engine: COMPLETE**
Tag: v0.28.0-promotions
- [x] Step 1 — Promotion model + migration
- [x] Step 2 — Promotion service
- [x] Step 3 — Promotions API + public validate
- [x] Step 4 — Booking promotion integration
- [x] Step 5 — Promotions UI + sidebar
- [x] Phase close — tag v0.28.0-promotions

**Phase 39 — Wave 1 / Review photos + Guest messaging: COMPLETE**
Tag: v0.29.0-reviews-messaging
- [x] Step 1 — ReviewPhoto model + upload API
- [x] Step 2 — Review photos on tenant page
- [x] Step 3 — Write-review modal with photo upload
- [x] Step 4 — Message model + migration
- [x] Step 5 — Messages service + API
- [x] Step 6 — Messages inbox page + sidebar
- [x] Phase close — tag v0.29.0-reviews-messaging

**Phase 40 — Wave 1 / Group booking: COMPLETE**
Tag: v0.30.0-group-booking
- [x] Step 1 — GroupMember model + is_group on Booking
- [x] Step 2 — Group service
- [x] Step 3 — Group booking API
- [x] Step 4 — Group management UI
- [x] Phase close — tag v0.30.0-group-booking

**Phase 41 — Wave 1 / Nearby attractions: COMPLETE**
Tag: v0.31.0-nearby
- [x] Step 1 — Attraction model + migration + seed (12 Dubai attractions)
- [x] Step 2 — Attraction service + public API
- [x] Step 3 — Nearby attractions UI on tenant page
- [x] Phase close — tag v0.31.0-nearby

**Phase 42 — Recent searches: COMPLETE**
Tag: v0.32.0-recent-searches
- [x] Step 1 — RecentSearch model + API
- [x] Step 2 — Recent searches UI in /search
- [x] Phase close — tag v0.32.0-recent-searches

**Phase 43 — Price alerts: COMPLETE**
Tag: v0.33.0-price-alerts
- [x] Step 1 — PriceAlert model + service + API
- [x] Step 2 — Price alerts UI + watch button
- [x] Phase close — tag v0.33.0-price-alerts

**Phase 44 — Loyalty redemption: COMPLETE**
Tag: v0.34.0-loyalty-redeem
- [x] Step 1 — Redeem service + API
- [x] Step 2 — Redeem page UI
- [x] Phase close — tag v0.34.0-loyalty-redeem

**TIER 1+2 = 100% complete after Phase 44.**

### Phase 45 — AI Location Recommender (Wave 2): COMPLETE
Tag: v0.35.0-ai-location
- Step 1 — AI Location Recommender service
  - Deterministic layer: nearby attractions + nearby services via Haversine
  - User preference inference from past bookings (top category)
  - AI layer: short grounded recommendation (en/ar/fil/hi)
  - Deterministic fallback if AI fails
- Step 2 — Public API: POST /ai/location/recommend (15/min)
  - Optional auth (best-effort user detection via Bearer token)
  - Returns { attractions, services, advice, provider }
- Step 3 — UI on /search
  - "✨ AI Recommend here" button in map controls
  - Panel showing AI advice + Nearby places + Nearby businesses
  - Uses current map center, else Dubai (25.2048, 55.2708) fallback

### Phase 46 — AI Trip Memory (Wave 2): COMPLETE
Tag: v0.36.0-ai-trip-memory
- Step 1 — AI Trip Memory service (app/services/ai/trip_memory.py)
  - Deterministic profile: total trips, favorite category, cities,
    avg price + band, currency, avg guests, preferred months, top tenants
  - Excludes cancelled bookings
  - AI recap grounded in the profile (en/ar/fil/hi)
  - Deterministic fallback when AI fails
- Step 2 — API: GET /account/api/ai/memory (auth required, 30/min)
  - Returns { profile, recap, suggestions, provider }
  - 422 on unsupported language
- Step 3 — UI on /account/ai
  - "🧠 My Trip Memory" button reveals panel with recap + 6 profile pills
    + "Most visited" list; lazy-loaded on first open

### Phase 50 — AI Budget Optimizer (Wave 2, AI depth): COMPLETE
Tag: v0.40.0-budget-optimizer
- Step 1 — AI Budget Optimizer service (app/services/ai/budget_optimizer.py)
  - Deterministic allocation policy (fixed, transparent):
      hotels 50%, restaurants 25%, entertainment 15%, travel 10%
  - Categories with no candidates are skipped; their allocation is
    redistributed proportionally among present categories
  - Per-category heuristic: highest-rated service whose estimated
    total cost fits the allocation; fallback to cheapest
  - Estimated total uses days (hotels) or min(days,3) (others), and
    guests only for hotels
  - AI writes rationale grounded ONLY in the chosen package (4 langs)
  - Deterministic fallback always available
- Step 2 — Public API: POST /api/budget-optimize (15/min)
  - Validates budget, days, guests, language
  - Returns { package[], total_estimated, budget, currency, remaining,
    advice, provider }
- Step 3 — UI on /account/ai
  - "💸 Budget Optimizer" button reveals panel with city/days/guests/
    budget/currency + Optimize button
  - Renders advice + recommended package list + totals

### Phase 49 — Trust Score per Business (Wave 3, Blue-Ocean B11): COMPLETE
Tag: v0.39.0-trust-score
- Step 1 — Trust Score service (deterministic, no AI, no new table)
  - Composite 0..100 from 4 components:
      Rating 40% (avg review rating), Volume 20% (30-day paid bookings,
      log-scaled), Verification 20% (verified / published reviews),
      Responsiveness 20% (responded / published reviews)
  - Neutral 50 baseline for rating/verification/responsiveness when
    no reviews exist; volume falls to 0
  - Excludes hidden reviews and cancelled bookings from volume
  - Helpers: compute, get_by_slug, compute_many, tier_label
- Step 2 — Public API
  - GET  /api/trust-score/{tenant_slug}    (60/min)
  - POST /api/trust-score/bulk             (30/min, max 50 ids)
  - 404 on unknown tenant, 422 on bad bulk request
- Step 3 — Search integration + UI badge
  - search_service enriches each item with "trust_score"
  - SearchItem schema exposes trust_score (float | None)
  - search.html renders 🛡️ badge next to rating

### Phase 48 — Smart Waitlist (Wave 3, Blue-Ocean B8): COMPLETE
Tag: v0.38.0-waitlist
- Step 1 — WaitlistEntry model + service
  - Model: user_id + service_id + check_in + check_out (unique),
    guests, active, notified_at, position_at_join
  - Service: is_full (capacity vs overlapping active bookings),
    join (FIFO position), list_entries (enriched with position),
    leave, check_and_notify (FIFO first un-notified)
- Step 2 — API under /me/waitlist
  - GET /        list user's entries (active_only optional)
  - POST /       join (409 if not full, 422 bad dates, 404 service)
  - DELETE /{id} leave
  - POST /check  on-demand FIFO notify if capacity freed
- Step 3 — UI page /account/waitlist
  - List with Waiting/Notified/Left badge, position, dates, guests
  - "Show all" toggle, leave per entry
- Step 4 — Auto-notify integration
  - Hook in booking_service.cancel_booking
  - Hook in cancellation_service.cancel_booking
  - Best-effort try/except (never breaks cancellation)

### Phase 47 — Predictive Price Locks (Wave 3, Blue-Ocean B7): COMPLETE
Tag: v0.37.0-price-locks
- Step 1 — PriceLock model + service
  - Model: user_id + service_id (unique), locked_price, currency,
    active, expires_at, consumed_at, consumed_booking_id
  - Service: create_lock (replaces existing), get_active_lock,
    list_locks (enriched), consume_lock, delete_lock
  - Window bounds: 1..168 hours (default 48)
  - Excludes inactive services; excludes cancelled/consumed locks
- Step 2 — API under /me/price-locks
  - GET /        list user's locks (active_only optional)
  - POST /       create/replace a lock
  - DELETE /{id} remove a lock
  - POST /consume mark consumed by a booking
  - 404 on missing service/booking, 409 on inactive lock, 422 on bad window
- Step 3 — UI page /account/price-locks
  - List with locked vs current price, "Saving" badge when live > locked
  - Remaining-time formatter, "Show all" toggle, remove per lock
- Step 4 — "🔒 Lock" button on each /search card
  - Prompt for hours (1-168), calls POST /me/price-locks

Temporary policy note: 3 default redeem options (500/1000/2000 pts -> 25/50/100 AED).
To be replaced when the user provides the final Rewards + Referral plan (Phase 24).

---

## WAVE 1 COMPLETE (v0.31.0-nearby)

Phases 32, 33, 34, 35, 36, 37, 38, 39, 40, 41 all done.
Total tests: 1011. Public API + Webhooks + All Wave 1 features live.
NEXT WAVE: Wave 2 — AI depth.

---

## 1. Project Overview

**Name:** Platform-X (working name)
**Type:** Multi-tenant smart platform for hospitality, travel, entertainment
**Purpose:** Hotels, restaurants, entertainment centers, travel agencies — one platform
**Long-term vision:** Modern alternative to Booking.com/Agoda/Expedia, multi-service

**First real tenant (future):** Trianon Royal Hotel
**Trianon existing site:** https://intermediate-aims-insights-metal.trycloudflare.com

---

## 2. Working Rules (NON-NEGOTIABLE)

1. Backup before every change (file-level with timestamp)
2. One step at a time — test after each change
3. Commit after every success
4. Handoff after every session
5. Test before claiming done
6. NEVER add features from yourself — follow roadmap
7. NEVER change architecture without explicit user approval
8. Do NOT ask the user technical decisions — decide as Tech Lead
9. Do NOT skip phases — finish current phase before next
10. Quality bar: EXCELLENCE — no shortcuts, no bugs, production-ready

**Language:** All responses in Persian (Farsi). Direct, no fluff.

---

## 3. Environment

- Platform: Termux on Android (mobile phone)
- Python: 3.13.13
- Repo: ~/platform-x
- Venv: ~/platform-x/venv

Backups: ~/platform-x/backups/
Logs: ~/platform-x/logs/

---

## 4. Tech Stack (Locked)

- Backend: FastAPI 0.115
- Database: SQLite (dev/Termux) → PostgreSQL (production VPS later)
- ORM: SQLAlchemy 2.0
- Migrations: Alembic
- Auth: JWT (python-jose) + bcrypt
- Templating: Jinja2
- Styling: Custom CSS (Light Hospitality theme) + Design System
- Fonts: Plus Jakarta Sans (display), Inter (body), JetBrains Mono (code)
- Testing: pytest + httpx TestClient
- Deploy: Cloudflare Quick Tunnel (Termux) → Named Tunnel + VPS later

---

## 5. Phases Status

### Phase 0 — Strategic Documents: COMPLETE
### Phase 0.5 — Executive Documents: COMPLETE

### Phase 1 — First Tenant Live: SKIPPED (intentional)
Reason: Build platform core first, migrate real tenants later.

### Phase 2 — Core Architecture: COMPLETE
Tag: v0.1.0-core
- 16 ORM models (see section 6)
- ~65 API routes
- JWT auth (users + platform admins, separated)
- Payment provider abstraction (mock for dev)
- Rewards tiers: welcome→silver→gold→platinum→royal
- Referrals with point awards (100/50)
- Notifications (5 channels)
- Analytics events
- Alembic migrations
- Production hardening (fail-fast config)
- Full demo seed

### Phase 3 — Frontend: COMPLETE
Tag: v0.2.0-frontend
- Jinja2 + custom CSS
- Design System v1 (dark luxury, later replaced)
- All pages: home, businesses, login, register, about, contact,
  tenant_home, tenant_book, tenant_pay, tenant_account
- Cloudflare Tunnel #2 online
- Always-on (wakelock + Termux:Boot)

### Phase 4 — UI Redesign + Rich Demo: COMPLETE
Tag: v0.3.0-polish
- **NEW: Light Hospitality theme** (cream white + navy #0f3d5c + gold accent #c9a961)
- **NEW: 4 Category colors** (hotels blue, restaurants red, travel green, entertainment purple)
- **NEW: platform.css** (light theme tokens + components)
- **NEW: platform-home.css** (all home/category/detail styles, 1500+ lines)
- **NEW: Plus Jakarta Sans** display font
- **NEW: 21 businesses seeded** with Unsplash images (5 hotels, 5 restaurants, 6 agencies, 5 entertainment)
- **NEW: Home** (Hero + Stats Strip + Categories + 4 Featured sections + Steps + CTA)
- **NEW: Business Detail** (Hero + Info bar + Gallery + Services)
- **NEW: Split Auth layout**
- **NEW: Account Dashboard** (Category browser + Rewards Panel + Stats + Recent Activity + Tabs)
- **NEW: 404 page**
- **NEW: Micro-interactions**

### Phase 5 — Full Feature Verification + Partner Onboarding: COMPLETE
Tag: v0.4.0-full-flow
- Platform-wide auth: users book across ALL tenants (major architecture change)
- Cross-tenant Bookings/Orders in account
- Rewards auto-award on payment
- Dynamic booking form per business type (hotel/restaurant/travel/entertainment)
- Payment page shows user details (name/email/phone)
- Phone uniqueness handling (409, not 500)
- Entertainment time slot added
- Account: category browser removed New Booking (misleading)
- Partner onboarding form (/partners/apply)
  - 6-step dynamic form (type → contact → business → specifics → plan → about)
  - Type-specific fields for each business type
  - Backend: PartnerApplication model + POST /partners/apply + admin list endpoint
- Header restructure: avatar outside mobile menu
- Stats strip on home (businesses, services, categories, locations) with count-up animation

---

### Phase 29 — Business Leaderboard + AI Scoring: COMPLETE
Tag: v0.14.0-leaderboard
- BusinessScore model + migration (17 columns, indexes for leaderboard)
- Scoring Engine: 5 criteria computed deterministically from DB
  (Customer Satisfaction 30%, Service Quality 25%, Pricing Competitiveness 20%,
   Engagement 15%, Loyalty 10%)
- Leaderboard service: recompute + ranks (overall + per category) +
  rewards mapping (Gold/Silver/Bronze) + leaderboard query + tenant score lookup
- Leaderboard AI Tips: AI grounded in real numbers, deterministic fallback
- Public API: /api/leaderboard, /api/leaderboard/categories
- Business API: /business/api/score, /business/api/score/tips
- Platform API: /platform/api/leaderboard/recompute (admin-only, 5/min)
- Public /leaderboard page (tabs per category, badges, mini-bars)
- Business /business/score widget (overall + 5 criteria + rewards + AI tips)
- Badges on business cards (businesses.html, home, category pages)
- recompute_scores CLI (python -m app.scripts.recompute_scores)
- NOTE: public API path is /api/leaderboard (HTML page occupies /leaderboard)

### Phase 23 — AI Content Writer + Importer: COMPLETE
Tag: v0.15.0-content-ai
- AI Content Writer service:
  - write_service_description (4 languages x 4 tones)
  - write_business_tagline
  - suggest_image_keywords (Unsplash URLs, no API key)
  - AI never invents facts (rating only mentioned if >= 4.5)
  - Deterministic fallback always available
- Business Content API (6 endpoints under /business/api/ai/content):
  - POST /service/{id}          generate description (preview)
  - POST /service/{id}/apply    generate + save (owner/manager only)
  - POST /tagline               business tagline
  - POST /image-keywords/{id}   keyword list + Unsplash URLs
  - POST /import/preview        parse free text into candidates
  - POST /import/create         bulk-create services (owner/manager only)
- AI Menu/Room Importer:
  - Parses menus, room lists, packages from text
  - AI never invents prices (null if missing; validated on save)
  - Deterministic line-based fallback (' - ', ': ', trailing number)
- Content Studio UI at /business/content:
  - Tagline generator (EN/AR/FIL/HI)
  - Import from raw text (paste + parse + preview candidates + create)
  - Per-service description generate + apply
  - Dark theme, responsive
- NOTE: URL Onboarding deferred to Phase 13 (Business Onboarding Tools)

### Phase 25 — AI Marketing Copilot: COMPLETE
Tag: v0.16.0-marketing-ai
- Marketing service: customer segmentation
  - 6 segments: all, past_bookers, inactive_90d, high_value (top 20%),
    new_30d, loyalty_gold_plus
  - Read-only; cross-tenant isolated; suspended users excluded
- AI Campaign Writer:
  - suggest_campaigns (3-5 grounded ideas per tenant, AI sees only counts)
  - generate_campaign (targeted by segment + goal)
  - AI never invents discounts; deterministic fallback always available
- AI Discount Suggester:
  - Fixed platform policy (max 20%): inactive_90d 15%, high_value 12%,
    loyalty_gold_plus 10%, new_30d 10%, past_bookers 8%, all 5%
  - AI writes ONLY the rationale; deterministic impact estimate
  - Platform cap enforced even if policy tampered
- Business Marketing API (7 endpoints under /business/api/marketing):
  - GET  /config              return email_enabled flag
  - GET  /segments            segmentation summary
  - GET  /segments/{name}     full email list (owner/manager only)
  - POST /campaigns/suggest   AI 3-5 ideas
  - POST /campaigns/generate  AI targeted campaign
  - POST /discounts/suggest   AI policy-bounded discounts
  - POST /campaigns/send      send (owner/manager), dry-run if EMAIL_ENABLED=false
- Marketing Copilot UI at /business/marketing:
  - Segments grid (click to view emails)
  - AI campaign ideas (language picker)
  - Targeted campaign generator
  - Discount suggestions with impact estimate
  - Send campaign form (subject + body)
  - Config badge (Sending enabled / Dry run only)
- Email sending gated by EMAIL_ENABLED (Phase 11 integration)
- NOTE: Phase 8 and Phase 24 merged; both WAITING for user's
  Rewards + Referral business plan.

### Phase 26 — Real-Time Occupancy + Analytics: COMPLETE
Tag: v0.17.0-occupancy
- Occupancy service:
  - occupancy_summary (booked nights vs capacity nights, clamped to window)
  - occupancy_by_service (per-service breakdown, sorted by occupancy)
  - occupancy_trend (current vs previous window + delta %)
  - Excludes cancelled bookings; capacity-only services counted
- Heatmap service:
  - day_of_week_heatmap (Mon..Sun + share %)
  - hour_of_day_heatmap (0-23, uses created_at as proxy)
  - calendar_heatmap (per-day series + peak)
  - Handles naive SQLite datetimes correctly
- Revenue forecast:
  - forecast_revenue: weighted daily avg (0.7*a30 + 0.3*a90) * growth * days
    growth from last 30 vs prior 30 (clamped +/-50%)
    +/-20% band
  - forecast_with_advice: same + AI interpretation + fallback
  - Only PAID bookings count; cancelled excluded
- Predictive capacity:
  - available_capacity per day + summary (min/max/avg)
  - near_fully_booked (threshold %)
  - next_available_date(service, guests) with bounded search
- Business Insights API (9 endpoints under /business/api/insights):
  - /occupancy, /occupancy/trend, /occupancy/by-service
  - /heatmap/day-of-week, /heatmap/hour-of-day, /heatmap/calendar
  - /revenue/forecast?days=&with_advice=
  - /capacity/available, /capacity/near-full, /capacity/next-available/{id}
  - Rate limits: 60/min reads, 15/min AI forecast
- Insights UI at /business/insights:
  - 4 KPI cards (occupancy %, booked nights, revenue 30d, forecast 30d)
  - Day-of-week heatmap, calendar heatmap (5 intensity levels, CSS-only)
  - Capacity summary + near-full days list
  - Revenue forecast with AI advice button
  - Days selector (30/90/180)
  - Dark theme, responsive

### Phase 27 — Competitor / Market Insights: COMPLETE
Tag: v0.18.0-market-insights
- Market Insights service (anonymized):
  - category_summary: quartiles (min/p25/median/p75/max/avg) of
    avg_price, rating, service_count, bookings_30d per category
  - tenant_position: percentile of self vs cohort
  - region_summary: aggregate peers by region (config.location last segment)
  - market_insights: combined output
  - Peer identities NEVER exposed (tested)
- AI Market Analyst:
  - highlight_strengths_and_weaknesses (deterministic from percentiles)
  - interpret_market: AI summary + advice (4 languages)
  - Robust JSON parsing (handles str, list, dict output variants)
  - Fallback text always available
- Business Market API (5 endpoints under /business/api/market):
  GET /summary, /position, /region, /insights, /insights/ai
  Rate limits: 30/min reads, 10/min AI
- Market Insights UI at /business/market:
  cohort card, position cards (percentile bars),
  strengths/weaknesses lists, benchmark table,
  AI interpretation with EN/AR/FIL/HI picker
- 43 new tests
- 10 smoke checks with real Gemini
- Bug found and fixed during smoke: AI can return advice as list
  or summary as dict; added _as_text() coercion + regression tests

### Phase 28 — AI Review Writer + Responder: COMPLETE
Tag: v0.19.0-reviews
- Review model + migration (19 columns, 3 indexes)
- Review service (deterministic):
  - compute_sentiment: lexicon (EN/AR/FIL/HI) + rating prior
  - create_review with verified-booking check
  - list / get / hide / set_response
  - tenant_review_summary (counts, avg, sentiment breakdown, verified)
- AI Review Writer/Responder:
  - polish_review: rewrite raw guest text (4 languages)
  - respond_to_review: professional reply (3 tones)
    Negative -> acknowledge + apologize + invite contact
    No promises of compensation
    Deterministic fallback per sentiment
- API:
  - /reviews/tenant/{slug} (public), /reviews (create), /reviews/mine
  - /business/api/reviews (list), /summary, /{id}/hide,
    /{id}/respond (AI or manual), /{id}/respond/preview, /polish
- UI:
  - Business Reviews page at /business/reviews
    (KPIs, list, response modal, AI preview, language + tone)
  - Reviews section on tenant home page (5 most recent published)
- 60+ tests, 12 smoke checks
- Bug fix during smoke: missing {% endif %} broke tenant_home.html

### Phase 30 — Wave 0 part A (Foundation, free): COMPLETE
Tag: v0.21.0-wave0-part-a
- Search: cross-tenant with dates, guests, filters, sort, currency
  - GET /api/search (60/min)
  - GET /search HTML page (client-side)
  - Home hero search form
- Availability:
  - GET /api/availability/{tenant_slug}?days=N
  - Calendar section on tenant page (14 days, colors, click-to-book)
- Cancellation + Refund:
  - Deterministic policy (>7d full, 3-7d partial, <72h none)
  - GET /bookings/{id}/refund-preview
  - POST /bookings/{id}/cancel-with-refund
  - Cancel button + modal in account page
- Multi-currency:
  - Fixed rates AED/USD/EUR/GBP/SAR
  - API + service integration
  - Dropdown in /search
- Booking receipt (print to PDF):
  - GET /bookings/{id}/receipt
  - Print/Save-as-PDF button
- PWA:
  - manifest.webmanifest, service worker, SVG icon
  - Registered in base layout
- Extended filters:
  - min_rating, service_type, location
  - UI in /search form
- Service gallery:
  - GET /services/{id}/gallery
  - Gallery section on tenant page with lightbox

**Not done (part B — needs purchases):**
- VPS + Domain + Named Tunnel
- Payment production (Telr/Stripe)

### Phase 14 — Public API + Webhooks + SDK: COMPLETE
Tag: v0.20.0-public-api
- APIKey model + service:
  - pk_live_ prefix, SHA-256 storage, scopes, expiry
  - constant-time auth (prefix lookup + hmac.compare_digest)
  - scopes: read:services, read:bookings, read:orders,
    read:reviews, read:analytics, write:webhooks
- Public API v1 (X-API-Key header, tenant-scoped):
  - GET /api/v1/me
  - GET /api/v1/services[/{id}]
  - GET /api/v1/bookings[/{id}]
  - GET /api/v1/reviews
  - GET /api/v1/analytics/summary?days=N
  - Read-only, paginated, scope-enforced
- Webhook model + service:
  - events: booking.created, booking.confirmed, booking.cancelled,
    payment.paid, review.created, review.responded
  - HMAC-SHA256 signature header: X-PlatformX-Signature: sha256=<hex>
  - Delivery log (WebhookDelivery) with status/response/error
  - URL rule: https or http://localhost (dev only)
- Business panel:
  - /business/api-keys: list/create/revoke API keys
  - Webhooks section on the same page: list/create/delete
- Public documentation:
  - /docs/api: overview, scopes, endpoints, Python/JS/cURL examples,
    webhook signature verification, error table, Swagger link
- KNOWN LIMITATION (technical debt):
  - Webhook secrets are stored as SHA-256 hash only; system-triggered
    delivery requires plaintext secret. Future phase: encrypted
    secret storage (per-installation symmetric key).
- 60+ tests, 13 smoke checks
- All AI-focused phases + Public API now complete.

### Phase 20 — Business Owner Panel: COMPLETE
Tag: v0.9.0-business
- Separate panel under /business/*
- Business login, dashboard, services CRUD, bookings inbox, customers,
  analytics, staff accounts (owner/manager/staff), settings
- Business notifications on new bookings

### Phase 21 — AI Business Assistant (Pricing Coach): COMPLETE
Tag: v0.12.0-pricing-coach
- Business Context Builder (real DB -> structured AI context, deterministic)
- Pricing Coach service: analyze / suggest / forecast / insights
  (metrics computed in Python, AI only advises on top of real numbers)
- 5 endpoints under /business/api/ai
- UI: two tabs (Chat + Pricing Coach), dark-theme compatible
- Bugfixes: account/ai tenant resolution, hardcoded business slug

### Phase 22 — Dynamic Pricing Rules: COMPLETE
Tag: v0.13.0-dynamic-pricing
- PricingRule + PricingRuleApplication models + Alembic migration
- Pricing Rules service (evaluate / compute / preview / record_application)
  Rule types: weekend / season / urgency / capacity / last_minute / custom
  Actions: percent (+/-), fixed (+/-), Decimal math, floor at 0
- Business Pricing API: 6 endpoints under /business/api/pricing
- Booking integration: opt-in via apply_pricing_rules=True (server-computed
  base price, priority-ordered stacking, audit per rule)
- UI: Rule Builder page in Business Panel (/business/pricing)
- Automated smoke test: scripts/smoke-pricing-rules.sh (11 checks)

### Phase 37 — Rate Plans: COMPLETE
Tag: v0.27.0-rate-plans
- RatePlan model (15 columns; unique per tenant+service+code)
- Service: CRUD + apply_plan_to_price (percent / fixed, floor at 0)
- API:
  - /business/api/rate-plans (GET/POST/PATCH/DELETE, owner/manager)
  - /services/{id}/rate-plans (public, active only)
- Booking integration: optional rate_plan_id; modifier applies to
  SERVICE base price (not client-supplied amount); 400 on invalid id
- UI: /business/rate-plans page + sidebar link
- Bugfix during phase: rate plan applies to service price, not client amount

### Phase 38 — Promotions Engine: COMPLETE
Tag: v0.28.0-promotions
- Promotion model (18 columns; unique per tenant+code)
- Service: CRUD + validate (active, dates, caps, min_amount,
  service restriction) + apply (percent/fixed, floor at 0)
- Business API: GET/POST/PATCH/DELETE + POST /validate (preview)
- Booking integration: optional promotion_code applies discount to
  SERVICE base price; used_count incremented; 400 on invalid code
- UI: /business/promotions page + sidebar link
- Bugfix during phase: promotion applies to service price, not
  client amount

### Phase 39 — Reviews Photos + Guest Messaging: COMPLETE
Tag: v0.29.0-reviews-messaging
- ReviewPhoto model (8 columns; max 3 per review, JPG/PNG/WebP, 5 MB)
- Photo upload API (POST /reviews/{id}/photos, DELETE .../photos/{id})
- Tenant page renders photos with lightbox
- Account: write-review modal with rating, title, body, photo upload
- Message model (11 columns; thread per booking)
- Messages service (thread listing with unread counts, mark-read)
- Messages API (user: /messages/*, business: /business/api/messages/*)
- Business Messages inbox page + sidebar link
- 981 tests passing

### Phase 40 — Group Booking: COMPLETE
Tag: v0.30.0-group-booking
- GroupMember model (10 columns; unique email per booking)
- Booking.is_group boolean (default False)
- Group service: add/update/remove/list members with share validation
  (total shares cannot exceed booking total; max 50 members)
- share_summary: booking_total / shares_total / paid / unpaid / remaining
- Group API: /bookings/{id}/group (GET, POST, PATCH/{member}, DELETE/{member})
- Group management modal in account with add/mark-paid/remove
- 1003 tests passing (milestone: crossed 1000)

### Phase 41 — Nearby Attractions: COMPLETE
Tag: v0.31.0-nearby
- Attraction model (platform-scoped, shared across tenants)
- Seed of 12 Dubai attractions
- Attraction service (list_all, nearby via Haversine)
- Public API: /api/attractions, /api/attractions/nearby?lat=&lng=&radius_km=
- UI: Nearby attractions section on tenant page
- 1011 tests passing

## WAVE 1 MILESTONE — 2026-09-30

Wave 1 (Competitive Parity) is COMPLETE:
- 32: Map + Location
- 33: Wishlist + Compare
- 34: Reports (CSV + PDF)
- 35: Booking modification + No-show
- 36: Room inventory
- 37: Rate Plans
- 38: Promotions Engine
- 39: Reviews Photos + Guest Messaging
- 40: Group Booking
- 41: Nearby Attractions
- 10 phases, 1011 tests, all green.

NEXT: Wave 2 (AI depth — connects AI to the Wave 1 foundation).

### Phase 42 — Recent Searches: COMPLETE
Tag: v0.32.0-recent-searches
- RecentSearch model (12 columns; user-scoped, max 10 kept)
- API: /me/recent-searches (GET, POST, DELETE)
- Auto-save on search with at least one meaningful filter
- Dedupe by (check_in, check_out, category, location)
- UI: recent chips above the /search form; click to restore

### Phase 43 — Price Alerts: COMPLETE
Tag: v0.33.0-price-alerts
- PriceAlert model (11 columns; user-scoped)
- Service: create/list/delete + on-demand check (current vs target)
- API: /me/price-alerts (GET, POST, DELETE, POST /check)
- UI: /account/price-alerts page + "Watch" button on search results
- Notified_at set on first trigger; no auto-scheduler (deferred to VPS)

### Phase 44 — Loyalty Redemption: COMPLETE
Tag: v0.34.0-loyalty-redeem
- RedeemOption model (9 columns; catalog lives in DB)
- Default catalog (TEMPORARY): 500/1000/2000 pts -> 25/50/100 AED credit
- Redeem service: list + redeem (deducts points via reward_service)
- API: GET /rewards/redeem-options + POST .../{id}/redeem
- UI: /account/redeem page with live balance + Redeem buttons

WARNING: This catalog is intentionally temporary. Final catalog will be
defined by the user's Rewards + Referral business plan (Phase 24).
Changing it = edit seed + re-run.

## 6. Data Models (19 tables)

Global:
- tenants (slug, name, tier, status, config JSON with branding/images/rating)
- platform_admins (email, role, mfa fields)
- audit_logs (actor, action, target, changes)
- subscriptions (tenant plan, billing)

Per-tenant (all have tenant_id):
- users (email, phone, password_hash, points, tier, referral_code, home_tenant_id via tenant_id)
- sessions (auth tokens)
- bookings (booking_type, service_id, check_in, check_out, guests, amount, status)
- services (type, name, price, image_urls, attributes)
- orders (service_type, quantity, amount, status)
- payments (booking_id OR order_id, provider, provider_reference, status)
- rewards (reward_type: earn/redeem/adjust, points)
- referrals (referrer_user_id, referred_user_id, reward_points)
- notifications (channel, template, content, status)
- analytics_events (event_type, metadata)

New in Phase 5:
- partner_applications (tenant_type, contact info, business info, tier_interest, languages, details JSON, status)

New in Phase 18-19:
- ai_chat_messages (tenant_id, user_id, layer (user|business), role, content, provider, tokens_used)

New in Phase 22:
- pricing_rules (tenant_id, name, description, active, priority, rule_type,
  conditions JSON, action JSON, service_ids JSON, valid_from, valid_to, created_by_user_id)
- pricing_rule_applications (tenant_id, rule_id, service_id, booking_id,
  original_price, adjusted_price, delta_amount, delta_percent, currency, note)

New in Phase 29:
- business_scores (tenant_id, category, period_start, period_end,
  overall_score, customer_satisfaction, service_quality,
  pricing_competitiveness, engagement, loyalty, rank_overall,
  rank_in_category, criteria_breakdown JSON, computed_at)
  UniqueConstraint(tenant_id, period_start, period_end)
  Indexes: (category, period_end, overall_score DESC) for leaderboard,
           (tenant_id, period_end) for tenant lookup

---

## 7. Key Architecture Decisions

### Platform-wide Users (Phase 5, CRITICAL)
- Users register on a "home tenant" but can book across ALL tenants
- JWT carries user_id + home tenant_id (reference only)
- Active tenant always from X-Tenant-Slug header
- get_current_user does NOT enforce tenant match
- Bookings/Orders/Payments use X-Tenant-Slug for the target tenant
- Account dashboard uses ?all=true to fetch across all tenants

### Multi-Tenancy
- Every tenant-scoped API needs X-Tenant-Slug header
- Fallback to DEFAULT_TENANT_SLUG for dev convenience
- Frontend: tenant slug from URL path (/{slug}/...) or default fallback

### Routes
- HTML routes at /login, /register, /hotels, /restaurants, /travel, /entertainment, /account, /partners/apply, /partners/thanks
- Tenant-scoped HTML: /{slug}/, /{slug}/book, /{slug}/pay, /{slug}/account
- API under /auth, /bookings, /orders, /payments, /rewards, /referrals, /notifications, /analytics, /platform, /partners
- Catch-all 404 last (after API, after reserved, after tenant)
- TrailingSlashRedirectMiddleware: /login/ → /login (for reserved slugs)

### Auth
- Users: POST /auth/register, POST /auth/login, GET /auth/me
- JWT contains sub (user_id), tenant_id (home), iat, exp
- Platform admins: POST /platform/auth/login, GET /platform/me
- JWT contains sub, actor=platform_admin, role

### Payment
- MockPaymentProvider for dev
- POST /payments/intent → returns redirect_url
- GET /payments/mock/confirm/{ref} → confirms (disabled in production via ENABLE_MOCK_PAYMENTS=false)
- POST /payments/webhook/{provider} → real provider callbacks
- On successful payment: booking.status confirmed, payment_status paid, reward points awarded (1pt per 10 units, min 5)

### Rewards
- Tiers: welcome (0), silver (500), gold (2000), platinum (5000), royal (15000)
- Auto-award on booking/order payment
- GET /rewards/me → summary with progress
- GET /rewards/history → paginated
- POST /rewards/redeem → redeem earn reward

### Referrals
- Each user has referral_code
- POST /referrals/apply → link user to referrer (once)
- Awards 100 pts (referrer) + 50 pts (referred)
- GET /referrals/me → code + list

---

## 8. Live URLs

Platform-X (dev demo):
https://larger-stable-are-southwest.trycloudflare.com

Trianon (existing, separate):
https://intermediate-aims-insights-metal.trycloudflare.com

Tunnel type: Cloudflare Quick Tunnel (URL may change on cloudflared restart)
Tunnel URL saved at: ~/platform-x/logs/tunnel.url

Get current URL: cat ~/platform-x/logs/tunnel.url

---

## 9. Runit Services (Termux)

Location: /data/data/com.termux/files/usr/var/service/

| Service | Purpose | Port |
|---|---|---|
| trianon | Trianon frontend (http.server) | 8000 |
| trianon-backend | Trianon FastAPI | 8001 |
| wordsmart-tunnel | Word Smart project tunnel | 8020 |
| platform-x-api | Platform-X FastAPI | 8030 |
| platform-x-tunnel | Platform-X Cloudflare tunnel | — |

Boot script: ~/.termux/boot/start-services.sh (requires Termux:Boot app)
Wake lock: Enabled (keeps services alive when Termux closed)

Management:
  sv status platform-x-api platform-x-tunnel
  sv up platform-x-api
  sv down platform-x-api
  sv restart platform-x-api

---

## 10. Demo Data

5 hotels:
- trianon-hotel (Trianon Royal Hotel) — 4.8★, Downtown Dubai
- azure-palm-resort (Azure Palm Resort) — 4.9★, Palm Jumeirah
- aurora-boutique (Aurora Boutique Hotel) — 4.7★, Alserkal
- marina-skylines (Marina Skylines Hotel) — 4.6★, Dubai Marina
- desert-rose-hotel (Desert Rose Hotel) — 4.5★, Al Fahidi

5 restaurants:
- saffron-restaurant (Modern Middle Eastern)
- olive-grove (Mediterranean)
- sakura-sushi (Japanese)
- the-copper-kitchen (European)
- spice-route-indian (Indian)

6 travel agencies:
- skyways-travel, horizon-voyages, caravan-tours, euro-explorer, blue-ocean-cruises, desert-tours

5 entertainment:
- oasis-entertainment (Family park), skypark-adventures (Ziplines),
- aqua-world (Waterpark), virtual-realm (VR), cinema-royale (Cinema)

Services: 127 across all tenants (auto-generated via seed_services_auto.py)

Platform Admin:
- Email: admin@platform-x.local
- Password: ChangeMe123! (CHANGE BEFORE PUBLIC DEMO)

Seed commands:
  python -m app.scripts.seed_all
  python -m app.scripts.seed_tenants
  python -m app.scripts.seed_services_auto
  python -m app.scripts.seed_admin

All idempotent.

---

## 11. Remaining Work

**Phase 24 (merged with Phase 8) — Cross-Business Rewards: DEFERRED BY USER**
User (2026-09-29): do NOT start until explicitly told.

**All AI-focused phases + Public API are COMPLETE.**
**Phase 45 (AI Location Recommender) is COMPLETE — Wave 2 first deliverable.**
**Phase 46 (AI Trip Memory) is COMPLETE — Wave 2 second deliverable.**
**Phase 47 (Predictive Price Locks) is COMPLETE — Wave 3 first deliverable.**
**Phase 48 (Smart Waitlist) is COMPLETE — Wave 3 second deliverable.**
**Phase 49 (Trust Score per Business) is COMPLETE — Wave 3 third deliverable.**
**Phase 50 (AI Budget Optimizer) is COMPLETE — Wave 2 continuation.**

Remaining phases all require user-side decisions or purchases:
- Phase 10 (Payment Production / Telr) — needs business account
- Phase 12 (VPS + Domain + Named Tunnel) — needs purchase
- Phase 13 (Business Onboarding Tools) — needs Phase 12
- Phase 15 (Trianon Migration) — after VPS
- Phase 16 / 30 (Mobile App) — long-term

**Technical debt (from Phase 14):**
- Webhook secret storage: currently SHA-256 only. To enable
  system-triggered deliveries, need encrypted secret storage
  (planned for a future phase, before production).

**Suggested next moves (all pending user):**
- Purchase VPS + domain → Phase 12 (VPS deploy)
- Get Telr/Stripe account → Phase 10 (Payment production)
- Provide Rewards plan → Phase 24


## 12. Future Phases (v2 Roadmap)

### Phase 6 — Security Hardening: COMPLETE (v0.5.0-security)
- Rate Limiting (login, register, partners, APIs)
- Security Headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
- JWT Refresh Tokens (access + refresh pattern)
- Password Policy + account lockout after 5 fails
- Session Revocation (real logout)
- CSRF Protection (HTML forms)
- XSS Sanitization audit
- SQL Injection audit
- HTTPS Enforcement (redirect HTTP → HTTPS)
- CORS Production (real domains only)
- 2FA for Platform Admin (model exists, UI needed)
- Audit Log coverage
- Secrets Management
- Backup Strategy (daily + off-site)
Estimate: 10-12 steps

### Phase 7 — Admin Panel UI: COMPLETE
Tag: v0.6.0-admin

### Phase 9 — i18n (4 languages): COMPLETE
Tag: v0.7.0-i18n
- EN, AR (RTL), FIL, HI — 186 keys each
- Language switcher (🌍 globe) in header
- All public pages + JS strings translated
- 154 tests passing

### Phase 8 — Rewards + Referral: WAITING (user plan pending)
### Phase 10 — Payment Production (Telr): AVAILABLE
### Phase 11 — Notifications: COMPLETE
Tag: v0.8.0-notifications
- Email service (Resend, EMAIL_ENABLED flag)
- 3 templates: welcome, booking_confirmed, password_reset
- Password Reset Flow (forgot + reset pages, hashed tokens)
- Auto-notifications on register/payment/reset
- Notification Center UI (account tab, badge, mark-as-read)
- 4 languages for notification UI
- SMS/WhatsApp deferred
- 154 tests passing
### Phase 12 — VPS Deploy + Domain + Named Tunnel: AVAILABLE
### Phase 13 — Business Onboarding Tools: AVAILABLE
### Phase 14 — API + Webhooks + SDK: AVAILABLE
### Phase 15 — Trianon Migration: AVAILABLE
### Phase 16 — Mobile App: AVAILABLE
### Phase 17 — AI Assistant: AVAILABLE
- Platform Admin Login
- Dashboard (analytics overview)
- Tenants list/detail, approve/suspend
- Applications review (partner applications)
- Subscriptions management
- Audit logs viewer
- Analytics dashboard (charts)
- User management (impersonate, reset, ban)
Estimate: 8-10 steps

### Phase 8 — Rewards + Referral Complete
- Redeem catalog (rewards shop)
- Rewards dashboard (tier progress, milestones)
- Referral dashboard (referred users, total earned)
- Referral milestones (bonus at 5, 10, 25 referrals)
- Special offers / promo codes
- Birthday rewards
- Tier benefits (real perks)
Estimate: 6-10 steps

### Phase 9 — i18n (EN / AR / FIL / HI)
- i18n foundation
- English complete
- Arabic + RTL layout
- Filipino
- Hindi
- Language switcher in header
- Currency switcher
- Locale-aware dates and numbers
Estimate: 5-8 steps

### Phase 10 — Payment Production (Telr)
- Telr provider (replace Mock)
- Webhook signature verification
- Refund flow (API + UI)
- Payment reconciliation (daily job)
- PCI compliance check
- Multi-currency
- Invoice / receipt PDF
- Failed payment retry
Estimate: 6-8 steps

### Phase 11 — Notifications (Real Providers)
- Email provider (SendGrid / Mailgun)
- SMS provider (Twilio / Unifonic)
- WhatsApp Business API
- Templates per notification type
- User notification preferences
- Digest emails
- Notification center UI
Estimate: 5-6 steps

### Phase 12 — VPS Deploy + Domain + Named Tunnel
- VPS provisioning (Ubuntu 22.04)
- Nginx reverse proxy
- Gunicorn/Uvicorn workers
- PostgreSQL migration (from SQLite)
- SSL certificate (Let's Encrypt / Certbot)
- Custom domain + Cloudflare DNS
- Named Cloudflare Tunnel (replaces Quick Tunnel)
- Subdomain per tenant (slug.platform-x.com)
- Custom domain support per tenant
- Monitoring (uptime + error tracking)
- Log aggregation
- Backup automation (cron + off-site)
- Deployment script / CI-CD
- Health checks
- Environment separation (dev/staging/prod)
- Graceful restart (zero-downtime)
Estimate: 8-10 steps

### Phase 13 — Business Onboarding Tools
- Subdomain routing per tenant
- Custom domain support
- SSL for custom domains (wildcard)
- DNS configuration guide
- Tenant self-service setup wizard
- Data import tools (from legacy systems)
- Tenant analytics dashboard
- Tenant staff accounts (Owner / Manager / Staff)
- Tenant billing (Platform-X → business)
- Subscriptions enforcement
Estimate: 10-15 steps

### Phase 14 — API + Webhooks + SDK
- Public API keys for businesses
- Webhooks outbound (Platform-X → business systems)
- API rate limiting per tenant
- API documentation (OpenAPI + examples)
- SDKs (Python, JavaScript)
- Flight API integration (Amadeus / Sabre)
- Google Maps integration
- Email service
- SMS service
- WhatsApp Business API
- Push notifications (future mobile)
Estimate: 6-8 steps

### Phase 15 — Trianon Migration
- Move real Trianon hotel onto Platform-X
- Import existing bookings, users, payments
- Adapt Trianon frontend to platform APIs
- Configure Trianon tenant
- Redirect trianon.com to platform
- Parallel run (2 weeks)
- Cutover
Estimate: 5-8 steps

### Phase 16 — Mobile App
- Framework decision (React Native vs Flutter)
- Shared API layer
- Customer app (iOS + Android)
- Business staff app
- Push notifications
- App Store + Play Store
Estimate: weeks/months


### Phase 17 — AI Assistant
- Floating chat button (FAB) on public site
- Chat panel UI (sidebar/modal with messages)
- Backend: POST /ai/chat endpoint
- LLM integration (OpenAI GPT-4o-mini OR Google Gemini)
- System prompt: knows Platform-X and can help with bookings
- Rate limiting per user (5/min)
- Chat history in localStorage
- Fallback message when AI unavailable
- Analytics: track chat usage
Estimated: 6-8 steps

---

## 13. Commands Cheat Sheet

Run dev server:
  cd ~/platform-x && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

Run tests:
  pytest

Apply migrations:
  alembic upgrade head

Create migration:
  alembic revision --autogenerate -m "description"

Seed demo data:
  python -m app.scripts.seed_all

Check services:
  sv status platform-x-api platform-x-tunnel

Restart Platform-X:
  sv restart platform-x-api

Get current tunnel URL:
  cat ~/platform-x/logs/tunnel.url

Business AI smoke test:
  bash scripts/smoke-business-ai.sh
  BASE=https://looks-...trycloudflare.com bash scripts/smoke-business-ai.sh

Pricing Rules smoke test:
  bash scripts/smoke-pricing-rules.sh

Content Studio smoke test:
  bash scripts/smoke-content-studio.sh

Marketing Copilot smoke test:
  bash scripts/smoke-marketing.sh

Insights smoke test:
  bash scripts/smoke-insights.sh

Market Insights smoke test:
  bash scripts/smoke-market.sh

Reviews smoke test:
  bash scripts/smoke-reviews.sh

Public API smoke test:
  bash scripts/smoke-public-api.sh

Fast backup scripts:
  bash scripts/backup.sh phase-N-step-M-done       (code only, ~0.2s)
  bash scripts/backup-full.sh vX.Y.Z-name          (code + DB + .env, ~0.25s)

Business login:
  slug=trianon-hotel / owner@trianon-hotel.com / OwnerPass123
  slug=saffron-restaurant / owner@saffron-restaurant.com / OwnerPass123

Leaderboard recompute (CLI):
  python -m app.scripts.recompute_scores            # current month
  python -m app.scripts.recompute_scores --previous # previous month
  python -m app.scripts.recompute_scores --all      # both

Leaderboard endpoints:
  GET  /leaderboard                   (HTML page)
  GET  /api/leaderboard               (JSON)
  GET  /api/leaderboard/categories    (JSON)
  GET  /business/api/score            (auth)
  GET  /business/api/score/tips       (auth)
  POST /platform/api/leaderboard/recompute  (admin)

---

## 14. Test Count: 1139 tests, all passing

Test files:
- test_health.py
- test_security.py (11)
- test_schemas.py (7)
- test_auth_api.py (11)
- test_tenants_api.py (5)
- test_bookings_api.py (11)
- test_services_api.py (12)
- test_orders_api.py (11)
- test_payments_api.py (11)
- test_rewards_referrals_api.py (12)
- test_notifications_api.py (8)
- test_analytics_api.py (6)
- test_production_hardening.py (7)
- test_demo_flow.py (2)
- test_web_pages.py (10)
- test_auth_pages.py (7)
- test_booking_page.py (5)
- test_payment_page.py (5)
- test_account_page.py (6)
- test_category_pages.py (7)
- test_business_api.py (17, Phase 20)
- test_business_context.py (10, Phase 21)
- test_pricing_coach.py (17, Phase 21)
- test_business_ai_api.py (18, Phase 21)
- test_business_ai_page.py (3, Phase 21)
- test_business_ai_page_theme.py (2, Phase 21)
- test_pricing_rules_service.py (23, Phase 22)
- test_business_pricing_api.py (17, Phase 22)
- test_booking_pricing_integration.py (8, Phase 22)
- test_business_pricing_page.py (4, Phase 22)
- test_scoring_engine.py (21, Phase 29)
- test_leaderboard_service.py (12, Phase 29)
- test_leaderboard_api.py (18, Phase 29)
- test_leaderboard_tips.py (8, Phase 29)
- test_leaderboard_page.py (4, Phase 29)
- test_business_score_page.py (4, Phase 29)
- test_badges_helper.py (2, Phase 29)
- test_businesses_badges.py (4, Phase 29)
- test_content_writer.py (13, Phase 23)
- test_content_importer.py (18, Phase 23)
- test_business_content_api.py (20, Phase 23)
- test_business_content_page.py (6, Phase 23)
- test_marketing_segments.py (13, Phase 25)
- test_campaign_writer.py (14, Phase 25)
- test_discount_suggester.py (10, Phase 25)
- test_business_marketing_api.py (16, Phase 25)
- test_business_marketing_page.py (6, Phase 25)
- test_occupancy_service.py (14, Phase 26)
- test_heatmap_service.py (9, Phase 26)
- test_revenue_forecast.py (12, Phase 26)
- test_capacity_forecast.py (15, Phase 26)
- test_business_insights_api.py (22, Phase 26)
- test_business_insights_page.py (6, Phase 26)
- test_market_insights.py (14, Phase 27)
- test_market_analyst.py (12, Phase 27)
- test_business_market_api.py (14, Phase 27)
- test_business_market_page.py (7, Phase 27)
- test_review_service.py (21, Phase 28)
- test_reviews_api.py (17, Phase 28)
- test_business_reviews_page.py (6, Phase 28)
- test_tenant_home_reviews.py (4, Phase 28)
- test_api_key_service.py (16, Phase 14)
- test_public_api_v1.py (14, Phase 14)
- test_webhook_service.py (15, Phase 14)
- test_business_api_keys_api.py (11, Phase 14)
- test_business_webhooks_api.py (12, Phase 14)
- test_api_docs_page.py (6, Phase 14)

Speed: BCRYPT_ROUNDS=4 in tests, schema created once per session.

---

## 15. Key Files

- app/core/config.py — Settings (production hardening)
- app/core/security.py — bcrypt hash, JWT
- app/api/deps.py — get_current_tenant, get_current_user
- app/api/deps_admin.py — get_current_admin, require_role
- app/web/pages.py — HTML routes + CATEGORIES registry
- app/web/templates.py — shared Jinja2 env + globals (tenant_path, now_year)
- app/static/css/platform.css — light theme tokens + components
- app/static/css/platform-home.css — all page-specific styles (1500+ lines)
- app/static/js/px-core.js — shared utilities (getToken, authHeaders, initHeaderAuth, logout, count-up)
- app/templates/layouts/platform_base.html — main layout
- app/templates/partials/platform_header.html — dynamic header with avatar

---

## 16. How to Start a New Session

1. Read this HANDOFF.md fully
2. Read PROJECT-RULES.md
3. Check current state:
   cd ~/platform-x
   git log --oneline -5
   git tag -l
   sv status platform-x-api platform-x-tunnel
4. Ask user what to work on next
5. Follow working rules: backup → change → test → commit → report

---

## 17. Contact / User Preferences

User's goal: Professional Demo online to show to business partners.

User's style:
- Persian only, direct
- Does not want to be asked technical decisions
- Wants excellence quality
- Wants full phases completed (no skipping)
- Does not want features outside roadmap

---



---

## 18. Security Checklist (Before Production)

- [ ] Rate Limiting enabled
- [ ] Security headers configured
- [ ] JWT Refresh tokens implemented
- [ ] Password policy enforced
- [ ] Account lockout after failures
- [ ] Session revocation works
- [ ] CSRF protection on forms
- [ ] XSS audit complete
- [ ] SQL injection audit complete
- [ ] HTTPS enforced
- [ ] CORS restricted to real domains
- [ ] 2FA for admins
- [ ] Audit logs complete
- [ ] Secrets in secure store
- [ ] Backup strategy active
- [ ] Payment webhook signature verified
- [ ] PCI compliance reviewed

---

## 19. Production Deployment Checklist

- [ ] VPS provisioned
- [ ] PostgreSQL installed and migrated
- [ ] Nginx configured
- [ ] SSL certificate issued
- [ ] Custom domain configured
- [ ] Named Cloudflare Tunnel set up
- [ ] Subdomain routing per tenant
- [ ] Monitoring active (uptime + errors)
- [ ] Logs aggregated
- [ ] Backup automation running
- [ ] Health checks configured
- [ ] Environment variables secure
- [ ] DNS records verified
- [ ] Custom domain per tenant ready

---

## 20. Business Onboarding Checklist (per new tenant)

- [ ] Partner application received
- [ ] Application reviewed and approved
- [ ] Tenant created in DB
- [ ] Subdomain or custom domain configured
- [ ] SSL certificate issued
- [ ] Branding configured (colors, fonts, logo)
- [ ] Services imported (rooms, menu, packages, tickets)
- [ ] Staff accounts created
- [ ] Billing activated
- [ ] Tenant admin dashboard access granted
- [ ] Email/notifications configured
- [ ] Tenant live

---

**END OF v2 ROADMAP SECTIONS**




### Phase 18 — AI Foundation: COMPLETE
Tag: v0.10.0-ai-foundation
- LLM provider integration (OpenAI GPT-4o-mini OR Google Gemini)
- AI service layer (prompt management, safety)
- Rate limiting per user
- Cost tracking + budget caps
- Context injection (tenant data, user data)
- Fallback + error handling
- AI audit log
Estimated: 6-8 steps

### Phase 19 — AI Guest Assistant (User AI, Layer 2): COMPLETE
Tag: v0.11.0-user-ai
- Floating chat widget on public site
- AI Travel Planner (multi-business itinerary)
- AI Concierge (during trip)
- AI Booking Agent (can actually book)
- AI Negotiation (auto-offers from businesses)
- Chat history + context memory
- Multi-language AI
Estimated: 6-8 steps

### Phase 22 — Dynamic Pricing Rules: COMPLETE
Tag: v0.13.0-dynamic-pricing
- PricingRule + PricingRuleApplication models + Alembic migration
- Pricing Rules service (evaluate / compute / preview / record_application)
  Rule types: weekend / season / urgency / capacity / last_minute / custom
  Actions: percent (+/-) and fixed (+/-), Decimal math, floor at 0
  Priority-ordered stacking (lower = first)
- Business Pricing API: 6 endpoints under /business/api/pricing
  CRUD + preview, owner/manager write, staff read-only, cross-tenant isolation
- Booking integration: opt-in via apply_pricing_rules=True
  Server-computed base price (from service), audit per applied rule
- UI: Rule Builder page in Business Panel (/business/pricing)
- Automated smoke test: scripts/smoke-pricing-rules.sh (11 checks)
- 273 tests passing

### Phase 21 — AI Business Assistant (Pricing Coach): COMPLETE
Tag: v0.12.0-pricing-coach
- Business Context Builder (real DB → structured AI context, deterministic)
- Pricing Coach service: analyze / suggest / forecast / insights
  (metrics computed in Python, AI only advises on top of real numbers)
- 5 endpoints under /business/api/ai:
    POST /chat, POST /pricing/analyze, POST /pricing/suggest,
    POST /demand/forecast (7-90 days, clamped), POST /insights
- UI: two tabs (Chat + Pricing Coach), dark-theme compatible
- Bugfixes:
    - account/ai: use authenticated user's home tenant, not URL slug
    - business_ai: removed hardcoded 'trianon-hotel' slug
    - business_ai: dark theme tokens (no hardcoded light colors)
- Automated smoke test: scripts/smoke-business-ai.sh (11 checks)
- 221 tests passing

### Phase 20 — Business Owner Panel
- Separate panel: /business/*
- Dashboard (bookings, revenue, occupancy)
- Services management (rooms, menu, packages)
- Bookings inbox + status
- Customer list + history
- Analytics (views, bookings, conversion)
- Staff accounts (Owner / Manager / Staff roles)
- Business notifications
Estimated: 10-12 steps

### Phase 21 — AI Business Assistant (Pricing Coach)
- AI competitor price intelligence (confidential)
- AI pricing suggestions
- AI demand forecasting
- AI competitor benchmark
- AI market insights
Estimated: 8-10 steps

### Phase 22 — Dynamic Pricing Rules
- Rule builder for owners
- Auto price adjustment (weekends, seasons, urgency)
- Capacity-based pricing
- Last-minute discounts
- AI learning from historical data
Estimated: 6-8 steps

### Phase 23 — AI Content Writer + Onboarding
- AI auto-generate service descriptions (4 languages)
- AI-suggested images
- AI Onboarding (URL → extract business info)
- AI menu/room importer
Estimated: 6-8 steps

### Phase 24 — Cross-Business Rewards Enhancement
- Spend points across categories
- Tier benefits (real perks)
- Redeem catalog
- Birthday rewards
- Milestone bonuses
Estimated: 4-6 steps

### Phase 25 — AI Marketing Copilot
- AI campaign suggestions
- Auto email/SMS to past customers
- AI discount suggestions based on trends
- Personalized offers per user segment
Estimated: 5-7 steps

### Phase 26 — Real-Time Occupancy + Analytics
- Live occupancy dashboard
- Predictive capacity
- Revenue forecasting
- Booking heatmaps
Estimated: 5-6 steps

### Phase 27 — Competitor Insights
- Aggregate market data (anonymized)
- Industry benchmarks
- Anonymous peer comparison
- Region/category insights
Estimated: 5-7 steps

### Phase 28 — AI Review Writer + Responder
- AI writes reviews from guest input
- Business AI auto-responds to reviews
- Multi-language reviews
- Sentiment analysis
Estimated: 4-5 steps

### Phase 29 — Business Leaderboard + AI Scoring ⭐
- Monthly AI scoring (5 criteria):
  - Customer Satisfaction (30%)
  - Service Quality (25%)
  - Pricing Competitiveness (20%)
  - Engagement (15%)
  - Platform Loyalty (10%)
- Per-category Leaderboard (Hotels, Restaurants, Travel, Entertainment)
- Auto-rewards:
  - Rank 1: Hero Featured + Sponsored Promotion + Gold Badge + Email to users + 0% commission next month
  - Rank 2: Category Featured + Silver Badge + 50% commission discount
  - Rank 3: Bronze Badge + Featured in search
- Public /leaderboard page
- Business Panel: My Score + AI tips
- Badges on cards
- AI suggestions for improvement
Estimated: 6-8 steps

### Phase 40 — Mobile App (formerly Phase 30 in v2 roadmap)
- Framework: React Native or Flutter
- Guest app (iOS + Android)
- Business staff app
- Push notifications
- Store submission
Estimated: weeks/months

---

## Strategic Differentiation (from partner meeting 2026-09-28)

### For Guests (vs Agoda/Booking.com):
1. AI Travel Planner (itinerary in one click)
2. Multi-Business Cart (hotel + restaurant + tour in one booking)
3. Universal Rewards (cross-category earn and spend)
4. AI Negotiation (auto-offer discounts)
5. AI Concierge (24/7 in-trip assistant)
6. Group Booking simplified by AI
7. Referral Cash Rewards (real money, not just points)
8. AI Review Writer
9. 5-Tier Loyalty (Welcome/Silver/Gold/Platinum/Royal)
10. AI Trip Memory (hyper-personalization)

### For Business Owners:
1. Business Panel with AI assistant
2. AI Pricing Coach (market comparison)
3. Dynamic Pricing Rules
4. AI Content Writer (4 languages)
5. AI Onboarding (URL extraction, no forms)
6. AI Booking Manager
7. AI Marketing Copilot
8. Real-Time Occupancy Dashboard
9. AI Competitor Insights
10. AI Review Responder
11. Zero setup cost + AI-driven
12. Multi-Staff with role-based access

### Unique vs Agoda/Booking.com:
- AI everywhere (booking, pricing, content, marketing)
- Multi-business cart (they only have hotel)
- Cross-category rewards
- Confidential price intelligence
- AI-powered leaderboard with auto-rewards
- Real cash referral rewards

### Business-First Strategy:
- Prioritize Business Panel + AI Pricing Coach
- Then AI Guest Assistant
- Reason: businesses pay; users use

### Platform Commission:
- Rank 1 (monthly): 0% next month
- Rank 2 (monthly): 50% off
- Rank 3 (monthly): standard
- Standard rate: TBD (decision pending)




---

## AI Architecture (Three Layers)

### Layer 1 — Floating AI Assistant (FAB)
- **Location:** All public pages (bottom-right floating button)
- **Users:** Everyone (guest or logged in)
- **Purpose:** Quick questions, navigation, short help
- **History:** Session-only (browser memory)
- **Endpoints:** POST /ai/chat
- **Rate:** 20/min
- **Provider:** configurable (mock default)
- **Status:** COMPLETE (Phase 18)

### Layer 2 — User AI (Account Dashboard)
- **Location:** /account/ai (new tab in account dashboard)
- **Users:** Logged-in guests only
- **Purpose:** AI Travel Planner, Booking Agent, Concierge, Personal recommendations
- **Can ACTUALLY book** on behalf of user
- **Has access to:** user's bookings, rewards, referrals, language, preferences
- **History:** Persistent (DB)
- **Endpoints:** POST /account/api/ai/chat, POST /account/api/ai/plan, POST /account/api/ai/book
- **Rate:** 30/min
- **Status:** NEXT (Phase 19)

### Layer 3 — Business AI (Business Panel)
- **Location:** /business/ai (Business Panel sidebar)
- **Users:** Business owners, managers, staff
- **Purpose:** Pricing Coach, Content Writer, Marketing Copilot, Competitor Insights
- **Has access to:** tenant's services, bookings, revenue, customers
- **History:** Persistent per user (DB)
- **Endpoints:** POST /business/api/ai/chat (and future: /analyze, /write, /suggest)
- **Rate:** 30/min
- **Status:** PARTIAL (Phase 18 — chat works); full features in Phase 21

**All three layers share the same AI Foundation (Phase 18):**
- Same Provider Abstraction (mock / gemini / openai)
- Same Factory
- Same service layer (app/services/ai/service.py)




---

## AI Context — Why We Are Where We Are

This section explains the strategic decisions that led to the current
state. Any new AI session MUST read this before suggesting next steps.

### Why Phase 1 (First Tenant Live) was SKIPPED

**Roadmap v1 order:** Phase 1 = First Tenant Live (real hotel on platform)

**Reality when starting work:**
- The platform backend did not exist yet
- Frontend did not exist yet
- Trianon Hotel (real first tenant) had its own separate site
- User's goal changed mid-project: "build a professional Demo first"

**Decision (made by Tech Lead, approved by user):**
- Skip Phase 1 for now
- Build Phase 2 (Core Architecture) first — get the platform ready
- Then Phase 3 (Frontend), 4 (UI Polish), 5 (Full Flow)
- Migrate Trianon later (Phase 15)

**Consequence:** Phase 1 (real first tenant) will happen after the Demo
is complete and VPS deployment is done. This is intentional.

### Business-First Order (authoritative)

Current working order. Do NOT jump phases. Do NOT skip.

1. Phase 20 (Business Panel) — COMPLETE
2. Phase 18 (AI Foundation) — COMPLETE
3. Phase 21 (AI Business Assistant / Pricing Coach) — COMPLETE
4. Phase 22 (Dynamic Pricing Rules) — COMPLETE
5. Phase 29 (Leaderboard + AI Scoring) — COMPLETE
6. Phase 19 (User AI) — COMPLETE
7. Phase 23 (AI Content Writer) — COMPLETE
8. Phase 24 (Cross-Business Rewards) — DEFERRED BY USER (do not start until told)
9. Phase 10 (Payment Production — needs Telr/Stripe account)
10. Phases 25-28 DONE (all AI features complete) (AI Marketing, Occupancy, Competitor Insights, Review Responder)
11. Phase 12 (VPS + Domain + Named Tunnel — needs purchase)
12. Phase 13 (Business Onboarding Tools — needs Phase 12)
13. Phase 14 (API + Webhooks + SDK)
14. Phase 15 (Trianon Migration — after VPS)
15. Phase 16 (Mobile App)
16. Phase 30 (Native Mobile App)

Rationale: businesses pay; users use. Prioritize value for business owners first.

### Why Phase 8 (Rewards + Referral) is WAITING

**Reason:** This phase requires a **business plan from the user** for
reward tiers, redeem options, milestones, and referral bonuses.

**Without that plan, we cannot build it correctly.** Any AI attempting
to build it would be guessing.

**When the user provides the plan, this phase becomes available.**

### Why phases are not in numeric order

The user's goal after partner meetings (2026-09-28) was:

**"Business-First Strategy"** — prioritize value for business owners
before guests. Reason: businesses pay; users use.

**Business-First Order:**
1. Phase 20 (Business Panel) — COMPLETE
2. Phase 18 (AI Foundation) — COMPLETE
3. Phase 21 (AI Business Assistant) — NEXT
4. Phase 22 (Dynamic Pricing Rules) — SOON
5. Phase 29 (Leaderboard + AI Scoring) — SOON
6. Phase 19 (User AI) — COMPLETE (was done early because foundation was ready)
7. Phase 23 (AI Content Writer) — COMPLETE
8. Phase 24 (Cross-Business Rewards) — DEFERRED BY USER (do not start until told)
9. Phase 10 (Payment Production)
10. Phase 25-28 (AI Marketing, Occupancy, Competitor Insights, Review Responder)
11. Phase 12 (VPS + Domain + Named Tunnel) — requires purchase
12. Phase 13 (Business Onboarding Tools) — needs Phase 12 for subdomains
13. Phase 14 (API + Webhooks + SDK)
14. Phase 15 (Trianon Migration) — after VPS
15. Phase 16 (Mobile App) — last

### What has been done and why

- **Phases 2, 3, 4, 5** — Foundation (backend, frontend, UI, full flow)
- **Phase 6** — Security (before any real user touches the platform)
- **Phase 7** — Admin Panel (for platform admins to manage)
- **Phase 9** — i18n (4 languages: EN, AR, FIL, HI) — required by Design System
- **Phase 11** — Notifications (Resend email, Password Reset, Notification Center)
- **Phase 18** — AI Foundation (provider abstraction, Gemini active)
- **Phase 19** — User AI (Chat, Travel Planner, Booking Agent with Gemini)
- **Phase 20** — Business Owner Panel (dashboard, services, bookings, staff)

### What is specifically NOT done yet

- **Phase 8** — needs user business plan
- **Phase 10** — needs Business Account for Telr/Stripe
- **Phase 12** — needs VPS + domain purchase
- **Phase 13** — needs Phase 12 for subdomains
- **Phase 14** — API/Webhooks (later)
- **Phase 15** — Trianon migration (after VPS)
- **Phase 16** — Mobile App (last)
- **Phase 17** — AI Assistant (merged into 18/19)
- **Phase 21** — AI Business Assistant (NEXT)
- **Phase 22** — Dynamic Pricing (soon)
- **Phase 23-28** — AI features (soon)
- **Phase 29** — Leaderboard + AI Scoring
- **Phase 30** — Mobile Native App

### What Is NOT Done Yet (honest list)

- **Phase 8** (Rewards + Referral) — WAITING for user's business plan
- **Phase 10** (Payment Production / Telr) — needs business account
- **Phase 12** (VPS + Domain + Named Tunnel) — needs purchase
- **Phase 13** (Business Onboarding Tools) — needs Phase 12 for subdomains
- **Phase 14** (API + Webhooks + SDK) — later
- **Phase 15** (Trianon Migration) — after VPS
- **Phase 16 / 30** (Mobile App) — last
- **Phase 23-25** (AI Content Writer, Cross-Business Rewards, AI Marketing) — soon
- **Phase 26-28** (Realtime Occupancy, Competitor Insights, Review Writer) — soon
- **Phase 24 (merged with 8)** — WAITING for user's Rewards + Referral plan
- **Phases 25-28 ALL DONE (AI features complete)**
- **Phase 14 (API/Webhooks/SDK)** — next candidate (no purchases needed)

### Known Pitfall — pydantic + FastAPI routes

Do NOT use `from __future__ import annotations` in API files that define
pydantic schemas referenced in route signatures. It converts type hints
to strings and pydantic may fail with:
  PydanticUndefinedAnnotation: name 'X' is not defined
This was hit in Phase 25 (business_marketing.py). Keep API files free of
that import.

### Key Rules for Future Sessions

1. **Do NOT jump phases** — follow Business-First order
2. **Do NOT start Phase 8** without explicit user business plan
3. **Do NOT start Phase 10/12/13** without user providing account/purchase
4. **Provider-agnostic AI** — never hardcode a specific provider
5. **Preserve the 3-layer AI architecture** (FAB, User AI, Business AI)
6. **ALWAYS backup + test + commit after each change**
7. **Follow EXCELLENCE quality** — no shortcuts
8. **NEVER ask user technical questions** — decide as Tech Lead
9. **All responses in Persian (Farsi)** — direct, no fluff

### Live URL and Services

- Live URL: check `~/platform-x/logs/tunnel.url` (changes on restart)
- Restart command: `cd ~/platform-x && sv up platform-x-api && sv up platform-x-tunnel && sleep 20 && bash start-platform.sh`
- Test suite (full, sequential): `cd ~/platform-x && source venv/bin/activate && pytest tests/`
- Test suite (full, parallel — Phase close default): `pytest tests/ -n auto`  (~2.5x faster, same results)
- Test suite (single file, during steps): `pytest tests/test_<name>.py`
- HANDOFF: `cat ~/platform-x/HANDOFF.md`



END OF HANDOFF
