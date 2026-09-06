# Desktop Alpha Validation Log

90-day public validation window for the Desktop Alpha release.
**Day 0 = 2026-08-29**（Public Desktop Alpha released）· Window: Day 0 → Day 90.

## Data source & honesty rules

- Metrics come **only from the GitHub public API**. **No Desktop telemetry** is
  added or used (the Desktop app sends no outbound telemetry by design).
- **Download counts are NOT a proxy for real users.** A download may be a bot,
  a mirror, a re-test, or one person downloading twice. "Meaningful external
  users" is assessed separately from qualitative signals (Issues / PRs /
  Discussions / direct contact).
- Threshold reference: [DESKTOP_ALPHA_90_DAY_VALIDATION.md](../product/DESKTOP_ALPHA_90_DAY_VALIDATION.md)
  - **Minimum signal**: ≥25 Desktop downloads · ≥5 external users with meaningful interaction · ≥3 substantive Issue/Discussion threads
  - **Strong signal**: ≥100 Desktop downloads · ≥15 meaningful external users · ≥5 feature/compatibility requests
  - **Platform signal**: repeated requests for ≥1 non-Hermes agent collector

## Metrics

| metric | definition |
|---|---|
| DMG downloads | `Hermes-HUD-Desktop-0.1.0-macOS-arm64.dmg` download_count (release `desktop-v0.1.0-alpha`) |
| Stars | `stargazers_count` |
| Forks | `forks_count` |
| external Issues | issues opened by non-maintainer accounts (PRs excluded) |
| Discussions | discussion count (note: announcement post is maintainer-authored) |
| external PRs | PRs opened by non-maintainer accounts |
| meaningful external users | distinct humans who engaged (Issue/PR/Discussion/contact) beyond a single drive-by action |
| non-Hermes collector requests | requests to use the HUD as a data collector for a non-Hermes agent/system |

## Checkpoints

| checkpoint | date | DMG dl | Stars | Forks | ext Issues | Disc | ext PRs | meaningful users | non-Hermes requests |
|---|---|---|---|---|---|---|---|---|---|
| **Day 0** | 2026-08-29 | **2** | **1** | **1** | **0** | **1**（公告帖 #16，maintainer） | **1**（PR #4 mariopablobarron） | **0** | **0** |
| **Day 7** | 2026-09-05 | **2** | **4** | **1** | **0** | **2**（#16 公告 + #18 v1.1.1 发布帖，均 maintainer） | **1**（PR #4 mariopablobarron） | **0** | **0** |
| Day 30 | 2026-09-28 | — | — | — | — | — | — | — | — |
| Day 60 | 2026-10-28 | — | — | — | — | — | — | — | — |
| Day 90 | 2026-11-27 | — | — | — | — | — | — | — | — |

> Day 0 baseline captured live from GitHub API on 2026-08-29 (not hand-filled).
> Day 7 values re-read live from GitHub API on 2026-09-06 immediately before commit（closeout executed 2026-09-06; Day 7 window date = 2026-09-05）.

## Day 7 review — decision（2026-09-06 closeout）

**Decision**

- P0 product defects: **0**
- P1 product defects: **0**
- One P1 candidate was investigated during the window and **closed as local stale-installation state** — NOT an external Desktop product defect; no product code shipped for it. Recorded only as:

  `P1 candidate → investigated → local environment → remediated → CLOSED`

- Desktop 0.1.1: **NO-GO**
- HUD v1.1.3: **NO-GO**
- Next priority: **Distribution + Observation**
- Show HN: **UNBLOCKED**
- Next formal checkpoint: **Day 30 — 2026-09-28**

**Strict evidence notes**

- **Meaningful external users = 0.** The only external human signal is mariopablobarron's
  merged PR #4 (2026-08-29, +119/−2 functional fix) — counted under external PRs = 1. He is
  NOT counted as a meaningful user: his entire repo engagement is that single PR, with zero
  issues / comments / discussion / review interaction (API-verified 2026-09-06), which does not
  clear the "beyond a single drive-by action" bar — consistent with the Day 0 baseline, where
  the same author's open PR also counted 0. Download counts are not user evidence.
- **Non-Hermes collector requests = 0** — no public evidence exists.
- Week-1 trend: stars 1→4 · forks 1 · external issues 0 · discussions 2（均 maintainer 帖）·
  external PRs 1（merged）. Minimum-signal thresholds（≥25 dl / ≥5 meaningful users / ≥3
  threads）not approached — no action beyond Distribution + Observation.

## Issue triage policy

| priority | definition | action |
|---|---|---|
| **P0** | security / data corruption / cannot launch | **immediate triage** (same-day, highest urgency) |
| **P1** | install failure / connect failure / core feature incorrect | evaluate for **0.1.1** (next patch window) |
| **P2** | UX / feature request / enhancement | collect until **Day 7 review** |

Rules:
- P0 → immediate triage, no batching.
- P1 → evaluate for 0.1.1 (Desktop patch) at the next release gate.
- P2 → batch and review at the Day 7 Product Review.
- No new Desktop feature development starts before the Day 7 review
  (Post-Launch Operations v1 scope).

## How to update

Daily: a cron agent (`hud-release-metrics`) reads the GitHub public API and
posts the daily summary to Telegram — the log itself is updated at each
checkpoint (Day 7 / 30 / 60 / 90) via a normal repo PR.
