import type { InsightResponse } from '$lib/api/insights';

type Translate = (key: string, options?: { values?: Record<string, string | number> }) => string;

function count(value: unknown): number | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null;
}

/** Use persisted counts, including for older rows whose stored sentence mentions lift. */
export function formatSymptomTagStatement(insight: InsightResponse, t: Translate): string | null {
  if (insight.insight_type !== 'symptom_tag_cooccurrence') return null;
  const payload = insight.payload ?? {};
  const together = count(payload.co_count);
  const symptomDays = count(payload.symptom_count);
  const tagDays = count(payload.tag_count);
  const symptom =
    typeof payload.symptom_name === 'string' ? payload.symptom_name : (insight.subject_label ?? '');
  const tag = typeof payload.tag_name === 'string' ? payload.tag_name : '';
  if (
    together === null ||
    symptomDays === null ||
    tagDays === null ||
    together > symptomDays ||
    together > tagDays ||
    symptomDays === 0 ||
    !symptom ||
    !tag
  )
    return t('insights.symptoms.cooccurrence_insufficient');
  return t('insights.symptoms.cooccurrence_statement', {
    values: { symptom, tag, together, symptomDays, tagDays },
  });
}
