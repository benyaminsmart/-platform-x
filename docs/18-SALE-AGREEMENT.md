# Platform-X — Sale Term Sheet & Legal Checklist

> **Two-part document:**
> 1. A Term Sheet for negotiation (both parties).
> 2. A Legal Checklist for the DIFC lawyer who drafts the full
>    Sale Agreement.
>
> This document is not a substitute for legal advice. It is a
> framework for negotiation and for briefing a lawyer.

---

# PART 1 — TERM SHEET

## Asset Purchase Term Sheet

**Seller:** Benjamin Bahoush (platformx2026@gmail.com)
**Buyer:** [BUYER NAME]
**Date:** [DATE]

### 1. Transaction

The Seller agrees to sell, and the Buyer agrees to purchase, all
intellectual property rights, source code, documentation, tests,
deployment scripts, and the documented AI-driven development
methodology associated with the software platform currently known as
**Platform-X** (the "Asset").

### 2. Included Assets

- Full source code (252 Python files, 34,342 lines)
- Automated test suite (1,509 tests)
- Full documentation (`HANDOFF.md`, `docs/`, `docs/buyer/`)
- Deployment scripts and configuration templates
- Database migrations (33 Alembic revisions)
- Architectural design decisions
- AI-driven development methodology (documented)
- All associated git history (89 tags, 646 commits)
- Handover support (see §7)

### 3. Excluded Assets

The following are NOT part of the Asset and remain the Buyer's
responsibility:

- Brand name (Buyer selects its own)
- Domain name(s)
- VPS / hosting infrastructure
- Payment provider accounts (Telr, Stripe, PayTabs)
- AI provider accounts (Gemini, OpenAI)
- Hospitality operating licenses in any jurisdiction
- SSL certificates

### 4. Purchase Price

- **Asking price:** AED 5,000,000 (five million UAE dirhams)
- **Acceptable range:** AED 5,000,000 – AED 7,000,000
- **Floor:** AED 5,000,000
- **Currency:** AED or USD at the Buyer's election, at the exchange
  rate on the date of signing.

### 5. Payment Structure

- **50%** on signing of the Sale Agreement.
- **50%** on completion of asset transfer and close of the handover
  window (see §7).
- **Escrow:** required for transfers above USD 500,000. Held by the
  marketplace (Flippa / Acquire.com) or by a DIFC-licensed escrow
  agent. Release of escrow funds is triggered by written confirmation
  from the Buyer that the asset transfer is complete.

### 6. Transfer Process

1. NDA signed (see `docs/19-NDA-TEMPLATE.md`).
2. Buyer reviews the repository (read-only) for due diligence.
3. Term Sheet agreed and signed.
4. Sale Agreement drafted by Buyer's DIFC lawyer, reviewed by
   Seller's counsel.
5. Sale Agreement signed.
6. First payment deposited into escrow.
7. Source code, documentation, and all assets transferred to the
   Buyer's repository.
8. Buyer confirms successful deployment on their infrastructure.
9. Second payment released from escrow.
10. Handover window begins.

### 7. Handover

- The Seller provides full support to the Buyer's team **until the
  platform is deployed, configured, and declared live by the Buyer**.
  This period is not time-boxed.
- After the platform is declared live, the Seller provides
  **emergency support only**, for incidents directly related to
  code authored by the Seller.
- Routine maintenance, feature development, and ongoing operations
  are the Buyer's sole responsibility.
- Emergency support ends 12 months after the Buyer declares the
  platform live.

### 8. Warranties

The Seller warrants that:

(a) The Seller is the sole owner of the Asset and has the full right
    and authority to sell it.

(b) To the best of the Seller's knowledge, the Asset does not
    infringe any third-party intellectual property. (See
    `docs/buyer/TECH-DEBT-LIST.md` for known third-party
    dependencies, all of which are standard open-source libraries
    with permissive licenses.)

(c) The Asset is provided "AS IS" without warranty of merchantability
    or fitness for a particular purpose. The Seller does not
    guarantee that the Asset will generate revenue or achieve any
    specific commercial outcome.

(d) The Seller has disclosed all known gaps and limitations in
    `HANDOFF.md` §9 and `docs/buyer/TECH-DEBT-LIST.md`.

### 9. Non-Compete

- The Seller agrees not to build, sell, or license a directly
  competing multi-tenant hospitality SaaS platform for a period of
  **24 months** from the closing date.
- The Seller retains the right to work on unrelated software
  projects, AI tooling, and consulting during this period.

### 10. Confidentiality

