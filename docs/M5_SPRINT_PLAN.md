# M5 Sprint Plan - Habits Core ohne Gamification

Last updated: 2026-05-28

M5 delivers goal-based habit tracking without engagement loops. The canonical
scope follows `DESIGN_DOCUMENT.md` and GitHub issues #157/#159. The previous
Tag Co-Occurrence Heatmap note is moved to M5.1/backlog.

## Overview

| Sprint | Title                   | Exit                                               |
| ------ | ----------------------- | -------------------------------------------------- |
| 0      | Scope & Docs            | M5 scope fixed; co-occurrence rescoped             |
| 1      | Backend Habit Contracts | Habit tag fields exposed; stats endpoints live     |
| 2      | Habit Configuration UI  | Settings > Tags can configure build/reduce habits  |
| 3      | Trends Habits Tab       | `/trends` shows habit list and detail              |
| 4      | No-Gamification Polish  | Neutral EN/DE copy and responsive QA               |
| 5      | Closeout                | Tests, docs, changelog and GitHub closure complete |

## Scope

- `tags.habit_type` and `tags.target_frequency` are existing schema fields and
  are activated through API/UI only.
- Adherence is goal-based: `build` measures progress toward weekly target days;
  `reduce` measures whether tracked days stay within the configured target
  range.
- Correlation contribution is read-only from existing M3 insights and may be
  `null`.
- No streak counters, badges, points, rewards, urgency copy or guilt framing.

## Out of Scope

- Pause mode, habit reminders and habit notification flows.
- New analytics engine work.
- Tag Co-Occurrence Heatmap, now tracked as M5.1/backlog quick win.
