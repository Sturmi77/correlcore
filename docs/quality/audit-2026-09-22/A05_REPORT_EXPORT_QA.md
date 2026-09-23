# A05 report export QA

This note records the implementation evidence and the remaining release-candidate checks for
[#989](https://github.com/Sturmi77/correlcore/issues/989).

## Shared report contract

`InsightReportRow` is the only row contract consumed by the on-screen table and the PDF, PNG,
CSV, and JSON renderers. It carries the selected row id, factor, metric, effect, confidence,
with/without group sizes, total sample, tier, actual analysis-window boundaries, generation date,
and statement. Missing optional values remain `null` in the model and JSON, empty in CSV, and are
shown with the localized missing-value label in visual formats.

The backend adds `analysis_window_start` and `analysis_window_end` from the first and last daily
entry actually used by the insight run. Consumers do not infer a window from the generation date
or sample count.

## CSV formula protection

CSV columns have an explicit text or numeric type. Text is prefixed with an apostrophe when its
first character after ASCII whitespace or control bytes is `=`, `+`, `-`, or `@`. CSV quoting and
quote doubling run afterwards as a separate step. Numeric cells are emitted as unquoted decimal
values, so negative effects and other numbers remain usable for calculations.

The protection applies to the report CSV download. JSON, PDF, and PNG are not interpreted as
spreadsheet formulas. The prefix is a defense for common spreadsheet import behavior; it is not a
general sanitizer for arbitrary downstream programs that intentionally remove the prefix or
transform cell contents before evaluation. A recipient should still import the file as UTF-8 and
keep external links/macros disabled for files from untrusted sources.

Automated coverage includes `=1+1`, `+`, `-`, `@`, leading tab/CR/LF, quotes, commas, semicolons,
and a negative numeric effect through the real `exportReportCsv` download path.

## Automated evidence

- `vitest`: 44 focused report/export tests passed.
- `svelte-check`: 0 errors and 0 warnings.
- `eslint`: changed web files passed.
- `ruff`: changed backend files passed.
- `pytest`: the analysis-window regression assertion passed.

## Final release-candidate checks

Run these checks against the final RC build and attach screenshots/files to the issue before it is
closed:

- Open the harmless CSV fixture in the supported spreadsheet applications. Confirm every formula
  probe stays text and numeric effect/sample cells can still be summed.
- Exercise anonymous login return with a selected signal, invalid or stale signal, initial load
  failure, refresh failure, and explicit deselection in a real browser.
- Export 5 and 95 selected groups in all four formats and compare row ids plus evidence values.
- Inspect multi-page PDF and tall PNG output with long names, umlauts, and missing values for
  clipping, dropped groups, or unreadable characters.
