# Insight state migration (#978)

## Layouts

Version 1 is the eight-section, all-enabled template in
`LEGACY_DEFAULT_INSIGHT_SECTIONS`. Only a stored array with those eight keys in
that exact order and with those exact flags is converted to the version 2
template. A reordered section or changed flag makes the layout customized;
all explicit known keys keep their order and flags. Missing known keys are
appended in version 2 default order with version 2 flags. Unknown keys and
invalid entries are discarded and cannot make a stored array count as the
exact version 1 template. A null or empty value uses version 2 defaults.
The migration is one-time: version 2 reads do not repeat the transform.

The Python and TypeScript implementations consume the same cases from
`tests/fixtures/insight_sections_migration.json`.

Version 2 rows that were already changed by the previous migration have no
provenance marker for which enabled flags were intentional. The live JSON
cannot reconstruct the earlier choice. The user can restore sections in
Insights settings. If an operator needs a historical comparison, the database
backup procedure in `docs/selfhost/INSTALL.md` can be used on a separate
restore environment to inspect an older `user_preferences.insight_sections`
value. Do not copy a guessed layout over the live row.

## Dismissals

Migration 055 rewrites known persisted formats to the same canonical key used
on reads and writes: older changepoint labels become the metric's series key;
`null_association` and `pointbiserial` share the tag association identity;
older per-lag keys become pair keys. The metric, series, tag subject, and user
remain part of the identity. Unknown key shapes are left opaque. When keys
collide for one user, the row with the latest `dismissed_at` survives, with a
stable ID tie break. The migration is idempotent; the read path also
canonicalizes keys during rollout so old rows remain hidden before the schema
upgrade completes. Removing a dismissal clears every equivalent key for that
user, including a legacy collision.
