# Platform-X — Data Room Guide

> **Purpose:** A structured index for a buyer's due-diligence data
> room. The data room is a private repository (or shared folder)
> containing all documents a serious buyer needs to evaluate
> Platform-X.
>
> **Access:** Granted only after NDA signature. Revocable at will.
> Watermarked or read-only where possible.

---

## 1. Data Room Structure

---

## 2. Access Tiers

### Tier 1 — NDA signed, initial interest
Grant access to:
- `01-Overview/`
- `05-Legal/LICENSE`, `AUTHORS.md`

### Tier 2 — Serious buyer, term sheet discussion
Grant access to:
- Everything in Tier 1
- `02-Technical/`
- `03-Security/`
- `04-Business/`
- `06-Buyer/`
- `07-Verification/`

### Tier 3 — Under signed Sale Agreement
Grant access to:
- Everything in Tier 2
- Read-only access to the full source repository
- The full git history (89 tags, 646 commits)
- Backups and assets

---

## 3. What is NOT in the data room

- **`.env` file** — contains secrets. Never shared.
- **`platform_x.db`** — dev database with no live data. Not
  relevant.
- **Backups** — shared only at Tier 3 under signed agreement.
- **Payment provider credentials** — seller-side only.
- **AI provider keys** — seller-side only.

---

## 4. Read-only vs. download

Default policy: **read-only, watermarked**.

- PDFs: watermarked with the buyer's name and date.
- Markdown: served via read-only viewer (e.g., GitHub private repo
  with read-only collaborator access, or Notion with viewer access).
- Source code: read-only repository access at Tier 3.

Download is permitted only for the Investment Memorandum and the
pitch deck, and only after NDA signature.

---

## 5. Watermarking

Every PDF shared in the data room should carry a footer:

Tools: Adobe Acrobat, PDFtk, or any PDF editor with a watermark
function.

---

## 6. Logging and revocation

- Maintain a log of every access grant: who, when, what tier.
- Revoke access immediately if:
  - The buyer discloses the data room contents publicly.
  - The buyer stops responding for more than 60 days.
  - The buyer breaches the NDA.
- For GitHub-based data rooms, use per-collaborator access so
  revocation is clean.

---

## 7. Recommended hosting

Options, in order of preference:

1. **GitHub private repository** (read-only collaborator) — free,
   auditable, easy to revoke.
2. **Notion** — free tier, per-user viewer access, watermarked
   exports.
3. **Google Drive (private folder)** — per-user sharing, no
   watermarking by default.
4. **Dropbox Business** — watermarking available, per-user access.
5. **DocSend** — paid, best-in-class for watermarking and analytics.

For a transaction of this size, **DocSend** or **GitHub + a PDF
watermarker** is recommended.

---

## 8. First-contact flow

1. Initial email sent (see `docs/26-OUTREACH-EMAILS.md`).
2. Buyer responds with interest.
3. Send NDA (`docs/19-NDA-TEMPLATE.md`).
4. NDA signed (electronic signature accepted).
5. Grant Tier 1 access.
6. 30-minute call to walk through the deck.
7. If interest continues, grant Tier 2 access.
8. Term sheet negotiation begins.
9. If term sheet agreed, DIFC lawyer drafts full Sale Agreement.
10. Grant Tier 3 (source repository access).
11. Escrow funded. Transfer begins.

---

## 9. Email template for granting Tier 1 access

**Subject:** Platform-X — Data Room Access (Tier 1)

**Body:**

Dear [Name],

Thank you for signing the NDA. Here is Tier 1 access to the
Platform-X data room:

[link]

Included: project overview, Investment Memorandum, pitch deck,
and roadmap.

I'd suggest starting with the Investment Memorandum, then the pitch
deck. Both can be read in under 30 minutes.

Let me know if you'd like a 30-minute call to walk through anything.

Best regards,
Benjamin Bahoush

---

## 10. Document control

- **Version:** 1.0
- **Date:** 2026-10-16
- **Author:** Benjamin Bahoush (with AI assistance)
- **Status:** Ready to deploy

