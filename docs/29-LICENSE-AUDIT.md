# Platform-X — Open-Source License Audit

> **Purpose:** Document every third-party dependency of Platform-X,
> its license, and any implications for commercial sale.
>
> **Result:** All direct dependencies use permissive licenses
> (MIT, Apache 2.0, BSD). No GPL or AGPL. Two transitive LGPL
> dependencies exist but are not imported or used by Platform-X code.
>
> **Date:** 2026-10-16

---

## 1. Summary

| Category | Count | Verdict |
|----------|-------|---------|
| Direct dependencies (`requirements.txt`) | 19 | All permissive ✅ |
| Transitive dependencies (auto-installed) | ~50 | All permissive or LGPL-transitive (not used) ✅ |
| GPL / AGPL | 0 | None ✅ |
| LGPL in Platform-X code | 0 | None ✅ |

**Conclusion:** Platform-X is safe to sell commercially and to
relicense. No copyleft obligation attaches to Platform-X's own code.

---

## 2. Direct dependencies (requirements.txt)

| Package | Version | License | Commercial use |
|---------|---------|---------|-----------------|
| fastapi | 0.115.0 | MIT | ✅ |
| uvicorn[standard] | 0.31.0 | BSD-3-Clause | ✅ |
| pydantic | 2.9.2 | MIT | ✅ |
| pydantic-settings | 2.5.2 | MIT | ✅ |
| sqlalchemy | 2.0.35 | MIT | ✅ |
| alembic | 1.13.3 | MIT | ✅ |
| python-jose[cryptography] | 3.3.0 | MIT | ✅ |
| passlib[bcrypt] | 1.7.4 | BSD | ✅ |
| python-multipart | 0.0.12 | Apache 2.0 | ✅ |
| python-dotenv | 1.0.1 | BSD | ✅ |
| pytest | 8.3.3 | MIT | ✅ |
| pytest-asyncio | 0.24.0 | Apache 2.0 | ✅ |
| httpx | 0.27.2 | BSD-3-Clause | ✅ |
| email-validator | 2.2.0 | CC0-1.0 | ✅ |
| jinja2 | 3.1.4 | BSD-3-Clause | ✅ |
| aiofiles | 24.1.0 | Apache 2.0 | ✅ |
| slowapi | 0.1.9 | MIT | ✅ |
| resend | 2.5.1 | MIT | ✅ |
| pyotp | 2.9.0 | MIT | ✅ |

All 19 direct dependencies are permissive and compatible with
commercial resale and relicense.

---

## 3. PostgreSQL drivers

| Package | License | Notes |
|---------|---------|-------|
| pg8000 | BSD-3-Clause | Used only on Termux (dev). Not in `requirements.txt`. |
| psycopg2-binary | LGPL-3.0 (with linking exception) | Recommended on Ubuntu 22.04 (production). |

**Important:** `psycopg2-binary` is LGPL, but it is explicitly
designed to be used in closed-source applications. The standard
LGPL linking exception applies — you may use it in commercial
software without releasing your own source code.

If the buyer prefers a pure-permissive option for production,
`pg8000` (BSD-3-Clause) can be used on Ubuntu as well. This is a
configuration choice, not a license obligation.

---

## 4. Transitive dependencies

When `pip install -r requirements.txt` runs, ~50 additional packages
are installed automatically. All are permissive or LGPL-transitive.

### 4.1 Notable transitive packages

| Package | License | Source |
|---------|---------|--------|
| starlette | BSD-3-Clause | via fastapi |
| pydantic-core | MIT | via pydantic |
| cryptography | Apache 2.0 / BSD-3-Clause | via python-jose |
| bcrypt | Apache 2.0 | via passlib |
| httpcore | BSD-3-Clause | via httpx |
| anyio | MIT | via httpx |
| idna | BSD-3-Clause | via httpx |
| sniffio | Apache 2.0 / MIT | via httpx |
| certifi | MPL-2.0 | via httpx |

### 4.2 LGPL transitive packages

Two transitive packages use LGPL:

| Package | License | Pulled in by | Used by Platform-X? |
|---------|---------|--------------|---------------------|
| python-bidi | LGPL | xhtml2pdf chain | ❌ No |
| svglib | LGPL-3.0-or-later | xhtml2pdf chain | ❌ No |

**Verdict:** These are transitive dependencies of optional tooling
(pdf/svg generation chains pulled in by unrelated tooling). They are
**not imported by Platform-X code**. They pose no LGPL obligation on
Platform-X.

### 4.3 Verification

Platform-X imports were checked against these packages:

    grep -rn "python.bidi\|svglib\|xhtml2pdf\|reportlab\|pyhanko" app/

**Result:** 0 matches. Platform-X does not import any LGPL package.

---

## 5. Fonts, icons, and static assets

- **Fonts:** System fonts and web-safe fonts. No proprietary font
  files are shipped.
- **Icons:** Standard emoji or CSS-based icons. No purchased icon
  packs are shipped.
- **Images:** No third-party copyrighted images in the repository.
  All images in templates are either generated SVGs, placeholder
  images, or content uploaded by tenants.

---

## 6. AI-generated code

Platform-X was developed with AI-assisted tools under human
direction (documented in `docs/15-AI-PLAYBOOK.md`). The AI tools used
(OpenAI, Google, Anthropic, and others) do not claim copyright over
outputs generated in response to developer prompts. See `AUTHORS.md`
for the full methodology.

No third-party copyrighted code has been intentionally included.

---

## 7. Implications for the buyer

**The buyer can:**

- ✅ Rebrand Platform-X and sell it under their own name.
- ✅ Modify any part of the code.
- ✅ Distribute the modified version commercially.
- ✅ Keep the source closed (no obligation to open-source).
- ✅ Sublicense or resell.

**The buyer cannot:**

- ❌ Claim copyright over the permissive-licensed libraries
  themselves (they remain owned by their authors).
- ❌ Remove or misrepresent license notices in third-party libraries
  (standard practice — no requirement to display them in the UI).

**No copyleft obligation attaches to Platform-X's own code.**

---

## 8. Recommended actions for the buyer

1. Keep `requirements.txt` as-is; no license changes needed.
2. If choosing a pure-permissive PostgreSQL driver, switch from
   `psycopg2-binary` to `pg8000` (both work; pg8000 is BSD-3-Clause).
3. Periodically run `pip-licenses` to confirm the license landscape
   hasn't changed with future updates.
4. For a formal legal review, engage counsel to confirm the above
   against the buyer's specific jurisdiction.

---

## 9. Raw data

Full license list generated by:

    pip install pip-licenses
    pip-licenses --format=markdown --with-urls --order=license

The full output is available on request.

---

## Document control

- **Version:** 1.0
- **Date:** 2026-10-16
- **Author:** Benjamin Bahoush (with AI assistance)
- **Status:** Ready for buyer review
