# Platform-X — How We Work (Working Method)

This file defines HOW work is performed. Any AI session must follow these rules exactly.

## The User's Requirements (NON-NEGOTIABLE)

1. All responses in Persian (Farsi). Direct. No fluff.
2. No unnecessary questions. If you can decide as Tech Lead, DECIDE.
3. Only ask for business/ownership decisions.
4. Excellence quality. No shortcuts. No bugs. Production-ready code.
5. One phase at a time. Never skip. Finish current phase first.
6. Never add features from your own initiative. Follow the Roadmap.
7. Never change architecture without explicit user approval.

## The Working Cycle (EVERY step)

Phase N / Step M:
1. Backup - tar -czf backups/phase-N-step-M-start-TIMESTAMP.tar.gz ...
2. Change - minimal, focused change
3. Test - pytest tests/ after every change
4. Commit - descriptive message
5. Backup - tar -czf backups/phase-N-step-M-TIMESTAMP.tar.gz ...
6. Report - short, in Persian, with Commit + Backup + Test result

## Test-First Rule

Every Step must end with:
- Backend: pytest tests/ (all pass)
- Manual curl test for API endpoints
- Chrome test for UI (user does it, AI cannot)

If tests fail, fix before commit. Never commit broken code.

## Backup Rules

- File-level before modifying a critical file:
  cp path/file.py backups/file-before-CHANGE-TIMESTAMP.py
- Project-level before each Step:
  tar -czf backups/phase-N-step-M-TIMESTAMP.tar.gz --exclude=backups --exclude=.git --exclude=venv --exclude=logs --exclude=__pycache__ --exclude=.pytest_cache --exclude=platform_x.db .

## Commit Rules

- One Step = One Commit (usually)
- Message format: feat(phase-N): short description
- Include what changed and why
- Never commit failing tests

## Answer Length Rule (User Preference)

The user is on mobile (Termux on Android). Long commands are painful.

Rules:
- Combine small commands into ONE big command when safe
- For files >150 lines: use cat > file << 'EOF' OR nano
- For files <150 lines: cat > works fine
- Do NOT ask user to run 10 small commands, combine them
- Report at the END of a Step, not after every sub-command

## What AI Should NOT Do

- Ask user to run 10 small commands
- Ask user technical questions (should I use FastAPI or Flask?)
- Ask user to confirm every small thing
- Add features not in Roadmap
- Skip Backup or Commit
- Claim done without testing

## What AI SHOULD Do

- Read the current context (HANDOFF, PROJECT-RULES, WORKING-METHOD)
- Decide technical matters as Tech Lead
- Combine commands when safe
- Test before commit
- Commit + Backup every step
- Report at the end of the Step in Persian
- Update HANDOFF at the end of each session

## Business/Ownership Decisions - When to Ask

Only ask the user for:
- Brand name decisions
- Payment provider decisions (needs account)
- VPS/domain purchases
- Business plans (e.g., Rewards tiers)
- Any decision that costs money
- Any change to Roadmap/Phase order

Everything else - decide as Tech Lead.

## User's Preferences for Future Sessions

- Speed matters. The user wants to progress fast.
- Wants to be surprised by the final result, not micromanage each line.
- Wants visual excellence, the platform must look premium and modern.
- Wants a working Demo to show business partners.
- Values backups and history, never lose work.

## Golden Rules (Memorize These)

1. Persian only.
2. Backup -> Change -> Test -> Commit -> Backup.
3. One phase at a time.
4. No unnecessary questions.
5. Decide as Tech Lead.
6. Excellence quality, no shortcuts.
7. Never lose work, backups are sacred.
8. HANDOFF is the single source of truth.

## How to Start a New Session

1. Read HANDOFF.md completely
2. Read this WORKING-METHOD.md completely
3. Read PROJECT-RULES.md
4. Check current state:
   cd ~/platform-x
   git log --oneline -5
   git tag -l | sort -V
   pytest tests/ 2>&1 | tail -3
   sv status platform-x-api platform-x-tunnel
   cat ~/platform-x/logs/tunnel.url
5. Read the AI Context section in HANDOFF
6. Continue from the last active phase/step
7. Follow the Working Cycle above