The terms of this transaction remain confidential. Neither Party
will disclose the transaction or its terms to any third party
without the other Party's written consent, except as required by
law.

### 11. Governing Law

This Term Sheet and the resulting Sale Agreement are governed by the
laws of the **Dubai International Financial Centre (DIFC)**. Disputes
are subject to the exclusive jurisdiction of the DIFC Courts.

### 12. Non-Binding Nature

This Term Sheet is a statement of intent. It does not create a
binding legal obligation except for §10 (Confidentiality) and §11
(Governing Law), which are binding from the date of signature. The
full obligations of the Parties are established only by the Sale
Agreement.

---

## Signatures (Term Sheet)

**Seller:** _________________________  Date: __________

**Buyer:** _________________________  Date: __________

---

# PART 2 — LEGAL CHECKLIST FOR THE DIFC LAWYER

> This section is for the lawyer drafting the full Sale Agreement.
> It lists the topics the Sale Agreement should address.

## 1. Corporate Structure

- [ ] Confirm Seller's legal capacity (individual or corporate).
- [ ] If individual: confirm no spousal or third-party claim on the
      IP under UAE law.
- [ ] If corporate: confirm board resolution and shareholder
      approval.

## 2. Asset Identification

- [ ] Full IP schedule: source code, documentation, trademarks (if
      any), domains (if any), repositories.
- [ ] Confirm the Asset is free of third-party liens, security
      interests, or encumbrances.
- [ ] Confirm there is no pending litigation or IP dispute
      involving the Asset.

## 3. Third-Party Dependencies

- [ ] List of open-source dependencies and their licenses.
- [ ] Confirm no GPL or copyleft licenses that would contaminate the
      Asset on transfer.
- [ ] Confirm no dependencies have license terms incompatible with
      commercial resale.

## 4. Employees and Contractors

- [ ] Confirm no employee or contractor has any claim to the IP.
- [ ] Confirm AI-assisted development methodology does not create
      any third-party claim (document the AI tools used and their
      terms of service).

## 5. Transfer Mechanics

- [ ] Method of transferring the repository and all assets.
- [ ] Treatment of git history and backups.
- [ ] Deletion of all Seller-side copies after closing, except one
      archival copy for legal compliance.

## 6. Payment and Escrow

- [ ] Escrow agent selection and escrow agreement.
- [ ] Trigger conditions for release of escrow funds.
- [ ] Currency, exchange rate, and tax treatment.

## 7. Warranties and Indemnities

- [ ] Scope of the Seller's warranties.
- [ ] Cap and duration of the Seller's indemnity.
- [ ] Buyer's inspection rights and remedies for breach.

## 8. Handover Terms

- [ ] Definition of "platform live" (trigger for handover end).
- [ ] Scope of emergency support.
- [ ] Response times and communication channels.

## 9. Non-Compete and Non-Solicit

- [ ] Scope, duration, and geographic limits of the non-compete.
- [ ] Non-solicit of any Seller-side contractors or partners.

## 10. Confidentiality

- [ ] Post-closing confidentiality obligations.
- [ ] Press release and public statements.
- [ ] Employee and contractor confidentiality.

## 11. Tax

- [ ] UAE corporate tax treatment of the sale (if applicable).
- [ ] VAT treatment.
- [ ] Buyer's tax obligations in their jurisdiction.

## 12. Governing Law and Dispute Resolution

- [ ] Confirm DIFC law and DIFC Courts jurisdiction.
- [ ] Consider arbitration as an alternative (DIFC-LCIA).
- [ ] Language of the agreement (English, with Arabic translation if
      required).

## 13. Closing Conditions

- [ ] Conditions precedent to closing.
- [ ] Deliverables at closing.
- [ ] Post-closing obligations.

## 14. Miscellaneous

- [ ] Entire agreement clause.
- [ ] Amendment and waiver provisions.
- [ ] Notices clause.
- [ ] Severability.
- [ ] Counterparts and electronic signatures.

---

## Notes for the Seller (do not send to buyer)

- **Do not sign any Sale Agreement without a lawyer.** The Term
  Sheet above is for negotiation only.
- Engage a DIFC-licensed M&A lawyer as soon as a serious buyer
  appears. Budget: AED 15,000–50,000 for a full agreement,
  depending on complexity.
- Keep all communications in writing (email is sufficient).
- Do not transfer the repository before the escrow is funded.
- Do not delete your local backups until the second payment is
  released.
- If the buyer is a corporation, request their corporate documents
  before signing.
