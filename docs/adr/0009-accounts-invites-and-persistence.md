# ADR 0009: Invite-only accounts, saved trips, and a persistent place cache

Status: **Proposed - needs team review and merge approval** (date: 2026-10-28). Builds on [ADR 0008](0008-carpool-bus-choice-and-faster-suggestions.md).

## Context

Trips, badges and the tree were kept in memory and vanished whenever the server stopped. The team wants each member to have an account (about eight in all: the team, the professor and the TA), to keep their records, and to use the same running site from several computers while it runs on one of them. It is **not** a public service. The online place service has a small daily quota, so places searched once should not be searched again.

## Decision

**Storage.** One SQLite file, `data/app.sqlite` (git-ignored), holds users, invites, trips, preferences, the sign-up and log-in attempts, and the place and route cache. It is separate from the TCAT schedule index. The Python standard library is enough; no database server is needed.

**Accounts.**
- Sign-up needs an **invite code** made with `python -m src.manage create-invite`. A code is shown once and stored only as a SHA-256 hash; it has a use count and an expiry, and can be revoked. Passwords are stored only as salted **scrypt** hashes (N = 2^15, about 70 ms and 32 MB per check).
- **Simplified on 2026-10-28 at the team's request:** only three shared codes exist (team members, the project manager, the professor), each good for many accounts and never expiring. The accounts for the team and the professor's and TA's test accounts are created by `python -m src.manage seed` from a git-ignored `data/roster.json`. The sign-up form asks for user name, password, password again and invite code. Because the site is private, the per-address and per-day sign-up limits and the wrong-code limit were removed, and the password rule is now only 6 to 128 characters and not equal to the user name (the team chose simple passwords for the demo accounts). The log-in lockout stays.
- User name and password only; no email and no verification, as chosen by the team.
- There is no admin web page. Invites, demo accounts, password resets, deletion and backups are done with the `manage` command.
- Limits (project assumptions): 5 wrong passwords per user name or 20 per address in 15 minutes lock log-in for the rest of that window. A hidden form field catches simple bots. (Sign-up limits were removed; see the note above.)
- Log-in errors never say whether a user name exists, and an unknown name costs the same time as a wrong password.

**Sessions and forms.** A signed cookie (HttpOnly, SameSite=Lax, Secure when served over https) holds the account and a counter that is raised when the password changes, which signs every other browser out. Every POST needs a secret form token. The session key is made once and kept in `data/secret.key` (or taken from `ECOCOMMUTE_SECRET`), so people stay signed in across restarts. Pages carry a Content-Security-Policy, `X-Frame-Options: DENY`, `nosniff` and `no-store` on personal pages.

**Everything needs an account**, including the two JSON endpoints that spend the online-service quota, so the quota is only used by invited people.

**Data per account.** Trips (and the vehicles a person has) belong to the account. The shared tree is the sample data plus every account's trips, each counted by the same anti-gaming rules; only the total is shown. No page shows another account's trips. An account can download its data and delete itself with all its trips.

**Cache.** Place suggestions, looked-up places and routes between known places are kept for months (routes for 30 days) in the same file, shared by all accounts. An entry holds the question text or two known places and the answer, never who asked. Routes that start or end at someone's own position are not kept. A failed or estimated answer is never kept. A cache that cannot be read is skipped.

**Running it.** `python -m src.main_web` listens on this computer only. `--host 0.0.0.0` lets other devices connect and prints a warning, because plain http crosses the network unencrypted. `waitress` serves when installed. `ECOCOMMUTE_BEHIND_PROXY=1` trusts a tunnel's forwarded address and scheme; `ECOCOMMUTE_SECURE_COOKIES=1` marks cookies secure when the site is served over https.

## Consequences

- **Found while testing:** an empty token on both sides of the form check counted as a match, so a browser with no session could post the log-in form. The check now refuses an empty expected token, and a test covers it.
- The database holds personal data (user names, trips with places). Keep `data/` private, back it up with `python -m src.manage backup`, and ask the course staff whether keeping real people's trips is allowed.
- Anyone who can open the site can try the log-in page; only invite holders can create accounts. The limits slow guessing but do not stop a determined attacker. Use a private network (Tailscale) or a tunnel rather than opening a router port.
- If the computer running it is off, the site is off. A lost disk loses every account unless it was backed up.
- Passwords crossing plain http on a shared network can be read. Use a private network or https for anything beyond one computer.
- The shared tree now counts real accounts; the "126 trips by 41 students" sample data is still added and is still labelled. "Planting a real tree" remains the team's own commitment.
- SPEC.md and model 10.9 do not describe accounts, invites, saved trips or the shared total.
- Tests build their own temporary database; the web tests start from a signed-in client.

## Evidence that would change this decision

- More than a few dozen users, or use from the open internet: a hosted database, email recovery, a CAPTCHA, audit logs.
- Course staff require different handling of personal data.
- A second server is needed: SQLite would give way to a database server.
